import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TEST_ENVIRONMENT = os.getenv('HOWLER_TESTING_ENVIRONMENT') == 'true'

if TEST_ENVIRONMENT:
    TRIVIA_CHANNEL = 870019149743669288
    TRIVIA_ROLE = 843691473408360478
else:
    TRIVIA_CHANNEL = 846527981349240922
    TRIVIA_ROLE = 851886327808655431


async def add_user(member, user_collection):
    if await user_collection.count_documents({"_id": str(member.id)}, limit=1) != 0:
        return
    name = member.display_name
    if len(member.display_name) > 21 and len(member.name) <= 21:
        name = member.name
    elif len(member.display_name) > 21 and len(member.name) > 21:
        name = member.display_name[0:21]

    user_dict = {"_id": str(member.id), 'answer': 0, 'number_correct': 0, 'display_name': name}
    await user_collection.insert_one(user_dict)


async def update_answer(user, answer, user_collection):
    await user_collection.update_one({"_id": str(user.id)}, {"$set": {'answer': answer}})


async def give_points(name_list, user_collection, correct_answer):
    users = user_collection.find()
    ans_correctly = 0
    ans_total = 0
    for user in await users.to_list(length=None):
        user_id, answer, points, name = user['_id'], user['answer'], user['number_correct'], user['display_name']
        if str(answer) == str(correct_answer):
            ans_correctly += 1
            await user_collection.update_one({"_id": str(user_id)}, {"$set": {'number_correct': points + 1}})
            name_list.append(name)
            ans_total += 1
        elif answer != 0:
            ans_total += 1
        await user_collection.update_one({"_id": str(user_id)}, {"$set": {'answer': 0}})

    return {"total": ans_total, "correct": ans_correctly}


