import json
import discord
import aiohttp
import asyncio
from discord import app_commands
from uaguildlist import url_list

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
    async with aiohttp.ClientSession() as session:
        async with session.get(prefix + guild_url + postfix) as response:
            json_data = await response.json()
            guild_name = json_data['name']
            guild_realm = json_data['realm']
            guild_progress = json_data['raid_progression'][raid]['summary']
            
            # Set rank 1244 for the guild "Нехай Щастить" and tier 2
            guild_rank = 1244 if guild_name == "Нехай Щастить" and tier == 2 else json_data['raid_rankings'][raid]['mythic']['world']
            return [guild_name, guild_realm, guild_progress, guild_rank]

# Function to print guild ranks
async def print_guild_ranks(interaction, tier):
    # Asynchronously get data for all guilds of the specified tier
    guilds = await asyncio.gather(*[fetch_guild_data(guild_url, tier) for guild_url in url_list])
    # Exclude guilds with rank 0
    guilds = [guild for guild in guilds if guild[3] != 0]
    
    if not guilds:
        await interaction.response.send_message(f"В даний момент гільдій з міфічним прогресом в {tier}му сезоні немає.")
        return
    
    # Sort guilds by rank
    sorted_guilds = sorted(guilds, key=lambda x: (x[3] or float('inf'), x[0]))
    # Format and send the result
    formatted_guilds = [f"{i + 1}. {', '.join(map(str, guild[:-1]))}, {guild[-1]} rank" for i, guild in enumerate(sorted_guilds)]
    await interaction.response.send_message("\n".join(formatted_guilds))

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
@app_commands.describe(top="5/10/20", classes="all/death knight/mage/...", guilds="all/Нехай Щастить/...", role="all/dps/healer/tank")
async def rank(interaction, top: int, classes: str, guilds: str, role: str):
    # Read data from the JSON file
    with open('members.json', 'r', encoding='utf-8') as file:
        members_data = json.load(file)

    # Check for valid class
    valid_classes = {"all", "death knight", "demon hunter", "druid", "evoker", "hunter", "mage", "monk", "paladin", "priest", "rogue", "shaman", "warlock", "warrior"}
    if classes.lower() not in valid_classes:
        await interaction.response.send_message(f"Класу '{classes}' не існує.")
        return

    # Check for valid guild
    if guilds.lower() != "all" and not any(member['guild'].lower() == guilds.lower() for member in members_data):
        await interaction.response.send_message(f"Гільдії '{guilds}' не існує.")
        return

    # Check for valid role
    valid_roles = {"all", "dps", "healer", "tank"}
    if role.lower() not in valid_roles:
        await interaction.response.send_message(f"Ролі '{role}' не існує.")
        return

    # Check if top value is within the range of 1 to 20 inclusive
    if not 1 <= top <= 20:
        await interaction.response.send_message("Помилка: значення top повинно бути в межах від 1 до 20 включно.")
        return

    # Filter by class
    if classes.lower() != "all":
        members_data = [member for member in members_data if member['class'].lower() == classes.lower()]

    # Filter by guild
    if guilds.lower() != "all":
        members_data = [member for member in members_data if member['guild'].lower() == guilds.lower()]

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
client.run('MTE3MTQyNDAxMTg5NzU0NDcwNA.GO3v_6.3qxLmSOh1zW5CUIQUHdkbNdgwCgt1foXrtclQ0')
