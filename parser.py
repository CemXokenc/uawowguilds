import aiohttp
import asyncio
import json
import time
from datetime import datetime

error_urls = []  # List to store URLs that returned errors during requests

# Function to read guild data from the file
def read_guild_data(file_path=r'C:\Users\Administrator\Desktop\uaguildlist.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            return [line.strip() for line in lines]
    except Exception as e:
        print(f"An error occurred while reading guild data: {e}")
        return []

# Asynchronous function to fetch data from a given URL
async def fetch_data(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        error_urls.append(url)
        return None
        
# Asynchronous function to process a player and fetch their RIO data
async def process_player(session, realm, name, data_dict):
    # Construct the URL for player data
    url = f"http://raider.io/api/v1/characters/profile?region=eu&realm={realm}&name={name}&fields=mythic_plus_scores_by_season:current"
    player_data = await fetch_data(session, url)

    if player_data is not None:
        # Handle status 400 (bad request) by logging the player's name and realm
        if 'statusCode' in player_data and player_data['statusCode'] == 400:
            with open("400.txt", "a", encoding="utf-8") as error_file:
                error_file.write(f"Character not found: {name} from realm {realm}\n")
            return

        # If Mythic+ score data exists, extract scores
        if 'mythic_plus_scores_by_season' in player_data:
            scores = player_data['mythic_plus_scores_by_season'][0]['scores']
            all_score = scores.get('all', 0)
            dps_score = scores.get('dps', 0)
            healer_score = scores.get('healer', 0)
            tank_score = scores.get('tank', 0)
            spec_0 = scores.get('spec_0', 0)
            spec_1 = scores.get('spec_1', 0)
            spec_2 = scores.get('spec_2', 0)
            spec_3 = scores.get('spec_3', 0)

            # Update the corresponding player record in data_dict with RIO scores
            player_key = (realm, name)
            if player_key in data_dict:
                player = data_dict[player_key]
                player['rio_all'] = all_score
                player['rio_dps'] = dps_score
                player['rio_healer'] = healer_score
                player['rio_tank'] = tank_score
                player['spec_0'] = spec_0
                player['spec_1'] = spec_1
                player['spec_2'] = spec_2
                player['spec_3'] = spec_3
            else:
                print(player_key)
        else:
            print(f"No M+ data for: {name} from realm {realm}")

# Asynchronous function to process a guild and fetch its members
async def process_guild(session, url, data_dict):
    guild_data = await fetch_data(session, url)

    # Check if the guild data contains a list of members
    if 'members' in guild_data:
        for member in guild_data.get('members', []):
            # Get player-specific realm and guild information
            realm = member.get('character', {}).get('realm')  # Get player's realm
            guild = guild_data['name']  # Guild name
            name = member.get('character', {}).get('name')
            class_ = member.get('character', {}).get('class')
            active_spec_name = member.get('character', {}).get('active_spec_name')

            if name and class_:
                # Add guild member's data to data_dict
                player_key = (realm, name)  # Use player's realm, not guild's realm
                data_dict[player_key] = {'realm': realm, 'guild': guild, 'name': name, 'class': class_, 'active_spec_name': active_spec_name}

# Main function to coordinate fetching and processing data
async def main():
    # Clear the error log file before starting
    with open("400.txt", "w", encoding="utf-8") as error_file:
        error_file.write("")

    data_dict = {}  # Dictionary to store player data
    prefix = "http://raider.io/api/v1/guilds/profile?region=eu&"
    postfix = "&fields=members"

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        url_list = read_guild_data()
        request_count = 0  # Counter for the number of requests

        # Process each guild in the URL list
        for url in url_list:
            await process_guild(session, prefix + url + postfix, data_dict)

        # Fetch RIO data for each player
        for player_key in data_dict.keys():
            realm, name = player_key
            await process_player(session, realm, name, data_dict)
            request_count += 1
            
            # Pause after every 190 requests to avoid being rate-limited
            if request_count % 190 == 0:                
                await asyncio.sleep(2 * 60)  # Pause for 2 minutes
        
        # Retry failed URLs (if needed)
        for url in error_urls:
            await process_guild(session, prefix + url + postfix, data_dict)

    # Clear the JSON file before writing new data    
    with open(r'C:\Users\Administrator\Desktop\members.json', 'w', encoding='utf-8') as file:
        file.write("[]")

    # Write player data to the JSON file
    with open(r'C:\Users\Administrator\Desktop\members.json', 'w', encoding='utf-8') as file:
        json.dump(list(data_dict.values()), file, ensure_ascii=False, indent=2)

# Measure the execution time
start_time = time.time()

# Call the asynchronous function
asyncio.run(main())

# Display information about the execution time
end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time: {execution_time} seconds")
