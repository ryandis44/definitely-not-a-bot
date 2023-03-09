import asyncio
import time
import discord
from Database.database_class import Database
from Playtime.playtime import today
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from misc.misc import determine_htable_key, locate_htable_obj, time_elapsed
from Database.GuildObjects import MikoMember
from tunables import *
tv = Database("Voice.track_voice.py")

def fetch_voicetime_sessions(client: discord.Client):
    
    sel_cmd = "SELECT value FROM PERSISTENT_VALUES WHERE variable='GLOBAL_REBOOT_TIME_ACTIVITY'"
    end_time = tv.db_executor(sel_cmd)
    if end_time is None:
        sel_cmd = "SELECT end_time FROM VOICE_HISTORY WHERE end_time is not NULL ORDER BY end_time DESC LIMIT 1"
        end_time = tv.db_executor(sel_cmd)
    
    if end_time is None or end_time == []:
        print("Could not fetch a time to restore any voicetime sessions.")
        return
    
    sel_cmd = (
        "SELECT user_id, start_time, server_id FROM VOICE_HISTORY "
        f"WHERE end_time={end_time}"
    )
    val = tv.db_executor(sel_cmd)
    rst = 0
    t = int(time.time()) - tunables('THRESHOLD_RESUME_REBOOT_VOICE_ACTIVITY')
    def restore(member: discord.Member, restore=True):
        u = MikoMember(user=member, client=client)
        key = determine_htable_key(map=VOICE_SESSIONS, key=member.id)
        if restore: VOICE_SESSIONS[key] = VoiceActivity(u=u, start_time=t)
        else: VOICE_SESSIONS[key] = VoiceActivity(u=u)
        return
    
    # Not very fast, but only way to achieve voice session restoration
    for guild in client.guilds:
        if val == []: break
        for member in guild.members:
            if val == []: break
            if val != [] and any(str(member.id) in sl for sl in val) and member.voice is not None:
                

                # Find which iteration of val the member.id was matched to
                outer = 0
                found = False
                for i, entry in enumerate(val):
                    for user in entry:
                        if user == str(member.id):
                            found = True
                            break
                    if found:
                        outer = i
                        break


                # If the current app id is equal to the playtime database entry, continue
                if str(val[outer][2]) == str(guild.id):
                    
                    #if val[outer][1] >= t:
                    restore(member)
                    print(f"> Restored {member}'s voice session")
                    rst += 1
                else:
                    restore(member=member, restore=False)
                    print(f"> {member} switched guilds during restart, created a new voice session for them")

                
                del val[outer] # Done processing this user, delete from memory

    if rst > 0:
        print(f"Restored {rst} voice sessions.")
        print("Voice session restoration complete.")
    else: print("No voice sessions were restored.")
    return

# Responsible for calculating total voicetime in a search result
def total_voicetime_result(result):
    voicetime = 0
    for val in result: voicetime += val[2]
    return int(voicetime)

# Responsible for calculating average voicetime in a search result
def avg_voicetime_result(result):
    total = 0
    i = 0
    for val in result:
        if val[3] == 0: total += val[2]
        else: total += val[3]
        i += 1
    return int(total / i)

def get_recent_voice_activity(user: discord.Member, page_size=10, offset=0):
    
    sel_cmd = (
        "SELECT end_time, server_id, (end_time - start_time) AS total "
        f"FROM VOICE_HISTORY WHERE user_id='{user.id}' AND "
        f"end_time is not NULL "
        f"AND (end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} "
        "ORDER BY end_time DESC "
        f"LIMIT {page_size} OFFSET {offset}"
    )
    
    items = tv.db_executor(sel_cmd)
    if items == []: return None
    return items

def get_voicetime_today(user_id) -> int:
    sel_cmd = (
        f"SELECT SUM(end_time - {today()}) "
        "FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND end_time is not NULL AND end_time>='{today()}' AND (end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} "
        f"AND start_time<'{today()}'"
    )
    voice_activity_before_midnight = tv.db_executor(sel_cmd)

    sel_cmd = (
        "SELECT SUM(end_time - start_time) "
        "FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND end_time is not NULL AND start_time>='{today()}' AND (end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} "
    )
    voice_activity_after_midnight = tv.db_executor(sel_cmd)

    if voice_activity_before_midnight is None: voice_activity_before_midnight = 0
    if voice_activity_after_midnight is None: voice_activity_after_midnight = 0
    return int(voice_activity_after_midnight + voice_activity_before_midnight)

