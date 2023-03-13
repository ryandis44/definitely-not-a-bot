import asyncio
import time
import discord
from tunables import *
from GreenBook.Objects import GreenBook, Person
from Database.GuildObjects import MikoMember
from Database.database_class import AsyncDatabase
db = AsyncDatabase("GreenBook.UI.py")

        


class BookView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('BOOK_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client, check_exists=False)
        self.book = GreenBook(self.u)

    async def ainit(self):
        await self.respond(init=True)    

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except: return
    
    # /book and back button response
    async def respond(self, init=False) -> None:
        res = await self.book.recent_entries
        res_len = len(res)
        async def __default_embed() -> discord.Embed:
            temp = []

            temp.append(
                "The YMCA Green Book for swim tests.\n"
                "This book can be accessed any time in this server "
                "using </book:1082021544831754301>.\n"
                ""
                "Use the buttons below to search, add, or modify entries "
                "in the green book.\n\n"
            )

            total_entries = await self.book.total_entries
            if res_len > 0: temp.append("__Recent entries__ `[Last Name, First Name]`:")
            else: temp.append("There are no entries in this book. Add one by pressing the  `New Entry`  button.")
            for result in res:
                temp.append(f"\n{result}")
            
            if res_len < total_entries:
                temp.append(f"... and {(total_entries - res_len):,} more\n\n")
            

            embed = discord.Embed(description=''.join(temp), color=GREEN_BOOK_NEUTRAL_COLOR)
            embed.set_author(
                icon_url=self.u.guild.icon,
                name=f"{self.u.guild} Green Book"
            )
            return embed
        
        self.clear_items()
        if res_len > 0: self.add_item(SelectEntries(bview=self, res=res))
        self.add_item(NewEntry(bview=self))
        self.add_item(SearchButton(bview=self))
        if self.u.user.guild_permissions.manage_guild:
            self.add_item(LogChannelButton(bview=self))
        # if admin, add more stuff self.add_item(admin)

        if init: self.msg = await self.original_interaction.original_response()
        await self.msg.edit(
            content=None,
            embed=await __default_embed(),
            view=self
        )

    # Response after completing search modal
    async def respond_modal_search(self, modal) -> None:
        res = await self.book.search(query=modal.name.value)
        cnt = len(res)
        if cnt == 1:
            await self.respond_select_person(p=res[0])
            return

        def __search_embed() -> discord.Embed:
            temp = []

            if cnt == 0:
                temp.append(f"Could not find an entry matching `{modal.name.value}`")
                color = GREEN_BOOK_FAIL_COLOR
            else:
                temp.append(f"{cnt if cnt < 9 else 'Top ten most relevant'} search result{'s' if cnt > 1 else ''}:\n\n__`Last Name, First Name`__\n")
                color = GREEN_BOOK_NEUTRAL_COLOR
            for result in res:
                temp.append(f"{result}\n")

            embed = discord.Embed(description=''.join(temp), color=color)
            embed.set_author( icon_url=self.u.guild.icon, name=f"{self.u.guild} Green Book")
            return embed
        
        self.clear_items()
        b = BackToMainButton(bview=self)
        b.row = 2
        self.add_item(b)
        if cnt > 0: self.add_item(SelectEntries(bview=self, res=res))
        self.add_item(SearchButton(bview=self))

        await self.msg.edit(
            content=None,
            embed=__search_embed(),
            view=self
        )
        self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_SEARCHED')

    # Response after choosing someone from the dropdown
    async def respond_select_person(self, p: Person) -> None:
        async def __selected_person_embed() -> discord.Embed:
            embed = discord.Embed(
                description=''.join(await self.__detailed_entry_embed_description(p=p)),
                color=GREEN_BOOK_NEUTRAL_COLOR
            )
            embed.set_author(
                icon_url=self.u.guild.icon,
                name=f"{self.u.guild} Green Book"
            )
            return embed
        self.clear_items()
        self.add_item(BackToMainButton(bview=self))
        self.add_item(EditEntry(bview=self, p=p))
        if self.u.user.guild_permissions.manage_guild:
            self.add_item(DeleteEntry(bview=self, p=p))

        await self.msg.edit(
            content=None,
            embed=await __selected_person_embed(),
            view=self
        )

    # Description for full entry info
    async def __detailed_entry_embed_description(self, p: Person, history=True) -> list:
        temp = []
        
        temp.append(
            f"Full Entry Info for **{p.last}**, **{p.first}**:\n\n"

            f"First Name: **{p.first}**\n"
            f"Last Name: **{p.last}**\n"
            f"Age: **{p.age}**\n"
            # f"DOB: "
            f"Wristband Level: {p.wristband_emoji} **{p.wristband}**\n"
            f"Entered: __{p.pass_time_formatted}__\n"
            f"By: {p.creator_id_mention}\n"
            f"EID: `{p.eid}`\n"
        )

        hist = await p.history
        hist_len = len(hist)
        if hist_len == 0 and history:
            temp.append("\nThis entry has not been updated since its creation.")
        elif history:
            temp.append(
                f"\nThis entry has been updated `{hist_len if hist_len < 10 else 'more than 10'}` time{'s' if hist_len > 1 else ''}. "
                f"{'These are the latest updates:' if hist_len > 1 else 'This is the latest update:'}\n"
            )
            for update in hist:
                temp.append(f"\n{update}")
        
        return temp

    # Response for selecting individual user
    async def respond_detailed_entry(self, t: str, p: Person=None, modal=None) -> None:
        desc = []

        # Embed setup
        history=True
        match t:
            
            case 'EDIT':
                if await p.edit(modal=modal, modifier=self.u.user):
                    desc.append(
                        f":white_check_mark: __**Success! The entry for  `{p.last}, {p.first}`  has been updated.**__"
                    )
                    color = GREEN_BOOK_SUCCESS_COLOR
                    self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_EDITED')
        
            case 'NEW':
                wristband = modal.wristband.value
                if wristband.upper() == "Y": wristband = "YELLOW"
                elif wristband.upper() == "R": wristband = "RED"
                else: wristband = "GREEN"
                p: Person = await self.book.create(
                    first=modal.first.value,
                    last=modal.last.value,
                    age=modal.age.value,
                    wristband=wristband
                )
                if p.new:
                    desc.append(
                        f":white_check_mark: __**Success!  `{p.last}, {p.first}`  has been added to the Green Book.**__"
                    )
                    color = GREEN_BOOK_SUCCESS_COLOR
                else:
                    desc.append(
                        f":exclamation:  __**`{p.last}, {p.first}`  is already in the Green Book. Here is their info:**__"
                    )
                    color = GREEN_BOOK_WARN_COLOR
                self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_CREATED')

            case 'DELETE_WARN':
                desc.append(
                    f"⚠ __**Warning: You are about to remove  `{p.last}, {p.first}`  from the Green Book. "
                    "Confirm deletion?**__"
                )
                history=False
                color = GREEN_BOOK_WARN_COLOR
            
            case 'DELETE_CONFIRM':
                desc.append(
                    f":white_check_mark: __**Success!  `{p.last}, {p.first}`  has been removed from the Green Book.**__"
                )
                color = GREEN_BOOK_SUCCESS_COLOR
                await p.delete()
                self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_DELETED')
            
            case 'DELETE_CANCEL':
                desc.append(
                    f":x: __**Cancelled.  `{p.last}, {p.first}`  was not removed from the Green Book.**__"
                )
                color = GREEN_BOOK_FAIL_COLOR
                
            case _:
                color = GREEN_BOOK_NEUTRAL_COLOR



        if t not in ['DELETE_CONFIRM']:
            desc.append("\n\n")
            desc.append(''.join(await self.__detailed_entry_embed_description(p=p, history=history)))
        embed = discord.Embed(description=''.join(desc), color=color)
        embed.set_author(icon_url=self.u.guild.icon, name=f"{self.u.guild} Green Book")

        self.clear_items()
        match t:
            case 'DELETE_WARN':
                self.add_item(DeleteCancel(bview=self, p=p))
                self.add_item(DeleteConfirm(bview=self, p=p))

            case 'DELETE_CONFIRM':
                self.add_item(BackToMainButton(bview=self))

            case _:
                self.add_item(BackToMainButton(bview=self))
                self.add_item(EditEntry(bview=self, p=p))
                if self.u.user.guild_permissions.manage_guild:
                    self.add_item(DeleteEntry(bview=self, p=p))

        await self.msg.edit(
            content=None,
            embed=embed,
            view=self
        )


    def __log_channel_description(self, log_channel: discord.TextChannel = None) -> list:
        temp = []

        if log_channel is not None:
            log_channel = log_channel.mention
        else: log_channel = "`None`"

        temp.append(
            f"__Current Log channel: {log_channel}\n\n__"
        )

        temp.append(
            "Use the dropdown below to set the channel "
            f"that {self.u.client.user.mention} will send new Green Book entries "
            "to. Select `Deselect Channel` to remove current channel "
            "(if any)."
            "\n\n"
            "**Note**: If your channel does not appear, it could be "
            f"because {self.u.client.user.mention} does not have `Send Messages` and/or `View Channel` "
            "permissions in that channel."
            "\n\n"
            "Press the `Use ID` "
            "button to choose a channel by pasting in its channel ID. To get "
            "a channel ID, type `#` in chat and begin typing its name. Select "
            "it from the list of channels that pop up and then put a backslash "
            "`\\` in front of it. It will give you something that looks like "
            "`<#1084326524683038880>`. The ID is the numbers and the numbers only."
        )

        return temp

    async def respond_log_channel(self, t: str, channel: discord.TextChannel = None) -> None:
        desc = []

        log_channel = await self.u.ymca_green_book_channel
        # Embed setup
        match t:
            
            case 'SET':
                send_msg = False
                read_msg = False
                er = []
                try:
                    send_msg = channel.permissions_for(channel.guild.me).send_messages
                    read_msg = channel.permissions_for(channel.guild.me).read_messages
                except: pass
                if not send_msg or not read_msg:
                    if not send_msg: er.append('`Send Messages`')
                    if not read_msg: er.append('`Read Messages`')
                    desc.append(
                        f"❗ **Error: Unable to set channel {channel.mention} as log channel. I do not "
                        f"have {' or '.join(er)} "
                        "permissions in that channel.**"
                    )
                    color = GREEN_BOOK_FAIL_COLOR
                else:
                    desc.append(
                        f"✅ **Success! Set {channel.mention} as the Green Book log channel. "
                        "To unset this channel, press the `Deselect Channel` button.**"
                    )
                    await db.execute(
                        f"UPDATE SERVERS SET ymca_green_book_channel='{channel.id}' "
                        f"WHERE server_id='{self.original_interaction.guild.id}'"
                    )
                    log_channel = channel
                    color = GREEN_BOOK_SUCCESS_COLOR

            case 'DESELECT':
                if log_channel is not None:
                    desc.append(
                        f"✅ **Success! {log_channel.mention} will no longer receive "
                        "Green Book log updates.**"
                    )
                    await db.execute(
                        "UPDATE SERVERS SET ymca_green_book_channel=NULL WHERE "
                        f"server_id='{self.original_interaction.guild.id}'"
                    )
                    log_channel = None
                    color = GREEN_BOOK_SUCCESS_COLOR
                else:
                    desc.append(
                        "⚠ Error: There is no active log channel."
                    )
                    color = GREEN_BOOK_WARN_COLOR
                
            case _:
                color = GREEN_BOOK_NEUTRAL_COLOR

        desc.append("\n\n")
        desc.append(''.join(self.__log_channel_description(log_channel=log_channel)))
        embed = discord.Embed(description=''.join(desc), color=color)
        embed.set_author(icon_url=self.u.guild.icon, name=f"{self.u.guild} Green Book")

        self.clear_items()
        self.add_item(SelectLogChannel(bview=self))
        b = BackToMainButton(bview=self)
        b.row = 2
        self.add_item(b)
        self.add_item(UseChannelIDButton(bview=self))
        d = DeselectChannel(bview=self)
        if log_channel is not None: d.disabled=False
        self.add_item(d)

        await self.msg.edit(
            content=None,
            embed=embed,
            view=self
        )

class SearchButton(discord.ui.Button):

    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label=None,
            emoji="🔎",
            custom_id="search_button",
            row=2
        )
        self.bview = bview
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self.SearchModal(bview=self.bview))

    class SearchModal(discord.ui.Modal):

        def __init__(self, bview: BookView):
            super().__init__(title="Search the book", custom_id="search_modal")
            self.bview = bview

        name = discord.ui.TextInput(
                label="Search by Name (first, last, or both):",
                placeholder="Bradford",
                min_length=1,
                max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH')
            )
        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.edit_message()
            await self.bview.respond_modal_search(modal=self)