class TriviaBot(commands.Cog, name="Trivia"):
    def __init__(self, bot):
        print("Registering Trivia Cog")
        self.bot = bot
        self.server_info = bot.trivia_database['server_info']

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        server_info_collection = self.bot.trivia_database['server_info']
        trivia_question = await server_info_collection.find_one()
        current_season = trivia_question['current_season']
        season_user_collection = self.bot.trivia_database[current_season]
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        payload_message_id = payload.message_id
        question = await server_info_collection.find_one()
        target_message_id = question['message_id']

        if payload_message_id == target_message_id:
            if msg.author.id != payload.user_id:
                user = payload.member
                await msg.remove_reaction(payload.emoji, user)

                if payload.emoji.name == "🇦":
                    answer = 1
                elif payload.emoji.name == '🇧':
                    answer = 2
                elif payload.emoji.name == '🇨':
                    answer = 3
                elif payload.emoji.name == '🇩':
                    answer = 4
                else:
                    return

                await add_user(user, season_user_collection)
                await update_answer(user, answer, season_user_collection)

    @commands.group(brief="Trivia Group Commands", invoke_without_command=True)
    async def trivia(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send(
                "This is a group command, use `howler help trivia` to get list of subcommands under this command.")
            return

    @trivia.command()
    @commands.has_role('trivia master')
    async def setup(self, ctx, correct_answer, url):
        server_info_collection = self.bot.trivia_database['server_info']
        trivia_question = await server_info_collection.find_one()
        question_id = trivia_question['message_id']
        if question_id != 0:
            await ctx.send('There is already a trivia message running, end it before starting a new one!')
            return

        channel = self.bot.get_channel(TRIVIA_CHANNEL)

        role = ctx.guild.get_role(TRIVIA_ROLE)
        await channel.send(role.mention)

        embed = discord.Embed(
            title="Trivia Question",
            description="Get it right for a point!",
            color=discord.Colour.blue(),

        )
        embed.set_image(url=str(url))
        trivia_message = await channel.send(embed=embed)
        await server_info_collection.update_one({"_id": 1}, {"$set": {'message_id': trivia_message.id}})
        await trivia_message.add_reaction('\U0001F1E6')
        await trivia_message.add_reaction('\U0001F1E7')
        await trivia_message.add_reaction('\U0001F1E8')
        await trivia_message.add_reaction('\U0001F1E9')

        server_info_collection.update_one({"_id": 1}, {"$set": {'correct_answer': correct_answer}})

        await ctx.message.delete()

    @trivia.command(name="cancel", brief="Cancels the trivia question",
                    description="Cancels the current trivia question without awarding points")
    @commands.has_role('trivia master')
    async def _trivia_cancel(self, ctx):
        server_info_collection = self.bot.trivia_database['server_info']
        server_info = await server_info_collection.find_one()
        season_user_collection = self.bot.trivia_database[str(server_info['current_season'])]

        question_id = server_info['message_id']

        channel = self.bot.get_channel(TRIVIA_CHANNEL)

        msg = await channel.fetch_message(question_id)
        await msg.delete()

        await season_user_collection.update_many({'i': {'$gt': 0}}, {'$set': {'answer': 0}})
        await server_info_collection.update_one({"_id": 1}, {'$set': {'message_id': 0}})
        await ctx.send('Canceling the current trivia question. No points awarded')

    @trivia.command()
    @commands.has_role('trivia master')
    async def end(self, ctx):
        server_info_collection = self.bot.trivia_database['server_info']
        server_info = await server_info_collection.find_one()
        current_season = server_info['current_season']
        correct_answer = server_info['correct_answer']
        season_user_collection = self.bot.trivia_database[current_season]

        await ctx.send('Ending the current trivia question!')

        role = ctx.guild.get_role(TRIVIA_ROLE)
        await ctx.send(role.mention)

        embed = discord.Embed(
            title="These users answered correctly!",
            color=discord.Colour.blue(),
        )

        name_list = []
        ratio_dict = await give_points(name_list, season_user_collection, correct_answer)
        ratio_string = f"{ratio_dict['correct']}/{ratio_dict['total']} answered correctly"
        names_string = "```\n"

        for name in name_list:
            names_string += f"{name}\n"

        names_string += "```"
        embed.description = names_string
        embed.set_footer(text=ratio_string)
        await server_info_collection.update_one({"_id": 1}, {"$set": {'message_id': 0}})
        await ctx.send(embed=embed)

    @trivia.command()
    @commands.has_role('trivia master')
    async def startseason(self, ctx, *, season):
        server_info_collection = self.bot.trivia_database['server_info']
        await server_info_collection.update_one({"_id": 1}, {"$set": {'current_season': str(season)}})
        await ctx.send('Starting a new season!')

    @trivia.command()
    async def leaderboard(self, ctx, *, season=""):
        if season == "":
            x = await self.server_info.find_one()
            current_season = x['current_season']
            print(current_season)
        else:
            current_season = season

        await self.leaderboard_setup(ctx, current_season)

    async def leaderboard_setup(self, ctx, season):
        season_user_collection = self.bot.trivia_database[str(season)]

        if await season_user_collection.estimated_document_count() == 0:
            await ctx.send('The leaderboard is empty, complete a trivia question in the season first!')
            return

        user_names = []
        user_scores = []

        users = await season_user_collection.find().to_list(length=None)

        for user in users:
            points, name = user['number_correct'], user['display_name']
            user_names.append(name)
            user_scores.append(points)

        embed = discord.Embed(
            title=str(season) + " Trivia Leaderboard",
            color=discord.Colour.blue(),
        )

        zipped_lists = zip(user_scores, user_names)
        sorted_pairs = sorted(zipped_lists)

        tuples = zip(*sorted_pairs)
        user_scores, user_names = [list(tuple) for tuple in tuples]

        user_scores.reverse()
        user_names.reverse()
        ranks = []
        for rank in range(len(user_scores)):
            ranks.append(rank + 1)

        leaderboard_string = "```\n"

        for (user, score, rank) in zip(user_names, user_scores, ranks):
            if rank > 10:
                break
            leaderboard_string += f"{rank:<3}{user:<23} {score}\n"

        leaderboard_string += "```"
        embed.description = leaderboard_string
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TriviaBot(bot))
