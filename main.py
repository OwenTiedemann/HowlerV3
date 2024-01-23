import discord
import os
from discord.ext import commands, tasks
import motor.motor_asyncio
from publitio import PublitioAPI
from dotenv import load_dotenv
import aiohttp
import asyncio
from PIL import Image, ImageDraw, ImageFont
import functools

load_dotenv()

TEST_ENVIRONMENT = os.getenv('HOWLER_TESTING_ENVIRONMENT') == 'true'

if TEST_ENVIRONMENT:
    PREFIXES = os.environ['PREFIXES'].split(', ')
else:
    PREFIXES = ['howler ', 'Howler']
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
client.reaction_event_database = database_client['reactionevents']
client.game_tracker_database = database_client['game_tracker']

client.publitio_api = PublitioAPI(PUBLITIO_KEY, PUBLITIO_SECRET)
client.reaction_events = []

cogs = (
        'cogs.CustomCommands',
        'cogs.TriviaCommands',
        'cogs.ModTools',
        'cogs.Reactions',
        'cogs.NationalHockeyLeague',
        'cogs.HowlerAPI'
        )


def getCommandName(message):
    if message.content.startswith('howler '):
        return message.content[len('howler '):]
    elif message.content.startswith('Howler '):
        return message.content[len('Howler '):]


@client.event
async def on_message(message):
    if message.author.bot:
        return
    lowercase_message = message.content.lower()
    for event in client.reaction_events:
        if event.text in lowercase_message:
            if event.type == "custom":
                emoji = client.get_emoji(event.reaction)
                await message.add_reaction(emoji)
            else:
                await message.add_reaction(event.reaction)
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
    author_avatar = author.display_avatar
    user_avatar = user.display_avatar
    await author_avatar.save("slap/author.png")
    await user_avatar.save("slap/user.png")

    thing = functools.partial(sync_func)

    some_stuff = await client.loop.run_in_executor(None, thing)

    file = discord.File("slap/slap.png")
    await ctx.send(file=file)


def prepare_gif():
    images = []
    size = 64, 64
    profilePic = Image.open('yeet/user.png')
    profilePic.thumbnail(size, Image.LANCZOS)

    for i, (framePath, options) in enumerate(zip(yeetFrames, profilePicCoords)):
        frame = Image.open(framePath)
        profilePic.thumbnail(options['size'], Image.LANCZOS)
        frame.paste(profilePic, options["coords"])
        text = ImageDraw.Draw(frame)
        myFont = ImageFont.truetype('arial.ttf', 50)
        text.text((115, 140), "YEET", font=myFont)
        images.append(frame)
        profilePic.thumbnail(size, Image.LANCZOS)

    images[0].save('yeet/yeet.gif',
                   save_all=True, append_images=images[1:], optimize=False, duration=80, loop=0)


@client.event
async def setup_hook():
    for cog in cogs:
        await client.load_extension(cog)


yeetFrames = [
    "frames/frame_11_delay-0.1s.jpg",
    "frames/frame_12_delay-0.1s.jpg",
    "frames/frame_13_delay-0.1s.jpg",
    "frames/frame_14_delay-0.1s.jpg",
    "frames/frame_15_delay-0.1s.jpg",
    "frames/frame_16_delay-0.1s.jpg",
    "frames/frame_17_delay-0.1s.jpg",
    "frames/frame_18_delay-0.1s.jpg",
    "frames/frame_19_delay-0.1s.jpg",
    "frames/frame_20_delay-0.1s.jpg",
    "frames/frame_21_delay-0.1s.jpg",
    "frames/frame_22_delay-0.1s.jpg",
    "frames/frame_23_delay-0.1s.jpg",
    "frames/frame_24_delay-0.1s.jpg",
    "frames/frame_25_delay-0.1s.jpg",
    "frames/frame_26_delay-0.1s.jpg",
    "frames/frame_27_delay-0.1s.jpg",
    "frames/frame_28_delay-0.1s.jpg",
    "frames/frame_29_delay-0.1s.jpg",
    "frames/frame_30_delay-0.1s.jpg",
    "frames/frame_31_delay-0.1s.jpg",
    "frames/frame_32_delay-0.1s.jpg",
    "frames/frame_33_delay-0.1s.jpg",
    "frames/frame_34_delay-0.1s.jpg",
    "frames/frame_35_delay-0.1s.jpg",
    "frames/frame_36_delay-0.1s.jpg",
    "frames/frame_37_delay-0.1s.jpg",
    "frames/frame_38_delay-0.1s.jpg",
    "frames/frame_39_delay-0.1s.jpg",
    "frames/frame_40_delay-0.1s.jpg",
    "frames/frame_41_delay-0.1s.jpg",
    "frames/frame_42_delay-0.1s.jpg",
]

profilePicCoords = [
    {
        "coords": (162, 65),
        "size": (64, 64)
    },
    {
        "coords": (155, 50),
        "size": (64, 64)
    },
    {
        "coords": (100, 10),
        "size": (64, 64)
    },
    {
        "coords": (-100, -100),
        "size": (64, 64)
    },
    {
        "coords": (260, 90),
        "size": (64, 64)
    },
    {
        "coords": (162, 65),
        "size": (64, 64)
    },
    {
        "coords": (75, 0),
        "size": (64, 64)
    },
    {
        "coords": (120, 50),
        "size": (16, 16)
    },
    {
        "coords": (128, 30),
        "size": (16, 16)
    },
    {
        "coords": (175, 50),
        "size": (16, 16)
    },
    {
        "coords": (170, 65),
        "size": (16, 16)
    },
    {
        "coords": (160, 75),
        "size": (16, 16)
    },
    {
        "coords": (160, 79),
        "size": (16, 16)
    },
    {
        "coords": (160, 79),
        "size": (16, 16)
    },
    {
        "coords": (160, 79),
        "size": (16, 16)
    },
    {
        "coords": (172, 73),
        "size": (16, 16)
    },
    {
        "coords": (163, 40),
        "size": (16, 16)
    },
    {
        "coords": (83, 20),
        "size": (16, 16)
    },
    {
        "coords": (40, 13),
        "size": (16, 16)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
    {
        "coords": (-100, -100),
        "size": (32, 32)
    },
]


@client.command()
async def yeet(ctx, user: discord.User):
    user_avatar = user.display_avatar
    await user_avatar.save("yeet/user.png")

    thing = functools.partial(prepare_gif)

    some_stuff = await client.loop.run_in_executor(None, thing)

    file = discord.File("yeet/yeet.gif")
    await ctx.send(file=file)


print('starting bot')
client.run(DISCORD_TOKEN)
