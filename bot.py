import json
import discord
import aiohttp
import asyncio
import re
from discord import app_commands
from config import token

# Initialize intents and client
intents = discord.Intents.all()
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
            async with session.get(prefix + guild_url + postfix, ssl=False) as response:
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
        guilds = [guild for guild in guilds if guild and guild[3] != 0 and 'M' in guild[2]]

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

# Asynchronous function to send long messages
async def send_long_message(interaction, long_message):
    # Split the message into parts using the specified delimiters
    message_parts = re.split(r'\n\n', long_message)

    # Remove empty parts
    message_parts = [part.strip() for part in message_parts if part.strip()]

    # Send each part
    for i, part in enumerate(message_parts, start=1):
        try:
            # Use interaction.response for the first part and interaction.followup for the rest
            if i == 1:
                await interaction.response.send_message(part)
            else:
                await interaction.followup.send(part)
        except discord.errors.InteractionResponded:
            # If the response is already sent, catch the exception
            pass

# Asynchronous function to get top players for each class or guild based on rio_all
async def get_top(interaction, category="class", top=3):
    try:
        # Read data from the JSON file
        with open('members.json', 'r', encoding='utf-8') as file:
            members_data = json.load(file)

        # Checking the existence of data in the file
        if not members_data:
            await interaction.response.send_message("No data to process. Complete the 'members.json' file before using this command.")
            return

        # Check if the category is valid
        valid_categories = ["class", "guild"]
        if category.lower() not in valid_categories:
            await interaction.response.send_message("Invalid category. Use 'class' or 'guild'.")
            return

        # Group members data by class or guild
        category_groups = {}
        for member in members_data:
            category_name = member['class'] if category.lower() == "class" else member['guild']
            if category_name not in category_groups:
                category_groups[category_name] = []
            category_groups[category_name].append(member)

        # Get top players for each class or guild based on rio_all
        top_per_category = {}
        for category_name, category_members in category_groups.items():
            sorted_members = sorted(category_members, key=lambda x: max(x.get('rio_all', 0), 0), reverse=True)
            top_per_category[category_name] = sorted_members[:top]

        # Format and send the result
        result_message = ""
        for category_name, top_members in top_per_category.items():
            result_message += f"\n{category_name}:\n"
            for i, member in enumerate(top_members):
                result_message += f"{i + 1}. {member['name']} ({member['guild'] if category == 'class' else member['class']}) - RIO: {member['rio_all']}\n"

        # Send the potentially long message
        await send_long_message(interaction, result_message)

    except Exception as e:
        print(f"An error occurred while processing the /top command: {e}")
        await interaction.response.send_message("An error occurred while processing the command. Please try again later.")

# Command to print guilds raid ranks in the current addon
@tree.command(name="guilds", description="Guilds Raid Rank")
@app_commands.describe(
    season="1/2/3"
)
async def get_data(interaction, season: int = 3):
    await print_guild_ranks(interaction, season)

# Command to print player ranks in the current M+ season
@tree.command(name="rank", description="Guilds Mythic+ Rank")
@app_commands.describe(
    top="1-20",
    guilds="all/Нехай Щастить/... several guilds can be entered through ','.", 
    classes="all/death knight/death knight:3/... ':3' means you want to specify the spec.", 
    role="all/dps/healer/tank", 
    rio="0-3500"
)
async def rank(interaction, top: int = 10, classes: str = "all", guilds: str = "all", role: str = "all", rio: int = 3300):
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
        
# Command to print top players for each class or guild based on rio
@tree.command(name="top", description="Top Players for Each Class or Guild based on RIO")
@app_commands.describe(
    category="class/guild",
    top="top X"
)
async def top(interaction, category: str = "class", top: int = 3):
    await get_top(interaction, category, top)
    
