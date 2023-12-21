import discord
from discord.ext import tasks, commands
from datetime import datetime, time
import pytz
import aiohttp
from iso8601 import iso8601

EST = pytz.timezone('US/Eastern')
UTC = pytz.timezone('UTC')

CHANNEL_ID = 798968918692724736
DATABASE_RECORD = "1"


async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


class NationalHockeyLeague(commands.Cog):
    def __init__(self, bot):
        print("Registering National Hockey League Cog")
        self.bot = bot
        self.game_tracker = bot.game_tracker_database['game_tracker']
        self.postedMorningMessage = False
        self.game_time = None
        self.game_loop.start()
        self.game_id = None
        self.goals = []
        self.are_we_home = False
        self.morning_loop.start()

    async def generate_schedule_embed(self, team, enemy, game):
        game_time = iso8601.parse_date(game['startTimeUTC']).replace(tzinfo=UTC).astimezone(EST)
        game_id = game['id']
        await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
            "postedMorningMessage": True,
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

            if homeTeam['abbrev'] == 'ARI':
                self.are_we_home = True
                await self.generate_schedule_embed(homeTeam, awayTeam, game)
            elif awayTeam['abbrev'] == 'ARI':
                self.are_we_home = False
                await self.generate_schedule_embed(awayTeam, homeTeam, game)

    async def reset_after_failure(self):
        today = datetime.now(EST).strftime('%Y-%m-%d')
        response = await fetch(f'https://api-web.nhle.com/v1/schedule/{today}')
        todaysGames = response['gameWeek'][0]['games']
        for game in todaysGames:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI':
                game_time = iso8601.parse_date(game['startTimeUTC']).replace(tzinfo=UTC).astimezone(EST)
                game_id = game['id']
                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "gameTime": game_time.isoformat(),
                    "game_id": game_id,
                    "postedMorningMessage": True
                }})
                return
            elif awayTeam['abbrev'] == 'ARI':
                game_time = iso8601.parse_date(game['startTimeUTC']).replace(tzinfo=UTC).astimezone(EST)
                game_id = game['id']
                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "gameTime": game_time.isoformat(),
                    "game_id": game_id,
                    "postedMorningMessage": True
                }})
                return

    async def post_goal(self, goal):
        description = ''

        homeScore = goal['homeScore']
        awayScore = goal['awayScore']
        teamAbbrev = goal['teamAbbrev']
        goalsToDate = goal['goalsToDate']
        headshotUrl = goal['headshot']

        assists = []
        if 'assists' in goal and len(goal['assists']) > 0:
            assists.append(goal['assists'][0])

        description = f'{homeScore} - {awayScore} {teamAbbrev}'

        if teamAbbrev == 'ARI':
            description += f'\nHe has {goalsToDate} goals this season!'

        description += '\n'
        for assist in assists:
            description += f'Assist: {assist["firstName"]} {assist["lastName"]} ({assist["assistsToDate"]})'

        embed = discord.Embed(
            title=f'Goal scored by {goal["firstName"]} {goal["lastName"]}',
            description=description,
        )
        embed.set_thumbnail(url=headshotUrl)
        channel = self.bot.get_channel(CHANNEL_ID)
        await channel.send(embed=embed)

    async def reset_db_values(self):
        await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
            "postedMorningMessage": False,
            'gameTime': None,
            'game_id': 0,
            'goals': []
        }})

    async def retrieve_db_values(self):
        db_values = await self.game_tracker.find_one({"_id": DATABASE_RECORD})
        if db_values['gameTime'] is None or db_values['gameTime'] == '':
            self.game_time = None
        else:
            gameTime = iso8601.parse_date(db_values['gameTime'])
            self.game_time = gameTime

        self.postedMorningMessage = db_values['postedMorningMessage']
        self.game_id = db_values['game_id']
        self.goals = db_values['goals']

    @tasks.loop(time=time(hour=15))
    async def morning_loop(self):
        await self.post_game()

    @tasks.loop(seconds=15)
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

            if 'summary' not in game:
                return

            if 'scoring' not in game['summary']:
                return

            for period in game['summary']['scoring']:
                if 'goals' not in period:
                    continue
                for goal in period['goals']:
                    check_goals.append(goal)

            if len(check_goals) > len(self.goals):
                self.goals = check_goals
                await self.post_goal(self.goals[-1])
                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "goals": self.goals
                }})

            if game['gameState'] == 'FINAL':
                await self.game_tracker.update_one({"_id": DATABASE_RECORD}, {"$set": {
                    "goals": [],
                    "game_id": 0,
                }})

    @game_loop.before_loop
    async def before_game_loop(self):
        print('waiting...')
        await self.bot.wait_until_ready()

    @commands.command()
    async def post_goals(self, ctx, year: int, month: int, day: int):
        date = datetime(year=year, month=month, day=day).strftime('%Y-%m-%d')
        response = await fetch(f'https://api-web.nhle.com/v1/schedule/{date}')
        days_games = response['gameWeek'][0]['games']
        highlight_game_id = 0
        for game in days_games:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI':
                highlight_game_id = game['id']
                break
            elif awayTeam['abbrev'] == 'ARI':
                highlight_game_id = game['id']
                break

        if highlight_game_id == 0:
            ctx.send('No arizona games that day')
            return

        game = await fetch(f'https://api-web.nhle.com/v1/gamecenter/{highlight_game_id}/landing')

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
                    highlights_string += f'[{goal["teamAbbrev"]} ({score}) - {goal["name"]}({goal["goalsToDate"]}) {goal["shotType"]} shot - assists: '
                    if 'assists' in goal:
                        for assist in goal['assists']:
                            highlights_string += f'{assist["firstName"]} {assist["lastName"]} ({assist["assistsToDate"]}) '
                    highlights_string += "]"
                    highlights_string += f'(<https://players.brightcove.net/6415718365001/EXtG1xJ7H_default/index.html?videoId={goal["highlightClip"]}>)\n'

            await ctx.send(highlights_string)
            return

        await ctx.send('oopsie didnt find anything blame bert')

    @commands.command()
    async def post_recap(self, ctx, year: int, month: int, day: int):
        date = datetime(year=year, month=month, day=day).strftime('%Y-%m-%d')
        response = await fetch(f'https://api-web.nhle.com/v1/schedule/{date}')
        days_games = response['gameWeek'][0]['games']
        highlight_game_id = 0
        for game in days_games:
            awayTeam = game['awayTeam']
            homeTeam = game['homeTeam']

            if homeTeam['abbrev'] == 'ARI':
                highlight_game_id = game['id']
                break
            elif awayTeam['abbrev'] == 'ARI':
                highlight_game_id = game['id']
                break

        if highlight_game_id == 0:
            ctx.send('No arizona games that day')
            return

        game = await fetch(f'https://api-web.nhle.com/v1/gamecenter/{highlight_game_id}/landing')

        highlights_string = ''

        if game['gameState'] == 'FINAL' or game['gameState'] == 'OFF':
            highlights_string += f'[{game["homeTeam"]["abbrev"]} ({game["summary"]["linescore"]["totals"]["home"]}) - {game["awayTeam"]["abbrev"]} ({game["summary"]["linescore"]["totals"]["away"]})]'
            highlights_string += f'(https://players.brightcove.net/6415718365001/EXtG1xJ7H_default/index.html?videoId={game["summary"]["gameVideo"]["condensedGame"]})'

            await ctx.send(highlights_string)
            return

        await ctx.send('oopsie didnt find anything blame bert')


'''
    async def posthighlights(self, ctx):
        game = await fetch(f'https://api-web.nhle.com/v1/gamecenter/{self.game_id}/landing')
        if 'summary' not in game:
            return

        if 'scoring' not in game['summary']:
            return

        for period in game['summary']['scoring']:
            if 'goals' not in period:
                continue
            for goal in period['goals']:
                print(goal)
                if 'highlightClip' not in goal:
                    continue
                highlight_id = goal['highlightClip']
                url = GOOGLE_SEARCH_URL + str(highlight_id)
                print(url)
                response = await fetch(url)
                print(response)
'''


async def setup(bot):
    await bot.add_cog(NationalHockeyLeague(bot))
