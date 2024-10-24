from flask import Flask, jsonify, render_template_string
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
app.secret_key = 'your_secret_key'  # Needed for session management
raid_data_json = None
raid_data_cache = None
last_fetched = 0


def is_cache_valid():
    # Cache expires after 10 minutes
    return time.time() - last_fetched < 600  # 600 seconds = 10 minutes


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

            # Render HTML with Home button and token
            html_content = f'''
                <h1>Access Token Retrieved</h1>
                <p>Please Head to the Home Page</p>
                <a href="/home"><button>Home</button></a>
            '''
            return render_template_string(html_content)

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
        return '''
           <h1>Let's get Into it</h1>
           <h2>The following data has been retrieved from Warcraft Logs</h2>
           <a href="/raid-damage"><button>View Damage Breakdown</button></a>
           <a href="/raid-healing"><button>View Healing Breakdown</button></a>
           <a href="/gear-check"><button>View Gear Breakdown</button></a>
           <a href="/json-data"><button>Raw Data</button></a>
       '''
    else:
        # Handle errors
        return f"Error fetching raid data: {response.status_code} - {response.text}"


@app.route('/home')
def home():
    return '''
        <h1>Welcome to the BISLogDiver</h1>
        <h2>The following data has been retrieved from Warcraft Logs</h2>
        <a href="/raid-data"><button>Retrieve Data</button></a>
    '''


@app.route('/raid-damage')
def raid_damage():
    global raid_data_cache

    # Check if cached data is valid
    if not is_cache_valid() or raid_data_cache is None:
        return '''
        <h1>Data not available</h1>
        <p>Please retrieve fresh data from the /raid-data route.</p>
        <a href="/home"><button>Home</button></a>
        '''

    # Extract the entries for each player from the cached JSON
    entries = raid_data_cache['data']['reportData']['report']['damageTable']['data']['entries']

    # Create HTML string to display damage breakdown
    damage_breakdown = "<h1>Raid Damage Breakdown</h1>"

    for entry in entries:
        damage_breakdown += (f"<h2>{entry['name']} ({entry['type']})"
                             f"\nTotal Damage: {entry['total']}</h2>")
        # Targets breakdown
        damage_breakdown += "<h3>Targets:</h3><ul>"
        for target in entry["targets"]:
            damage_breakdown += f"<li>{target['name']}: {target['total']} damage</li>"
        damage_breakdown += "</ul>"

        # Abilities breakdown
        damage_breakdown += "<h3>Abilities:</h3><ul>"
        for ability in entry["abilities"]:
            damage_breakdown += f"<li>{ability['name']}: {ability['total']} damage</li>"
        damage_breakdown += "</ul>"

    damage_breakdown += '<a href="/home"><button>Home</button></a>'

    # Render the result as HTML
    return render_template_string(damage_breakdown)


@app.route('/raid-healing')
def raid_healing():
    global raid_data_cache

    # Check if cached data is valid
    if not is_cache_valid() or raid_data_cache is None:
        return '''
           <h1>Data not available</h1>
           <p>Please retrieve fresh data from the /raid-data route.</p>
           <a href="/home"><button>Home</button></a>
           '''
    # Extract the entries for each player from the JSON
    entries = raid_data_cache['data']['reportData']['report']['healingTable']['data']['entries']

    # Create HTML string to display damage breakdown
    healing_breakdown = "<h1>Raid Healing Breakdown</h1>"

    for entry in entries:
        healing_breakdown += (f"<h2>{entry['name']} ({entry['type']})"
                              f"\nTotal Healing: {entry['total']}</h2>")

        # Targets breakdown
        healing_breakdown += "<h3>Targets:</h3><ul>"
        for target in entry["targets"]:
            healing_breakdown += f"<li>{target['name']}: {target['total']} healing</li>"
        healing_breakdown += "</ul>"

        # Abilities breakdown
        healing_breakdown += "<h3>Abilities:</h3><ul>"
        for ability in entry["abilities"]:
            healing_breakdown += f"<li>{ability['name']}: {ability['total']} healing</li>"
        healing_breakdown += "</ul>"

    healing_breakdown += '<a href="/home"><button>Home</button></a>'

    # Render the result as HTML
    return render_template_string(healing_breakdown)


@app.route('/json-data')
def json_data():
    global raid_data_cache

    if not is_cache_valid() or raid_data_cache is None:
        return "No data available. Please retrieve the raid data first.", 404

    # Return the cached data as a JSON response
    return jsonify(raid_data_cache)


@app.route('/gear-check')
def gear_check():
    global raid_data_cache
    if not is_cache_valid() or raid_data_cache is None:
        return "No data available. Please retrieve the raid data first.", 404

    # Extract the entries for each player from the JSON
    entries = raid_data_cache['data']['reportData']['report']['damageTable']['data']['entries']

    gear_breakdown = "<h1>Gear Breakdown</h1>"

    for entry in entries:
        gear_breakdown += f"<h2>Player: {entry['name']}</h2>"
        gear_breakdown += "<ul>"
        for item in entry.get('gear', []):
            item_name = item.get('name', 'Unknown Item')
            item_level = item.get('itemLevel', 'Unknown Level')
            enchant_name = item.get('permanentEnchantName', 'No Enchant')

            if item_level == 0:
                continue

            gear_breakdown += f"<li>{item_name} - Item Level: {item_level} - Enchant: {enchant_name}</li>"
        gear_breakdown += "</ul>"

    gear_breakdown += '<a href="/home"><button>Home</button></a>'

    # Render the result as HTML
    return render_template_string(gear_breakdown)


if __name__ == '__main__':
    app.run(port=8000)
