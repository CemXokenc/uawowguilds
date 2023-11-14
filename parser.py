import aiohttp
import asyncio
import json
from uaguildlist import url_list
import time

async def fetch_data(session, url):
    async with session.get(url) as response:
        return await response.json()

async def process_player(session, realm, name, data_list):
    # Construct the URL for player data
    url = f"http://raider.io/api/v1/characters/profile?region=eu&realm={realm}&name={name}&fields=mythic_plus_scores_by_season:current"
    player_data = await fetch_data(session, url)

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

        # Update the corresponding player record in data_list with RIO scores
        for player in data_list:
            if player['name'] == name and player['realm'] == realm:
                player['rio_all'] = all_score
                player['rio_dps'] = dps_score
                player['rio_healer'] = healer_score
                player['rio_tank'] = tank_score
                player['spec_0'] = spec_0
                player['spec_1'] = spec_1
                player['spec_2'] = spec_2
                player['spec_3'] = spec_3

async def process_guild(session, url, data_list):
    guild_data = await fetch_data(session, url)

    if 'realm' in guild_data:
        realm = guild_data['realm']
        guild = guild_data['name']

        for member in guild_data.get('members', []):
            name = member.get('character', {}).get('name')
            class_ = member.get('character', {}).get('class')

            if name and class_:
                # Add guild member's data to data_list
                data_list.append({'realm': realm, 'guild': guild, 'name': name, 'class': class_})

async def main():
    data_list = []
    prefix = "http://raider.io/api/v1/guilds/profile?region=eu&"
    postfix = "&fields=members"

    async with aiohttp.ClientSession() as session:
        for url in url_list:
            await process_guild(session, prefix + url + postfix, data_list)
            await asyncio.sleep(1)  # Introduce a 1-second delay between guild requests

        # Fetch RIO data for each player
        for player in data_list:
            await process_player(session, player['realm'], player['name'], data_list)

    # Clear the file before writing
    with open('members.json', 'w', encoding='utf-8') as file:
        file.write("[]")

    # Write data to the JSON file
    with open('members.json', 'w', encoding='utf-8') as file:
        json.dump(data_list, file, ensure_ascii=False, indent=2)

# Measure execution time
start_time = time.time()

# Call the asynchronous function
asyncio.run(main())

# Display information about the execution time
end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time: {execution_time} seconds")
