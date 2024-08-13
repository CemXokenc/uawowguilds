import asyncio
import pandas as pd
import aiohttp
import json
import os
import time
from collections import defaultdict

# Disable SSL certificate verification
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

error_urls = []
sem = asyncio.Semaphore(100)  # Limit concurrent requests

def get_data_array(sheet_url):
    """
    Fetches data from a Google Sheets URL and converts it to a NumPy array.
    """
    df = pd.read_csv(sheet_url, header=None)  # Read the CSV data into a DataFrame
    df = df.iloc[:, [0, 1]]  # Select the first two columns
    array = df.to_numpy()  # Convert DataFrame to NumPy array
    return array

async def fetch_data(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        error_urls.append(url)
        return None

async def process_player(session, realm, name, data_dict):
    """
    Processes player data and updates the data_dict with Mythic+ scores.
    """
    url = f"http://raider.io/api/v1/characters/profile?region=eu&realm={realm}&name={name}&fields=mythic_plus_scores_by_season:current"
    player_data = await fetch_data(session, url)  # Fetch data for the player
    
    if player_data is not None:
        print(f"Received data for {name} on {realm}: {player_data}")
        
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

            player_key = (realm, name)
            player = data_dict[player_key]
            # Update player data with scores
            player.update({
                'rio_all': all_score,
                'rio_dps': dps_score,
                'rio_healer': healer_score,
                'rio_tank': tank_score,
                'spec_0': spec_0,
                'spec_1': spec_1,
                'spec_2': spec_2,
                'spec_3': spec_3
            })
        else:
            print(f"Data for {name} does not contain mythic_plus_scores_by_season: {player_data}")
    else:
        print(f"No data received for {name} on {realm}.")

async def main():
    """
    Main function to fetch and process player data from Google Sheets and Raider.io API.
    """
    sheet_url = "https://docs.google.com/spreadsheets/d/1YdZRWVXzOXaIZfb9YXDfqHEaeaVnv_3j4EykUZ4Kf4E/export?format=csv"
    data_array = get_data_array(sheet_url)  # Get data array from Google Sheets
    print(f"Data array: {data_array}")
    
    data_dict = defaultdict(lambda: {
        'name': None,
        'realm': None,
        'rio_all': 0,
        'rio_dps': 0,
        'rio_healer': 0,
        'rio_tank': 0,
        'spec_0': 0,
        'spec_1': 0,
        'spec_2': 0,
        'spec_3': 0
    })
    
    # Fill data_dict with initial data
    for character_name, realm in data_array:
        data_dict[(realm, character_name)]['name'] = character_name
        data_dict[(realm, character_name)]['realm'] = realm
    
    connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL certificate verification
    async with aiohttp.ClientSession(connector=connector) as session:
        request_count = 0

        for character_name, realm in data_array:
            await process_player(session, realm, character_name, data_dict)
            request_count += 1
            
            if request_count % 300 == 0:
                await asyncio.sleep(1 * 60)

        for url in error_urls:
            await fetch_data(session, url)  # Retry fetching data for URLs with errors

    output_file_path = r'C:\Users\Administrator\Desktop\tournament.json'
    output_dir = os.path.dirname(output_file_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # Create output directory if it does not exist

    if data_dict:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(list(data_dict.values()), file, ensure_ascii=False, indent=2)  # Write data_dict to JSON file
    else:
        print("No data to write.")

start_time = time.time()
asyncio.run(main())  # Run the main function
end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time: {execution_time} seconds")  # Print execution time
