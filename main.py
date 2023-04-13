import discord
import os
from discord.ext import commands, tasks
import motor.motor_asyncio
from publitio import PublitioAPI
from dotenv import load_dotenv

TEST_ENVIRONMENT = os.getenv('HOWLER_TESTING_ENVIRONMENT') == 'true'

load_dotenv()

if TEST_ENVIRONMENT:
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    MONGO_TOKEN = os.getenv('MONGO_TOKEN')
    PUBLITIO_KEY = os.getenv('PUBLITIO_KEY')
    PUBLITIO_SECRET = os.getenv('PUBLITIO_SECRET')
else:
    DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
    MONGO_TOKEN = os.environ['MONGO_TOKEN']
    PUBLITIO_KEY = os.environ['PUBLITIO_KEY']
    PUBLITIO_SECRET = os.environ['PUBLITIO_SECRET']

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=['howler ', 'Howler '], intents=intents)

database_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_TOKEN)
client.custom_commands_collection = database_client['commands']['custom']

client.publitio_api = PublitioAPI(PUBLITIO_KEY, PUBLITIO_SECRET)

cogs = ('cogs.CustomCommands', 'cogs.TriviaCommands')


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


@client.event
async def setup_hook():
    for cog in cogs:
        await client.load_extension(cog)


print('starting bot')
client.run(DISCORD_TOKEN)
