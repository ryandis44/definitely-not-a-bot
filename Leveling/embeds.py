import discord
from Database.GuildObjects import MikoMember
from tunables import *
from misc.misc import time_elapsed

def leveling_stats(u: MikoMember) -> discord.Embed:

    lc = u.leveling
    role: discord.Role = lc.get_role()
    # role = u.user.top_role

    temp = []
    temp.append(f"Total XP: **{(lc.xp):,}**")
    temp.append(f"\nLevel: **{lc.level}** • {role.mention}")

    temp.append(f"\nMessages: `{lc.msgs:,}`")
    temp.append(f"\nVoicetime: `{time_elapsed(u.user_voicetime + lc.active_voicetime, 'h')}`")

    # temp.append(f"\nMsg XP: **{lc.msg_xp:,}**")
    # temp.append(f"\nVoice XP: **{lc.voice_xp:,}**")

    embed = discord.Embed (
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    embed.set_thumbnail(url=u.user_avatar)
    embed.set_author(name=f"{u.username} Leveling Stats", icon_url=role.display_icon)
    return embed