class BackToMainButton(discord.ui.Button):

    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="Back",
            emoji=None,
            custom_id="back_button",
            row=1
        )
        self.bview = bview
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond()


def check_modal_error(modal) -> dict:
    e = {
        'age': False,
        'wristband': False,
        'type': False,
        'len': False,
        'channel': None
    }
    try: int(modal.age.value)
    except: e['age'] = True

    try: int(modal.chid.value)
    except: e['type'] = True

    try:
        if len(modal.chid.value) < 15: e['len'] = True
    except: pass

    try:
        if not e['type'] and not e['len']:
            e['channel'] = modal.bview.original_interaction.guild.get_channel(int(modal.chid.value))
    except: pass

    try:
        if not e['age']:
            if int(modal.age.value) < 1 or int(modal.age.value) > 100: e['age'] = True
    except: pass

    try:
        if modal.wristband.value.upper() not in ['G', 'Y', 'R', '']:
            e['wristband'] = True
    except: pass

    return e

async def on_modal_submit(modal, interaction: discord.Interaction, p: Person=None) -> None:
    e = check_modal_error(modal=modal)
    if e['age'] or e['wristband']: raise Exception

    # Message gets deleted during error handling; except and pass
    try: await interaction.response.edit_message()
    except: pass
    if p is None: await modal.bview.respond_detailed_entry(t='NEW', modal=modal)
    else: await modal.bview.respond_detailed_entry(t='EDIT', modal=modal, p=p)

