import discord
from discord.ext import commands
import asyncio
from config import SPAM_PING_COUNT, PING_DELAY, ADMIN_ID

class SpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cover = asyncio.Lock()
        self.spam_queues = {} # guild ID : { user ID : num pings remaining }

    @commands.Cog.listener()
    async def on_ready(self):
        print("SpamCog is ready!")

    @commands.command()
    async def spam(self, ctx, member: discord.Member):
        """Spams a user with mentions. Called on command with !spam."""

        if member == self.bot.user or member.id == ADMIN_ID:
            await ctx.send(f"Nice try {ctx.author.mention}, you cannot spam me.")
            return

        async with self.cover:
            guild_queues = self.spam_queues.setdefault(ctx.guild.id, {})
            if member.id in guild_queues:
                return  # Ignore if user is already being spammed
            guild_queues[member.id] = SPAM_PING_COUNT

            # If this is the first spam request, start the spammer task
            if len(guild_queues) == 1:
                ctx.guild._spam_task = self.bot.loop.create_task(self._spam_task(ctx))

    async def _spam_task(self, ctx):
        guild_id = ctx.guild.id
        while True:
            async with self.cover:
                queue = self.spam_queues.get(guild_id, {})
                if not queue:
                    break  # No more users to spam, exit task

                message = " | ".join(f"<@{uid}> [{queue[uid]}]" for uid in queue.keys())

                # Decrement spam counts
                for uid in list(queue.keys()):
                    queue[uid] -= 1
                    if queue[uid] <= 0:
                        del queue[uid]

            await ctx.send(message)
            await asyncio.sleep(PING_DELAY)

async def setup(bot):
    await bot.add_cog(SpamCog(bot))
