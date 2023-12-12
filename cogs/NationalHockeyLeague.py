import discord
from discord.ext import tasks, commands
from datetime import time, datetime
import pytz
import aiohttp
import asyncio

from iso8601 import iso8601

EST = pytz.timezone('US/Eastern')


async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


class NationalHockeyLeague(commands.Cog):
    def __init__(self, bot):
        print("Registering National Hockey League Cog")
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.bot.get_channel(1104121223409045647)
        await channel.send(member.mention)

    async def generate_schedule_embed(self, team, enemy, game):
        enemyName = enemy["placeName"]["default"]
        print(game['startTimeUTC'])
        embed = discord.Embed(
            title="It's Game Day!!!",
            timestamp=iso8601.parse_date(game['startTimeUTC']),
            description=f'{enemyName} gonna get stomped!'
        )
        embed.set_image(url="https://media.publit.io/file/fil-pmn.gif")

        channel = self.bot.get_channel(798968918692724736)
        await channel.send(embed=embed)

    @commands.command()
    async def checkifgame(self, ctx):
        today = datetime.today().strftime('%Y-%m-%d')
        response = await fetch(f'https://api-web.nhle.com/v1/schedule/{today}')
        todaysGames = response['gameWeek'][0]['games']
        for game in todaysGames:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI':
                await self.generate_schedule_embed(homeTeam, awayTeam, game)
                return
            elif awayTeam['abbrev'] == 'ARI':
                await self.generate_schedule_embed(awayTeam, homeTeam, game)
                return

        await ctx.send("It ain't")

    @tasks.loop(time=time(10, 0, 0, tzinfo=EST))
    async def post_game(self):
        today = datetime.today().strftime('%Y-%m-%d')
        response = await fetch(f'https://api-web.nhle.com/v1/schedule/{today}')
        todaysGames = response['gameWeek'][0]['games']
        for game in todaysGames:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI':
                await self.generate_schedule_embed(homeTeam, awayTeam, game)
            elif awayTeam['abbrev'] == 'ARI':
                await self.generate_schedule_embed(awayTeam, homeTeam, game)


async def setup(bot):
    await bot.add_cog(NationalHockeyLeague(bot))
