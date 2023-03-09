import discord
import time
from Database.database import get_user_total_msgs_server
from Database.database_class import Database
from tunables import tunables
from Voice.VoiceActivity import VoiceActivity
tc = Database("TokenClass.py")

class Token:

    def __init__(self, u):
        self.u = u

    @property
    def tokens(self):
        sel_cmd = f"SELECT tokens FROM USERS WHERE user_id='{self.u.user.id}' AND server_id='{self.u.guild.id}'"
        val = tc.db_executor(sel_cmd)
        if val == [] or val is None: return 0
        return int(val)
    @property
    def msgs(self):
        return get_user_total_msgs_server(user=self.u.user, server=self.u.guild)
    
    def determine_tokens_gained_msg(self):
        if self.msgs % tunables('THRESHOLD_MESSAGES_FOR_TOKEN') != 0: return
        self.add_tokens(tunables('TOKENS_GAINED_FROM_MESSAGES'))
    
    def add_tokens(self, tokens):
        upd_cmd = (
            f"UPDATE USERS SET tokens='{self.tokens + tokens}' WHERE "
            f"user_id='{self.u.user.id}' AND server_id='{self.u.guild.id}'"
        )
        tc.db_executor(upd_cmd)
    
    def can_afford(self, price):
        return self.tokens >= price