# Command "Tournament"
@tree.command(name="tournament", description="Get top players in a guild for a tournament")
@app_commands.describe(
    guild="Guild name for the tournament",
    top="Number of players to display (default: 3)"
)
async def tournament(interaction, guild: str = "Нехай Щастить", top: int = 3):
    # Read data from the JSON file
    with open('members.json', 'r', encoding='utf-8') as file:
        members_data = json.load(file)

    # Checking the existence of data in the file
    if not members_data:
        await interaction.response.send_message("No data to process. Complete the 'members.json' file before using this command.")
        return

    # Filter by guild
    guild_members = [member for member in members_data if member['guild'].lower() == guild.lower()]

    if not guild_members:
        await interaction.response.send_message(f"No data available for the guild '{guild}'.")
        return
    
    # Define desired specs for melee and ranged DPS
    melee_specs = ["frost", "unholy", "havoc", "feral", "survival", "windwalker", "retribution", "assassination", "outlaw", "subtlety", "enhancement", "arms", "fury"]
    ranged_specs = ["balance", "augmentation", "devastation", "beast mastery", "marksmanship", "arcane", "fire", "frost", "shadow", "elemental", "affliction", "demonology", "destruction"]

    # Get top players for the tank category
    top3_tank = sorted(guild_members, key=lambda x: max(x.get('rio_tank', 0), 0), reverse=True)[:top]
    
    # Get top players for the healer category
    top3_healer = sorted(guild_members, key=lambda x: max(x.get('rio_healer', 0), 0), reverse=True)[:top]
        
    # Get top players for the melee dps category
    top3_mdd = sorted([member for member in guild_members if member.get('active_spec_name') and member['active_spec_name'].lower() in melee_specs and member['class'] != 'Mage'], key=lambda x: max(x.get('rio_dps', 0), 0), reverse=True)[:top]
    
    # Get top players for the ranged dps category
    top3_rdd = sorted([member for member in guild_members if member.get('active_spec_name') and member['active_spec_name'].lower() in ranged_specs and member['class'] != 'Death Knight'], key=lambda x: max(x.get('rio_dps', 0), 0), reverse=True)[:top]

    # Format and send the result
    result_message = f"Top {top} Players in Guild '{guild}' for the Tournament:\n"
    
    # Add top 3 players for the tank category to the result
    result_message += "\nTanks:\n"
    for i, member in enumerate(top3_tank):
        result_message += f"{i + 1}. {member['name']} - {member['active_spec_name']} {member['class']} - {member['rio_tank']}\n"
        
    # Add top 3 players for the healer category to the result
    result_message += "\nHealers:\n"
    for i, member in enumerate(top3_healer):
        result_message += f"{i + 1}. {member['name']} - {member['active_spec_name']} {member['class']} - {member['rio_healer']}\n"
            
    # Add top 3 players for the melee dps category to the result
    result_message += "\nMelee DPS:\n"
    for i, member in enumerate(top3_mdd):
        result_message += f"{i + 1}. {member['name']} - {member['active_spec_name']} {member['class']} - {member['rio_dps']}\n"
        
    # Add top 3 players for the ranged dps category to the result
    result_message += "\nRanged DPS:\n"
    for i, member in enumerate(top3_rdd):
        result_message += f"{i + 1}. {member['name']} - {member['active_spec_name']} {member['class']} - {member['rio_dps']}\n"

    await interaction.response.send_message(result_message)
        
# Command "About us"
@tree.command(name="about_us", description="About us")
async def about_us(interaction):    
    await interaction.response.send_message("https://youtu.be/xvpVTd1gt5Q")
    
# Command "Rules"
@tree.command(name="rules", description="Rules")
async def rules(interaction):
    await interaction.response.send_message("https://cdn.discordapp.com/attachments/786720808788688918/1202356554523742289/image.png?ex=65e8d84d&is=65d6634d&hm=dee787e24cb77005a58568556547af37a24fe98bfcb11c1f6ecabc1bf72842ff&")
    
# Command "Help"
@tree.command(name="help", description="Get information about available commands")
async def help_command(interaction):
    try:
        help_message = (
            "**Available Commands:**\n"
            "\n/guilds - Get guild raid ranks in the current addon.\n"
            "       -season: Season number (1, 2, or 3, default is 3).\n"
            
            "\n/rank - Get player ranks in the current M+ season.\n"            
            "       -top: Number of top players to display (1-20, default is 10).\n"
            "       -guilds: Guilds to filter (all, guild names separated by ',').\n"
            "       -classes: Player classes to filter (all or specific class).\n"
            "       -role: Player role to filter (all, dps, healer, tank, or spec name).\n"
            "       -rio: Minimum RIO score to display (0-3500, default is 500).\n"
            
            "\n/top - Get top X players for each class or guild based on RIO.\n"            
            "       -category: Category to display (class or guild, default is class).\n"
            "       -top: top X players.\n"
            
            "\n/tournament - Get top players in each category.\n"            
            "       -guild: Top players of which guild will be searched.\n"
            "       -top: Top X players.\n"
            
            "\n/about_us - Learn more about us.\n"
            
            "\n/rules - Rules.\n"
            
            "\n/help - Get information about available commands.\n"
        )
        
        await interaction.response.send_message(help_message)

    except Exception as e:
        print(f"An error occurred while processing the help command: {e}")
        await interaction.response.send_message("An error occurred while processing the command. Please try again later.")

# Event handler for bot readiness
@client.event
async def on_ready():
    # Synchronize the command tree    
    await tree.sync()
    print("Ready!")
    
# Event handler for new messages
@client.event
async def on_message(message):
    # Check myself
    if message.author == client.user:
        return

    # Config    
    required_role = discord.utils.get(message.guild.roles, name="Guest")
    skiped_role = discord.utils.get(message.guild.roles, name="guild member")
    author = message.author.nick if isinstance(message.author, discord.Member) and message.author.nick else message.author.display_name    
    name_pattern = r"[|/(\[]"
    
    # Check if the message contains trigger text    
    if "видайте мені роль члена гільдії" in message.content.lower() and "флудилка" in message.channel.name:
        # If the author has the skiped_role, skip the checks
        if skiped_role in message.author.roles:
            await message.reply("You already have a role")            
        else:    
            # Check if the message author has a specific role and the message is sent in a specific channel
            if required_role not in message.author.roles or not re.search(name_pattern, author):
                # Check if the bot has permission to add reactions
                if message.channel.permissions_for(message.guild.me).add_reactions:
                    await message.add_reaction("⛔")
                else:
                    print("Bot does not have permission to add reactions in this channel.")
                    
                # Replying with a message
                await message.reply("https://cdn.discordapp.com/attachments/786720808788688918/1202356554523742289/image.png?ex=65e8d84d&is=65d6634d&hm=dee787e24cb77005a58568556547af37a24fe98bfcb11c1f6ecabc1bf72842ff&")
            
# Run the bot
client.run(token)
