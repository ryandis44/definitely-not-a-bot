import asyncio
import uuid
import discord
from discord.ext import commands
from Database.database_class import Database
from tunables import tunables
from discord.ext.commands import Context
import os
from dotenv import load_dotenv
from Playtime.playtime import sessions_hash_table
from Voice.VoiceActivity import VOICE_SESSIONS

from Playtime.playtime import fetch_playtime_sessions, find_type_playing, has_app_id, identify_current_application, sesh_id, start_time
from misc.misc import get_user_object
from Database.GuildObjects import MikoMember
from Polls.UI import active_polls
from Music.LavalinkClient import AUDIO_SESSIONS
load_dotenv()

dbg = Database("cogs.debugger.py")

class Debugger(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Generates a random number between 0 and 100 [inclusive]
    @commands.command(name='debug', aliases=['d'])
    @commands.guild_only()
    async def debugger(self, ctx: Context, *args):
        #if len(ctx.message.mentions) >= 1: user = ctx.message.mentions[0]
        #else: user = ctx.author
        u = MikoMember(user=ctx.author, client=self.client)
        if u.bot_permission_level <= 4: return
        u.increment_statistic('DEBUGGER_USED')

        if len(args) == 0:
            await ctx.channel.send(
                f"Please provide something to debug: `{os.getenv('CMD_PREFIX1')}d <category> (user)`\n"
                "Categories: `a` (activity), `gl` (guild list), "
                "`as` (active playtime sessions), `av` (active voice sessions), `po` (active polls) "
                "`music` (active music sessions), `tasks` (all active asyncio tasks)"
            )
            return
        
        if len(args) <= 1:
            user = ctx.author
        else:
            user = await get_user_object(self, ctx, args[1])
        
        match args[0].lower():
            case 'a':

                temp = []
                temp.append(f"All current activities: `{user.activities}`\n")

                for i, activity in enumerate(user.activities):
                    cur_playing = find_type_playing(user)
                    if cur_playing[0] and i == cur_playing[1]:
                        game = identify_current_application(activity, has_app_id(activity))
                    else:
                        game = None
                    st = start_time(activity)
                    temp.append(f"\nActivity `{i+1}`:\n")
                    temp.append(f"> Raw: `{activity}`\n")
                    temp.append(f"> Start time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Session ID: `{sesh_id(activity)}`\n")
                    temp.append(f"> Activity Info (Database): `{game}`")
                
                sesh = sessions_hash_table.get_val(user.id)
                if sesh is not None:
                    st = sesh.get_start
                    temp.append("\n")
                    temp.append(f"\n`GameActivity` Object: `{sesh}`\n")
                    temp.append(f"> User ID: `{sesh.get_id}`\n")
                    temp.append(f"> Start Time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Session ID: `{sesh.get_session_id}`\n")
                    temp.append(f"> App name/ID: `{sesh.get_app_name}`/`{sesh.get_app_id}`\n")
                    temp.append(f"> Restored: `{sesh.is_restored}`\n")
                    temp.append(f"> Resumed: `{sesh.is_resumed}` { f'<t:{sesh.get_resume_time}:R>' if sesh.get_resume_time is not None else '' }")

                # If active playtime session, print

                await ctx.channel.send(''.join(temp))
            
            case 'gl':
                
                guilds = self.client.guilds
                temp = []
                temp.append(f"I am in the following guilds (`{len(guilds)}`): ")
                for i, guild in enumerate(guilds):
                    if i == len(guilds) - 1:
                        temp.append(f"`{guild} ({guild.member_count})`")
                    else: temp.append(f"`{guild} ({guild.member_count})`, ")
                await ctx.channel.send(''.join(temp))
                
            #case 'rs':
            #    await ctx.channel.send("Attempting to restore sessions...")
            #    fetch_playtime_sessions(self.client)
            #    await ctx.channel.send("Active sessions restored.")
            
            case 'as': # Active playtime sessions
                temp = []
                sessions = sessions_hash_table.get_all
                await ctx.channel.send(f"`{len(sessions)}` active playtime :video_game: sessions")
                for pair in sessions:
                    st = pair[0][1].get_start
                    temp.append(f"\n{pair[0][1].get_user}:\n")
                    temp.append(f"> User ID: `{pair[0][1].get_id}`\n")
                    temp.append(f"> Start Time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Session ID: `{pair[0][1].get_session_id}`\n")
                    temp.append(f"> App name/ID: `{pair[0][1].get_app_name}`/`{pair[0][1].get_app_id}`\n")
                    temp.append(f"> Restored: `{pair[0][1].is_restored}`\n")
                    temp.append(f"> Resumed: `{pair[0][1].is_resumed}` { f'<t:{pair[0][1].get_resume_time}:R>' if pair[0][1].get_resume_time is not None else '' }\n")
                await ctx.channel.send(''.join(temp))
            
            case 'va': # Active voice sessions
                temp = []
                sessions = VOICE_SESSIONS.items()
                await ctx.channel.send(f"`{len(sessions)}` active voice :microphone2: sessions")
                await ctx.channel.send(f"{sessions}")
                for key, val in sessions:
                    st = val.start_time
                    user: discord.Member = val.member
                    temp.append(f"\n{user}:\n")
                    temp.append(f"> User ID: `{user.id}`\n")
                    temp.append(f"> Start Time: `{st}` { f'<t:{st}:R>' if st is not None else '' }\n")
                    temp.append(f"> Channel: {user.voice.channel.mention}\n")
                    temp.append(f"> Guild: `{val.guild}`\n")
                    temp.append(f"> Guild ID: `{val.guild.id}`\n")
                await ctx.channel.send(''.join(temp))
            
            case 'hash':
                
                aid = None
                res = None
                while True: # Make sure we do not have duplicate application id
                    aid = uuid.uuid4().hex
                    sel_check_cmd = f"SELECT * FROM APPLICATIONS WHERE app_id='{aid}'"
                    res = dbg.db_executor(sel_check_cmd)
                    if res == []: break
                
                await ctx.channel.send(f"{aid} {res}")
            
            case 'po':

                temp = []
                polls = active_polls.get_all
                print(f"DEBUG REQUESTED 'po': {polls}")
                await ctx.channel.send(f"`{len(polls)}` active polls :bar_chart:")
                for poll in polls:
                    user: discord.Member = poll[0][1].author.user
                    temp.append(f"\n{user}:\n")
                    temp.append(f"> End Time: <t:{poll[0][1].expiration}:R>\n")
                    temp.append(f"> Guild: `{poll[0][1].author.user.guild}`\n")
                    temp.append(f"> Guild ID: `{poll[0][1].author.user.guild.id}`")
                    temp.append(f"> Message Link: [WIP]")
                await ctx.channel.send(''.join(temp))

            case 'music':

                temp = []
                seshs = AUDIO_SESSIONS.items()
                print(f"DEBUG REQUESTED 'music': {seshs}")
                await ctx.channel.send(f"`{len(seshs)}` active music sessions :musical_note:")
                for key, sesh in seshs:
                    user: discord.Member = sesh.original_interaction.user
                    temp.append(f"\n{user} in {user.guild}:\n")
                    temp.append(f"> Player Object: `{sesh.player}`\n")
                    temp.append(f"> Message ID: `{sesh.message}`\n")
                    temp.append(f"> Stopping?: `{sesh.stopping}`")
                await ctx.channel.send(''.join(temp))

            case 'tasks':

                temp = []
                seshs = AUDIO_SESSIONS.items()
                print(f"DEBUG REQUESTED 'music': {asyncio.all_tasks()}")
                await ctx.channel.send(content=f"{asyncio.all_tasks()}")




async def setup(client: commands.Bot):
    await client.add_cog(Debugger(client))