import asyncio

import aiohttp_cors
from aiohttp import web
from discord.ext import commands, tasks
import discord
import os
import aiohttp
from bson import json_util
import json

app = web.Application()
routes = web.RouteTableDef()


def rgb2hex(r,g,b):
    return "#{:02x}{:02x}{:02x}".format(r,g,b)


async def setup(bot):
    await bot.add_cog(Webserver(bot))


class Webserver(commands.Cog):
    def __init__(self, bot):
        self.site = None
        print("Registering HowlerAPI Cog")
        self.bot = bot
        self.custom_commands_collection = bot.custom_commands_collection
        self.web_server.start()

        @routes.get('/api/image_commands')
        async def get_image_commands(request):
            print('called')
            commands_list = await self.custom_commands_collection.find().to_list(length=None)
            image_commands = []
            for command in commands_list:
                if 'image_url' in command:
                    image_commands.append(command)

            return web.json_response(json.loads(json_util.dumps(image_commands)))

        @routes.get('/api/text_commands')
        async def get_text_commands(request):
            commands_list = await self.custom_commands_collection.find().to_list(length=None)
            text_commands = []
            for command in commands_list:
                if 'text_response' in command:
                    text_commands.append(command)

            return web.json_response(json.loads(json_util.dumps(text_commands)))

        @routes.get('/api/utils/roles')
        async def get_valid_roles_from_roles(request):
            request_roles = request.rel_url.query.getall('roles[]')

            guild = await self.bot.fetch_guild(360903377216864267)

            valid_roles = []

            for guild_role in await guild.fetch_roles():
                for user_role in request_roles:
                    if str(guild_role.id) == user_role:
                        role = {
                            'id': guild_role.id,
                            'name': guild_role.name,
                            'color': rgb2hex(guild_role.color.b, guild_role.color.g, guild_role.color.r)
                        }

                        valid_roles.append(role)
                        break

            return web.json_response(json.loads(json_util.dumps(valid_roles)))

        self.webserver_port = os.environ.get('PORT', 5000)
        app.add_routes(routes)

        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*"
            )})

        for route in list(app.router.routes()):
            cors.add(route)

    def __unload(self):
        asyncio.ensure_future(self.site.stop())

    @tasks.loop()
    async def web_server(self):
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, host='0.0.0.0', port=self.webserver_port)
        await self.site.start()

    @web_server.before_loop
    async def web_server_before_loop(self):
        await self.bot.wait_until_ready()
