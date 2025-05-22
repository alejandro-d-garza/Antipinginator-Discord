import discord
from discord.ext import commands
import asyncio
from datetime import datetime
from config import SPAM_WINDOW, SPAM_THRESHOLD, PING_DELAY, ADMIN_ID

class OfflineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cover = asyncio.Lock()
        self.filename = "last_uptime.txt"

    @commands.Cog.listener()
    async def on_message(self, message):
        with open(self.filename, "w") as file: #overwrites file contents
            file.write(message.created_at.isoformat())
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("OfflineCog is ready!")

        try:
            with open(self.filename, "r") as file:
                timestamp = datetime.fromisoformat(file.read().strip())
        except Exception as e:
            print(f"Could not read last uptime: {e}")
            return
        
        # Gather all pings of interest from all text channels starting from timestamp.
        self.ping_data = {}
        for guild in self.bot.guilds:
            admin = guild.get_member(ADMIN_ID)
            admin_roles = admin.roles if admin else []
            for channel in guild.text_channels:
                async for msg in channel.history(after=timestamp, oldest_first=True, limit=None):
                    if any((user.id == ADMIN_ID or user == self.bot.user) for user in msg.mentions) or \
                    any(role in admin_roles for role in msg.role_mentions) or msg.mention_everyone:
                        chan_dict = self.ping_data.setdefault(channel.id, {})
                        chan_dict.setdefault(msg.author.id, []).append(msg)
        
        # For each list of msgs, filter out pings that do not meet criteria for spam
        # Access a message list with ping_data[channel.id][user.id]
        for chan_dict in self.ping_data.values():
            for user_id, msg_list in list(chan_dict.items()):
                if len(msg_list) < SPAM_THRESHOLD:
                    chan_dict[user_id] = 0
                    continue

                ping_count = 0
                include_next = 0
                for i in range(0, len(msg_list) - SPAM_THRESHOLD + 1):
                    if (msg_list[i+SPAM_THRESHOLD-1].created_at - msg_list[i].created_at).total_seconds() <= SPAM_WINDOW:
                        ping_count += 1
                        include_next = SPAM_THRESHOLD - 1
                    elif include_next > 0:
                        ping_count += 1
                        include_next -= 1
                ping_count += include_next
                
                # Now having filtered msgs, replace the list in the dictionary with the ping count
                chan_dict[user_id] = ping_count
            
        # Now with a properly compiled ping_data, sequentially perform pinging by channel
        try:
            print(self.ping_data)
            for channel_id in self.ping_data.keys():
                channel = self.bot.get_channel(channel_id)
                chan_dict = self.ping_data[channel_id]
                if not chan_dict or not channel:
                    continue
                await channel.send(f"I have awoken from my slumber... and I smell ping spam! Naughty, naughty... Prepare to feel my vengeance!")
                await asyncio.sleep(PING_DELAY)

                async with self.cover:
                    while chan_dict:
                        message = ' | '.join(f"<@{uid}> [{chan_dict[uid]}]" for uid in chan_dict.keys() if chan_dict[uid] != 0)
                        await channel.send(message)
                        await asyncio.sleep(PING_DELAY)
                        for uid in list(chan_dict.keys()):
                            chan_dict[uid] -= 1
                            if chan_dict[uid] <= 0:
                                del chan_dict[uid]
                        print(self.ping_data)
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(OfflineCog(bot))