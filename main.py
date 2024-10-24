from flask import Flask, jsonify, render_template_string, render_template
import requests
from requests.auth import HTTPBasicAuth
import time


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
@app.route('/raid-data')
def raid_data():
    global access_token  # Access the global token
    # global raid_data_json
    global raid_data_cache, last_fetched

    if is_cache_valid() and raid_data_cache is not None:
        # Use cached data if available and valid
        return '''
            <h1>Cached Raid Data</h1>
            <a href="/raid-damage"><button>View Damage Breakdown</button></a>
            <a href="/raid-healing"><button>View Healing Breakdown</button></a>
            '''

    # Prepare headers with the access token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    query = """
        {
          reportData {
            report(code: "7F1JBDwbL8VyNG4Y") {
              fights {
                id
                name
              }
              damageTable: table(dataType: DamageDone, fightIDs: [14])
              healingTable: table(dataType: Healing, fightIDs: [14])
            }
          }
        }
        """

    # Make the POST request to the Warcraft Logs API
    response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers, json={'query': query})

    if response.status_code == 200:
        raid_data_cache = response.json()
        last_fetched = time.time()
        return render_template('home.html')
    else:
        # Handle errors
        return f"Error fetching raid data: {response.status_code} - {response.text}"


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
