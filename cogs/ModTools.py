import discord
from discord.ext import commands


class ModTools(commands.Cog):
    def __init__(self, bot):
        print("Registering Mod Tools Cog")
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(1104121223409045647)
        await channel.send(member.mention)


async def setup(bot):
    await bot.add_cog(ModTools(bot))
