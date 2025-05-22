import discord
from discord.ext import commands
import asyncio
from config import SPAM_WINDOW, SPAM_THRESHOLD, RETURN_PINGS, TRACKING_PERIOD, PING_DELAY, ADMIN_ID

class TrackingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cover = asyncio.Lock()
        self.ping_data = {}  # Stores timestamps of pings
        self.retaliatory_pings = {}  # Counts pings over time
        self.tracking_task = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("TrackingCog is ready!")

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author == self.bot.user:
            return

        # Get admin's roles in the guild
        admin = msg.guild.get_member(ADMIN_ID)
        admin_roles = admin.roles if admin else []

        # Check if admin is mentioned
        if any((user.id == ADMIN_ID or user == self.bot.user) for user in msg.mentions) or \
           any(role in admin_roles for role in msg.role_mentions) or msg.mention_everyone:

            async with self.cover:
                if msg.author.id not in self.ping_data:
                    self.ping_data[msg.author.id] = []
                if msg.author.id not in self.retaliatory_pings:
                    self.retaliatory_pings[msg.author.id] = 0

                self.ping_data[msg.author.id].append(msg.created_at)

                # Clean up mentions older than SPAM_WINDOW
                self.ping_data[msg.author.id] = [
                    t for t in self.ping_data[msg.author.id] if (msg.created_at - t).total_seconds() < SPAM_WINDOW
                ]

                if self.tracking_task:
                    self.retaliatory_pings[msg.author.id] += 1

                # If spammed, retaliate
                if len(self.ping_data[msg.author.id]) >= SPAM_THRESHOLD:
                    await self.do_return_pings(msg)
                    if not self.tracking_task:
                        self.retaliatory_pings[msg.author.id] = SPAM_THRESHOLD
                        self.tracking_task = asyncio.create_task(self.start_tracking(msg))

    async def do_return_pings(self, msg):
        for _ in range(RETURN_PINGS):
            await msg.channel.send(f"Silence, {msg.author.mention} <:Pingsock:1317712720006615150>")
            await asyncio.sleep(PING_DELAY)

    async def start_tracking(self, message):
        await asyncio.sleep(TRACKING_PERIOD)

        async with self.cover:
            pings_to_send = {user_id: count for user_id, count in self.retaliatory_pings.items() if count >= SPAM_THRESHOLD}
            self.retaliatory_pings = {}
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
