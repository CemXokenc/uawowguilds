import json
import discord
import aiohttp
import asyncio
from discord import app_commands
from uaguildlist import url_list
from config import token

# Initialize intents and client
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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

# Command to print guild ranks in Vault of the Incarnates
@tree.command(name="guilds_rank_df_1", description="Vault of the Incarnates")
async def get_data_1(interaction):
    await print_guild_ranks(interaction, 1)

# Command to print guild ranks in Aberrus, the Shadowed Crucible
@tree.command(name="guilds_rank_df_2", description="Aberrus, the Shadowed Crucible")
async def get_data_2(interaction):
    await print_guild_ranks(interaction, 2)
    
# Command to print guild ranks in Amirdrassil, the Dream's Hope
@tree.command(name="guilds_rank_df_3", description="Amirdrassil, the Dream's Hope")
async def get_data_3(interaction):
    await print_guild_ranks(interaction, 3)

# Command to print player ranks in the current M+ season
@tree.command(name="rank", description="Top ua players")
@app_commands.describe(top="1-50", classes="all/death knight/mage/...", guilds="all/Нехай Щастить/...", role="all/dps/healer/tank")
async def rank(interaction, top: int, classes: str, guilds: str, role: str):
    try:
        # Read data from the JSON file
        with open('members.json', 'r', encoding='utf-8') as file:
            members_data = json.load(file)

        # Checking the existence of data in the file
        if not members_data:
            await interaction.response.send_message("No data to process. Complete the 'members.json' file before using this command.")
            return

        # Check for valid class
        valid_classes = {"all", "death knight", "demon hunter", "druid", "evoker", "hunter", "mage", "monk", "paladin", "priest", "rogue", "shaman", "warlock", "warrior"}
        if classes.lower() not in valid_classes:
            await interaction.response.send_message(f"Class '{classes}' does not exist. Use the valid classes: all, death knight, demon hunter, druid, evoker, hunter, mage, monk, paladin, priest, rogue, shaman, warlock, warrior.")
            return

        # Check for valid guild
        if guilds.lower() != "all":
            input_guilds = guilds.split(',')
            if not any(any(member['guild'].lower() == guild.lower() for member in members_data) for guild in input_guilds):
                await interaction.response.send_message(f"At least one of the entered guilds does not exist. Check the spelling. Several guilds can be entered through ','.")
                return

        # Check for valid role
        valid_roles = {"all", "dps", "healer", "tank"}
        if role.lower() not in valid_roles:
            await interaction.response.send_message(f"Role '{role}' does not exist. Use the valid roles: all, dps, healer, tank or spec name.")
            return

        # Check if top value is within the range of 1 to 50 inclusive
        if not 1 <= top <= 50:
            await interaction.response.send_message("Error: The value of top must be between 1 and 50 inclusive.")
            return

        # Filter by class
        if classes.lower() != "all":
            members_data = [member for member in members_data if member['class'].lower() == classes.lower()]

        # Filter by guilds
        members_data = [member for member in members_data if any(guild.strip().lower() == member['guild'].lower() for guild in input_guilds)]

        # Sort by RIO rating according to the role
        if role != "all":
            members_data = sorted(members_data, key=lambda x: x.get('rio_' + role.lower(), 0), reverse=True)
        else:
            members_data = sorted(members_data, key=lambda x: x.get('rio_all', 0), reverse=True)

        # Limit the number of displayed results
        members_data = members_data[:top]

        # Format header message
        header_message = f"Top {top}. Classes - {classes}. Guilds - {guilds}. Role - {role}"

        # Format and send the results
        result_message = "\n".join([f"{i + 1}. {member['name']} ({member['guild']}, {member['realm']}) - {member['class']} - RIO {role}: {member['rio_' + role.lower()]}" for i, member in enumerate(members_data)])
        await interaction.response.send_message(header_message + "\n" + result_message)
        
    except Exception as e:
        print(f"An error occurred while processing the rank command: {e}")
        await interaction.response.send_message("An error occurred while processing the command. Please try again later.")
  
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
