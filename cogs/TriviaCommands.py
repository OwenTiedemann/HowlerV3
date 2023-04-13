from discord.ext import commands


class TriviaCommandsCog(commands.Cog):
    def __init__(self, bot):
        print("Registering Trivia Commands Cog")
        self.bot = bot


async def setup(bot):
    await bot.add_cog(TriviaCommandsCog(bot))
