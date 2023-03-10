import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from Database.GuildObjects import MikoMember
from tunables import *
from Database.database_class import Database
import os
from dotenv import load_dotenv
load_dotenv()

dev_cmd_db = Database("app_commands.py")


class dev_cog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    group = app_commands.Group(name="dev", description="Miko dev commands")
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @group.command(name="set_level_roles", description=f"{os.getenv('APP_CMD_PREFIX')}Give all members their leveling role")
    @app_commands.guild_only
    async def set_level_roles(self, interaction: discord.Interaction):

        u = MikoMember(user=interaction.user, client=interaction.client)
        msg = await interaction.original_response()

        temp = []
        members = interaction.guild.members
        temp.append(f"Assigning leveling roles to all users... {tunables('LOADING_EMOJI')}")
        await msg.edit(content=''.join(temp))

        leveling_roles = [
            interaction.guild.get_role(tunables('RANK_ID_LEVEL_01')),
            interaction.guild.get_role(tunables('RANK_ID_LEVEL_05')),
            interaction.guild.get_role(tunables('RANK_ID_LEVEL_10'))
        ]

        temp.append("\n[")
        temp.append("?")
        temp.append(f"/{interaction.guild.member_count}]")
        for i, member in enumerate(members):
            m = MikoMember(user=member, client=interaction.client)
            if member.bot: continue
            await member.remove_roles(*leveling_roles)
            await member.add_roles(m.leveling.get_role())
            if i % 10 == 0:
                temp[2] = f"{i+1}"
                await msg.edit(content=''.join(temp))

        temp[2] = f"{interaction.guild.member_count}"
        temp[0] = "Assigning leveling roles to all users..."
        temp.append("\n\n**Complete!** Leveling roles have been assigned to all users")
        await msg.edit(content=''.join(temp))



    @group.command(name="tabulate_levels", description=f"{os.getenv('APP_CMD_PREFIX')}Determine all members level and XP")
    @app_commands.guild_only
    async def tabulate_levels(self, interaction: discord.Interaction):
        msg = await interaction.original_response()

        temp = []
        temp.append(f"Compiling user data and determining all XP levels and ranks in this guild... {tunables('LOADING_EMOJI')}")
        await msg.edit(content=''.join(temp))

        sel_cmd = (
            "SELECT user_id FROM USERS WHERE "
            f"server_id='{interaction.guild.id}'"
        )
        msg_totals = dev_cmd_db.db_executor(sel_cmd)

        temp.append("\n[")
        temp.append("?")
        temp.append(f"/{interaction.guild.member_count}]")
        for i, user in enumerate(msg_totals):
            user_obj = self.client.get_user(int(msg_totals if type(msg_totals) is str else user[0]))
            if user_obj is None: continue
            u = MikoMember(user=user_obj, client=interaction.client, guild_id=interaction.guild.id)
            lc = u.leveling

            times_to_give_xp = int(lc.msgs / tunables('THRESHOLD_MESSAGES_FOR_XP'))
            xp = times_to_give_xp * tunables('XP_GAINED_FROM_MESSAGES')
            await lc.add_xp_msg(xp=xp, manual=True)

            times_to_give_xp = int(u.user_voicetime / tunables('THRESHOLD_VOICETIME_FOR_XP'))
            xp = times_to_give_xp * tunables('XP_GAINED_FROM_VOICETIME')
            await lc.add_xp_voice(xp=xp, manual=True)
            if type(msg_totals) == int: break
            if i % 10 == 0:
                temp[3] = f"{i+1}"
                await msg.edit(content=''.join(temp))


        temp[2] = f"{interaction.guild.member_count}"
        temp[0] = "Assigning leveling roles to all users..."
        temp.append("\n\n**Complete!** Levels and xp has been added")
        await msg.edit(content=''.join(temp))


    @group.command(name="calculate_member_numbers", description=f"{os.getenv('APP_CMD_PREFIX')}Reset and calculate all unique member numbers")
    @app_commands.guild_only
    async def calculate_member_numbers(self, interaction: discord.Interaction):

        u = MikoMember(user=interaction.user, client=interaction.client)
        msg = await interaction.original_response()

        temp = []
        members = interaction.guild.members
        temp.append(f"Resetting and recalculating all unique member numbers... {tunables('LOADING_EMOJI')}")
        await msg.edit(content=''.join(temp))


        temp.append("\nEnsuring all members are in database... [")
        temp.append("?")
        temp.append(f"/{interaction.guild.member_count}]")
        for i, member in enumerate(members):
            m = MikoMember(user=member, client=interaction.client)
            if i % 10 == 0:
                temp[2] = f"{i+1}"
                await msg.edit(content=''.join(temp))

        temp[2] = f"{interaction.guild.member_count}"



        db_members = dev_cmd_db.db_executor(
            "SELECT user_id FROM USERS WHERE "
            f"server_id='{interaction.guild.id}' "
            "ORDER BY original_join_time ASC"
        )

        temp.append("\nRecalculating unique member numbers... [")
        temp.append("?")
        temp.append(f"/{interaction.guild.member_count}]")
        for i, db_member in enumerate(db_members):
            
            dev_cmd_db.db_executor(
                f"UPDATE USERS SET unique_number='{i+1}' WHERE "
                f"user_id='{db_member[0]}' AND server_id='{interaction.guild.id}'"
            )
            if i % 10 == 0:
                temp[5] = f"{i+1}"
                await msg.edit(content=''.join(temp))

        temp[5] = f"{interaction.guild.member_count}"
        temp[0] = "Reset and recalculated all unique member numbers."
        temp.append("\n\n**Complete!**")
        await msg.edit(content=''.join(temp))
    




    async def interaction_check(self, interaction: discord.Interaction):
        u = MikoMember(user=interaction.user, client=interaction.client)
        if u.bot_permission_level >= 5:
            await interaction.response.send_message("Executing dev command...")
            u.increment_statistic('DEV_CMDS_USED')
            return True
        
        await interaction.response.send_message(tunables('NO_PERM'), ephemeral=True)
        return False



async def setup(client: commands.Bot):
    await client.add_cog(dev_cog(client))