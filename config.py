import os
from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_ID = int(os.getenv("ALEX_ID")) # The admin's numeric Discord user ID
SPAM_WINDOW = 60 # Spam ping detection window, in seconds
TRACKING_PERIOD = 300 # Grace period before retaliatory ping sequence, in seconds
PING_DELAY = 1.0 # Delay between each ping in spam in seconds
SPAM_THRESHOLD = 4 # Amount of pings needed to initiate return/retaliatory pings
RETURN_PINGS = 3 # Amount of return pings
SPAM_PING_COUNT = 30 # Amount of !spam pings

# List of cogs to load
COGS = ["cogs.spam", "cogs.tracking"]
# Emote IDs that you want this bot to use
EMOTES = {'Pingsock': '<:Pingsock:1317712720006615150>'}

if not DISCORD_TOKEN:
    raise ValueError("No Discord token provided. Make sure it's set in the environment variables.")