def get_voicetime_today_user_guild(user_id, server_id) -> int:
    sel_cmd = (
        f"SELECT SUM(end_time - {today()}) "
        "FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND server_id='{server_id}' AND end_time is not NULL AND end_time>='{today()}' AND (end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} " # AND (end_time - start_time)>300
        f"AND start_time<'{today()}'"
    )
    voice_activity_before_midnight = tv.db_executor(sel_cmd)

    sel_cmd = (
        "SELECT SUM(end_time - start_time) "
        "FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND server_id='{server_id}' AND end_time is not NULL AND start_time>='{today()}' AND (end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} "
    )
    voice_activity_after_midnight = tv.db_executor(sel_cmd)

    if voice_activity_before_midnight is None: voice_activity_before_midnight = 0
    if voice_activity_after_midnight is None: voice_activity_after_midnight = 0
    return int(voice_activity_after_midnight + voice_activity_before_midnight)

def get_total_voice_activity_updates(user_id: int) -> int:
    sel_cmd = (
        "SELECT COUNT(*) FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND end_time is not NULL AND "
        f"(end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')}"
    )
    val = tv.db_executor(sel_cmd)
    if val == []: return int(0)
    else: return int(val)

def get_total_voicetime_user(user_id) -> int:
    sel_cmd = (
        "SELECT SUM(end_time - start_time) FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND end_time is not NULL AND "
        f"(end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} GROUP BY user_id"
    )
    val = tv.db_executor(sel_cmd)
    if val == []: return int(0)
    else: return int(val)

def get_total_voicetime_user_guild(user_id, server_id) -> int:
    sel_cmd = (
        "SELECT SUM(end_time - start_time) FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND server_id='{server_id}' AND end_time is not NULL AND "
        f"(end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')} GROUP BY user_id"
    )
    val = tv.db_executor(sel_cmd)
    if val == []: return int(0)
    else: return int(val)

def get_average_voice_session(user_id: discord.User) -> str:
    
    sel_cmd = (
        "SELECT AVG(end_time - start_time) FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND "
        f"(end_time - start_time)>={tunables('THRESHOLD_LIST_VOICE_ACTIVITY')}"
    )

    val = tv.db_executor(sel_cmd)
    if val is None or val == []: return "`None`"
    return f"`{time_elapsed(int(val), 'h')}`"

def last_voiced_server(user_id, server_id) -> int:
    
    sel_cmd = (
        "SELECT end_time FROM VOICE_HISTORY WHERE "
        f"user_id='{user_id}' AND server_id='{server_id}' "
        "AND end_time is not NULL "
        "ORDER BY end_time DESC LIMIT 1"
    )
    
    val = tv.db_executor(sel_cmd)
    if val == []:
        return 0
    else: return int(val)

async def process_voice_state(u: MikoMember, bef: discord.VoiceState, cur: discord.VoiceState):

    # if channel has not changed, ignore this update
    if bef.channel == cur.channel: return

    '''
    Using functions locate_htable_obj and determine_htable_key, we are
    able to briefly allow for "duplicate" hash entries, allowing us to handle
    when discord sends updates out of order ('join' before 'left').
    '''
    def stop():
        sesh = locate_htable_obj(map=VOICE_SESSIONS,
                                 key=u.user.id,
                                 comparable=u.guild.id)
        if sesh[0] is not None:
            sesh[0].end()
            del VOICE_SESSIONS[sesh[1]]
           
    async def start():
        if not u.track_voicetime: return
        sesh = locate_htable_obj(map=VOICE_SESSIONS,
                                 key=u.user.id,
                                 comparable=u.guild.id)
        if sesh[0] is not None: stop()
        key = determine_htable_key(map=VOICE_SESSIONS, key=u.user.id)
        VOICE_SESSIONS[key] = VoiceActivity(u=u)

    async def check_tracking():
        sesh = locate_htable_obj(map=VOICE_SESSIONS,
                                 key=u.user.id,
                                 comparable=u.guild.id)
        if sesh[0] is None: await start()
    
    '''If member joins any voice channel that is not the afk channel, start tracking'''
    if bef.channel is None and (cur.channel is not None and cur.channel != cur.channel.guild.afk_channel):
        await start()
        return
    
    '''If member leaves all voice channels or goes to the afk channel, stop tracking'''
    if (bef.channel is not None and bef.channel != u.guild.afk_channel) and (cur.channel is None or cur.channel == cur.channel.guild.afk_channel):
        stop()
        return
    
    '''
    If member is in afk channel but moves to active channel, start tracking
    If member is in channel in same guild but is moved/switches to another
    channel, continue tracking
    '''
    if bef.channel is not None and (cur.channel is not None and cur.channel != u.guild.afk_channel):
        await check_tracking()
        return