import discord
from discord.ext import commands
import asyncio
from config import SPAM_PING_COUNT, PING_DELAY, ADMIN_ID

class SpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cover = asyncio.Lock()
        self.spam_queues = {}

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
            if self.spam_queues.get(ctx.guild.id, {}).get(member.id, 0) > 0:
                return  # Ignore if user is already being spammed
            self.spam_queues.setdefault(ctx.guild.id, {})[member.id] = SPAM_PING_COUNT

        while self.spam_queues[ctx.guild.id][member.id] > 0:
            await ctx.send(f"{member.mention} <:Pingsock:1317712720006615150>")
            async with self.cover:
                self.spam_queues[ctx.guild.id][member.id] -= 1
            await asyncio.sleep(PING_DELAY)

async def setup(bot):
    await bot.add_cog(SpamCog(bot))