async def on_modal_error(modal, error_interaction: discord.Interaction):
        e = check_modal_error(modal=modal)
        
        temp = []
        if e['age']: temp.append("`Age` must be a number between 1 and 100.")
        if e['wristband']: temp.append("`Wristband Color` must be one letter: `r` for Red, `y` for Yellow, or `g` for Green (or leave empty for Green)")

        try:
            modal.first.default = modal.first.value
            modal.last.default = modal.last.value
        except: pass
        if not e['age']: modal.age.default = modal.age.value
        if not e['wristband']: modal.wristband.default = modal.wristband.value

        if not error_interaction.response.is_done():
            await error_interaction.response.send_message(
                content='\n'.join(temp),
                ephemeral=True,
                view=ModalTryAgain(calling_modal=modal, error_interaction=error_interaction)
            )


     
class FullEntryModal(discord.ui.Modal):

    def __init__(self, bview: BookView, p: Person=None):
        super().__init__(title="New Green Book Entry", custom_id="entry_modal")
        self.bview = bview
        self.p = p

    first = discord.ui.TextInput(
            label="First Name",
            placeholder="Chris",
            min_length=1,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            default=None
        )
    
    last = discord.ui.TextInput(
            label="Last Name",
            placeholder="Bradford",
            min_length=1,
            max_length=tunables('GREEN_BOOK_MAX_SEARCH_LENGTH'),
            default=None
        )
    
    age = discord.ui.TextInput(
            label="Age:",
            placeholder="12",
            min_length=1,
            max_length=3,
            default=None
        )

    wristband = discord.ui.TextInput(
            label="Wristband Color (Leave blank for green):",
            placeholder="r (red), y (yellow), g (green)",
            min_length=0,
            max_length=1,
            required=False,
            default=None
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await on_modal_submit(modal=self, interaction=interaction, p=self.p)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await on_modal_error(modal=self, error_interaction=interaction)


class AgeWristbandModal(discord.ui.Modal):

    def __init__(self, bview: BookView, p: Person):
        super().__init__(title="New Green Book Entry", custom_id="entry_modal")
        self.bview = bview
        self.p = p
    
    age = discord.ui.TextInput(
            label="Age:",
            placeholder="12",
            min_length=1,
            max_length=3,
            default=None
        )

    wristband = discord.ui.TextInput(
            label="Wristband Color (Leave blank for green):",
            placeholder="r (red), y (yellow), g (green)",
            min_length=0,
            max_length=1,
            required=False,
            default=None
        )
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await on_modal_submit(modal=self, interaction=interaction, p=self.p)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await on_modal_error(modal=self, error_interaction=interaction)


class NewEntry(discord.ui.Button):

    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="New Entry",
            emoji=None,
            custom_id="new_button",
            row=2
        )
        self.bview = bview
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(FullEntryModal(bview=self.bview))


