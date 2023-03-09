''' Voicetime activity tracking 1.0

This class handles all voicetime tracking. It is very similar to the GameActivity class,
which tracks all playtime activity.

Like the GameActivity class, this class will determine if an entry can be "resumed" upon
creation.

If an activity is started but it is not "resumable", we will create a new entry which can
be resumed.

An activity can be resumed if:
    - The activity is being resumed in the same guild
    - The activity is being resumed within 2 minutes of the previous activity ending
    - The activity is not being resumed in the guild 'afk channel'.

If an activity is resumed, we will set the end_time value in the database back to NULL,
just as it is when an activity is new and has not yet concluded for the first time.
'''

import asyncio
import discord
from Database.database_class import Database
from misc.misc import time_elapsed
from tunables import *
import time

VOICE_SESSIONS = {}

va = Database("Voice.VoiceActivity.py")
class VoiceActivity():
    
    def __init__(self, u, start_time=None):
        self.u = u
        self.__member: discord.Member = u.user
        if start_time is None:
            self.__start_time = int(time.time())
            self.__resume_threshold = self.__start_time - tunables('THRESHOLD_RESUME_VOICE_ACTIVITY')
        else:
            self.__start_time = start_time
            self.__resume_threshold = self.__start_time - tunables('THRESHOLD_RESUME_REBOOT_VOICE_ACTIVITY')
        self.__guild: discord.Guild = u.guild
        self.resume_time = 0
        self.__stored_voicetime: int = u.user_voicetime
        self.__new_voice_entry()
        self.last_xp_award = -1
        self.last_token_award = -1
        self.active = True
        # if u.profile.
        asyncio.create_task(self.heartbeat())
    
    @property
    def comparable(self) -> int:
        return self.__guild.id
    
    @property
    def time_elapsed(self) -> int:
        return int(int(time.time()) - self.__start_time)
    
    @property
    def guild(self) -> discord.Guild:
        return self.__guild

    @property
    def start_time(self) -> int:
        return self.__start_time
    
    @property
    def member(self) -> discord.Member:
        return self.__member
    
    def end(self, current_time=None): self.__close_voice_entry(current_time)
    
    def __new_voice_entry(self, attempt=0):
        sel_cmd = (
            "SELECT end_time,start_time FROM VOICE_HISTORY WHERE "
            f"user_id={self.__member.id} AND end_time is not NULL "
            f"AND end_time>='{self.__resume_threshold}' "
            f"AND server_id='{self.__guild.id}' "
            "ORDER BY end_time DESC "
            "LIMIT 1"
        )
        val = va.db_executor(sel_cmd)

        # If no voice activity was found
        if val == []:
            ins_cmd = (
                "INSERT INTO VOICE_HISTORY (server_id,user_id,start_time) VALUES "
                f"('{self.__guild.id}', '{self.__member.id}', '{self.__start_time}')"
            )
            va.db_executor(ins_cmd)
        
        
        # If end time is less than our resume
        # threshold—in this case, x minutes—
        # resume the activity.
        elif int(val[0][0]) >= self.__resume_threshold:
            self.resume_time = int(time.time())
            self.__start_time = int(val[0][1])
            upd_cmd = (
                "UPDATE VOICE_HISTORY SET end_time=NULL,"
                f"resume_time='{self.resume_time}' WHERE "
                f"user_id='{self.__member.id}' "
                f"AND server_id='{self.__guild.id}' "
                f"AND start_time='{self.__start_time}'"
            )
            va.db_executor(upd_cmd)
            
        
        # Verify a database entry has been made, else __end_session
        sel_cmd = (
            "SELECT * FROM VOICE_HISTORY WHERE "
            f"user_id='{self.__member.id}' AND end_time is NULL "
            f"AND server_id='{self.__guild.id}' "
            f"AND start_time='{self.__start_time}' "
            "LIMIT 1"
        )
        val = va.db_executor(sel_cmd)
        if val == [] and not attempt >= 5:
            self.__new_voice_entry(attempt + 1) # Only try 5 times
        elif attempt >= 5: self.end() # No entry found after 5 attempts, abort tracking this entry entirely
        return

    def __close_voice_entry(self, current_time):
        if current_time is None: current_time = int(time.time())
        upd_cmd = (
            f"UPDATE VOICE_HISTORY SET end_time='{current_time}' "
            f"WHERE user_id='{self.__member.id}' AND start_time='{self.__start_time}' "
            f"AND end_time is NULL AND server_id='{self.__guild.id}'"
        )
        va.db_executor(upd_cmd)
        self.__end_session()
    
    
    def __end_session(self):
        self.active = False
        del self
    
    async def heartbeat(self) -> None:
        
        voicetime = self.__stored_voicetime - self.time_elapsed
        # Determine the modulo of the stored voicetime so we can use it as reference
        # if a user resumes their voicetime entry.
        prev_tok = voicetime % tunables('THRESHOLD_VOICETIME_FOR_TOKEN')
        prev_xp = voicetime % tunables('THRESHOLD_VOICETIME_FOR_XP')
        
        while self.active:

            await asyncio.sleep(1)
            combined = voicetime + self.time_elapsed
            current_tok = combined % tunables('THRESHOLD_VOICETIME_FOR_TOKEN')
            current_xp = combined % tunables('THRESHOLD_VOICETIME_FOR_XP')
            # print(
            #     f"Stored voicetime: {time_elapsed(voicetime, 'h')} | "
            #     f"Cached voicetime: {self.time_elapsed} | "
            #     f"Combined voicetime: {voicetime + self.time_elapsed} % T:{current_tok} |  XP:{current_xp} | "
            #     f"prev_tok == {prev_tok} current_tok == {current_tok} | "
            #     f"resume_time == {self.resume_time} | start_time == {self.__start_time} | rt - st == {self.resume_time - self.__start_time}"
            #     f"prev_xp == {prev_xp} current_xp == {current_xp}"
            # )
            
            # If prev >= current, that means we have hit the 2h mark and the modulo
            # has reset back to zero.
            if (self.resume_time - self.start_time) > tunables('THRESHOLD_LIST_VOICE_ACTIVITY') or self.resume_time == 0:
                if prev_tok > current_tok:
                    # print(f"2h found? prev == {prev_tok} current == {current_tok}")
                    self.u.tokens.add_tokens(tunables('TOKENS_GAINED_FROM_VOICETIME'))
                    # print(f"{tunables('TOKENS_GAINED_FROM_VOICETIME')} token added to {self.member}")
                
                if prev_xp > current_xp:
                    # print(f"4 min found? prev_xp == {prev_xp} current == {current_xp}")
                    await self.u.leveling.add_xp_voice(tunables('XP_GAINED_FROM_VOICETIME'))
                    # print(f"{tunables('XP_GAINED_FROM_VOICETIME')} xp added to {self.member}")
            else:
                self.resume_time += 1
                # print(
                #     f"Cancelling token/xp award. Entry is less than '{tunables('THRESHOLD_LIST_VOICE_ACTIVITY')}' seconds: "
                #     f"resume_time == {self.resume_time - 90} | start_time == {self.__start_time}"
                # )
            
            prev_tok = combined % tunables('THRESHOLD_VOICETIME_FOR_TOKEN')
            prev_xp = combined % tunables('THRESHOLD_VOICETIME_FOR_XP')
        return