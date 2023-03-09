import time
import discord
from discord.ui import View
from Database.database_class import Database
from Tokens.ShopItems import ShopItem
from tunables import tunables
from misc.embeds import modified_playtime_embed
from Playtime.playtime import avg_playtime_result, get_total_activity_updates, get_total_activity_updates_query, playtime_embed, total_playtime_result
tdb = Database("Tokens.Views.py")


class ShopView(View):
    
    def __init__(self, interaction: discord.Interaction, items: list):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.add_item(ItemSelector(interaction=interaction, items=items))
        self.interaction = interaction
        self.user = interaction.user
        self.items = items
    
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji="1️⃣", custom_id="one", disabled=False, row=1)
    # async def one(self, interaction: discord.Interaction, button = discord.Button):
    #     await interaction.response.edit_message()
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji="2️⃣", custom_id="two", disabled=False, row=1)
    # async def two(self, interaction: discord.Interaction, button = discord.Button):
    #     await interaction.response.edit_message()
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji="3️⃣", custom_id="three", disabled=False, row=1)
    # async def three(self, interaction: discord.Interaction, button = discord.Button):
    #     await interaction.response.edit_message()
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji=GENERIC_PREV_BUTTON, custom_id="left", disabled=False, row=2)
    # async def left(self, interaction: discord.Interaction, button = discord.Button):
    #     await interaction.response.edit_message()
    
    # @discord.ui.button(style=discord.ButtonStyle.gray, emoji=GENERIC_NEXT_BUTTON, custom_id="right", disabled=False, row=2)
    # async def right(self, interaction: discord.Interaction, button = discord.Button):
    #     await interaction.response.edit_message()
    
    # Only the user that ran the command to press buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user


class ItemSelector(discord.ui.Select):
    def __init__(self, interaction: discord.Interaction, items: list):
        self.interaction = interaction
        self.items = items

        options = []
        for i, item in enumerate(items):
            item: ShopItem = item
            options.append(
                discord.SelectOption(
                    label=f"{item.name} — {item.price} {'Tokens' if item.price != 1 else 'Token'}",
                    description=item.dur_formatted,
                    value=i,
                    emoji=item.emoji
                )
            )
            

        super().__init__(placeholder="Select an option", max_values=1, min_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):

        self.disabled = True
        i = int(self.values[0])
        await interaction.response.edit_message(
            view=ConfirmSelection(
                interaction=interaction,
                item=self.items[i]
            ),
            content=None,
            embed=self.items[i].sel()
        )


class ConfirmSelection(View):
    
    def __init__(self, interaction: discord.Interaction, item: ShopItem):
        super().__init__(timeout=tunables('GLOBAL_VIEW_TIMEOUT'))
        self.interaction = interaction
        self.user = interaction.user
    
    
    @discord.ui.button(style=discord.ButtonStyle.green, emoji=tunables('GENERIC_CONFIRM_BUTTON'), custom_id="c", disabled=False, row=1)
    async def one(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()
    
    @discord.ui.button(style=discord.ButtonStyle.red, emoji=tunables('GENERIC_DECLINE_BUTTON'), custom_id="d", disabled=False, row=1)
    async def two(self, interaction: discord.Interaction, button = discord.Button):
        await interaction.response.edit_message()