class EditEntry(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.green,
            label=None,
            emoji="✏",
            custom_id="new_button",
            row=1
        )
        self.bview = bview
        self.p = p
        
        if self.bview.u.user.guild_permissions.manage_guild:
            self.m = FullEntryModal(bview=self.bview, p=self.p)
            self.m.first.default = p.first
            self.m.last.default = p.last
        else:
            self.m = AgeWristbandModal(bview=self.bview, p=self.p)
        self.m.age.default = p.age
        self.m.wristband.default = p.wristband_letter
        

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self.m)


class ModalTryAgain(discord.ui.View):
    def __init__(self, calling_modal, error_interaction: discord.Interaction):
        super().__init__(timeout=tunables('BOOK_VIEW_TIMEOUT'))
        self.calling_modal = calling_modal
        self.error_interaction = error_interaction

    async def __original_response(self):
        try: self.original_response = await self.error_interaction.original_response()
        except: pass

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="Try Again", custom_id="button_try_again")
    async def try_again(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.send_modal(self.calling_modal)
        self.stop()
        await self.__original_response()
        try: await self.original_response.delete()
        except: pass


class SelectEntries(discord.ui.Select):
    def __init__(self, bview: BookView, res: list):
        self.bview = bview
        self.res = res

        options = []

        for i, result in enumerate(res):
            result: Person = result
            options.append(
                discord.SelectOption(
                    label=f"{result.last}, {result.first}",
                    description=f"Age {result.age}",
                    value=i,
                    emoji=result.wristband_emoji
                )
            )

        super().__init__(
            placeholder="Select an entry from above",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
            custom_id="select_entry",
            disabled=False
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message()
        p = self.res[int(self.values[0])]
        await self.bview.respond_select_person(p=p)

class DeleteEntry(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Delete",
            emoji=None,
            custom_id="delete_button",
            row=1
        )
        self.bview = bview
        self.p = p

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_detailed_entry(t='DELETE_WARN', p=self.p)

class DeleteCancel(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.red,
            label=None,
            emoji="✖",
            custom_id="cancel_delete_button",
            row=1
        )
        self.bview = bview
        self.p = p

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_detailed_entry(t='DELETE_CANCEL', p=self.p)

class DeleteConfirm(discord.ui.Button):
    def __init__(self, bview: BookView, p: Person):
        super().__init__(
            style=discord.ButtonStyle.green,
            label=None,
            emoji="✔",
            custom_id="confirm_delete_button",
            row=1
        )
        self.bview = bview
        self.p = p

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_detailed_entry(t='DELETE_CONFIRM', p=self.p)


class LogChannelButton(discord.ui.Button):
    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="Log Channel",
            emoji=None,
            custom_id="logc_button",
            row=2
        )
        self.bview = bview

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_log_channel(t='DEFAULT')



class UseChannelIDButton(discord.ui.Button):
    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="Use ID",
            emoji=None,
            custom_id="id_button",
            row=2
        )
        self.bview = bview

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(self.ChannelIDModal(bview=self.bview))

    class ChannelIDModal(discord.ui.Modal):

        def __init__(self, bview: BookView):
            super().__init__(title="Enter Channel ID", custom_id="channel_id_modal")
            self.bview = bview

        chid = discord.ui.TextInput(
                label="Enter Channel ID:",
                placeholder=f"1084326524683038880",
                min_length=1,
                max_length=30
            )
        async def on_submit(self, interaction: discord.Interaction) -> None:
            e = check_modal_error(modal=self)
            if e['type'] or e['len'] or e['channel'] is None: raise Exception
            await interaction.response.edit_message()
            await self.bview.respond_log_channel(t='SET', channel=e['channel'])
        
        async def on_error(self, interaction: discord.Interaction, error) -> None:
            e = check_modal_error(modal=self)
            temp = []
            if e['type']: temp.append("`Channel ID` must be a number")
            if e['len']: temp.append("`Channel ID` must be between 15 and 30 numbers in length.")
            if not e['len'] and not e['type'] and e['channel'] is None:
                temp.append(f"No channel in this server found with ID `{self.chid.value}`")

            await interaction.response.send_message(
                content="\n".join(temp),
                ephemeral=True,
                view=ModalTryAgain(calling_modal=self, error_interaction=interaction)
            )


class SelectLogChannel(discord.ui.ChannelSelect):
    def __init__(self, bview: BookView):
        self.bview = bview

        super().__init__(
            placeholder="Select a channel",
            min_values=1,
            max_values=1,
            row=1,
            custom_id="select_channel",
            disabled=False,
            channel_types=[discord.ChannelType.text]
        )
    
    async def callback(self, interaction: discord.Interaction):
        ch: discord.app_commands.AppCommandChannel = self.values[0]
        try: ch = await ch.fetch()
        except: pass
        await interaction.response.edit_message()
        await self.bview.respond_log_channel(t='SET', channel=ch)


class DeselectChannel(discord.ui.Button):
    def __init__(self, bview: BookView):
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Deselect Channel",
            emoji=None,
            custom_id="deselect_button",
            row=2,
            disabled=True
        )
        self.bview = bview

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message()
        await self.bview.respond_log_channel(t='DESELECT')