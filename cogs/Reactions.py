import typing

import discord
from discord.ext import commands, tasks


def has_custom_commands_role():
    def pred(ctx):
        if discord.utils.get(ctx.author.roles, name="Rick Tocchet Stan"):
            return True
        elif discord.utils.get(ctx.author.roles, name="Discord Admin"):
            return True
        else:
            return False

    return commands.check(pred)


class ReactionEvent:
    def __init__(self, event_id, text, type, reaction, reaction_name):
        self.event_id = event_id
        self.text = text
        self.type = type
        self.reaction = reaction
        self.reaction_name = reaction_name


class Reactions(commands.Cog, name="Reactions"):
    def __init__(self, bot):
        print("Registering Reactions Cog")
        self.bot = bot
        self.reaction_events_collection = bot.reaction_event_database['events']
        self.get_all_reaction_events.start()

    @tasks.loop(count=1)
    async def get_all_reaction_events(self):
        self.bot.reaction_events.clear()
        collection = await self.reaction_events_collection.find({}).to_list(length=None)
        for document in collection:
            x = ReactionEvent(document["_id"], document['text'], document['type'], document['reaction'],
                              document['reaction_name'])
            self.bot.reaction_events.append(x)

    @commands.group(brief="Reaction Event Group Commands")
    async def reactionevent(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send(
                "This is a group command, use `howler help reactionevent` to get list of subcommands under this command.")
            return

    @has_custom_commands_role()
    @reactionevent.command(brief="Adds a reaction event.")
    async def add(self, ctx, event_id: int, reaction: typing.Union[discord.Emoji, str], *, text):
        if type(reaction) == str:
            if await self.reaction_events_collection.count_documents({"_id": event_id}, limit=1) != 0:
                await ctx.send("That event id already exists, try a different one!")
                return

            text = text.lower()

            reaction_event_dict = {"_id": event_id, "text": text, "type": "built-in", "reaction": reaction,
                                   "reaction_name": None}

            await self.reaction_events_collection.insert_one(reaction_event_dict)
            x = ReactionEvent(event_id, text, "built-in", reaction, None)
            self.bot.reaction_events.append(x)

        else:
            if not reaction.is_usable():
                await ctx.send("I can't use that emoji, try a diffe rent one!")
                return
            if await self.reaction_events_collection.count_documents({"_id": event_id}, limit=1) != 0:
                await ctx.send("That event id already exists, try a different one!")
                return

            text = text.lower()

            reaction_event_dict = {"_id": event_id, "text": text, "type": "custom", "reaction": reaction.id,
                                   "reaction_name": reaction.name}
            await self.reaction_events_collection.insert_one(reaction_event_dict)
            x = ReactionEvent(event_id, text, "custom", reaction.id, reaction.name)
            self.bot.reaction_events.append(x)

    @has_custom_commands_role()
    @reactionevent.command(brief="Removes a reaction event.")
    async def remove(self, ctx, event_id: int):
        await self.reaction_events_collection.delete_many({"_id": event_id})
        self.get_all_reaction_events.start()

    @reactionevent.command(brief="Lists all reaction events.")
    async def list(self, ctx):
        list_string = "```"
        for reaction_event in self.bot.reaction_events:
            if len(reaction_event.text) <= 10:
                if reaction_event.type == "custom":
                    list_string += f"{reaction_event.event_id} :{reaction_event.reaction_name}: {reaction_event.text}\n"
                else:
                    list_string += f"{reaction_event.event_id} {reaction_event.reaction} {reaction_event.text}\n"
            else:
                if reaction_event.type == "custom":
                    list_string += f"{reaction_event.event_id} :{reaction_event.reaction_name}: {reaction_event.text[:10]}..\n"
                else:
                    list_string += f"{reaction_event.event_id} {reaction_event.reaction} {reaction_event.text[:10]}..\n"

        list_string += "```"

        embed = discord.Embed(
            title="Reaction Events",
            description=list_string
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Reactions(bot))
