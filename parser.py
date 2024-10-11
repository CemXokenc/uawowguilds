import aiohttp
import asyncio
import json
import time
from datetime import datetime

error_urls = []

# Function to read guild data from the file
def read_guild_data(file_path=r'C:\Users\Administrator\Desktop\uaguildlist.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            return [line.strip() for line in lines]
    except Exception as e:
        print(f"An error occurred while reading guild data: {e}")
        return []

async def fetch_data(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        error_urls.append(url)
        return None

async def process_player(session, realm, name, player):
    # Construct the URL for player data
    url = f"http://raider.io/api/v1/characters/profile?region=eu&realm={realm}&name={name}&fields=mythic_plus_scores_by_season:current"
    player_data = await fetch_data(session, url)

    if player_data is not None:
        # If the status is 400 (request error), write the nickname and server to the file
        if 'statusCode' in player_data and player_data['statusCode'] == 400:
            with open("400.txt", "a", encoding="utf-8") as error_file:
                error_file.write(f"Character not found: {name} from realm {realm}\n")
            return

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

            # Update the corresponding player record with RIO scores
            player['rio_all'] = all_score
            player['rio_dps'] = dps_score
            player['rio_healer'] = healer_score
            player['rio_tank'] = tank_score
            player['spec_0'] = spec_0
            player['spec_1'] = spec_1
            player['spec_2'] = spec_2
            player['spec_3'] = spec_3
        else:
            print(f"No M+ data for: {name} from realm {realm}")

async def process_guild(session, url, data_dict):
    guild_data = await fetch_data(session, url)

    if 'realm' in guild_data:
        realm = guild_data['realm']
        guild = guild_data['name']

        for member in guild_data.get('members', []):
            name = member.get('character', {}).get('name')
            class_ = member.get('character', {}).get('class')
            active_spec_name = member.get('character', {}).get('active_spec_name')

            if name and class_:
                # We create a unique key: name and server as a key
                player_key = f"{name}_{realm}"

                # If the player already exists, we add it as a new entry to the list
                if player_key in data_dict:
                    data_dict[player_key].append({
                        'realm': realm,
                        'guild': guild,
                        'name': name,
                        'class': class_,
                        'active_spec_name': active_spec_name
                    })
                else:
                    data_dict[player_key] = [{
                        'realm': realm,
                        'guild': guild,
                        'name': name,
                        'class': class_,
                        'active_spec_name': active_spec_name
                    }]

async def main():
    # Clean the file before starting work
    with open("400.txt", "w", encoding="utf-8") as error_file:
        error_file.write("")

    data_dict = {}
    prefix = "http://raider.io/api/v1/guilds/profile?region=eu&"
    postfix = "&fields=members"

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        url_list = read_guild_data()
        request_count = 0  # Request counter

        for url in url_list:
            await process_guild(session, prefix + url + postfix, data_dict)

        # Fetch RIO data for each player
        for player_list in data_dict.values():
            for player in player_list:
                realm, name = player['realm'], player['name']
                await process_player(session, realm, name, player)
                request_count += 1

                # Delay after every 190 requests
                if request_count % 190 == 0:
                    await asyncio.sleep(2 * 60)
        
        # Reprocess invalid URLs
        for url in error_urls:
            await process_guild(session, prefix + url + postfix, data_dict)

    # Clear the file before writing    
    with open(r'C:\Users\Administrator\Desktop\members.json', 'w', encoding='utf-8') as file:
        file.write("[]")

    # Write the data to a JSON file
    with open(r'C:\Users\Administrator\Desktop\members.json', 'w', encoding='utf-8') as file:
        json.dump([player for sublist in data_dict.values() for player in sublist], file, ensure_ascii=False, indent=2)

# Measure execution time
start_time = time.time()

# Call the asynchronous function
asyncio.run(main())

# We display information about the execution time
end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time: {execution_time} seconds")
