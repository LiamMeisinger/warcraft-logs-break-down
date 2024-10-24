from flask import Flask, jsonify, render_template_string
import requests
from requests.auth import HTTPBasicAuth


def load_secrets(file_path="secrets.txt"):
    secrets = {}
    with open(file_path, "r") as file:
        for line in file:
            key, value = line.strip().split("=", 1)
            secrets[key] = value
    return secrets


secrets = load_secrets()
print(secrets)
client_id = secrets["CLIENT_ID"]
token_url = secrets["TOKEN_URL"]
client_secret = secrets["CLIENT_SECRET"]
access_token = None


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management
raid_data_json = None


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
    global raid_data_json

    if access_token is None:
        return "Access token not available. Please visit the home page to fetch the token."

    # Prepare headers with the access token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Example GraphQL query to fetch raid data (replace "your_report_id")
    query = """
        {
          reportData {
            report(code: "Twgb46h8aJq7RtPz") {
              fights {
                id
                name
              }
              damageTable: table(dataType: DamageDone, fightIDs: [2])
              healingTable: table(dataType: Healing, fightIDs: [2])
            }
          }
        }
        """

    # Make the POST request to the Warcraft Logs API
    response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers, json={'query': query})

    if response.status_code == 200:
        # Successfully received the data
        raid_data_json = response.json()
        return '''
        <h1>Let's get Into it</h1>
        <h2>The following data has been retrieved from Warcraft Logs</h2>
        <a href="/raid-damage"><button>View Damage Breakdown</button></a>
    '''
    else:
        # Handle errors
        return f"Error fetching raid data: {response.status_code} - {response.text}"


@app.route('/home')
def home():
    # Render a simple home page with a button to view damage breakdown
    return '''
        <h1>Welcome to the BISLogDiver</h1>
        <h2>The following data has been retrieved from Warcraft Logs</h2>
        <a href="/raid-data"><button>Retrieve Data</button></a>
    '''


@app.route('/raid-damage')
def raid_damage():
    global raid_data_json
    # Extract the entries for each player from the JSON
    entries = raid_data_json['data']['reportData']['report']['damageTable']['data']['entries']

    # Create HTML string to display damage breakdown
    damage_breakdown = "<h1>Raid Damage Breakdown</h1>"

    for entry in entries:
        damage_breakdown += f"<h2>{entry['name']} ({entry['type']}) - Total Damage: {entry['total']}</h2>"

        # Abilities breakdown
        damage_breakdown += "<h3>Abilities:</h3><ul>"
        for ability in entry["abilities"]:
            damage_breakdown += f"<li>{ability['name']}: {ability['total']} damage</li>"
        damage_breakdown += "</ul>"

        # Targets breakdown
        damage_breakdown += "<h3>Targets:</h3><ul>"
        for target in entry["targets"]:
            damage_breakdown += f"<li>{target['name']}: {target['total']} damage</li>"
        damage_breakdown += "</ul>"

    damage_breakdown += '<a href="/"><button>Home</button></a>'

    # Render the result as HTML
    return render_template_string(damage_breakdown)


if __name__ == '__main__':
    app.run(port=8000)
