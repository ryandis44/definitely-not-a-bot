import asyncio
from curses.ascii import isdigit
import discord
from discord.ext import commands
from discord import app_commands
import typing
from Database.GuildObjects import MikoMember
from Playtime.Views import PlaytimePageSelector, PlaytimeSearchPageSelector
from Voice.Views import VoicetimePageSelector, VoicetimeSearchPageSelector
from Voice.embeds import voicetime_embed, voicetime_search_embed
from Voice.track_voice import avg_voicetime_result, get_average_voice_session, get_total_voice_activity_updates, get_total_voicetime_user, get_total_voicetime_user_guild, get_voicetime_today, total_voicetime_result
from misc.embeds import modified_playtime_embed
from Playtime.playtime import avg_playtime_result, get_app_from_str, get_average_session, get_total_activity_updates, get_total_playtime_user, playtime_embed, total_playtime_result
from tunables import *
from Database.database_class import Database, AsyncDatabase
import re
import os
from dotenv import load_dotenv
load_dotenv()

app_cmd_db = AsyncDatabase("PlaytimeCog.py")
        

class PlaytimeCog(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.tree = app_commands.CommandTree(self.client)


    @app_commands.command(name="playtime", description=f"{os.getenv('APP_CMD_PREFIX')}View playtime for yourself or other people")
    @app_commands.guild_only
    @app_commands.describe(
        user='User to view playtime (if none specified, will search for yourself)',
        game='Game to filter playtime result by (Use "!game" to search for games that do not match "game")',
        sort='Choose how to sort search result',
        page_size='How many results to display at once',
        playtime='Playtime to sort by: >5m, <5h, all (all results), > is greater than, < is less than. [Session based]',
        scope='Choose level to search on: User level (default), Guild level, or Global level',
        query_limit='Change how many total results will be queryed from the database (different than limit)'
    )
    @app_commands.choices(
    sort=[
        app_commands.Choice(name='Most Played', value='mp'),
        app_commands.Choice(name='Least Played', value='lp'),
        app_commands.Choice(name='Session Count (by Game)', value='sc'),
        app_commands.Choice(name='Longest Session (detailed activity list)', value='ls')
    ],
    page_size=[
        app_commands.Choice(name='5 Results', value=5),
        app_commands.Choice(name='10 Results (default)', value=10),
        app_commands.Choice(name='25 Results', value=25)
    ],
    scope=[
        app_commands.Choice(name='User (default)', value="user"),
        app_commands.Choice(name='Guild', value="guild"),
        app_commands.Choice(name='Global', value="global")
    ],
    query_limit=[
        app_commands.Choice(name='1,000 (default)', value="LIMIT 1000"),
        app_commands.Choice(name='Unlimited (could take up to a minute)', value="")
    ])
    async def pt(self, interaction: discord.Interaction,
                 user: typing.Optional[discord.User] = None,
                 game: typing.Optional[str] = None,
                 sort: app_commands.Choice[str] = None,
                 page_size: app_commands.Choice[int] = None,
                 playtime: typing.Optional[str] = None,
                 scope: app_commands.Choice[str] = "user",
                 query_limit: app_commands.Choice[str] = "LIMIT 1000"):


        await interaction.response.send_message(content=f"Querying database. This may take a few seconds... {tunables('LOADING_EMOJI')}")
        orig_msg = await interaction.original_response()


        # Guild MEMBER object needed, we can retrieve like this
        try:
            if scope.value != 'user': scope_not_user = True
            else: scope_not_user = False
        except: scope_not_user = False
        if user is None or scope_not_user: user = interaction.guild.get_member(interaction.user.id)
        #else:
        #    user_temp = interaction.guild.get_member(user.id)
        #    if user_temp is not None: user = user_temp
        #if user is None:
        #    await orig_msg.edit(content="Error: User not found.")
        #    return
        
        if page_size is None: page_size = 10
        else: page_size = page_size.value


        # Determine what search modifiers the user has entered
        game_query = False
        sort_query = False
        playtime_query = False
        if game is not None: game_query = True
        if sort is not None: sort_query = True
        if playtime is not None: playtime_query = True

        try: query_limit = query_limit.value
        except: pass
        #if scope_not_user and page_size == 40: page_size = 25

        try:
           if not game_query and not sort_query and not playtime_query and not scope_not_user:
               tup = get_total_activity_updates(user)
               avg = get_average_session(user)
               tot_playtime = get_total_playtime_user(user)
               if tup > page_size: view = PlaytimePageSelector(interaction.user, user, page_size, updates=tup,
                   playtime=tot_playtime, avg_session=avg)
               else: view = None
               await orig_msg.edit(content=tunables('PLAYTIME_CONTENT_MSG'), embed=playtime_embed(user, page_size, updates=tup,
                   playtime=tot_playtime, avg_session=avg), view=view)
               return
        except:
           await orig_msg.edit(content=tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE'))
           return

        
        sel_cmd = []

        part1 = []    
        part1.append("SELECT app.emoji, pt.app_id, app.name")
        if sort_query and sort.value not in ['ls', 'sc']: # if not 'detailed'
            part1.append(", SUM(pt.end_time - pt.start_time) AS ptime, AVG(pt.end_time - pt.start_time) AS avg, 0")
        elif sort_query and sort.value == 'sc':
            part1.append(", SUM(pt.end_time - pt.start_time) AS ptime, AVG(pt.end_time - pt.start_time) AS avg, COUNT(pt.end_time) AS sc")
        else:
            part1.append(", (pt.end_time - pt.start_time) AS ptime, 0, pt.end_time")
        if scope_not_user: part1.append(", pt.user_id")
        sel_cmd.append(''.join(part1))
        del part1

        part2 = []
        part2.append(
            " FROM PLAY_HISTORY AS pt "+
            "INNER JOIN APPLICATIONS AS app ON "+
            "(pt.app_id=app.app_id AND pt.end_time!=-1 AND app.counts_towards_playtime!='FALSE'"
            )
        

        # Handle playtime query
        if playtime_query:
            if playtime.lower() == "all":
                part2.append(") ")
            else:
                regex_pt = r"^[<>]\d{1,5}[smhd]{0,1}$|^all$"
                if not re.match(regex_pt, playtime.lower()):
                    await orig_msg.edit(content=f"Error: Invalid playtime entry `{playtime}`. Examples: `>5m` (greater than 5 minutes), `<5h` (less than 5 hours), `all` returns all results. `<` and `>` are **required**.")
                    return
                
                multiplicity = 1
                if not playtime[len(playtime) - 1].isdigit():
                    match playtime[len(playtime) - 1].lower():
                        case 's': pass # No change to multiplicity
                        case 'm': multiplicity = 60
                        case 'h': multiplicity = 3600
                        case 'd': multiplicity = 86400
                
                if playtime[len(playtime) - 1].isdigit(): playtime_val = playtime[1:]
                else: playtime_val = playtime[1:-1]
                
                playtime_val = multiplicity * int(playtime_val)
                part2.append(f" AND (pt.end_time - pt.start_time){playtime[0]}{playtime_val}) ")
        else:
            part2.append(f" AND (pt.end_time - pt.start_time)>={tunables('THRESHOLD_LIST_GAME_ACTIVITY')}) ")
        ####


        # Determine search scope (User, Guild, global)
        if scope_not_user and scope.value == "guild":
            part2.append(
                    "INNER JOIN USERS AS u ON "+
                    f"(pt.user_id=u.user_id AND u.server_id='{interaction.guild.id}') "
                )
        sel_cmd.append(''.join(part2))
        del part2
        ####


        # Handle game query
        part3 = []
        if game_query:
            inverse_search = False
            if game.startswith('!'):
                part3.append("WHERE pt.app_id NOT IN (")
                inverse_search = True
            else:
                part3.append("WHERE pt.app_id IN (")
            
            if inverse_search:
                if game[1:] == "": apps = []
                else: 
                    try: apps = get_app_from_str(game[1:])
                    except:
                        await orig_msg.edit(content=tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE'))
                        return
            else:
                try: apps = get_app_from_str(game)
                except:
                    await orig_msg.edit(content=tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE'))
                    return
            if apps == []:
                await orig_msg.edit(content=f"Could not find any games matching: `{game}`")
                return

            previous = False
            for app in apps:
                if not previous:
                    part3.append(f"'{app[1]}'")
                    previous = True
                else:
                    part3.append(f", '{app[1]}'")
            if not scope_not_user: part3.append(f") AND pt.user_id={user.id} ")
        else:
            if not scope_not_user: part3.append(f"WHERE pt.user_id={user.id} ")
        if game_query or not scope_not_user: sel_cmd.append(f"{''.join(part3)}{')' if game_query and scope_not_user else ''} ")
        del part3
        ####


        # Handle sort query
        part4 = []
        if sort_query and sort.value != 'ls':
            part4.append(f"GROUP BY pt.app_id{', pt.user_id' if scope_not_user else ''} ") # if not 'detailed'
        
        if sort_query:
            match sort.value:
                case 'mp' | 'ls':
                    part4.append("ORDER BY ptime DESC ")
                
                case 'lp':
                    part4.append("ORDER BY ptime ASC ")
                
                case 'sc':
                    part4.append("ORDER BY sc DESC ")
        else:
            part4.append("ORDER BY end_time DESC ")
        sel_cmd.append(''.join(part4))
        del part4
        
        sel_cmd.append(query_limit)

        try:
            playtime_by_game = await app_cmd_db.execute(''.join(sel_cmd))

            if playtime_by_game == []:
                msg = []
                msg.append("Games found, but no activity was found with the given search criteria:\n")
                if game is not None: msg.append(f"`Game: {game}`\n")
                if playtime is not None: msg.append(f"`Playtime: {playtime}`\n")
                if game is not None or playtime is not None: msg.append(f"`Scope: {scope}`")
                await orig_msg.edit(content=''.join(msg))
                return

            if user != interaction.user and scope_not_user: ct = "`User` field supplied; omitting due to current scope"
            else: ct = None
            search_total = total_playtime_result(playtime_by_game)
            search_avg = avg_playtime_result(playtime_by_game)
            if len(playtime_by_game) > page_size:
                view = PlaytimeSearchPageSelector(interaction.user, user, game, sort, page_size, len(playtime_by_game),
                                                    query=sel_cmd, scope=[scope_not_user, scope],
                                                    result=playtime_by_game, total=search_total, avg=search_avg)
            else: view = None
            await orig_msg.edit(content=ct, embed=modified_playtime_embed(user, game, playtime_by_game[:page_size],
                                sort, page_size, len(playtime_by_game), scope=[scope_not_user, scope], ptquery=playtime,
                                total=search_total, avg=search_avg), view=view)

            return
        except: await orig_msg.edit(content=tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE'))
        

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        u = MikoMember(user=interaction.user, client=interaction.client)
        if not u.profile.cmd_enabled('PLAYTIME'):
            await interaction.response.send_message(content=tunables('GENERIC_BOT_DISABLED_MESSAGE'), ephemeral=True)
            return False
        
        if not tunables('COMMAND_ENABLED_PLAYTIME_GENERIC'):
            await interaction.response.send_message(content=tunables('COMMAND_DISABLED_MESSAGE'), ephemeral=True)
            return False

        u.increment_statistic('PLAYTIME_COMMAND')
        return True



async def setup(client: commands.Bot):
    await client.add_cog(PlaytimeCog(client))