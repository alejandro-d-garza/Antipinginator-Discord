import discord
from discord.ext import commands
import asyncio
from config import DISCORD_TOKEN, COGS

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Load all cogs dynamically
async def load_cogs():
    for cog in COGS:
        await bot.load_extension(cog)

async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())