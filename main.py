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
raider_ids = []


def is_cache_valid():
    # Cache expires after 100 minutes
    return time.time() - last_fetched < 6000  # 6000 seconds = 100 minutes


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


@app.route('/raid-data', methods=['GET', 'POST'])
def raid_data():
    global access_token, raid_data_cache, last_fetched, raid_code, raider_ids

    if request.method == 'POST':
        raid_code = request.form['raidCode']

        # Prepare headers with the access token
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Step 1: Get all fight IDs
        query_fights = f"""
            {{
              reportData {{
                report(code: "{raid_code}") {{
                  fights(killType:Kills) {{
                    id
                    name
                    difficulty
                    friendlyPlayers
                  }}
                }}
              }}
            }}
        """
        response_fights = requests.post(
            'https://www.warcraftlogs.com/api/v2/client',
            headers=headers,
            json={'query': query_fights}
        )

        if response_fights.status_code == 200:
            data = response_fights.json()
            fights = data.get('data', {}).get('reportData', {}).get('report', {}).get('fights', [])

            # Filter to include only boss encounters
            unique_fights = {fight['name']: fight for fight in fights if fight['name'] in bosses}

            fight_ids = [fight['id'] for fight in unique_fights.values()]
            raider_ids = [fight['friendlyPlayers'] for fight in unique_fights.values()][0]
            print(fight_ids)
            print(raider_ids)

            if not fight_ids:
                return render_template('home.html', error="No valid boss encounters found.")

            # Step 2: Fetch damage and healing data
            query = f"""
            {{
              reportData {{
                report(code: "{raid_code}") {{
                  fights {{
                    id
                    name
                  }}
                  damageTable: table(dataType: DamageDone, fightIDs: {fight_ids})
                  healingTable: table(dataType: Healing, fightIDs: {fight_ids})
                }}
              }}
            }}
        """
            response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers,
                                     json={'query': query})

            if response.status_code == 200:
                raid_data_cache = response.json()
                last_fetched = time.time()
                return render_template('home.html', fights=unique_fights.values())

            return render_template('home.html',
                                   error=f"Error fetching raid data: {response.status_code} - {response.text}")

    # Use cached data if available and valid
    if is_cache_valid() and raid_data_cache is not None:
        fights = raid_data_cache['data']['reportData']['report']['fights']
        unique_fights = {fight['name']: fight for fight in fights if fight['name'] in bosses}
        return render_template('home.html', fights=unique_fights.values())

    return render_template('home.html', error="Please enter a raid code.")


@app.route('/home')
def home():
    return render_template('home.html')


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


@app.route('/raid-damage/<int:fight_id>')
def raid_damage(fight_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    query = f"""
                {{
                  reportData {{
                    report(code: "{raid_code}") {{
                      fights {{
                        id
                        name
                      }}
                      damageTable: table(dataType: DamageDone, killType:Kills, fightIDs: [{fight_id}])
                    }}
                  }}
                }}
            """
    response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers,
                             json={'query': query})

    # Parse response data
    if response.status_code != 200 or 'errors' in response.json():
        return "Failed to retrieve data for the specified fight.", 500

    damage_data = response.json()['data']['reportData']['report']['damageTable']['data']['entries']

    # Render template with the filtered data
    return render_template('raid_damage.html', entries=damage_data)


@app.route('/raid-healing/<int:fight_id>')
def raid_healing(fight_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    query = f"""
                {{
                  reportData {{
                    report(code: "{raid_code}") {{
                      fights {{
                        id
                        name
                      }}
                      healingTable: table(dataType: Healing, killType:Kills, fightIDs: [{fight_id}])
                    }}
                  }}
                }}
            """
    response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers,
                             json={'query': query})
    print(response.json())

    # Parse response data
    if response.status_code != 200 or 'errors' in response.json():
        return "Failed to retrieve data for the specified fight.", 500

    healing_data = response.json()['data']['reportData']['report']['healingTable']['data']['entries']

    # Render template with the filtered data
    return render_template('raid_healing.html', entries=healing_data)


@app.route('/raid-buff/<int:fight_id>')
def raid_buff(fight_id):
    global raider_ids

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Dictionary to store buffs grouped by raider ID
    buffs_by_raider = {}

    for raider_id in raider_ids:
        query = f"""
        {{
          reportData {{
            report(code: "{raid_code}") {{
              buffTable: table(dataType: Buffs, fightIDs:[{fight_id}], sourceID:{raider_id}, viewOptions:16)
            }}
          }}
        }}
        """
        response = requests.post('https://www.warcraftlogs.com/api/v2/client', headers=headers, json={'query': query})

        if response.status_code != 200 or 'errors' in response.json():
            return response.json(), 500

        # Parse the response and extract relevant buff data
        auras = response.json()['data']['reportData']['report']['buffTable']['data']['auras']
        buffs = [{"name": aura["name"], "totalUses": aura["totalUses"]} for aura in auras]

        # Add buffs to the dictionary under the raider ID
        buffs_by_raider[raider_id] = buffs

    # Pass the data to the template
    return render_template('raid_buff.html', buffs_by_raider=buffs_by_raider)


if __name__ == '__main__':
    app.run(port=8000)

"""TODO
1. Migrate Healing and dmg to ID encounter
"""
