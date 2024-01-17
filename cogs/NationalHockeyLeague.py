import os

import discord
from discord.ext import tasks, commands
from datetime import datetime, time
import pytz
import aiohttp
from iso8601 import iso8601
from bs4 import BeautifulSoup

EST = pytz.timezone('US/Eastern')
UTC = pytz.timezone('UTC')

TEST_ENVIRONMENT = os.getenv('HOWLER_TESTING_ENVIRONMENT') == 'true'

if TEST_ENVIRONMENT:
    CHANNEL_ID = 870019149743669288
    DATABASE_RECORD = "2"
else:
    CHANNEL_ID = 798968918692724736
    DATABASE_RECORD = "1"

HIGHLIGHT_VIDEO_URL = 'https://players.brightcove.net/6415718365001/EXtG1xJ7H_default/index.html?videoId'


async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()


def default(dictionary):
    if 'cs' in dictionary:
        return dictionary['cs']

    if 'sk' in dictionary:
        return dictionary['sk']

    if 'default' in dictionary:
        return dictionary['default']


def periodDescription(period):
    if period == 1:
        return 'the 1st period'
    if period == 2:
        return 'the 2nd period'
    if period == 3:
        return 'the 3rd period'
    if period == 4:
        return 'overtime'


def shotType(goal):
    if 'shotType' in goal:
        return f'{goal["shotType"]} shot'

    return ''


