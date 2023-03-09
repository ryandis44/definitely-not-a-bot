import time
import discord
from Database.database import get_user_total_msgs_server
from Database.database_class import Database
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from tunables import *
from misc.misc import locate_htable_obj
lc = Database("LevelClass.py")

class LevelClass:


    def __init__(self, u):
        self.u = u
        self.user: discord.Member = u.user
        self.guild: discord.Guild = u.guild
    
    @property
    def active_voicetime(self):
        current: VoiceActivity = locate_htable_obj(
            map=VOICE_SESSIONS,
            key=self.user.id
        )[0]
        if current is None: return 0
        return current.time_elapsed
    @property
    def xp(self) -> int:
        return self.voice_xp + self.msg_xp
    @property
    def msgs(self):
        return get_user_total_msgs_server(user=self.user, server=self.guild)
    @property
    def voice_xp(self) -> int:
        val = lc.db_executor(
            "SELECT voice_xp FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    def msg_xp(self) -> int:
        val = lc.db_executor(
            "SELECT msg_xp FROM USERS WHERE "
            f"user_id='{self.user.id}' AND server_id='{self.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)
    @property
    def level(self) -> int:
        lv = 0
        if self.xp >= tunables('XP_LEVEL_01'): lv += 1
        if self.xp >= tunables('XP_LEVEL_02'): lv += 1
        if self.xp >= tunables('XP_LEVEL_03'): lv += 1
        if self.xp >= tunables('XP_LEVEL_04'): lv += 1
        if self.xp >= tunables('XP_LEVEL_05'): lv += 1
        if self.xp >= tunables('XP_LEVEL_06'): lv += 1
        if self.xp >= tunables('XP_LEVEL_07'): lv += 1
        if self.xp >= tunables('XP_LEVEL_08'): lv += 1
        if self.xp >= tunables('XP_LEVEL_09'): lv += 1
        if self.xp >= tunables('XP_LEVEL_10'): lv += 1
        return int(lv)
    
    async def determine_xp_gained_msg(self) -> None:
        if self.msgs % tunables('THRESHOLD_MESSAGES_FOR_XP') != 0: return
        await self.add_xp_msg(tunables('XP_GAINED_FROM_MESSAGES'))
    
    async def determine_xp_gained_voice(self, sesh: VoiceActivity) -> None:
        if sesh.time_elapsed >= tunables('THRESHOLD_VOICETIME_FOR_XP') and\
            sesh.time_elapsed % tunables('THRESHOLD_VOICETIME_FOR_XP') <= 90\
                and sesh.last_xp_award <= int(time.time() - 90):
            await self.add_xp_voice(tunables('XP_GAINED_FROM_VOICETIME'))
            sesh.last_xp_award = int(time.time())
    
    async def add_xp_msg(self, xp, manual=False) -> None:
        lv = self.level
        upd_cmd = f"UPDATE USERS SET msg_xp={self.msg_xp + xp} WHERE server_id='{self.guild.id}' AND user_id='{self.user.id}'"
        lc.db_executor(upd_cmd)
        if self.level > lv and not manual: await self.__assign_role()

    async def add_xp_voice(self, xp, manual=False) -> None:
        lv = self.level
        upd_cmd = f"UPDATE USERS SET voice_xp={self.voice_xp + xp} WHERE server_id='{self.guild.id}' AND user_id='{self.user.id}'"
        lc.db_executor(upd_cmd)
        if self.level > lv and not manual: await self.__assign_role()
    
    async def __assign_role(self) -> None:
        if self.u.client.user.id != 1017998983886545068: return
        role = self.get_role()
        leveling_roles = [
            self.guild.get_role(tunables('RANK_ID_LEVEL_01')),
            self.guild.get_role(tunables('RANK_ID_LEVEL_05')),
            self.guild.get_role(tunables('RANK_ID_LEVEL_10'))
        ]
        await self.user.remove_roles(*leveling_roles)
        await self.user.add_roles(role)
    
    def __get_role_id(self) -> int:
        level = self.level
        if level >= 10: return tunables('RANK_ID_LEVEL_10')
        elif level >= 5: return tunables('RANK_ID_LEVEL_05')
        else: return tunables('RANK_ID_LEVEL_01')
    
    def get_role(self) -> discord.Role:
        id = self.__get_role_id()
        return self.guild.get_role(id)