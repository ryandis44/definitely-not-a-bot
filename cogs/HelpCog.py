import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from misc.embeds import help_embed
from tunables import *
from Database.database_class import Database
import re
import os
from dotenv import load_dotenv
load_dotenv()

hc = Database("HelpCog.py")
        

class HelpCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="help", description=f"{os.getenv('APP_CMD_PREFIX')}Miko Help")
    @app_commands.guild_only
    @app_commands.describe(
        category="Select a category for a more detailed help menu"
    )
    @app_commands.choices(
    category=[
        app_commands.Choice(name='Playtime/Voicetime', value='ptvt'),
        app_commands.Choice(name='Polls', value='polls'),
    ])
    async def h(self, interaction: discord.Interaction, category: app_commands.Choice[str] = None):
        await help(interaction=interaction, category=category)


    @app_commands.command(name="mikohelp", description=f"{os.getenv('APP_CMD_PREFIX')}Miko Help")
    @app_commands.guild_only
    @app_commands.describe(
        category="Select a category for a more detailed help menu"
    )
    @app_commands.choices(
    category=[
        app_commands.Choice(name='Playtime/Voicetime', value='ptvt'),
        app_commands.Choice(name='Polls', value='polls'),
    ])
    async def mh(self, interaction: discord.Interaction, category: app_commands.Choice[str] = None):
        await help(interaction=interaction, category=category)




    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        await interaction.response.send_message(content=f"{tunables('LOADING_EMOJI')}", ephemeral=True)
        u.increment_statistic('HELP_COMMAND')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(HelpCog(client))


async def help(interaction: discord.Interaction, category) -> None:

    msg = await interaction.original_response()

    u = MikoMember(user=interaction.user, client=interaction.client, check_exists=False)

    temp = []

    if category is not None: category = category.value

    match category:
        
        case "ptvt":
            temp.append(
                f":video_game: Playtime and :microphone2: Voicetime is tracked automatically for all users in all guilds with {interaction.client.user.mention}. These settings "
                "can be changed at any time using `/settings`."
                "\n\n"
                "The `/playtime` and `/voicetime` commands supports several arguments, allowing for advanced searches. Using "
                f"this command without any arguments will pull up your own activity since {interaction.client.user.mention} "
                "began tracking it. By default, playtime shows entries longer than 5 minutes and voicetime shows entries "
                "longer than 1 minute."
                "\n\n"
                "As mentioned previously, tracking is available in all guilds and its __tracking cannot be "
                "overridden by anyone__, including the guild owner (i.e. if you disable it, the guild owner "
                "cannot enable it)."
                "\n\n"
                f"You are in complete control of whether {interaction.client.user.mention} "
                "tracks your playtime and voice activities. Activity that has already been tracked is permanent and "
                "cannot be modified by anyone."
                "\n\n"
                "__**Parameter information**__:\n"
                "> • `playtime` & `voicetime`: These parameters take a time value: `<1h`, `<3d`, and a special parameter `all`, which shows all entries >1s. For example, if you "
                "want to search for activity entries that are longer than 5 hours, that would look like `>5h`. Less than "
                "5 hours: `<5h`, more than 3 days: `>3d`, all results: `all`"
                "\n> \n"
                "> • `scope`: This parameter allows you to search `Global` (playtime only), `Guild`, or `User`. The global scope will "
                f"allow you to search for entries from all users tracked by {interaction.client.user.mention}, guild scope will search "
                "for entries by users in the current guild, and user will search for your own entries (default)."
            )
        
        case "polls":
            temp.append(
                f"{interaction.client.user.mention} supports creating polls with the creator having full control "
                "over these polls."
                "\n\n"
                "Each poll can be set to last up to 24-hours. When a poll expires, the "
                "creator of this poll will be mentioned along with the results."
                "\n\n"
                "Polls can be ended early by pressing the red `End` button. The creator of a poll "
                "can end their poll at any time using this, as well as users that have the "
                "`Mange Messages` permission in the channel the poll was created in."
                "\n\n"
                "If a poll's message is deleted beforee the poll ends, the poll will be immediately "
                "ended and the results will not be sent. It's like it was never there."
            )

        case _: # No category specified
            temp.append(''.join(help_embed(u=u)))


    

    embed = discord.Embed (
        # title = 'Miko Command List and Brief Description',
        color = GLOBAL_EMBED_COLOR,
        description=''.join(temp)
    )
    embed.set_author(icon_url=interaction.client.user.avatar, name=f"{interaction.client.user.name} Help")
    await msg.edit(content=None, embed=embed)