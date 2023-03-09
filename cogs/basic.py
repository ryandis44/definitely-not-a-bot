import asyncio
import discord
from discord.ext import commands
from discord.utils import get
import random
import time
from Database.GuildObjects import MikoGuild, MikoMember, MikoTextChannel
from Database.database_class import Database
from Plex.embeds import plex_update_2_2
from Database.database import add_bot, add_react_all_to_user, add_react_to_user, add_rename_any_user, add_rename_to_user, del_bot, del_react_all_to_user, del_react_to_user, del_rename_any_user, del_rename_to_user, generic_list_embed, get_server_status, set_status_active, set_status_scraping, top_channels_embed_server, top_users_embed_server, user_info_embed
from misc.holiday_roles import get_holiday
from misc.misc import time_elapsed, translate_mention
import os
from dotenv import load_dotenv
from discord.ext.commands import Context
from tunables import *

b = Database("basic.py")

running = 0


class Basic(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.client.user} has connected to Discord!')

        # WIP
        #else:
        #    print("Connection has been restored to the Discord API, ending and restarting all playtime sessions...")
        #    end_all_sessions(self.client)
        #    print("Complete.")
        #print("Scraping.. ?")
        #scrape_sessions(self.client)


    # Generates a random number between 0 and 100 [inclusive]
    @commands.command(name='roll', aliases=['r'])
    @commands.guild_only()
    async def roll(self, ctx: Context):
        
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('ROLL'): return
        u.increment_statistic('ROLL')
        
        user = ctx.message.author
        roll = random.randint(0, 100)
        if roll < 10:
            if roll == 1:
                await ctx.send(f'{user.mention} rolled a **{roll}**! ...better than zero')
            elif roll == 7:
                await ctx.send(f'{user.mention} rolled a **{roll}**! Looks like lucky number seven isn\'t so lucky this time...')
            else:
                await ctx.send(f'{user.mention} rolled a **{roll}**! My my, quite unfortunate! <:okand:947697439048073276>')
        
        elif roll > 90:
            if roll == 100:
                await ctx.send(f'{user.mention} rolled a **:100:**! GG. Might as well just give <@221438665749037056> the card.')
            else:
                await ctx.send(f'{user.mention} rolled a **{roll}**! Very impressive! <@357939301100683276> <:hector_talking:947690384841146368><:hector_talking:947690384841146368><:hector_talking:947690384841146368><:hector_talking:947690384841146368><:hector_talking:947690384841146368><:hector_talking:947690384841146368>')
        
        elif roll == 50:
            await ctx.send(f'{user.mention} rolled a **{roll}**! It could go either way at this point!')
        elif roll == 69:
            await ctx.send(f'{user.mention} rolled a **{roll}**! :smirk:')
        else:
            await ctx.send(f'{user.mention} rolled a **{roll}**!')


    # Simple magic 8-ball command
    @commands.command(name='8ball', aliases=['8b'])
    async def eightball(self, ctx: Context, *args):
        
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('EIGHT_BALL'): return
        u.increment_statistic('EIGHT_BALL')

        user = ctx.message.author
        if len(args) == 0:
            await ctx.send(f'{user.mention} you need to enter a question!')
        else:
            responses = ['It is certain.', 'It is decidedly so.', 'Without a doubt.', 'Yes - definitely.', 'You may rely on it.', 'As I see it, yes.', 'Most likely.', 'Outlook good.', 'Yes.', 'Signs point to yes.', 'Reply hazy, try again.', 'Ask again later.', 'Better not tell you now.', 'Cannot predict now.', 'Concentrate and ask again.', 'Don\'t count on it.', 'My reply is no.', 'My sources say no.', 'Outlook not so good.', 'Very doubtful.']
            await ctx.send(f'{user.mention} {random.choice(responses)}')


    # Simple flip-a-coin command
    @commands.command(name='flip', aliases=['fl'])
    async def flip(self, ctx: Context):
        
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('COIN_FLIP'): return
        u.increment_statistic('COIN_FLIP')
        
        user = ctx.message.author
        coin = ['Heads', 'Tails']
        await ctx.send(f'{user.mention} {random.choice(coin)}!')


    # Pulls all holiday roles and member counts for each and 
    @commands.command(name='roleassignment', aliases=['ra'])
    @commands.guild_only()
    async def holiday(self, ctx: Context):
        g = MikoGuild(guild=ctx.guild, client=self.client)
        if not g.profile.cmd_enabled('ROLE_ASSIGNMENT'):
            return
        await ctx.send(embed=get_holiday(ctx, "EMBED"))


    # Simple help embed
    # @commands.command(name='help', aliases=['h'])
    # async def help(self, ctx):
    #     embed = discord.Embed (
    #         title = 'Miko Help!',
    #         color = GLOBAL_EMBED_COLOR
    #     )
    #     embed.set_thumbnail(url='https://cdn.givemesport.com/wp-content/uploads/2022/02/Yae-Miko-Voice-Actors-960x620-c-default.jpg')
    #     if str(get_server_status(ctx.guild.id)) != "inactive":
    #         embed.add_field(name='r, roll', value=':game_die: Roll a die!', inline=True)
    #         embed.add_field(name='p, poll', value=':bar_chart: Create a poll!', inline=True)
    #         embed.add_field(name='h, help', value=':question: Get help!', inline=True)
    #         embed.add_field(name='8b, 8ball', value=':8ball: Ask any question!', inline=True)
    #         embed.add_field(name='fl, flip', value=':coin: Flip a coin!', inline=True)
    #         embed.add_field(name='as, anisearch', value='<:uwuyummy:958323925803204618> Find an anime!', inline=True)
    #         embed.add_field(name='roleassignment, ra', value=':construction_worker: Holiday Role Info!', inline=True)
    #         embed.add_field(name='tunables, t', value=':gear: Bot Settings!', inline=True)
    #     embed.add_field(name='info, s', value=':bar_chart: User Stats/Info!', inline=True)
    #     embed.add_field(name='/playtime, pt', value=':video_game: Playtime Tracker!', inline=True)
    #     await ctx.send(embed=embed)

    
    # User message statistics page
    @commands.command(name='info', aliases=['s'])
    @commands.guild_only()
    async def info(self, ctx: Context, *args):
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('USER_INFO'): return
        elif u.status == "SCRAPING":
            await ctx.channel.send("That command is disabled while I am gathering guild info. Try again later.")
            return
        u.increment_statistic('USER_INFO')

        if len(args) == 0:
            referenced_user = ctx.author
        else:
            # Get user mentioned
            temp = args[0]
            temp = translate_mention(temp)
            referenced_user = ctx.guild.get_member(int(temp))

        if referenced_user is None:
            await ctx.channel.send(content=tunables('USER_NOT_FOUND'))
            return

        await ctx.send(embed=user_info_embed(MikoMember(user=referenced_user, client=self.client, guild_id=ctx.guild.id)))


    @commands.command(name='playtime', aliases=['pt'])
    @commands.guild_only()
    async def playtime(self, ctx: Context):
        
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('PLAYTIME'): return
        
        await ctx.channel.send("This command is depreciated. Please use `/playtime` instead.")

        if ctx.author.id != 221438665749037056: return
        try: user = ctx.message.mentions[0]
        except: user = ctx.author

        # await ctx.channel.send(f"{playtimeContentMessage()}")

        #g = MikoGuild(guild=ctx.guild, client=self.client)
        #await ctx.channel.send(f"{await g.emoji}")
        #ch = MikoTextChannel(channel=ctx.channel, client=self.client)
        u = MikoMember(user=user, client=self.client)
        await ctx.send(
            f"{time_elapsed(u.user_voicetime, 'h')}"
        )
        # await ctx.send(
        #     f"{asyncio.all_tasks()}"
        # )
        # guild = ctx.guild
        # await ctx.send(
        #     content=(
        #         "I joined a new guild!\n"
        #         f"> Added at: <t:{int(time.time())}:R>\n"
        #         f"> Guild name: **{guild.name}** [`{guild.id}`]\n"
        #         f"> Guild owner: {guild.owner.mention} [`{guild.owner.id}`]\n"
        #         f"> Guild members: `{guild.member_count}`\n"
        #         f"> Guild profile [DB]: `{u.status}`\n"
        #         f"> Guild Locale (Region): `{guild.preferred_locale}`\n"
        #         f"> Guild 2FA Level: `{guild.mfa_level}`\n"
        #         f"> Guild NSFW Level: `{guild.nsfw_level}`\n"
        #         f"> Guild Nitro boost level: `{guild.premium_tier}`\n"
        #         f"> Guild Nitro boost count: `{guild.premium_subscription_count}`\n"
        #         f"> Guild Text Channels: `{len(guild.text_channels) if guild.text_channels is not None else 0}`\n"
        #         f"> Guild Voice Channels: `{len(guild.voice_channels) if guild.voice_channels is not None else 0}`\n"
        #         f"> Guild Vanity URL: {guild.vanity_url} | `{guild.vanity_url_code}`\n"
        #         f"> Guild Icon: {guild.icon}\n"
        #         f"> Guild Banner: {guild.banner}\n"
        #         f"> My permissions: `{guild.me.guild_permissions}`\n"
        #     ),
        #     allowed_mentions=discord.AllowedMentions(users=False)
        # )
        # await ctx.channel.send(f"{u.profile} {u.profile.cmd_enabled('PLAYTIME')}")
        # await ctx.channel.send(f"{(7150 % tunables('THRESHOLD_VOICETIME_FOR_TOKEN')) >= tunables('THRESHOLD_VOICETIME_FOR_TOKEN') - 30} ({tunables('THRESHOLD_VOICETIME_FOR_TOKEN')}) | {u.user_voicetime}")
        #await ctx.channel.send(
        #    f"{u.user_messages} {u.user_messages_today} {u.considered_bot} "
        #    f"{u.react} {u.reactall} {u.rename} {u.renameany} {u.bot_permission_level} "
        #    f"{u.pets.pet}"
        #    )

        # msg = await ctx.channel.send("Updating database...")
        # sel_cmd = f"SELECT server_id FROM SERVERS"
        # servers = b.db_executor(sel_cmd)

        # users = 0
        # for guild in servers:

        #     sel_cmd = (
        #         f"SELECT user_id,server_id FROM USERS WHERE server_id='{guild[0]}' "
        #         "ORDER BY joined_at ASC"
        #     )

        #     res = b.db_executor(sel_cmd)
        #     for i, e in enumerate(res):
        #         upd_cmd = (
        #             f"UPDATE USERS SET unique_number={i+1} "
        #             f"WHERE user_id='{e[0]}' AND server_id='{e[1]}'"
        #         )
        #         b.db_executor(upd_cmd)
        #         users += 1

        # await msg.edit(content=f"Updated {users} users")
        return


    # @commands.command(name='databaserefresh', aliases=['refresh'])
    # @commands.guild_only()
    # async def databaserefresh(self, ctx: Context):
    #     await ctx.send("Command requires attention.")
        # global running
        # u = MikoMember(user=ctx.author, client=self.client)
        # if u.bot_permission_level <= 4:
        #     await ctx.channel.send("`You do not have permission to use this command.`")
        #     return
        
        # if u.status == "scraping":
        #     await ctx.channel.send('`A refresh for this guild is already running. Check console for progress.`')
        #     return
        # else: set_status_scraping(ctx.guild)
        
        # await ctx.channel.send("`Manually refreshing database. This may take a while.`")
        # print("Manually refreshing database.")
        # running = 1
        # start_time = time.time()

        # #for user in ctx.guild.members:
        # #    username_hist(user)

        # #print(f"Calculating total channel messages for {ctx.guild.name}")
        # #await ctx.channel.send(f"Calculating total messages for `{ctx.guild.name}`")
        # #for i, channel in enumerate(ctx.guild.text_channels):
        # #    channel_msg_count = 0
        # #    print(f" [{i+1}/{len(ctx.guild.text_channels)}] in {channel}...")
        # #    await ctx.channel.send(f"> [{i+1}/{len(ctx.guild.text_channels)}] in `{channel}`...")
        # #    async for message in channel.history(limit=None):
        # #        #for user in ctx.guild.members:
        # #        #    if message.author.id == user.id:
        # #        #        manual_increment(user, ctx)
        # #        channel_msg_count += 1
        # #    channel_update(channel, channel_msg_count)
        # #    msg = f"(!) {channel} complete. Total messages: {channel_msg_count}"
        # #    print(msg)
        # #    await ctx.channel.send(msg)

        # # Disabled code: Scrapes entire server for messages from any
        # # user. Counts and stores that number in database. Also
        # # determines total messages in every channel and stores
        # # that number in database as well.
        # #
        # # New code to fetch user message count

        # ###############
        # calc_msg = f"Calculating total messages for `{ctx.guild.name}`"
        # print(calc_msg)
        # await ctx.channel.send(calc_msg)
        # all_users = False
        # for i, channel in enumerate(ctx.guild.text_channels):
        #     channel_msg_count = 0
        #     upd_msg = f" [{i+1}/{len(ctx.guild.text_channels)}] in {channel}..."
        #     print(upd_msg)
        #     await ctx.channel.send(f">{upd_msg}")
        #     async for message in channel.history(limit=None):
        #         for user in ctx.guild.members:
        #             if not all_users: r = MikoMember(user=user, client=self.client)
        #             if message.author.id == user.id:
        #                 manual_increment(user, channel)
        #                 c = MikoTextChannel(channel=channel, client=self.client)
        #         all_users = True
        #         channel_msg_count += 1
        #     msg = f" [{i+1}/{len(ctx.guild.text_channels)}] {channel} complete. Total messages: `{channel_msg_count}`"
        #     print(msg)
        #     await ctx.channel.send(f">{msg}")
        # ###############

        # set_status_active(ctx.guild)
        # stop_time = time.time()
        # runtime = time_elapsed(stop_time - start_time, ':')
        # print(f"Complete. Took {runtime}")
        # await ctx.channel.send(f"`Manual channel message count refresh complete. Took {runtime}`")

    @commands.command(name='sgstop', aliases=['st'])
    @commands.guild_only()
    async def top(self, ctx: Context):
        
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('TOP_USERS_BY_MESSAGES'): return
        u.increment_statistic('TOP_USERS_BY_MESSAGES')
        
        await ctx.send(embed=top_users_embed_server(MikoGuild(guild=ctx.guild, client=self.client)))

    @commands.command(name='channelstop', aliases=['ct'])
    async def ctop(self, ctx: Context):
        
        u = MikoMember(user=ctx.author, client=self.client)
        if not u.profile.cmd_enabled('TOP_CHANNELS_BY_MESSAGES'): return
        u.increment_statistic('TOP_CHANNELS_BY_MESSAGES')
        
        await ctx.channel.send("This command is disabled for now.")
        # if str(get_server_status(ctx.guild.id)) in ["inactive", "silent"]:
        #     return
        # elif str(get_server_status(ctx.guild.id)) == "scraping":
        #     await ctx.channel.send("That command is disabled while I am gathering guild info. Try again later.")
        #     return
        # await ctx.send(embed=top_channels_embed_server(MikoTextChannel(channel=ctx.channel, client=self.client)))

    @commands.command(name='plexreqembed', aliases=['pre'])
    async def plexreqembed(self, ctx: Context):
        #admins = get_bot_devs()
        #if str(ctx.author.id) not in admins:
        #    await ctx.channel.send(tunables('NO_PERM'))
        #    return
        u = MikoMember(user=ctx.author, client=self.client)
        if u.bot_permission_level <= 4:
            return
        #await ctx.channel.send("<@&1001733271459221564>", embed=plex_requests_embed()) # Plex role
        msg = "<@&1001733271459221564>"
        await ctx.channel.send(content=msg, embed=plex_update_2_2())



    # Main command 
    @commands.command(name='fun', aliases=['f'])
    @commands.guild_only()
    async def fun(self, ctx: Context, *args):
        # Guild owners have full access to modify, as this is server based
        u = MikoMember(user=ctx.author, client=self.client)
        if u.bot_permission_level <= 3 and ctx.author.id != ctx.guild.owner.id:
            return
        
        if args == (): args = ["None"]
        match args[0].lower():

            # React subcommand
            case "react":
                if len(args) == 2 and args[1].lower() != "list":
                    await ctx.message.reply("Please type the command again mentioning the user you wish to modify.")
                else:

                    match args[1].lower():
                        case "add":
                            if add_react_to_user(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:green_plus:998447990035464233>  User {args[2]} added to reaction list.')
                            else:
                                await ctx.channel.send(f':exclamation: User {args[2]} is already on the reaction list.')
                        case "del":
                            if del_react_to_user(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:red_minus:998447601739386981>  User {args[2]} removed from reaction list.')
                            else:
                                await ctx.channel.send(f':exclamation: User {args[2]} is not on the reaction list.')
                        case "list":
                            await ctx.send(embed=generic_list_embed(ctx.guild, "react"))

            case "reactall":
                if len(args) == 2 and args[1].lower() != "list":
                    await ctx.message.reply("Please type the command again mentioning the user you wish to modify.")
                else:

                    match args[1].lower():
                        case "add":
                            if add_react_all_to_user(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:green_plus:998447990035464233>  User {args[2]} added to reaction list.')
                            else:
                                await ctx.channel.send(f':exclamation: User {args[2]} is already on the reaction list.')
                        case "del":
                            if del_react_all_to_user(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:red_minus:998447601739386981>  User {args[2]} removed from reaction list.')
                            else:
                                await ctx.channel.send(f':exclamation: User {args[2]} is not on the reaction list.')
                        case "list":
                            await ctx.send(embed=generic_list_embed(ctx.guild, "reactall"))
            
            case "bot":
                if len(args) == 2 and args[1].lower() != "list":
                    await ctx.message.reply("Please type the command again mentioning the bot you wish to modify.")
                else:

                    match args[1].lower():
                        case "add":
                            if add_bot(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:green_plus:998447990035464233> Bot {args[2]} added to bot list.')
                            else:
                                await ctx.channel.send(f':exclamation: Bot {args[2]} is already on the bot list.')
                        case "del":
                            if del_bot(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:red_minus:998447601739386981> Bot {args[2]} removed from bot list.')
                            else:
                                await ctx.channel.send(f':exclamation: Bot {args[2]} is not on the bot list.')
                        case "list":
                            await ctx.send(embed=generic_list_embed(ctx.guild, "bot"))
            
            # case "rename":
            #     if len(args) == 2 and args[1].lower() != "list":
            #         await ctx.message.reply("Please type the command again mentioning the user you wish to modify.")
            #     else:

            #         match args[1].lower():
            #             case "add":
            #                 if add_rename_to_user(translate_mention(args[2]), ctx.guild):
            #                     await ctx.channel.send(f'<:green_plus:998447990035464233>  User {args[2]} added to rename list.')
            #                 else:
            #                     await ctx.channel.send(f':exclamation: User {args[2]} is already on the rename list.')
            #             case "del":
            #                 if del_rename_to_user(translate_mention(args[2]), ctx.guild):
            #                     await ctx.channel.send(f'<:red_minus:998447601739386981>  User {args[2]} removed from rename list.')
            #                 else:
            #                     await ctx.channel.send(f':exclamation: User {args[2]} is not on the rename list.')
            #             case "list":
            #                 await ctx.send(embed=generic_list_embed(ctx.guild, "rename"))

            case "renameany":
                if len(args) == 2 and args[1].lower() != "list":
                    await ctx.message.reply("Please type the command again mentioning the user you wish to modify.")
                else:

                    match args[1].lower():
                        case "add":
                            if add_rename_any_user(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:green_plus:998447990035464233>  User {translate_mention(args[2])} added to renameany list.')
                            else:
                                await ctx.channel.send(f':exclamation: User {translate_mention(args[2])} is already on the renameany list.')
                        case "del":
                            if del_rename_any_user(translate_mention(args[2]), ctx.guild):
                                await ctx.channel.send(f'<:red_minus:998447601739386981>  User {translate_mention(args[2])} removed from renameany list.')
                            else:
                                await ctx.channel.send(f':exclamation: User {translate_mention(args[2])} is not on the renameany list.')
                        case "list":
                            await ctx.send(embed=generic_list_embed(ctx.guild, "renameany"))

            case _:
                temp = []               

                temp.append(f"`{os.getenv('CMD_PREFIX1')}f` subcommands:\n\n")
                temp.append("- `bot` [`add`, `del`, `list`] <`@Bot`> - Add, remove, or list bot accounts registered with <@912572126026924072> [server specific].\n")
                temp.append("- `react` [`add`, `del`, `list`] <`@User`> - Add, remove, or list users to be reacted to [server specific].\n")
                temp.append("- `reactall` [`add`, `del`, `list`] <`@User`> - Add, remove, or list users to flood their message with reactions[server specific].\n")
                # temp.append("- `rename` [`add`, `del`, `list`] <`@User`> - Add, remove, or list users to be renamed a random word from a random message sent from them every now and then [server specific].\n")
                temp.append("- `renameany` [`add`, `del`, `list`] <`@User`> - Add, remove, or list users to be renamed a random word from a random message sent from __every user__ (occasional) [server specific].")

                embed = discord.Embed (
                title = 'Tunables Help (Bot Settings)',
                color = GLOBAL_EMBED_COLOR,
                description=f"{''.join(temp)}"
                )
                embed.set_thumbnail(url=ctx.guild.icon)
                await ctx.send(embed=embed)


async def setup(client: commands.Bot):
    await client.add_cog(Basic(client))
