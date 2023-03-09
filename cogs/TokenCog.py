import discord
from discord.ext import commands
from discord import app_commands
from Tokens.ShopItems import shop_items
from Tokens.Views import ShopView
from Tokens.embeds import token_shop
from Database.database import get_server_status
from tunables import tunables
from Database.database_class import Database
from Database.GuildObjects import MikoMember
import os
from dotenv import load_dotenv
from Tokens.TokenClass import Token
load_dotenv()

tc = Database("TokenCog.py")
        

class TokenCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="tokens", description=f"{os.getenv('APP_CMD_PREFIX')}View your tokens")
    @app_commands.guild_only
    @app_commands.guilds(discord.Object(id=890638458211680256))
    async def tokens(self, interaction: discord.Interaction, user: discord.Member = None):
        if str(get_server_status(interaction.guild.id)) == "inactive":
            await interaction.response.send_message("This bot has been disabled in this guild.", ephemeral=True)
            return

        if user is None: user = interaction.user

        u = MikoMember(user=user, client=interaction.client)
        t = u.tokens
        if user == interaction.user:
            msg = f"You have :coin: `{t.tokens} {'Tokens' if t.tokens != 1 else 'Token'}`"
        else:
            msg = f"{user.mention} has :coin: `{t.tokens} {'Tokens' if t.tokens != 1 else 'Token'}`"

        await interaction.response.send_message(content=msg, ephemeral=False)


    # @app_commands.command(name="shop", description=f"{os.getenv('APP_CMD_PREFIX')}Token Shop")
    # @app_commands.guild_only
    # @app_commands.guilds(discord.Object(id=890638458211680256))
    # async def tshop(self, interaction: discord.Interaction):
        
    #     if str(get_server_status(interaction.guild.id)) == "inactive":
    #         await interaction.response.send_message("This bot has been disabled in this guild.", ephemeral=True)
    #         return

    #     u = MikoMember(user=interaction.user, client=interaction.client)
    #     t = u.tokens
    #     items = shop_items(interaction=interaction, t=t)
    #     await interaction.response.send_message(embed=token_shop(items, t), view=ShopView(interaction, items))


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

async def setup(client: commands.Bot):
    await client.add_cog(TokenCog(client))