class NationalHockeyLeague(commands.Cog):
    def __init__(self, bot):
        print("Registering National Hockey League Cog")
        self.bot = bot
        self.game_tracker = bot.game_tracker_database['game_tracker']
        self.game_time = None
        self.game_loop.start()
        self.game_id = None
        self.goals = []
        self.are_we_home = False
        self.preview_posted = False
        self.morning_loop.start()
        self.preview_loop.start()

    async def generate_schedule_embed(self, team, enemy, game):
        game_time = iso8601.parse_date(game['startTimeUTC']).replace(tzinfo=UTC).astimezone(EST)
        game_id = game['id']
        await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
            "gameTime": game_time.isoformat(),
            "game_id": game_id
        }})
        enemyName = enemy["placeName"]["default"]
        embed = discord.Embed(
            title="It's Game Day!!!",
            timestamp=iso8601.parse_date(game['startTimeUTC']),
            description=f'{enemyName} gonna get stomped!'
        )
        embed.set_image(url="https://media.publit.io/file/fil-pmn.gif")

        channel = self.bot.get_channel(CHANNEL_ID)
        await channel.send(embed=embed)

    def isNowInTimePeriod(self, startTime, endTime, nowTime):
        if startTime < endTime:
            return startTime <= nowTime <= endTime
        else:  # Over midnight
            return nowTime >= startTime or nowTime <= endTime

    async def post_game(self):
        today = datetime.now(EST).strftime('%Y-%m-%d')
        response = await fetch(f'https://api-web.nhle.com/v1/schedule/{today}')
        todaysGames = response['gameWeek'][0]['games']
        for game in todaysGames:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI' or homeTeam['abbrev'] == 'PHX':
                self.are_we_home = True
                await self.generate_schedule_embed(homeTeam, awayTeam, game)
            elif awayTeam['abbrev'] == 'ARI' or homeTeam['abbrev'] == 'PHX':
                self.are_we_home = False
                await self.generate_schedule_embed(awayTeam, homeTeam, game)

    async def post_goal(self, goal, homeAbbrev, awayAbbrev):
        assistString = ''
        if len(goal['assists']) == 1:
            assistString += f'{goal["assists"][0]["name"]} ({goal["assists"][0]["assistsToDate"]})'
        elif len(goal['assists']) == 2:
            assistString += f'{default(goal["assists"][0]["name"])} ({goal["assists"][0]["assistsToDate"]}), '
            assistString += f'{default(goal["assists"][1]["name"])} ({goal["assists"][1]["assistsToDate"]})'

        embed = discord.Embed(
            title=f'{default(goal["name"])} ({goal["goalsToDate"]})',
            description=assistString
        )
        if default(goal['teamAbbrev']) == homeAbbrev:
            homeScore = f'*{goal["homeScore"]}*'
            awayScore = f'{goal["awayScore"]}'
        else:
            homeScore = f'{goal["homeScore"]}'
            awayScore = f'*{goal["awayScore"]}*'

        embed.add_field(name=awayAbbrev, value=awayScore, inline=True)
        embed.add_field(name=homeAbbrev, value=homeScore, inline=True)
        footer = f'{goal["strength"].upper()} goal at {goal["timeInPeriod"]} of {periodDescription(goal["period"])}'
        embed.set_footer(text=footer)
        embed.set_thumbnail(url=goal['headshot'])

        channel = self.bot.get_channel(CHANNEL_ID)
        await channel.send(embed=embed)

    async def reset_db_values(self):
        await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
            'gameTime': None,
            'game_id': 0,
            'goals': [],
            'preview_posted': False
        }})

    async def retrieve_db_values(self):
        db_values = await self.game_tracker.find_one({"_id": DATABASE_RECORD})
        if db_values['gameTime'] is None or db_values['gameTime'] == '':
            self.game_time = None
        else:
            gameTime = iso8601.parse_date(db_values['gameTime'])
            self.game_time = gameTime

        self.game_id = db_values['game_id']
        self.goals = db_values['goals']
        self.preview_posted = db_values['preview_posted']

    @tasks.loop(time=time(hour=15))
    async def morning_loop(self):
        await self.reset_db_values()
        await self.post_game()

    @tasks.loop(minutes=30)
    async def preview_loop(self):
        await self.retrieve_db_values()
        if self.game_time is None or self.preview_posted == True:
            return
        else:
            response = await fetch_html('https://www.nhl.com/coyotes/news/')
            today = datetime.now(EST).strftime('%m%d%y')
            html = BeautifulSoup(response, "html.parser")
            profiles = []
            for profile in html.findAll('a'):
                profile = profile.get('href')
                profiles.append(profile)

            for profile in profiles:
                if profile and str(today) in profile:
                    channel = self.bot.get_channel(CHANNEL_ID)
                    await channel.send(f'https://www.nhl.com' + profile)
                    await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                        "preview_posted": True
                    }})
                    return

    @tasks.loop(seconds=30)
    async def game_loop(self):
        if self.game_loop.current_loop % 10 == 0:
            print(f'Game Loop iteration: ' + str(self.game_loop.current_loop))

        currentDay = datetime.now().day
        currentMonth = datetime.now().month
        currentYear = datetime.now().year
        nineAM = datetime(currentYear, currentMonth, currentDay, hour=9, minute=0, second=0, tzinfo=EST)

        await self.retrieve_db_values()

        if self.game_time is None:
            return

        if self.isNowInTimePeriod(self.game_time, nineAM, datetime.now(tz=EST)):
            print('Inside the game loop now')
            game = await fetch(f'https://api-web.nhle.com/v1/gamecenter/{self.game_id}/landing')
            check_goals = []
            homeTeam = game['homeTeam']['abbrev']
            awayTeam = game['awayTeam']['abbrev']

            if 'summary' not in game:
                return

            if 'scoring' not in game['summary']:
                return

            for period in game['summary']['scoring']:
                if 'goals' not in period:
                    continue
                for goal in period['goals']:
                    goal["period"] = period['period']
                    check_goals.append(goal)

            if len(check_goals) > len(self.goals):
                self.goals = check_goals
                await self.post_goal(self.goals[-1], homeAbbrev=homeTeam, awayAbbrev=awayTeam)
                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "goals": self.goals
                }})

            if len(check_goals) < len(self.goals):
                self.goals = check_goals
                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "goals": self.goals
                }})

            if game['gameState'] == 'FINAL':
                if len(game["summary"]["threeStars"]) != 3:
                    return

                threeStars = game["summary"]["threeStars"]

                embed = discord.Embed(
                    title='Three Stars of the Game'
                )
                embed.add_field(name="⭐", value=f'{threeStars[0]["firstName"]} {threeStars[0]["lastName"]}', inline=False)
                embed.add_field(name="⭐⭐", value=f'{threeStars[1]["firstName"]} {threeStars[1]["lastName"]}',inline=False)
                embed.add_field(name="⭐⭐⭐", value=f'{threeStars[2]["firstName"]} {threeStars[2]["lastName"]}',inline=False)
                channel = self.bot.get_channel(CHANNEL_ID)
                await channel.send(embed=embed)

                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "goals": [],
                    "game_id": 0,
                }})

    @game_loop.before_loop
    async def before_game_loop(self):
        print('waiting...')
        await self.bot.wait_until_ready()

    @commands.command()
    async def goals(self, ctx, year: int, month: int, day: int):
        date = datetime(year=year, month=month, day=day).strftime('%Y-%m-%d')
        url = f'https://api-web.nhle.com/v1/schedule/{date}'
        print(url)
        response = await fetch(url)
        days_games = response['gameWeek'][0]['games']
        highlight_game_id = 0
        for game in days_games:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI' or homeTeam['abbrev'] == 'PHX':
                highlight_game_id = game['id']
                break
            elif awayTeam['abbrev'] == 'ARI' or homeTeam['abbrev'] == 'PHX':
                highlight_game_id = game['id']
                break

        if highlight_game_id == 0:
            ctx.send('No arizona games that day')
            return

        url = f'https://api-web.nhle.com/v1/gamecenter/{highlight_game_id}/landing'
        print(url)
        game = await fetch(url)

        highlights_string = ''

        homeTeam = game['homeTeam']['abbrev']
        awayTeam = game['awayTeam']['abbrev']

        if game['gameState'] == 'FINAL' or game['gameState'] == 'OFF':
            for period in game['summary']['scoring']:
                if 'goals' not in period:
                    continue
                for goal in period['goals']:
                    if goal['teamAbbrev'] == homeTeam:
                        score = goal['homeScore']
                    else:
                        score = goal['awayScore']

                    teamAbbrev = default(goal['teamAbbrev'])
                    name = default(goal['name'])
                    shotTypeString = shotType(goal)

                    if "highlightClip" in goal:
                        highlights_string += f'[{teamAbbrev} ({score}) - {name}({goal["goalsToDate"]}) {shotTypeString}'
                    else:
                        highlights_string += f'{teamAbbrev} ({score}) - {name}({goal["goalsToDate"]}) {shotTypeString}'
                    if 'assists' in goal and len(goal['assists']) > 0:
                        highlights_string += " - assists: "
                        for assist in goal['assists']:
                            assistName = default(assist['name'])
                            highlights_string += f'{assistName} ({assist["assistsToDate"]}) '

                    if "highlightClip" in goal:
                        highlights_string += "]"
                        highlights_string += f'(<{HIGHLIGHT_VIDEO_URL}={goal["highlightClip"]}>)\n'
                    else:
                        highlights_string += '\n'

            await ctx.send(highlights_string)
            return

        await ctx.send('oopsie didnt find anything blame bert')

    @commands.command()
    async def recap(self, ctx, year: int, month: int, day: int):
        date = datetime(year=year, month=month, day=day).strftime('%Y-%m-%d')
        url = f'https://api-web.nhle.com/v1/schedule/{date}'
        print(url)
        response = await fetch(url)
        days_games = response['gameWeek'][0]['games']
        highlight_game_id = 0
        for game in days_games:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI' or homeTeam['abbrev'] == 'PHX':
                highlight_game_id = game['id']
                break
            elif awayTeam['abbrev'] == 'ARI' or homeTeam['abbrev'] == 'PHX':
                highlight_game_id = game['id']
                break

        if highlight_game_id == 0:
            await ctx.send('No arizona games that day')
            return

        url = f'https://api-web.nhle.com/v1/gamecenter/{highlight_game_id}/landing'
        print(url)
        game = await fetch(url)

        highlights_string = ''

        if game['gameState'] == 'FINAL' or game['gameState'] == 'OFF':
            highlights_string += f'[{game["homeTeam"]["abbrev"]} ({game["summary"]["linescore"]["totals"]["home"]}) - {game["awayTeam"]["abbrev"]} ({game["summary"]["linescore"]["totals"]["away"]})]'

            if 'gameVideo' not in game['summary']:
                await ctx.send(
                    'no vids sorry\n' + f'{game["homeTeam"]["abbrev"]} ({game["summary"]["linescore"]["totals"]["home"]}) - {game["awayTeam"]["abbrev"]} ({game["summary"]["linescore"]["totals"]["away"]})')
                return

            if 'condensedGame' in game["summary"]["gameVideo"]:
                highlights_string += f'({HIGHLIGHT_VIDEO_URL}={game["summary"]["gameVideo"]["condensedGame"]})'
            elif 'threeMinRecap' in game["summary"]["gameVideo"]:
                highlights_string += f'({HIGHLIGHT_VIDEO_URL}={game["summary"]["gameVideo"]["threeMinRecap"]})'

            await ctx.send(highlights_string)
            return

        await ctx.send('oopsie didnt find anything blame bert')

    @commands.command()
    async def threestars(self, ctx):
        threeStars = [
            {
                "star": 1,
                "playerId": 8475760,
                "teamAbbrev": "ARI",
                "headshot": "https://assets.nhle.com/mugs/nhl/20232024/ARI/8475760.png",
                "name": "N. Bjugstad",
                "firstName": "Nick",
                "lastName": "Bjugstad",
                "sweaterNo": 17,
                "position": "C",
                "goals": 3,
                "assists": 0,
                "points": 3
            },
            {
                "star": 2,
                "playerId": 8478971,
                "teamAbbrev": "ARI",
                "headshot": "https://assets.nhle.com/mugs/nhl/20232024/ARI/8478971.png",
                "name": "C. Ingram",
                "firstName": "Connor",
                "lastName": "Ingram",
                "sweaterNo": 39,
                "position": "G",
                "goalsAgainstAverage": 0.0,
                "savePctg": 1.0
            },
            {
                "star": 3,
                "playerId": 8479343,
                "teamAbbrev": "ARI",
                "headshot": "https://assets.nhle.com/mugs/nhl/20232024/ARI/8479343.png",
                "name": "C. Keller",
                "firstName": "Clayton",
                "lastName": "Keller",
                "sweaterNo": 9,
                "position": "R",
                "goals": 2,
                "assists": 1,
                "points": 3
            }
        ]

        if len(threeStars) == 3:
            embed = discord.Embed(
                title='Three Stars of the Game'
            )
            embed.add_field(name="⭐", value=f'{threeStars[0]["firstName"]} {threeStars[0]["lastName"]}', inline=False)
            embed.add_field(name="⭐⭐", value=f'{threeStars[1]["firstName"]} {threeStars[1]["lastName"]}', inline=False)
            embed.add_field(name="⭐⭐⭐", value=f'{threeStars[2]["firstName"]} {threeStars[2]["lastName"]}', inline=False)
            channel = self.bot.get_channel(CHANNEL_ID)
            await channel.send(embed=embed)
        else:
            return


async def setup(bot):
    await bot.add_cog(NationalHockeyLeague(bot))
