import asyncio
import random
import re
import time
import discord
from Music.LavalinkClient import AUDIO_SESSIONS
from Database.database_class import Database
from Leveling.LevelClass import LevelClass
# from Pets.PetClass import PetOwner
from Tokens.TokenClass import Token
from Emojis.emoji_generator import get_emoji_url, get_guild_emoji
from misc.embeds import help_embed
from misc.holiday_roles import get_holiday
from misc.misc import generate_nickname, react_all_emoji_list, today
from tunables import *
go = Database("GuildObjects.py")

class MikoGuild():

    def __init__(self, guild: discord.Guild, client: discord.Client, guild_id: int = None, check_exists=True, check_exists_guild=True):
        if guild_id is None: self.guild = guild
        else: self.guild = client.get_guild(int(guild_id))
        self.client = client
        self.log_channel = client.get_channel(1073509692363517962) # miko-logs channel in The Boys Hangout
        if check_exists and check_exists_guild: self.__exists()

    def __str__(self):
        return f"{self.guild} | MikoGuild Object"

    @property
    def __last_updated(self) -> int:
        sel_cmd = f"SELECT last_updated FROM SERVERS WHERE server_id='{self.guild.id}'"
        val = go.db_executor(sel_cmd)
        if val is not None and val != []: return int(val)
        print(f"Error when checking 'last_updated' in MikoGuild object: {val} | {self.guild.name} | {self.guild.id} | {int(time.time())}")
        return 1
    @property
    def guild_messages(self) -> int:
        sel_cmd = (
            "SELECT SUM(count) FROM USER_MESSAGE_COUNT WHERE "
            f"server_id='{self.guild.id}'"
        )
        val = go.db_executor(sel_cmd)
        if val is None or val == []: return 0
        return int(val)
    @property
    def guild_messages_nobots(self) -> int:
        sel_cmd = (
            "SELECT SUM(mc.count) FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON "
            "(mc.user_id=u.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE') WHERE "
            f"mc.server_id='{self.guild.id}'"
        )
        val = go.db_executor(sel_cmd)
        if val is None or val == []: return 0
        return int(val)
    @property
    def guild_messages_today(self) -> int:
        sel_cmd = (
            "SELECT messages_today FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        val = go.db_executor(sel_cmd)
        if val == [] or val is None: return 0
        if self.__last_updated >= today(): return int(val)
        return 0
    @property
    def status(self) -> str:
        sel_cmd = f"SELECT status FROM SERVERS WHERE server_id={self.guild.id}"
        val: str = go.db_executor(sel_cmd)
        if val == []: return None
        return val.upper()
    @property
    def music_channel(self) -> discord.TextChannel:
        sel_cmd = f"SELECT music_channel FROM SERVERS WHERE server_id='{self.guild.id}'"
        val = go.db_executor(sel_cmd)
        if val is None or val == []: return None
        return self.guild.get_channel(int(val))
    @property
    async def emoji(self) -> discord.Emoji:
        return await get_guild_emoji(self.client, self.guild)
    @property
    def top_ten_total_messages_nobots(self):
        val = go.db_executor(
            "SELECT cnt,user_id FROM ("
            "SELECT grouped.*, ROW_NUMBER() OVER ("
            "PARTITION BY grouped.server_id ORDER BY grouped.cnt DESC) AS row "
            "FROM ("
            "SELECT mc.server_id, mc.user_id, SUM(mc.count) AS cnt "
            "FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON u.user_id=mc.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE' "
            f"WHERE mc.server_id='{self.guild.id}' "
            "GROUP BY mc.user_id, mc.server_id) AS grouped) AS ranked "
            "ORDER BY cnt DESC LIMIT 10"
        )
        if val == [] or val is None: return None
        return val
    @property
    def nickname_in_ctx(self) -> bool:
        val = go.db_executor(
            "SELECT nickname_in_ctx FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == "TRUE" and tunables('NICKNAME_IN_CONTEXT'): return True
        return False
    @property
    def guild_do_big_emojis(self) -> bool:
        val = go.db_executor(
            "SELECT big_emojis FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == "FALSE" or not tunables('BIG_EMOJIS_ENABLED'): return False
        return True
    @property
    def profile(self) -> GuildProfile:
        return tunables(f'GUILD_PROFILE_{self.status}')
    @property
    def renamehell_members(self) -> list:
        val = go.db_executor(
            "SELECT user_id FROM USERS WHERE rename_any_true_false=\"TRUE\" "
            f"AND server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is list else [val]
    @property
    def clown_react_users(self) -> list:
        val = go.db_executor(
            "SELECT user_id FROM USERS WHERE react_true_false=\"TRUE\" AND "
            f"server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is list else [val]
    @property
    def react_all_users(self) -> list:
        val = go.db_executor(
            "SELECT user_id FROM USERS WHERE react_all_true_false=\"TRUE\" AND "
            f"server_id='{self.guild.id}'"
        )
        return [item[0] for item in val] if type(val) is list else [val]
    @property
    def ymca_green_book_channel(self) -> discord.TextChannel:
        val = go.db_executor(
            "SELECT ymca_green_book_channel FROM SERVERS WHERE "
            f"server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return None
        return self.client.get_channel(int(val))

    def set_member_numbers(self) -> None:
        member_ids = go.db_executor(
            "SELECT user_id FROM USERS WHERE "
            f"server_id='{self.guild.id}' "
            "ORDER BY original_join_time ASC"
        )
        for i, db_member in enumerate(member_ids):
            go.db_executor(
                f"UPDATE USERS SET unique_number='{i+1}' WHERE "
                f"user_id='{db_member[0]}' AND server_id='{self.guild.id}'"
            )

    def daily_msg_increment_guild(self) -> None:
        upd_cmd = []
        upd_cmd.append("UPDATE SERVERS SET ")

        # Using this logic, 'last_updated' will only be updated when a user
        # sends a message in a guild for the first time that day. And again
        # when a message is sent on a following day
        if self.__last_updated >= today():
            upd_cmd.append(f"messages_today='{self.guild_messages_today + 1}'")
        else:
            upd_cmd.append(f"messages_today='{self.guild_messages_today + 1}',last_updated='{int(time.time())}'")

        upd_cmd.append(f" WHERE server_id={self.guild.id}")
        go.db_executor(''.join(upd_cmd))
        return
    
    async def __leave_guild_log_message(self) -> None:

        i = 0
        while self.log_channel is None:
            await asyncio.sleep(1)
            if i >= 10:
                print("Log channel not found")
                return
            i += 1

        await self.log_channel.send(
            content=(
                "```diff\n"
                "- I left a guild! -\n"
                "```\n"
                f"> Left: <t:{int(time.time())}:R>\n"
                f"> Guild name: **{self.guild.name}** [`{self.guild.id}`]\n"
                f"> Guild owner: {self.guild.owner.mention} [`{self.guild.owner.id}`] 『`{self.guild.owner}`』\n"
                f"> Guild members: `{self.guild.member_count}`\n"
                f"> Guild profile [DB]: `{self.status}`\n"
                f"> Guild Locale (Region): `{self.guild.preferred_locale}`\n"
                f"> Guild 2FA Level: `{self.guild.mfa_level}`\n"
                f"> Guild NSFW Level: `{self.guild.nsfw_level}`\n"
                f"> Guild Nitro boost level: `{self.guild.premium_tier}`\n"
                f"> Guild Nitro boost count: `{self.guild.premium_subscription_count}`\n"
                f"> Guild Text Channels: `{len(self.guild.text_channels) if self.guild.text_channels is not None else 0}`\n"
                f"> Guild Voice Channels: `{len(self.guild.voice_channels) if self.guild.voice_channels is not None else 0}`\n"
                f"> Guild Vanity URL: {self.guild.vanity_url} | `{self.guild.vanity_url_code}`\n"
                f"> Guild Icon: {self.guild.icon}\n"
                f"> Guild Banner: {self.guild.banner}\n"
            ),
            allowed_mentions=discord.AllowedMentions(users=False)
        )

    async def __new_guild_log_message(self, new=True) -> None:

        channel = None
        if self.guild.system_channel is not None: channel = self.guild.system_channel
        else:
            for ch in self.guild.text_channels:
                channel = ch
                if ch.permissions_for(self.guild.me).send_messages: break
        
        if channel is not None:
            try:
                sent_channel = f"**Yes**. To {channel.mention} [`{channel.id}`] 『`#{channel.name}`』"
                u = MikoMember(user=self.guild.owner, client=self.client, check_exists=False)
                embed=discord.Embed(
                    color=GLOBAL_EMBED_COLOR,
                    description=''.join(help_embed(u=u))
                )
                embed.set_author(
                    icon_url=self.client.user.avatar,
                    name=f"{self.client.user.name} Help"
                )
                await channel.send(
                    content=(
                        "Thanks for adding me to your server! I have automatically enabled "
                        "playtime and voicetime tracking for all users in this guild. If you "
                        f"would like to change these settings, use {tunables('SLASH_COMMAND_SUGGEST_SETTINGS')}."
                    ),
                    embed=embed
                )
            except Exception as e: sent_channel = f"**No**: `{e}`"
        else: sent_channel = "**No**."

        i = 0
        while self.log_channel is None:
            await asyncio.sleep(1)
            if i >= 10: return
            i += 1

        await self.log_channel.send(
            content=(
                "```diff\n"
                f"+ I {'joined' if new else 'REJOINED'} a guild! +\n"
                "```\n"
                f"> Added: <t:{int(time.time())}:R>\n"
                f"> Help embed sent? {sent_channel}\n"
                f"> Guild name: **{self.guild.name}** [`{self.guild.id}`]\n"
                f"> Guild owner: {self.guild.owner.mention} [`{self.guild.owner.id}`] 『`{self.guild.owner}`』\n"
                f"> Guild members: `{self.guild.member_count}`\n"
                f"> Guild profile [DB]: `{self.status}`\n"
                f"> Guild Locale (Region): `{self.guild.preferred_locale}`\n"
                f"> Guild 2FA Level: `{self.guild.mfa_level}`\n"
                f"> Guild NSFW Level: `{self.guild.nsfw_level}`\n"
                f"> Guild Nitro boost level: `{self.guild.premium_tier}`\n"
                f"> Guild Nitro boost count: `{self.guild.premium_subscription_count}`\n"
                f"> Guild Text Channels: `{len(self.guild.text_channels) if self.guild.text_channels is not None else 0}`\n"
                f"> Guild Voice Channels: `{len(self.guild.voice_channels) if self.guild.voice_channels is not None else 0}`\n"
                f"> Guild Vanity URL: {self.guild.vanity_url} | `{self.guild.vanity_url_code}`\n"
                f"> Guild Icon: {self.guild.icon}\n"
                f"> Guild Banner: {self.guild.banner}\n"
                f"> My permissions: `{self.guild.me.guild_permissions}`\n"
            ),
            allowed_mentions=discord.AllowedMentions(users=False)
        )

    async def handle_leave_guild(self) -> None:
        await self.__leave_guild_log_message()

    async def __handle_returning_guild(self) -> None:
        await self.__new_guild_log_message(new=False)

    async def __handle_new_guild(self) -> None:
        await self.__new_guild_log_message()

    def __exists(self) -> None:
        sel_cmd = f"SELECT cached_name,owner_name,owner_id,total_members,latest_join_time FROM SERVERS WHERE server_id='{self.guild.id}'"
        rows = go.db_executor(sel_cmd)

        # If guild exists in database, update cache and return
        if go.exists(len(rows)):
            self.__update_cache(rows)
            return


        # If guild does not exist in database, create it
        ins_cmd = (
            "INSERT INTO SERVERS (server_id, latest_join_time, cached_name, owner_name, owner_id, total_members, status) VALUES "
            f"('{self.guild.id}', '{int(self.guild.me.joined_at.timestamp())}', \"{self.guild.name}\", \"{self.guild.owner.name}\", "
            f"'{self.guild.owner.id}', '{self.guild.member_count}', '{tunables('DEFAULT_GUILD_STATUS')}')"
        )
        go.db_executor(ins_cmd)
        asyncio.create_task(self.__handle_new_guild())
        print(f"Added server {self.guild.name} ({self.guild.id}) to database")
        
        for member in self.guild.members:
            u = MikoMember(user=member, client=self.client, check_exists_guild=False)
        self.set_member_numbers()

    def __update_cache(self, rows) -> None:
        params_temp = []
        params_temp.append("UPDATE SERVERS SET ")

        updating = False
        if self.guild.name != rows[0][0]:
            updating = True
            params_temp.append(f"cached_name=\"{self.guild.name}\"")
        
        if str(self.guild.owner) != rows[0][1]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"owner_name=\"{self.guild.owner}\"")
        
        if self.guild.owner.id != rows[0][2]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"owner_id=\"{self.guild.owner.id}\"")

        if self.guild.member_count != rows[0][3]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"total_members=\"{self.guild.member_count}\"")

        latest_join_time = int(self.guild.me.joined_at.timestamp())
        if latest_join_time != rows[0][4]:
           if updating: params_temp.append(",")
           updating = True
           params_temp.append(f"latest_join_time='{latest_join_time}'")
           if rows[0][4] != 0 and type(rows[0][4] == int): asyncio.create_task(self.__handle_returning_guild())
        
        if updating:
            params_temp.append(f" WHERE server_id=\"{self.guild.id}\"")
            upd_cmd = f"{''.join(params_temp)}"
            go.db_executor(upd_cmd)
        return


class MikoTextChannel(MikoGuild):

    def __init__(self, channel: discord.TextChannel, client: discord.Client):
        super().__init__(guild=channel.guild, client=client)
        self.channel = channel
        self.__exists()


    @property
    def is_private(self) -> bool:
        sel_cmd = (
            "SELECT private_true_false FROM CHANNELS WHERE "
            f"channel_id='{self.channel.id}' AND server_id='{self.guild.id}'"
        )
        val = go.db_executor(sel_cmd)
        if val == [] or "FALSE": return True
        return False
    @property
    def channel_messages(self):
        sel_cmd = (
            "SELECT SUM(count) FROM USER_MESSAGE_COUNT WHERE "
            f"channel_id='{self.channel.id}' AND server_id='{self.guild.id}'"
        )
        val = go.db_executor(sel_cmd)
        if val == [] or val is None: return 0
        return int(val)
    @property
    def channel_messages_nobots(self):
        sel_cmd = (
            "SELECT SUM(mc.count) FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON "
            "(mc.user_id=u.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE') WHERE "
            f"mc.channel_id='{self.channel.id}' AND mc.server_id='{self.guild.id}'"
        )
        val = go.db_executor(sel_cmd)
        if val == [] or val is None: return 0
        return int(val)

    def __exists(self) -> None:
        sel_cmd = f"SELECT * FROM CHANNELS WHERE server_id='{self.guild.id}' AND channel_id='{self.channel.id}'"
        rows = go.db_executor(sel_cmd)

        # If channel exists in database, update cache and return
        if go.exists(len(rows)):
            self.__update_cache(rows)
            return
        
        # If channel does not exist, create it
        ins_cmd = (
            "INSERT INTO CHANNELS (server_id,channel_id,channel_name,created_at) VALUES "
            f"('{self.guild.id}', '{self.channel.id}', \"{self.channel.name}\", "
            f"'{int(self.channel.created_at.timestamp())}')"
        )
        go.db_executor(ins_cmd)
        print(f"Added channel {self.channel.name} ({self.channel.id}) from {self.guild.name} ({self.guild.id}) to database")
    
    def __update_cache(self, rows) -> None:
        params_temp = []
        params_temp.append("UPDATE CHANNELS SET ")

        overwrite = self.channel.overwrites_for(self.channel.guild.default_role)
        if overwrite.view_channel == False:
            # Tell our database this channel is PRIVATE
            is_private = "TRUE"
        else:
            # Tell our database this channel is PUBLIC
            is_private = "FALSE"

        updating = False
        if self.channel.name != rows[0][0]:
            updating = True
            params_temp.append(f"channel_name=\"{self.channel.name}\"")
        
        if is_private != rows[0][1]:
            if updating: params_temp.append(",")
            updating = True
            params_temp.append(f"private_true_false=\"{is_private}\"")
        
        if updating:
            params_temp.append(f" WHERE server_id=\"{self.guild.id}\" AND channel_id=\"{self.channel.id}\"")
            upd_cmd = f"{''.join(params_temp)}"
            go.db_executor(upd_cmd)
        return




class MikoMember(MikoGuild):
    def __init__(self, user: discord.Member, client: discord.Client, guild_id: int = None, check_exists=True, check_exists_guild=True):
        if guild_id is None: super().__init__(guild=user.guild, client=client, check_exists=check_exists, check_exists_guild=check_exists_guild)
        else: super().__init__(guild=None, client=client, guild_id=guild_id, check_exists=check_exists, check_exists_guild=check_exists_guild)
        self.user = user
        self.greeting_task = None
        if check_exists and not user.pending: self.__exists()
    
    def __str__(self):
        return f"{self.user} - {self.guild} | MikoMember Object"

    @property
    def __last_updated(self) -> int:
        val = go.db_executor(
            "SELECT last_updated FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val is not None and val != []: return int(val)
        print(f"Error when checking 'last_updated' in MikoMember object: {val} | {self.user} | {self.user.id} | {self.guild} | {self.guild.id} | {int(time.time())}")
        return 1
    @property
    def first_joined(self) -> int:
        val = go.db_executor(
            "SELECT original_join_time FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return -1
        return int(val)
    @property
    def member_number(self) -> int:
        val = go.db_executor(
            "SELECT unique_number FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return -1
        return int(val)
    @property
    def user_voicetime(self) -> int:
        val = go.db_executor(
            "SELECT SUM(end_time - start_time) FROM VOICE_HISTORY WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}' AND end_time is not NULL AND "
            f"(end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} GROUP BY user_id"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    def user_messages(self) -> int:
        val = go.db_executor(
            "SELECT SUM(count) FROM USER_MESSAGE_COUNT WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    def user_messages_today(self) -> int:
        val = go.db_executor(
            "SELECT messages_today FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        if self.__last_updated >= today(): return int(val)
        return 0
    @property
    def considered_bot(self) -> bool:
        val = go.db_executor(
            "SELECT is_bot FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    def react(self) -> bool:
        val = go.db_executor(
            "SELECT react_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    def reactall(self) -> bool:
        val = go.db_executor(
            "SELECT react_all_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    def rename(self) -> bool:
        val = go.db_executor(
            "SELECT rename_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    def renameany(self) -> bool:
        val = go.db_executor(
            "SELECT rename_any_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None or val == "FALSE": return False
        return True
    @property
    def usernames(self):
        val = go.db_executor(
            f"SELECT name,last_change FROM USERNAME_HISTORY WHERE "
            f"user_id={self.user.id} ORDER BY last_change DESC"
        )
        names = []
        for item in val:
            names.append(item[0])
            names.append(item[1])
        return names
    @property
    def message_rank(self):
        val = go.db_executor(
            "SELECT row FROM ("
            "SELECT grouped.*, ROW_NUMBER() OVER ("
            "PARTITION BY grouped.server_id ORDER BY grouped.cnt DESC) AS row "
            "FROM ("
            "SELECT mc.server_id, mc.user_id, SUM(mc.count) AS cnt "
            "FROM USER_MESSAGE_COUNT AS mc "
            "INNER JOIN USERS AS u ON u.user_id=mc.user_id AND mc.server_id=u.server_id AND u.is_bot!='TRUE' "
            f"WHERE mc.server_id='{self.guild.id}' "
            "GROUP BY mc.user_id, mc.server_id) AS grouped) AS ranked "
            f"WHERE user_id='{self.user.id}' "
            "LIMIT 1"
        )
        if val == [] or val is None: return -1
        return int(val)
    @property
    def tokens(self) -> Token:
        return Token(u=self)
    @property
    def leveling(self) -> LevelClass:
        return LevelClass(u=self)
    # @property
    # def pets(self) -> PetOwner:
    #     return PetOwner(user=self.user)
    @property
    def bot_permission_level(self):
        val = go.db_executor(
            "SELECT bot_permission_level FROM USERS WHERE "
            f"user_id='{self.user.id}' "
            "ORDER BY bot_permission_level DESC LIMIT 1"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    def do_big_emojis(self):
        val = go.db_executor(
            "SELECT big_emojis FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if not self.profile.feature_enabled('BIG_EMOJIS'): return False
        if val == "FALSE" or not self.guild_do_big_emojis: return False
        return True
    @property
    def track_playtime(self):
        val = go.db_executor(
            "SELECT track_playtime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE" or not tunables('TRACK_PLAYTIME'): return False
        return True
    @property
    def public_playtime(self):
        val = go.db_executor(
            "SELECT public_playtime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE": return False
        return True
    @property
    def track_voicetime(self):
        val = go.db_executor(
            "SELECT track_voicetime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE" or not tunables('TRACK_VOICETIME'): return False
        return True
    @property
    def public_voicetime(self):
        val = go.db_executor(
            "SELECT public_voicetime FROM USER_SETTINGS WHERE "
            f"user_id='{self.user.id}'"
        )
        if val == "FALSE": return False
        return True

    '''
    user_avatar
        Will return guild avatar (if enabled by guild) if there is one
        or will return user avatar
    username
        Will return guild nickname (if enabled by guild) if there is one
        or will return user name (without discriminator)
    '''
    @property
    def user_avatar(self):
        if self.user.guild_avatar is None: return self.user.avatar
        elif self.nickname_in_ctx: return self.user.guild_avatar
        return self.user.avatar
    @property
    def username(self):
        if self.user.nick is None: return self.user.name
        elif self.nickname_in_ctx: return self.user.nick
        return self.user.name

    # async def __member_leave_message(self) -> None: pass

    async def __new_member_greeting(self, new=True) -> None:
        match self.status:

            case "THEBOYS":

                if self.client.user.id == 1017998983886545068: return # Only send welcome messages/role assignments if prod miko
                channel = self.guild.system_channel
                if channel is not None:
                    await asyncio.sleep(1) # To ensure welcome message is sent after join message
                    await channel.send(
                        f'Hi {self.user.mention}, welcome{" BACK" if not new else ""} to {self.guild}! :tada:\n'
                        f'> You are unique member `#{self.member_number}`'
                    )
                else: print(f"\n\n**************************\nCOULD NOT SEND WELCOME MESSAGE FOR {self.user}\n**************************\n\n")
                
                '''
                As of 12/11/2022, we will no longer assign the 'Bro'
                role to new users at join. [theboyshangout]
                '''

                holiday = self.guild.get_role(get_holiday(self.user, "ROLE"))
                await self.user.add_roles(holiday)
                
                if self.user.bot:
                    bot = self.guild.get_role(890642126445084702)
                    await self.user.add_roles(bot)
                    return

                leveling_role = self.leveling.get_role()
                await self.user.add_roles(leveling_role)
            
            case "YMCA":

                lifeguard = self.guild.get_role(1060366318462828574)
                if not self.user.bot: await self.user.add_roles(lifeguard)

    # async def handle_member_leave(self) -> None: pass

    async def __handle_new_member(self) -> None:
        if self.user.id == self.client.user.id: return
        await self.__new_member_greeting()
    
    async def __handle_returning_member(self) -> None:
        if self.user.id == self.client.user.id: return
        await self.__new_member_greeting(new=False)


    def __exists(self) -> None:
        sel_cmd = f"SELECT cached_username,latest_join_time FROM USERS WHERE user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        rows = go.db_executor(sel_cmd)
        self.__settings_exist()

        if go.exists(len(rows)):
            self.__update_cache(rows)
            return
        

        latest_join_time = int(self.user.joined_at.timestamp())
        ins_cmd = (
            "INSERT INTO USERS (server_id,user_id,original_join_time,latest_join_time,cached_username) VALUES "
            f"('{self.guild.id}', '{self.user.id}', '{latest_join_time}', '{latest_join_time}',"
            f"\"{self.user}\")"
        )
        go.db_executor(ins_cmd)
        self.greeting_task = asyncio.create_task(self.__handle_new_member(), name=f"New member to {self.guild}: {self.user}")
        print(f"Added user {self.user.id} ({self.user}) in guild {self.guild} ({self.guild.id}) to database")


        # Unique number handling
        sel_cmd = (
            "SELECT unique_number FROM USERS WHERE "
            f"server_id='{self.guild.id}' ORDER BY unique_number DESC LIMIT 1"
        )
        val = go.db_executor(sel_cmd)
        if val == [] or val is None: return
        upd_cmd = (
            f"UPDATE USERS SET unique_number={int(val)+1} WHERE user_id='{self.user.id}' "
            f"AND server_id='{self.guild.id}'"
        )
        go.db_executor(upd_cmd)
    
    def __settings_exist(self):
        rows = go.db_executor(f"SELECT * FROM USER_SETTINGS WHERE user_id='{self.user.id}'")
        if go.exists(len(rows)): return
        go.db_executor(
            f"INSERT INTO USER_SETTINGS (user_id) VALUES ('{self.user.id}')"
        )

    def __update_cache(self, rows) -> None:
        params_temp = []
        params_temp.append("UPDATE USERS SET ")

        updating = False
        if str(self.user) != rows[0][0]:
            updating = True
            params_temp.append(f"cached_username=\"{self.user}\"")

        latest_join_time = int(self.user.joined_at.timestamp())
        if latest_join_time != rows[0][1]:
           if updating: params_temp.append(",")
           updating = True
           params_temp.append(f"latest_join_time='{latest_join_time}'")
           if rows[0][1] != 0 and type(rows[0][1] == int):
               self.greeting_task = asyncio.create_task(self.__handle_returning_member(), name=f"Returning member to {self.guild}: {self.user}")
        
        if updating:
            params_temp.append(f" WHERE user_id=\"{self.user.id}\" AND server_id=\"{self.guild.id}\"")
            upd_cmd = f"{''.join(params_temp)}"
            go.db_executor(upd_cmd)
    
    def add_rename_hell(self) -> bool:
        val = go.db_executor(
            "SELECT rename_any_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == "TRUE": return False

        go.db_executor(
            "UPDATE USERS SET rename_any_true_false=\"TRUE\" WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        return True

    def del_rename_hell(self) -> bool:
        val = go.db_executor(
            "SELECT rename_any_true_false FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == "FALSE" or val == "": return False

        go.db_executor(
            "UPDATE USERS SET rename_any_true_false=\"FALSE\" WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        return True
    
    def manage_guild(self):
        perms = self.user.guild_permissions
        if perms.administrator: return True
        if perms.manage_guild: return True
        if self.bot_permission_level >= 5: return True
        return False
    
    def daily_msg_increment_user(self) -> None:
        self.daily_msg_increment_guild()
        upd_cmd = []
        upd_cmd.append("UPDATE USERS SET ")

        # Using this logic, 'last_updated' will only be updated when a user
        # sends a message in a guild for the first time that day. And again
        # when a message is sent on a following day
        if self.__last_updated >= today():
            upd_cmd.append(f"messages_today='{self.user_messages_today + 1}'")
        else:
            upd_cmd.append(f"messages_today='{self.user_messages_today + 1}',last_updated='{int(time.time())}'")

        upd_cmd.append(f" WHERE server_id={self.guild.id} AND user_id='{self.user.id}'")
        go.db_executor(''.join(upd_cmd))
        return
    
    def increment_statistic(self, key: str, increment: int=1) -> None:
        key = key.upper()
        val = go.db_executor(
            "SELECT value FROM STATISTICS WHERE "
            f"server_id='{self.guild.id}' AND user_id='{self.user.id}' "
            f"AND stat=\"{key}\" LIMIT 1"
        )
        if val is None or val == []:
            go.db_executor(
                "INSERT INTO STATISTICS (server_id,user_id,stat,value) VALUES "
                f"('{self.guild.id}', '{self.user.id}', '{key}', '{increment}')"
            )
            return
        
        go.db_executor(
            f"UPDATE STATISTICS SET value='{val + increment}' WHERE "
            f"server_id='{self.guild.id}' AND user_id='{self.user.id}' AND "
            f"stat='{key}'"
        )

    def get_statistic(self, key: str) -> int:
        val = go.db_executor(
            "SELECT value FROM STATISTICS WHERE "
            f"server_id='{self.guild.id}' AND user_id='{self.user.id}' "
            f"AND stat='{key}' LIMIT 1"
        )
        if val is None or val == []: return 0
        return int(val)
        

class MikoMessage():
    def __init__(self, message: discord.Message, client: discord.Client):
        self.user = MikoMember(user=message.author, client=client)
        self.channel = MikoTextChannel(channel=message.channel, client=client)
        self.message = message
        self.__exists()
    
    
    def __exists(self) -> None:
        row = go.db_executor(
            "SELECT count FROM USER_MESSAGE_COUNT WHERE "
            f"user_id={self.user.user.id} AND channel_id={self.channel.channel.id} "
            f"AND server_id={self.user.guild.id}"
        )
        if type(row) is int or go.exists(len(row)):
            self.__cached_count = int(row)
            self.__increment_msg_count()
            return
        self.__cached_count = 1

        go.db_executor(
            "INSERT INTO USER_MESSAGE_COUNT (user_id,channel_id,server_id,count) VALUES "
            f"('{self.user.user.id}', '{self.channel.channel.id}', '{self.user.guild.id}', '1')"
        )
        print(f"Added user_message_count for {self.user.user} ({self.user.user.id}) in channel {self.channel.channel} ({self.channel.channel.id}) in server {self.user.guild} ({self.user.guild.id}) to database")
    
    def __increment_msg_count(self) -> None:
        # Increment USER_MESSAGE_COUNT
        go.db_executor(
            f"UPDATE USER_MESSAGE_COUNT SET count='{self.__cached_count + 1}' WHERE "
            f"user_id={self.user.user.id} AND channel_id={self.channel.channel.id} AND server_id={self.user.guild.id}"
        )

        # Increment messages_today [MEMBER, GUILD]
        self.user.daily_msg_increment_user()
    
    async def handle_leveling(self) -> None:
        if not self.message.author.bot and self.channel.profile.feature_enabled('LEVELING'):
            lc = self.user.leveling
            await lc.determine_xp_gained_msg()
            tc = self.user.tokens
            tc.determine_tokens_gained_msg()
    
    async def handle_persistent_player_reposition(self) -> None:
        # Persistent music player embed. Will delete the embed and re-send
        # it so the embed is always the first message in the channel.
        try: sesh = AUDIO_SESSIONS[self.message.guild.id]
        except: sesh = None
        if sesh is not None and self.channel.music_channel.id == self.message.channel.id:
            # If message is not from miko OR if message IS from miko AND is not an embed, reposition
            if self.message.author != self.user.client.user or (self.message.embeds == [] and self.message.author == self.user.client.user):
                await sesh.reposition()
    
    async def handle_rename_hell(self) -> None:
        if self.channel.guild_messages % 20 == 0 and self.message.channel.id != 963928489248063539:
            users = self.user.renamehell_members
            if users != [] and users is not None:
                await self.message.add_reaction('<:nametag:1011514395630764032>')
                for user in users:
                    user = self.user.guild.get_member(int(user))
                    u = MikoMember(user=user, client=self.user.client)
                    try: await u.user.edit(nick=generate_nickname(self.message))
                    except discord.Forbidden as e:
                        await self.message.channel.send(f"Unable to rename {u.user.mention}, removing them from the renameany list: `{e}`")
                        u.del_rename_hell()

    def __big_emoji_embed(self, auth) -> discord.Embed:
        msg: discord.Message = self.message
        embed = discord.Embed (
            color = 0x2f3136,
        )
        embed.set_author(icon_url=self.user.user_avatar, name=f"{self.user.username}{'' if auth is None else f' → {auth.username}'}")
        url, emoji_name = get_emoji_url(msg.content)
        embed.set_image(url=url)
        embed.set_footer(text=f":{emoji_name}:")
        return embed

    async def handle_big_emojis(self) -> bool:
        if self.user.do_big_emojis and not self.message.author.bot:
            if len(self.message.content.split()) == 1 and self.message.author.id != self.user.client.user.id:
                if self.message.content.startswith("<") and self.message.content[1] not in ['@', '#']:
                    try:
                        if self.message.reference is not None:
                            ref: discord.Message = await self.message.channel.fetch_message(self.message.reference.message_id)
                            auth = MikoMember(user=ref.author, client=self.user.client)
                        else: auth = None

                        await self.message.delete()
                        e = self.__big_emoji_embed(auth)
                        if auth is not None: await ref.reply(embed=e, silent=True)
                        else: await self.message.channel.send(embed=e, silent=True)
                        self.user.increment_statistic('BIG_EMOJIS_SENT')
                        return True
                    except Exception as e: print(f"Big emoji error: {e}")
        return False
    
    async def handle_bruh_react(self) -> None:
        if not self.channel.profile.feature_enabled('BRUH_REACT') or self.user.client.user.id != 1017998983886545068: return
        for word in tunables('BRUH_REACT_WORDS').split():
            racist_regex =  rf".*\b{word}\b.*"
            if re.match(racist_regex, self.message.content.lower()) or word == self.message.content.lower():
                emoji = [
                    "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
                    "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
                    "\N{REGIONAL INDICATOR SYMBOL LETTER U}",
                    "\N{REGIONAL INDICATOR SYMBOL LETTER H}"
                ]
                for i, letter in enumerate(emoji):
                    if i > 0: await asyncio.sleep(0.5)
                    await self.message.add_reaction(letter)
                break
    
    async def handle_instagram_reel_links(self) -> bool:
        if not self.channel.profile.feature_enabled('DELETE_INSTAGRAM_REEL_LINKS'): return False
        ig_regex = r".*\binstagram.com\/reel\b.*"
        if re.match(ig_regex, self.message.content.lower()):
            await self.message.delete()
            return True
        return False
    
    async def handle_clown_react(self) -> None:
        if self.message.author.id in self.channel.clown_react_users:
            await self.message.add_reaction('<:clown:903162517365330000>')
            
    async def handle_react_all(self) -> None:
        imgay = [
            "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
            "\N{LARGE BLUE SQUARE}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
            "\N{REGIONAL INDICATOR SYMBOL LETTER Y}"
        ]
        sample_list = random.sample(react_all_emoji_list(), 19)
        if self.message.author.id in self.channel.react_all_users:
            num = random.randint(0, 10)
            if num == 5:
                for emoji in imgay:
                    await asyncio.sleep(0.5)
                    await self.message.add_reaction(emoji)
            else:
                for emoji in sample_list:
                    await asyncio.sleep(0.5)
                    await self.message.add_reaction(emoji)