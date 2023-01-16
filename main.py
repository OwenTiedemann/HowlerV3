import configparser
import discord
from supabase import create_client, Client

config = configparser.ConfigParser()
config.read('config.ini')
DISCORD_TOKEN = config['DISCORD']['token']
SUPABASE_URL = config['SUPABASE']['url']
SUPABASE_KEY = config['SUPABASE']['public']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    result = supabase.table("members").select('*').eq("discord_id", message.author.id).execute()

    if len(result.data) == 0:
        supabase\
            .table("members")\
            .insert({"discord_id": message.author.id, "message_count": 1})\
            .execute()
    else:
        supabase.table("members")\
            .update({"message_count": result.data[0]['message_count'] + 1})\
            .eq("id", result.data[0]['id'])\
            .execute()

client.run(DISCORD_TOKEN)
