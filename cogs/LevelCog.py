import discord
from discord.ext import commands
from discord import app_commands
from Database.database import get_server_status
from Leveling.embeds import leveling_stats
from tunables import *
import os
from Database.GuildObjects import MikoMember
from Database.database_class import Database

lv = Database("LevelCog.py")

class LevelCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)

    @app_commands.command(name="level", description=f"{os.getenv('APP_CMD_PREFIX')}View your rank and level for yourself or other members")
    @app_commands.guilds(discord.Object(id=890638458211680256))
    @app_commands.guild_only
    async def lv_cmd(self, interaction: discord.Interaction, user: discord.Member = None):

        if user is None: user = interaction.user
        u = MikoMember(user=user, client=interaction.client)
        await interaction.response.send_message(content=None, embed=leveling_stats(u))


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        if not u.profile.cmd_enabled('LEVELING'):
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False
        return True



async def setup(client: commands.Bot):
    await client.add_cog(LevelCog(client))