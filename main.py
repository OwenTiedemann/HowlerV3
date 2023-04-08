import discord
import os
from discord.ext import commands

DISCORD_TOKEN = os.environ['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='$', intents=intents)


@client.command()
async def ping(ctx):
    await ctx.send("pong")


print('starting bot')
client.run(DISCORD_TOKEN)
