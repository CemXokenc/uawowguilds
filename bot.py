import json
import discord
import aiohttp
import asyncio
import re
from discord import app_commands
from config import token

# Initialize intents and client
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Function to read guild data from the file
def read_guild_data(file_path='uaguildlist.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            return [line.strip() for line in lines]
    except Exception as e:
        print(f"An error occurred while reading guild data: {e}")
        return []

# Asynchronous function to fetch guild data
async def fetch_guild_data(guild_url, tier):
    # Set the prefix and suffix for forming the API request URL
    prefix = "http://raider.io/api/v1/guilds/profile?region=eu&"
    postfix = "&fields=raid_rankings,raid_progression"
    
    # Dictionary to map tier number to raid name
    switch_dict = {
        1: "vault-of-the-incarnates",
        2: "aberrus-the-shadowed-crucible",
        3: "amirdrassil-the-dreams-hope"
    }
    raid = switch_dict.get(tier)
    
    # Asynchronous request to Raider.io API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(prefix + guild_url + postfix) as response:
                json_data = await response.json()

                # Check for required keys in API response
                if 'name' not in json_data or 'realm' not in json_data or 'raid_progression' not in json_data or 'raid_rankings' not in json_data:
                    raise ValueError("Invalid API response format")

                guild_name = json_data['name']
                guild_realm = json_data['realm']
                guild_progress = json_data['raid_progression'][raid]['summary']

                # Set rank 1244 for the guild "Нехай Щастить" and tier 2
                guild_rank = 1244 if guild_name == "Нехай Щастить" and tier == 2 else json_data['raid_rankings'][raid]['mythic']['world']
                return [guild_name, guild_realm, guild_progress, guild_rank]

    except Exception as e:
        print(f"An error occurred while fetching guild data: {e}")
        return None

# Function to print guild ranks
async def print_guild_ranks(interaction, tier):
    try:
        # Asynchronously get data for all guilds of the specified tier
        url_list = read_guild_data()
        guilds = await asyncio.gather(*[fetch_guild_data(guild_url, tier) for guild_url in url_list])
        # Exclude guilds with rank 0
        guilds = [guild for guild in guilds if guild and guild[3] != 0]

        if not guilds:
            await interaction.response.send_message(f"At the moment, there are no guilds with mythic progression in the {tier} season.")
            return

        # Sort guilds by rank
        sorted_guilds = sorted(guilds, key=lambda x: (x[3] or float('inf'), x[0]))
        # Format and send the result
        formatted_guilds = [f"{i + 1}. {', '.join(map(str, guild[:-1]))}, {guild[-1]} rank" for i, guild in enumerate(sorted_guilds)]
        await interaction.response.send_message("\n".join(formatted_guilds))

    except Exception as e:
        print(f"An error occurred while printing guild ranks: {e}")
        await interaction.response.send_message("An error occurred while processing the request. Please try again later.")

# Asynchronous function to get top 3 players for each class based on rio_all
async def get_top3(interaction):
    try:
        # Read data from the JSON file
        with open('members.json', 'r', encoding='utf-8') as file:
            members_data = json.load(file)

        # Checking the existence of data in the file
        if not members_data:
            await interaction.response.send_message("No data to process. Complete the 'members.json' file before using this command.")
            return

        # Group members data by class
        class_groups = {}
        for member in members_data:
            class_name = member['class']
            if class_name not in class_groups:
                class_groups[class_name] = []
            class_groups[class_name].append(member)

        # Get top 3 players for each class based on rio_all
        top3_per_class = {}
        for class_name, class_members in class_groups.items():
            sorted_members = sorted(class_members, key=lambda x: max(x.get('rio_all', 0), 0), reverse=True)
            top3_per_class[class_name] = sorted_members[:3]

        # Format and send the result
        result_message = ""
        for class_name, top3_members in top3_per_class.items():
            result_message += f"\n{class_name}:\n"
            for i, member in enumerate(top3_members):
                result_message += f"{i + 1}. {member['name']} ({member['guild']}) - RIO all: {member['rio_all']}\n"

        await interaction.response.send_message(result_message)

    except Exception as e:
        print(f"An error occurred while processing the /top3 command: {e}")
        await interaction.response.send_message("An error occurred while processing the command. Please try again later.")

# Command to print guilds raid ranks in the current addon
@tree.command(name="guilds", description="Guilds Raid Rank")
@app_commands.describe(
    season="1/2/3"
)
async def get_data(interaction, season: int = 2):
    await print_guild_ranks(interaction, season)

# Command to print player ranks in the current M+ season
@tree.command(name="rank", description="Guilds Mythic+ Rank")
@app_commands.describe(
    top="1-50", 
    guilds="all/Нехай Щастить/... several guilds can be entered through ','.", 
    classes="all/death knight/death knight:3/... ':3' means you want to specify the spec.", 
    role="all/dps/healer/tank", 
    rio="0-3500"
)
async def rank(interaction, top: int = 10, classes: str = "all", guilds: str = "all", role: str = "all", rio: int = 3000):
    try:
        # Read data from the JSON file
        with open('members.json', 'r', encoding='utf-8') as file:
            members_data = json.load(file)

        # Checking the existence of data in the file
        if not members_data:
            await interaction.response.send_message("No data to process. Complete the 'members.json' file before using this command.")
            return

        # Check for valid guild
        if guilds.lower() != "all":
            input_guilds = guilds.split(',')
            if not any(any(member['guild'].lower() == guild.lower() for member in members_data) for guild in input_guilds):
                await interaction.response.send_message(f"At least one of the entered guilds does not exist. Check the spelling. Several guilds can be entered through ','.")
                return
        
        # Check for valid class
        spec_number = 0
        valid_classes = {"all", "death knight", "demon hunter", "druid", "evoker", "hunter", "mage", "monk", "paladin", "priest", "rogue", "shaman", "warlock", "warrior"}
        if ':' in classes.lower():
            # Line separator with a colon
            split_result = classes.split(':')            
            # Checking parts after splitting
            if len(split_result) == 2 and split_result[1].isdigit() and 1 <= int(split_result[1]) <= 4:
                classes = split_result[0]
                spec_number = int(split_result[1])                
                role = "all" # So that there are no conflicts with incorrect input
            else:
                await interaction.response.send_message("Wrong class format. Use the valid format: death knight:3 or warrior:1.")
                return
        else:
            if classes.lower() not in valid_classes:
                await interaction.response.send_message(f"Class '{classes}' does not exist. Use the valid classes: all, death knight, demon hunter, druid, evoker, hunter, mage, monk, paladin, priest, rogue, shaman, warlock, warrior.")
                return        

        # Check for valid role
        valid_roles = {"all", "dps", "healer", "tank"}
        if role.lower() not in valid_roles:
            await interaction.response.send_message(f"Role '{role}' does not exist. Use the valid roles: all, dps, healer, tank or spec name.")
            return

        # Check if top value is within the range of 1 to 20 inclusive
        if not 1 <= top <= 20:
            await interaction.response.send_message("Error: The value of top must be between 1 and 20 inclusive.")
            return
            
        # Check if rio value is within the range of 0 to 3500 inclusive
        if not 0 <= rio <= 3500:
            await interaction.response.send_message("Error: The value of rio must be between 0 and 3500 inclusive.")
            return

        # Filter by guilds
        if guilds.lower() != "all":
            members_data = [member for member in members_data if any(guild.strip().lower() == member['guild'].lower() for guild in input_guilds)]
            
        # Filter by class
        if classes.lower() != "all":
            members_data = [member for member in members_data if member['class'].lower() == classes.lower()]

        # Check whether the specification is entered
        if spec_number == 0:
            # Sort by RIO rating according to the role
            if role.lower() != "all":
                members_data = sorted(members_data, key=lambda x: max(x.get('rio_' + role.lower(), 0), 0), reverse=True)
            else:
                members_data = sorted(members_data, key=lambda x: max(x.get('rio_all', 0), 0), reverse=True)

            # Filter by rio
            members_data = [member for member in members_data if max(member.get('rio_' + role.lower(), 0), 0) > rio]
        else:
            spec = str(spec_number - 1)
            # Sort by RIO rating according to the role
            members_data = sorted(members_data, key=lambda x: max(x.get('spec_' + spec, 0), 0), reverse=True)

            # Filter by rio
            members_data = [member for member in members_data if max(member.get('spec_' + spec, 0), 0) > rio]

        # Limit the number of displayed results
        members_data = members_data[:top]

        # Format header message                
        header_message = f"Top {top} | Classes -> {classes} | Guilds -> {guilds} | Role -> {role} | Rio > {rio}"

        # Format and send the results
        if spec_number == 0:
            result_message = "\n".join([f"{i + 1}. {member['name']} ({member['guild']}, {member['realm']}) - {member['active_spec_name']} {member['class']} - RIO {role}: {member['rio_' + role.lower()]}" for i, member in enumerate(members_data)])
        else:
            result_message = "\n".join([f"{i + 1}. {member['name']} ({member['guild']}, {member['realm']}) - {member['active_spec_name']} {member['class']} - RIO {role}: {member['spec_' + spec]}" for i, member in enumerate(members_data)])
        await interaction.response.send_message(header_message + "\n------------------------------------------------------------\n" + result_message)
        
    except Exception as e:
        print(f"An error occurred while processing the rank command: {e}")
        await interaction.response.send_message("An error occurred while processing the command. Please try again later.")
        
# Command to print top 3 players for each class based on rio_all
@tree.command(name="top3", description="Top 3 Players for Each Class based on RIO all")
async def top3(interaction):
    await get_top3(interaction)
        
# Command "About us"
@tree.command(name="about_us", description="About us")
async def about_us(interaction):    
    await interaction.response.send_message("https://youtu.be/xvpVTd1gt5Q")

# Event handler for bot readiness
@client.event
async def on_ready():
    # Synchronize the command tree    
    await tree.sync()
    print("Ready!")

# Run the bot
client.run(token)
