import os
import discord
from tunables import *
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from Database.database_class import Database
from GreenBook.UI import BookView
from dotenv import load_dotenv
load_dotenv()

bc = Database("HelpCog.py")
        

class BookCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="book", description=f"{os.getenv('APP_CMD_PREFIX')}View/Edit the Green Book")
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(id=890638458211680256), discord.Object(id=1060357911483797704))
    async def book(self, interaction: discord.Interaction):
        await BookView(original_interaction=interaction).ainit()


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        if not u.profile.cmd_enabled('GREEN_BOOK'):
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False

        await interaction.response.send_message(content=f"{tunables('LOADING_EMOJI')}", ephemeral=True)
        u.increment_statistic('YMCA_GREEN_BOOK_OPENED')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(BookCog(client))