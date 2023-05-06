import discord
from discord.ext import commands

CUSTOM_COMMANDS_CHANNEL_ID = 812144663279566899


class CustomCommandsCog(commands.Cog):
    def __init__(self, bot):
        print("Registering Custom Commands Cog")
        self.bot = bot
        self.collection = self.bot.custom_commands_collection
        self.publitio_api = bot.publitio_api

    async def upload_image(self, file):
        response = self.publitio_api.create_file(file=file)
        return response

    async def delete_image(self, file_id):
        response = self.publitio_api.delete_file(file_id)
        return response

    # Create a group command for custom commands
    @commands.group()
    @commands.has_any_role('Commander', 'Discord Admin', 'Rick Tocchet Stan')
    async def custom(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send("Tsk.")
            return

    async def post_new_lists(self):
        channel = self.bot.get_channel(CUSTOM_COMMANDS_CHANNEL_ID)
        commands_list = await self.collection.find({}).to_list(length=None)

        async def image_list():

            list_string = ""
            for command in commands_list:
                if len(list_string) > 1500:
                    embed = discord.Embed()
                    embed.title = "Image Commands"
                    embed.description = list_string
                    await channel.send(embed=embed)
                    list_string = ""
                if 'image_url' in command:
                    list_string += f"[howler {command['name']}]({command['image_url']})\n"

            embed = discord.Embed()
            embed.title = "Image Commands"
            embed.description = list_string
            await channel.send(embed=embed)

        async def text_list():
            list_string = ""
            for command in commands_list:
                if len(list_string) > 1500:
                    embed = discord.Embed()
                    embed.title = "Text Commands"
                    embed.description = list_string
                    await channel.send(embed=embed)
                    list_string = ""
                if 'text_response' in command:
                    list_string += f"howler {command['name']}\n"

            embed = discord.Embed()
            embed.title = "Text Commands"
            embed.description = list_string
            await channel.send(embed=embed)

        await image_list()
        await text_list()

    # Create a command to register new custom commands
    @custom.command()
    @commands.has_any_role('Commander', 'Discord Admin', 'Rick Tocchet Stan')
    async def add(self, ctx, response_type, command_name, *, text=None):
        # Check if the command name is already taken
        if await self.collection.find_one({'name': command_name}):
            await ctx.send(f"The custom command '{command_name}' is already taken.")
            return

        # Check if the response type is valid
        if response_type.lower() not in ['image', 'text']:
            await ctx.send(f"The response type must be 'image' or 'text'.")
            return

        # Check if the user included an attachment for an image command
        if response_type.lower() == 'image' and len(ctx.message.attachments) == 0:
            await ctx.send(f"An image attachment is required for an image command.")
            return

        channel = self.bot.get_channel(CUSTOM_COMMANDS_CHANNEL_ID)
        if response_type.lower() == 'image':
            file = await ctx.message.attachments[0].read()
            response = await self.upload_image(file)
            # Save the command name and image URL to the database
            await self.collection.insert_one({'name': command_name, 'user': str(ctx.author), 'image_url': response['url_preview'], 'publitio_id': response['id']})
            await ctx.send(f"The custom command '{command_name}' has been registered with an image.")
        else:
            if text is None:
                await ctx.send("Text custom commands can't have an empty message. Add a message.")
                return
            text_response = text
            # Save the command name and text response to the database
            await self.collection.insert_one({'name': command_name, 'user': str(ctx.author), 'text_response': text_response})
            await ctx.send(f"The custom command '{command_name}' has been registered with a text response.")

        await channel.purge(limit=100, check=self.bot.is_me)
        await self.post_new_lists()

    # Create a command to un register custom commands
    @custom.command()
    @commands.has_any_role('Commander', 'Discord Admin', 'Rick Tocchet Stan')
    async def remove(self, ctx, command_name):
        command = await self.collection.find_one({'name': command_name})
        if command:
            await self.collection.delete_many({'name': command_name})
            if 'image_url' in command:
                await self.delete_image(command['publitio_id'])
            await ctx.send(f"The custom command '{command_name}' has been deleted.")
            channel = self.bot.get_channel(CUSTOM_COMMANDS_CHANNEL_ID)
            await channel.purge(limit=100, check=self.bot.is_me)
            await self.post_new_lists()
        else:
            await ctx.send(f"The custom command '{command_name}' doesn't exist.")

    @commands.command()
    async def image(self, ctx, category):
        if category == "list":
            commands_list = await self.collection.find({}).to_list(length=None)

            list_string = ""
            for command in commands_list:
                if len(list_string) > 1500:
                    embed = discord.Embed()
                    embed.title = "Image Commands"
                    embed.description = list_string
                    await ctx.send(embed=embed)
                    list_string = ""
                if 'image_url' in command:
                    list_string += f"[howler {command['name']}]({command['image_url']})\n"

            embed = discord.Embed()
            embed.title = "Image Commands"
            embed.description = list_string
            await ctx.send(embed=embed)

    @commands.command()
    async def text(self, ctx, category):
        if category == "list":
            commands_list = await self.collection.find({}).to_list(length=None)

            list_string = ""
            for command in commands_list:
                if len(list_string) > 1500:
                    embed = discord.Embed()
                    embed.title = "Text Commands"
                    embed.description = list_string
                    await ctx.send(embed=embed)
                    list_string = ""
                if 'text_response' in command:
                    list_string += f"howler {command['name']}\n"

            embed = discord.Embed()
            embed.title = "Text Commands"
            embed.description = list_string
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CustomCommandsCog(bot))
