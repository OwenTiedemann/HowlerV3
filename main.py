import discord
import os
from discord.ext import commands, tasks
import motor.motor_asyncio
from publitio import PublitioAPI
from dotenv import load_dotenv
import aiohttp
import asyncio
from PIL import Image
import functools

load_dotenv()
TEST_ENVIRONMENT = os.getenv('HOWLER_TESTING_ENVIRONMENT') == 'true'

if TEST_ENVIRONMENT:
    PREFIXES = ['$', '%']
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    MONGO_TOKEN = os.getenv('MONGO_TOKEN')
    PUBLITIO_KEY = os.getenv('PUBLITIO_KEY')
    PUBLITIO_SECRET = os.getenv('PUBLITIO_SECRET')
else:
    PREFIXES = ['howler ', 'Howler ']
    DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
    MONGO_TOKEN = os.environ['MONGO_TOKEN']
    PUBLITIO_KEY = os.environ['PUBLITIO_KEY']
    PUBLITIO_SECRET = os.environ['PUBLITIO_SECRET']

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix=PREFIXES, intents=intents)

print(client.command_prefix)


def is_me(m):
    return m.author == client.user


client.is_me = is_me

database_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_TOKEN)
client.custom_commands_collection = database_client['commands']['custom']
client.trivia_database = database_client['database']

client.publitio_api = PublitioAPI(PUBLITIO_KEY, PUBLITIO_SECRET)

cogs = ('cogs.CustomCommands', 'cogs.TriviaCommands', 'cogs.ModTools')


def getCommandName(message):
    if message.content.startswith('howler '):
        return message.content[len('howler '):]
    elif message.content.startswith('Howler '):
        return message.content[len('Howler '):]


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith(tuple(client.command_prefix)):
        command_name = getCommandName(message)
        command = await client.custom_commands_collection.find_one({'name': command_name})
        if command:
            if 'image_url' in command:
                await message.channel.send(command['image_url'])
            elif 'text_response' in command:
                await message.channel.send(command['text_response'])

            return

    await client.process_commands(message)


@client.command()
async def bracket(ctx):
    async with aiohttp.ClientSession() as session:
        url = 'https://low6-nhl-brackets-prod.azurewebsites.net/leagues/38650/leaderboard?offset=0&limit=10'
        async with session.get(url) as resp:
            data = await resp.json()
            entries = data['entries']
            leaderboard = "```\n"
            for entry in entries:
                name = entry['entry_name']
                points = entry['points']
                possible_points = entry['possible_points']
                leaderboard += f'{name:<30}{points:<3} {possible_points:<3}\n'

            embed = discord.Embed(
                title="Bracket Challenge Leaderboard"
            )
            embed.description = leaderboard + "```"

            await ctx.send(embed=embed)


def sync_func():
    size = 128, 128

    authorIm = Image.open('slap/author.png')
    authorIm.thumbnail(size, Image.ANTIALIAS)
    userIm = Image.open('slap/user.png')
    userIm.thumbnail(size, Image.ANTIALIAS)
    batmanIm = Image.open('slap/batman.jpg')

    batmanIm.paste(authorIm, (150, 25))
    batmanIm.paste(userIm, (300, 110))
    batmanIm.save("slap/slap.png")


@client.command()
async def slap(ctx, user: discord.User):
    author = ctx.author

    if user.id == 151087006989025281:
        user = ctx.author
        author = client.user

    author_avatar = author.display_avatar
    user_avatar = user.display_avatar
    await author_avatar.save("slap/author.png")
    await user_avatar.save("slap/user.png")

    thing = functools.partial(sync_func)

    some_stuff = await client.loop.run_in_executor(None, thing)

    file = discord.File("slap/slap.png")
    await ctx.send(file=file)


@client.event
async def setup_hook():
    for cog in cogs:
        await client.load_extension(cog)


print('starting bot')
client.run(DISCORD_TOKEN)
