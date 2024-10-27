from flask import Flask, jsonify, render_template_string, render_template, request
import requests
from requests.auth import HTTPBasicAuth
import time
from bosses import bosses


def load_secrets(file_path="secrets.txt"):
    secrets = {}
    with open(file_path, "r") as file:
        for line in file:
            key, value = line.strip().split("=", 1)
            secrets[key] = value
    return secrets


secrets = load_secrets()
client_id = secrets["CLIENT_ID"]
token_url = secrets["TOKEN_URL"]
client_secret = secrets["CLIENT_SECRET"]
access_token = None

app = Flask(__name__)
raid_data_json = None
raid_data_cache = None
last_fetched = 0
raid_code = ""


def is_cache_valid():
    # Cache expires after 10 minutes
    return time.time() - last_fetched < 6000  # 6000 seconds = 100 minutes


# Step 1: Request access token using client credentials flow
@app.route('/')
def index():
    global access_token  # Declare the global token variable

    # Prepare the POST request to fetch the access token
    try:
        response = requests.post(
            token_url,
            data={'grant_type': 'client_credentials'},  # Required form data
            auth=HTTPBasicAuth(client_id, client_secret)  # Basic Auth using client_id and client_secret
        )

        # Check if request was successful
        if response.status_code == 200:
            token = response.json()
            access_token = token['access_token']  # Store the token in the global variable

            return render_template('index.html')

        else:
            return f"Error fetching token: {response.status_code} - {response.text}"

    except Exception as e:
        return f"An error occurred: {str(e)}"


# Example route that will use the stored access token
@app.route('/raid-data', methods=['GET', 'POST'])
def raid_data():
    global access_token  # Access the global token
    global raid_data_cache, last_fetched

    if request.method == 'POST':
        raid_code = request.form['raidCode']  # Get the raid code from the form input

        # Prepare headers with the access token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Insert the raid_code dynamically into the GraphQL query
        query = f"""
            {{
              reportData {{
                report(code: "{raid_code}") {{
                  fights {{
                    id
                    name
                  }}
                  damageTable: table(dataType: DamageDone, fightIDs: [31])
                  healingTable: table(dataType: Healing, fightIDs: [31])
                }}
              }}
            }}
        """

        # Make the POST request to the Warcraft Logs API
        response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers, json={'query': query})

        if response.status_code == 200:
            # Successfully received data, so cache it and update timestamp
            raid_data_cache = response.json()
            last_fetched = time.time()
            fights = raid_data_cache['data']['reportData']['report']['fights']

            # Dictionary to store the highest ID for each unique name
            unique_fights = {}
            for fight in fights:
                name = fight['name']
                id = fight['id']

                if name in bosses:
                    if name not in unique_fights or id > unique_fights[name]['id']:
                        unique_fights[name] = fight

            # Convert the dictionary back to a list of fights
            unique_fights_list = list(unique_fights.values())
            return render_template('home.html', fights=unique_fights_list)

        else:
            # Handle errors if API call fails
            error_message = f"Error fetching raid data: {response.status_code} - {response.text}"
            return render_template('home.html', error=error_message)

    if is_cache_valid() and raid_data_cache is not None:
        fights = raid_data_cache['data']['reportData']['report']['fights']

        unique_fights = {}
        for fight in fights:
            name = fight['name']
            id = fight['id']

            if name in bosses:
                if name not in unique_fights or id > unique_fights[name]['id']:
                    unique_fights[name] = fight

        unique_fights_list = list(unique_fights.values())
        return render_template('home.html', fights=unique_fights_list)

    # If GET request and no cache available, prompt user to enter a raid code
    return render_template('home.html', error="Please enter a raid code.")


@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/raid-damage')
def raid_damage():
    global raid_data_cache

    if not is_cache_valid() or raid_data_cache is None:
        return "No data available. Please retrieve the raid data first.", 404

    # Extract the damage data
    entries = raid_data_cache['data']['reportData']['report']['damageTable']['data']['entries']

    # Render the raid_damage.html template and pass the entries data
    return render_template('raid_damage.html', entries=entries)


@app.route('/raid-healing')
def raid_healing():
    global raid_data_cache

    if not is_cache_valid() or raid_data_cache is None:
        return "No data available. Please retrieve the raid data first.", 404

    # Extract the damage data
    entries = raid_data_cache['data']['reportData']['report']['healingTable']['data']['entries']

    # Render the raid_damage.html template and pass the entries data
    return render_template('raid_healing.html', entries=entries)


@app.route('/json-data')
def json_data():
    global raid_data_cache

    if not is_cache_valid() or raid_data_cache is None:
        return "No data available. Please retrieve the raid data first.", 404

    # Return the cached data as a JSON response
    return jsonify(raid_data_cache)


@app.route('/gear-check')
def raid_gear():
    global raid_data_cache

    if not is_cache_valid() or raid_data_cache is None:
        return "No data available. Please retrieve the raid data first.", 404

    # Extract gear data from the cached JSON
    entries = raid_data_cache['data']['reportData']['report']['damageTable']['data']['entries']

    # Render the raid_gear.html template and pass the entries data
    return render_template('raid_gear.html', entries=entries)


if __name__ == '__main__':
    app.run(port=8000)


"""TODO
1. Migrate Healing and dmg to ID encounter
2. Cache raid Data on /home directory
"""
