import asyncio
import time
import discord
from tunables import *
from GreenBook.Objects import GreenBook, Person
from Database.GuildObjects import MikoMember
from Database.database_class import Database
db = Database("GreenBook.UI.py")

        


class BookView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=tunables('BOOK_VIEW_TIMEOUT'))
        self.original_interaction = original_interaction
        self.u = MikoMember(user=original_interaction.user, client=original_interaction.client, check_exists=False)
        self.book = GreenBook(self.u)
        asyncio.create_task(self.respond(init=True))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.u.user.id

    async def on_timeout(self) -> None:
        try:
            msg = await self.original_interaction.original_response()
            await msg.delete()
        except: return
    
    # /book and back button response
    async def respond(self, init=False) -> None:
        res = self.book.recent_entries
        res_len = len(res)
        def __default_embed() -> discord.Embed:
            temp = []

            temp.append(
                "The YMCA Green Book for swim tests.\n"
                "This book can be accessed any time in this server "
                "using </book:1082021544831754301>.\n"
                ""
                "Use the buttons below to search, add, or modify entries "
                "in the green book.\n\n"
            )

            total_entries = self.book.total_entries
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
        # if admin, add more stuff self.add_item(admin)

        if init: self.msg = await self.original_interaction.original_response()
        await self.msg.edit(
            content=None,
            embed=__default_embed(),
            view=self
        )

    # Response after completing search modal
    async def respond_modal_search(self, modal) -> None:
        res = self.book.search(query=modal.name.value)
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
        else: self.add_item(SearchButton(bview=self))

        await self.msg.edit(
            content=None,
            embed=__search_embed(),
            view=self
        )
        self.u.increment_statistic('YMCA_GREEN_BOOK_ENTRIES_SEARCHED')

    # Response after choosing someone from the dropdown
    async def respond_select_person(self, p: Person) -> None:
        def __selected_person_embed() -> discord.Embed:
            embed = discord.Embed(
                description=''.join(self.__detailed_entry_embed_description(p=p)),
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
            embed=__selected_person_embed(),
            view=self
        )

    # Description for full entry info
    def __detailed_entry_embed_description(self, p: Person, history=True) -> list:
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

        hist = p.history
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


    async def respond_detailed_entry(self, t: str, p: Person=None, modal=None) -> None:
        desc = []

        # Embed setup
        history=True
        match t:
            
            case 'EDIT':
                if p.edit(modal=modal, modifier=self.u.user):
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
                p: Person = self.book.create(
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
                p.delete()
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
            desc.append(''.join(self.__detailed_entry_embed_description(p=p, history=history)))
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
        'wristband': False
    }
    try: int(modal.age.value)
    except: e['age'] = True

    if not e['age']:
        if int(modal.age.value) < 1 or int(modal.age.value) > 100: e['age'] = True

    if modal.wristband.value.upper() not in ['G', 'Y', 'R', '']:
        e['wristband'] = True
    
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
        asyncio.create_task(self.__original_response())

    async def __original_response(self):
        try: self.original_response = await self.error_interaction.original_response()
        except: pass

    @discord.ui.button(style=discord.ButtonStyle.blurple, label="Try Again", custom_id="button_try_again")
    async def try_again(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.send_modal(self.calling_modal)
        self.stop()
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