import time
import uuid

import discord
from tunables import tunables
from Database.GuildObjects import MikoMember
from Database.database_class import AsyncDatabase
db = AsyncDatabase("GreenBook.Objects.py")


class PersonUpdate:
    def __init__(
            self,
            eid: int,
            modifier_user_id: int,
            update_type: str,
            before: str,
            after: str,
            update_time: int
    ):
        self.eid = eid
        self.modifier_user_id = modifier_user_id
        self.update_type = update_type
        self.before = before
        self.after = after
        self.update_time = update_time
    
    def __str__(self): return (
                f":black_medium_small_square: {self.modifier_user_mention} {self.update_time_formatted}: "
                f"{self.update_type.upper()} - `{self.before}` → `{self.after}`"
    )
    
    @property
    def modifier_user_mention(self) -> str: return f"<@{self.modifier_user_id}>"

    @property
    def update_time_formatted(self) -> str: return f"<t:{self.update_time}:R>"


class Person:
    def __init__(self, creator_id: int=0, eid: str=None, first: str=None, last: str=None, age: int=0, pass_time: int=0, wristband: str="GREEN", new=False):
        self.creator_id = creator_id
        self.eid = eid
        self.first = first
        self.last = last
        self.age = age
        self.pass_time = pass_time
        self.wristband = wristband
        self.new = new

        self.__emojis = {
            'GREEN': "🟢",
            'YELLOW': "🟡",
            'RED': "🔴"
        }
    
    def __str__(self): return (
                f"{self.wristband_emoji} `{self.last}, {self.first}: Age {self.age}`\n"
                f"\u200b \u200b└→  Entered by {self.creator_id_mention} on {self.pass_time_formatted}\n"
    )

    async def edit(self, modal, modifier: discord.Member) -> bool:
        modified = {
            'first': False,
            'last': False,
            'age': False,
            'wristband': False
        }
        
        if int(modal.age.value) != int(self.age):
            modified['age'] = True
            modified['age_val'] = [int(self.age), int(modal.age.value)]
            self.age = int(modal.age.value)
        if str(modal.wristband.value) != str(self.wristband_letter):
            modified['wristband'] = True
            modified['wristband_val'] = [str(self.wristband)]
            self.set_wristband(c=str(modal.wristband.value))
            modified['wristband_val'].append(str(self.wristband))
        try:
            if str(modal.first.value) != str(self.first):
                modified['first'] = True
                modified['first_val'] = [str(self.first), str(modal.first.value).upper()]
                self.first = str(modal.first.value).upper()
        except: pass
        try:
            if str(modal.last.value) != str(self.last):
                modified['last'] = True
                modified['last_val'] = [str(self.last), str(modal.last.value).upper()]
                self.last = str(modal.last.value).upper()
        except: pass


        # Entry update command builder and history insertion
        upd_cmd = []
        upd_cmd.append("UPDATE YMCA_GREEN_BOOK_ENTRIES SET ")
        upd = False
        t = int(time.time())
        for key, val in modified.items():
            if not modified[key] or '_val' in key: continue

            match key:
                case 'first': upd_cmd.append(f"first_name='{self.first}'")
                case 'last': upd_cmd.append(f"{',' if upd else ''}last_name='{self.last}'")
                case 'age': upd_cmd.append(f"{',' if upd else ''}age='{self.age}'")
                case 'wristband': upd_cmd.append(f"{',' if upd else ''}wristband_color='{self.wristband}'")
            upd = True

            before = str(modified[f"{key}_val"][0])
            after = str(modified[f"{key}_val"][1])
            await db.execute(
                "INSERT INTO YMCA_GREEN_BOOK_HISTORY (entry_id,user_id,type,before_modification,after_modification,modification_time) VALUES "
                f"('{self.eid}', '{modifier.id}', '{key.upper()}', '{before}', '{after}', '{t}')"
            )
        if upd:
            upd_cmd.append(
                f" WHERE server_id='{modifier.guild.id}' AND entry_id='{self.eid}'"
            )
            await db.execute(''.join(upd_cmd))

        return upd

    async def delete(self) -> None:
        await db.execute(
            "DELETE FROM YMCA_GREEN_BOOK_ENTRIES WHERE "
            f"entry_id='{self.eid}'"
        )
        await db.execute(
            "DELETE FROM YMCA_GREEN_BOOK_HISTORY WHERE "
            f"entry_id='{self.eid}'"
        )


    @property
    def wristband_letter(self):
        match self.wristband:
            case "GREEN": return 'g'
            case "YELLOW": return 'y'
            case "RED": return 'r'

    @property
    def pass_time_formatted(self) -> str: return f"<t:{self.pass_time}:f>"

    @property
    def creator_id_mention(self) -> str: return f"<@{self.creator_id}>"

    @property
    def wristband_emoji(self): return self.__emojis[self.wristband]

    @property
    async def history(self) -> list:
        val = await db.execute(
            "SELECT * FROM YMCA_GREEN_BOOK_HISTORY WHERE "
            f"entry_id='{self.eid}' "
            "ORDER BY modification_time DESC LIMIT 10"
        )
        if val == [] or val is None: return []

        ulist = []
        for update in val:
            ulist.append(
                PersonUpdate(
                    eid=update[0],
                    modifier_user_id=update[1],
                    update_type=update[2],
                    before=update[3],
                    after=update[4],
                    update_time=update[5]
                )
            )
        
        return ulist
    
    def set_wristband(self, c: str):
        match c.upper():
            case 'G': self.wristband = "GREEN"
            case 'Y': self.wristband = "YELLOW"
            case 'R': self.wristband = "RED"

