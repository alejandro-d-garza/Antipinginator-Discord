import discord
import datetime
import asyncio
from config import *

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
cover = asyncio.Lock()

dirty_pingers = {} # Used for immediate return pings
pingers_retaliatory_count = {} # Used for delayed retaliatory ping spam
spam_queues = {} # Keeps track of how much spamming needed for each user for the !spam command, for each server
tracking_task = None

@client.event
async def on_ready():
    print(f'Successfully logged in as {client.user}')
    for guild in client.guilds:
        await initialize_users(guild)

# Initialize spam queue with all users in a server
async def initialize_users(guild):
    async with cover:
        if guild.id not in spam_queues:
            spam_queues[guild.id] = {}
        for member in guild.members:
            if member.id not in spam_queues[guild.id]:
                spam_queues[guild.id][member.id] = 0
        print(f'Initialized {guild.name} server in spam_queues')
        

@client.event
async def on_guild_join(guild):
    # Handle new servers when the bot joins
    initialize_users(guild)
    print(f'Joined new server: {guild.name}')

@client.event
async def on_member_join(member):
    async with cover:
        spam_queues[member.guild.id][member.id] = 0

@client.event
async def on_message(message):
    # Ignore messages from self to prevent infinite loops
    if message.author == client.user:
        return
    
    # Get my roles
    alex = message.guild.get_member(ADMIN_ID) # None if I'm not in server
    alex_roles = alex.roles if alex else []

    # Return ping sequence -- PING_THRESHOLD pings to me within TRACKING_INTERVAL causes ping spam in return to sender
    if any((user.id == ADMIN_ID or user == client.user) for user in message.mentions) or \
                            any(role in alex_roles for role in message.role_mentions) or \
                            '@everyone' in message.content or '@here' in message.content:
        global tracking_task
        async with cover:
            if message.author.id not in dirty_pingers:
                dirty_pingers[message.author.id] = []
            if message.author.id not in pingers_retaliatory_count:
                pingers_retaliatory_count[message.author.id] = 0

            dirty_pingers[message.author.id].append(message.created_at)

            # Clean up mentions older than SPAM_WINDOW
            dirty_pingers[message.author.id] = [t for t in dirty_pingers[message.author.id] if (message.created_at - t).total_seconds() < SPAM_WINDOW]

            # If tracking is happening and a ping has been received, log it in pingers_retaliatory_count
            if tracking_task:
                pingers_retaliatory_count[message.author.id] += 1

            # If spammed, do return pings, and start ping tracking
            if len(dirty_pingers[message.author.id]) >= SPAM_THRESHOLD:
                await do_return_pings(message)
                # Start delayed retaliatory ping sequence
                if not tracking_task:
                    pingers_retaliatory_count[message.author.id] = SPAM_THRESHOLD
                    tracking_task = asyncio.create_task(start_tracking(message))

    # Handle !spam command
    args = []
    if message.content.startswith('!spam'):
        args = message.content.split()

        # Error handling: if command used incorrectly
        if len(args) != 2 or not message.mentions:
            await message.channel.send('Syntax: !spam <@user>')
        else:
            await spam_command(message)

async def do_return_pings(message):
    for _ in range(RETURN_PINGS):
        await message.channel.send(f'Silence, {message.author.mention} {EMOTES['Pingsock']}')
        await asyncio.sleep(PING_DELAY)
    # Clear user's immediate pings
    dirty_pingers[message.author.id] = []

async def spam_command(message):
    target = message.mentions[0]
    # Me and the bot cannot be spam pinged
    if target == client.user or target.id == ADMIN_ID:
        for _ in range(RETURN_PINGS):
            await message.channel.send(f'<@{message.author.id}> Nice try loser. You cannot spam me')
            await asyncio.sleep(PING_DELAY)
        return
    
    # Handle the spam queue system
    async with cover:
        # Ignore !spam request if target is already being spammed
        if spam_queues[message.guild.id][target.id] > 0:
            return
        spam_queues[message.guild.id][target.id] = SPAM_PING_COUNT # target is to receive SPAM_PING_COUNT pings

    # Perform ping spam
    while any(count > 0 for count in spam_queues[message.guild.id].values()):
        await send_ping(message, spam_queues[message.guild.id])

async def start_tracking(message):
    await asyncio.sleep(TRACKING_PERIOD)

    async with cover:
        global pingers_retaliatory_count, tracking_task
        # Collect ping counts for each user, include if SPAM_THRESHOLD reached
        pings_to_send = {user_id: count for user_id, count in pingers_retaliatory_count.items() if count >= SPAM_THRESHOLD}
        pingers_retaliatory_count = {}
        tracking_task = None # Reset tracking task
    
    await message.channel.send(f'I have been transgressed! Pay for your sins, miscreants!')
    await asyncio.sleep(PING_DELAY)
    while any(count > 0 for count in pings_to_send.values()):
        await send_ping(message, pings_to_send)
        
async def send_ping(message, pings_to_send):
    pings = ' | '.join(f'<@{user_id}> [{count}]' for user_id, count in pings_to_send.items() if count > 0)
    await message.channel.send(pings)

    # Subtract one ping from each user
    async with cover:
        for user_id in pings_to_send:
            if pings_to_send[user_id] > 0:
                pings_to_send[user_id] -= 1
    
    await asyncio.sleep(PING_DELAY)

client.run(DISCORD_TOKEN)