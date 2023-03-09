import asyncio
import time
import discord
from Plex.background import end_of_week_int
from Plex.embeds import plex_multi_embed
from Voice.VoiceActivity import VoiceActivity, VOICE_SESSIONS
from Database.GuildObjects import MikoMember
from Database.database_class import Database
from Polls.UI import active_polls
import aiohttp

from tunables import tunables
ap = Database("async_processes.py")

client: discord.Client = None
def set_async_client(c):
    global client
    client = c


async def heartbeat():
    num = 1
    while True:

        if num % 60 == 0:
            try: await check_notify()
            except Exception as e: print(f"Plex notify check failed, trying again in 60 seconds...: {e}")

        # Check if miko is still in guilds
        # if num % 3600 == 0:
        #     try:
        #     except Exception as e: print()

        if num == 3700: num = 0
        num += 1
        # print(num)
        await asyncio.sleep(1)


async def check_notify():
    if client.user.id != 1017998983886545068: return
    notify_time = ap.db_executor(
        "SELECT value FROM PERSISTENT_VALUES WHERE variable='PLEX_UPCOMING_NOTIFY'"
    )

    if notify_time is None or int(time.time()) >= notify_time:
        ap.db_executor(
            f"UPDATE PERSISTENT_VALUES SET value='{end_of_week_int()}' "
            f"WHERE variable='PLEX_UPCOMING_NOTIFY'"
        )

        url = ap.db_executor(
            "SELECT value_str FROM PERSISTENT_VALUES WHERE variable='PLEX_WEBHOOK_URL'"
        )
        embeds = plex_multi_embed()
        for i, embed in enumerate(embeds):
            async with aiohttp.ClientSession() as s:
                webhook = discord.Webhook.from_url(
                    url,
                    session=s
                )
                if i == 0:
                    try: await webhook.send(
                        embed=None,
                        content=tunables('PLEX_WEBHOOK_NOTIFICATION_MESSAGE')
                    )
                    except Exception as e: print(e)
                await asyncio.sleep(1)
                try: await webhook.send(
                    embed=embed,
                    content=None
                )
                except Exception as e: print(e)