class GreenBook:
    def __init__(self, u: MikoMember):
        self.u = u

    @property
    async def total_entries(self) -> int:
        val = await db.execute(
            "SELECT COUNT(*) FROM YMCA_GREEN_BOOK_ENTRIES WHERE "
            f"server_id='{self.u.guild.id}'"
        )
        if val == [] or val is None: return 0
        return int(val)

    @property
    async def recent_entries(self) -> list:
        val = await db.execute(
            "SELECT * FROM YMCA_GREEN_BOOK_ENTRIES WHERE "
            f"server_id='{self.u.guild.id}' "
            f"ORDER BY pass_time DESC LIMIT {tunables('GREEN_BOOK_RECENT_ENTRIES_LIMIT')}"
        )
        if val == [] or val is None: return []
        plist = []
        for result in val:
            plist.append(
                Person(
                    creator_id=result[1],
                    eid=result[2],
                    first=result[3],
                    last=result[4],
                    age=result[5],
                    pass_time=result[6],
                    wristband=result[7]
                )
            )
        return plist


    # Handle full names; currently only does first OR last
    async def search(self, query: str) -> list:

        if ' ' in query:
            query = query.split(' ')
            s = (
                f"OR (first_name LIKE '%{query[1]}%' OR "
                f"last_name LIKE '%{query[1]}%' OR "
                f"entry_id LIKE '%{query[1]}%') "
            )
        else:
            query = [query]
            s = ''

        val = None
        if len(query) > 1:
            val = await db.execute(
                "SELECT * FROM YMCA_GREEN_BOOK_ENTRIES WHERE "
                f"server_id='{self.u.guild.id}' AND "
                f"first_name='{query[0]}' AND "
                f"last_name='{query[1]}' "
                "ORDER BY last_name ASC LIMIT 10"
            )

        if val == [] or val is None:
            val = await db.execute(
                "SELECT * FROM YMCA_GREEN_BOOK_ENTRIES WHERE "
                f"server_id='{self.u.guild.id}' AND "
                f"(first_name LIKE '%{query[0]}%' OR "
                f"last_name LIKE '%{query[0]}%' OR "
                f"entry_id LIKE '%{query[0]}%') {s}"
                "ORDER BY last_name ASC LIMIT 10"
            )

        if val == [] or val is None: return []

        plist = []
        for result in val:
            plist.append(
                Person(
                    creator_id=result[1],
                    eid=result[2],
                    first=result[3],
                    last=result[4],
                    age=result[5],
                    pass_time=result[6],
                    wristband=result[7]
                )
            )
        return plist
    
    async def create(self, first: str, last: str, age: int, wristband: str) -> Person:

        val = await db.execute(
            "SELECT * FROM YMCA_GREEN_BOOK_ENTRIES WHERE "
            f"server_id='{self.u.guild.id}' AND "
            f"first_name='{first.upper()}' AND "
            f"last_name='{last.upper()}' AND "
            f"age='{age}'"
        )

        # This line could cause issues in the future.
        if val != [] and val is not None:
            return Person(
                creator_id=val[0][1],
                eid=val[0][2],
                first=val[0][3],
                last=val[0][4],
                age=val[0][5],
                pass_time=val[0][6],
                wristband=val[0][7]
        )
        # EID generation
        eid = None
        while True:
            eid = uuid.uuid4().hex
            val = await db.execute(f"SELECT * FROM YMCA_GREEN_BOOK_ENTRIES WHERE entry_id='{eid}'")
            if val == []: break

        pass_time = int(time.time())
        await db.execute(
            "INSERT INTO YMCA_GREEN_BOOK_ENTRIES (server_id,user_id,entry_id,first_name,last_name,age,pass_time,wristband_color) VALUES "
            f"('{self.u.guild.id}', '{self.u.user.id}', '{eid}', '{first.upper()}', '{last.upper()}', '{age}', '{pass_time}', '{wristband}')"
        )

        rp = Person(
            creator_id=self.u.user.id,
            eid=eid,
            first=first.upper(),
            last=last.upper(),
            age=age,
            pass_time=pass_time,
            wristband=wristband,
            new=True
        )

        try:
            ch = await self.u.ymca_green_book_channel
            if ch is not None:
                await ch.send(
                    content=(
                        f"{self.u.user.mention} added `{rp.last}`, `{rp.first}`『`Age {rp.age}`』to the book "
                        f"as a {rp.wristband_emoji} `{rp.wristband}` band."
                    ),
                    allowed_mentions=discord.AllowedMentions(users=False)
                )
        except: pass

        return rp