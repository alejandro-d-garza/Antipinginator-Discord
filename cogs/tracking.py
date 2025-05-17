import discord
from discord.ext import commands
import asyncio
from config import SPAM_WINDOW, SPAM_THRESHOLD, RETURN_PINGS, TRACKING_PERIOD, PING_DELAY, ADMIN_ID

class TrackingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cover = asyncio.Lock()
        self.dirty_pingers = {}  # Stores timestamps of pings
        self.pingers_retaliatory_count = {}  # Counts pings over time
        self.tracking_task = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("TrackingCog is ready!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Get admin's roles in the guild
        admin = message.guild.get_member(ADMIN_ID)
        admin_roles = admin.roles if admin else []

        # Check if admin is mentioned
        if any((user.id == ADMIN_ID or user == self.bot.user) for user in message.mentions) or \
           any(role in admin_roles for role in message.role_mentions) or \
           '@everyone' in message.content or '@here' in message.content:
           
            async with self.cover:
                if message.author.id not in self.dirty_pingers:
                    self.dirty_pingers[message.author.id] = []
                if message.author.id not in self.pingers_retaliatory_count:
                    self.pingers_retaliatory_count[message.author.id] = 0

                self.dirty_pingers[message.author.id].append(message.created_at)

                # Clean up mentions older than SPAM_WINDOW
                self.dirty_pingers[message.author.id] = [
                    t for t in self.dirty_pingers[message.author.id] if (message.created_at - t).total_seconds() < SPAM_WINDOW
                ]

                if self.tracking_task:
                    self.pingers_retaliatory_count[message.author.id] += 1

                # If spammed, retaliate
                if len(self.dirty_pingers[message.author.id]) >= SPAM_THRESHOLD:
                    await self.do_return_pings(message)
                    if not self.tracking_task:
                        self.pingers_retaliatory_count[message.author.id] = SPAM_THRESHOLD
                        self.tracking_task = asyncio.create_task(self.start_tracking(message))

    async def do_return_pings(self, message):
        for _ in range(RETURN_PINGS):
            await message.channel.send(f"Silence, {message.author.mention} <:Pingsock:1317712720006615150>")
            await asyncio.sleep(PING_DELAY)

    async def start_tracking(self, message):
        await asyncio.sleep(TRACKING_PERIOD)

        async with self.cover:
            pings_to_send = {user_id: count for user_id, count in self.pingers_retaliatory_count.items() if count >= SPAM_THRESHOLD}
            self.pingers_retaliatory_count = {}
            self.tracking_task = None
        
        await message.channel.send(f"Alas! I have been transgressed! Pay for thy sins, foul miscreants!")
        await asyncio.sleep(PING_DELAY)

        while any(count > 0 for count in pings_to_send.values()):
            await self.send_ping(message.channel, pings_to_send)

    async def send_ping(self, channel, pings_to_send):
        pings = ' | '.join(f'<@{user_id}> [{count}]' for user_id, count in pings_to_send.items() if count > 0)
        await channel.send(pings)

        async with self.cover:
            for user_id in pings_to_send:
                if pings_to_send[user_id] > 0:
                    pings_to_send[user_id] -= 1
        
        await asyncio.sleep(PING_DELAY)

async def setup(bot):
    await bot.add_cog(TrackingCog(bot))
