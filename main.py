import discord
import os
from discord.ext import commands, tasks
import motor.motor_asyncio
import gridfs

DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
MONGO_TOKEN = os.environ['MONGO_TOKEN']

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='$', intents=intents)

database_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_TOKEN)
fs = gridfs.GridFS(database_client)
client.image_database = database_client['images']

client.image_commands = []


class ImageCommand:
    def __init__(self, command, file):
        self.command = command
        self.file = file


@tasks.loop(seconds=1, count=1)
async def get_all_images():
    client.image_commands.clear()
    collection = await client.image_database.find({}).to_list(length=None)
    for document in collection:
        x = ImageCommand(document["_id"], document['file'])
        client.image_commands.append(x)


@client.command()
async def ping(ctx):
    await ctx.send("pong")


@client.command()
async def upload(ctx):
    file = ctx.message.attachments[0]
    with open(file, 'rb') as f:
        contents = f.read()

    fs.put(contents, filename="file")


@client.event()
async def on_message(message):
    message_content = message.content.lower()
    if message.content.startswith(("howler ", "Howler ")):
        res = message.content[0].lower() + message.content[1:]
        for command in client.image_commands:
            if res == command.command:
                file = discord.File(f"images/{command.file}")
                await message.channel.send(file=file)
                return


print('starting bot')
client.run(DISCORD_TOKEN)
