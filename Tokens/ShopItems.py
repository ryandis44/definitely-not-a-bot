import discord
from Tokens.TokenClass import Token
from Tokens.embeds import sel_item

# Function containing all the item objects
def shop_items(interaction: discord.Interaction, t: Token) -> list:
    return [
        RenameHell(interaction, t),
        Timeout(interaction, t)
    ]

# Individual item parent class
class ShopItem:
    def __init__(self,
            emoji: str,
            name: str,
            dur: int,
            price: int,
            desc: str) -> None:

        self.emoji = emoji
        self.name = name
        self.dur = dur
        self.price = price
        self.desc = desc
    
    def __str__(self): return self.name
    
    @property
    def dur_formatted(self, granularity=1):
        secs = self.dur

        intervals = (
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),    # 60 * 60 * 24
            ('hours', 3600),    # 60 * 60
            ('minutes', 60),
            ('seconds', 1),
        )
        result = []

        for name, count in intervals:
            value = secs // count
            if value:
                secs -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        
        return ', '.join(result[:granularity])




class RenameHell(ShopItem):
    def __init__(self, interaction: discord.Interaction, t: Token):
        self.interaction = interaction
        self.t = t
        super().__init__(
            emoji="📝",
            name="Rename Hell",
            dur=604800,
            price=75,
            desc="Renames the user to a random word from a random message from any user"
        )

    def sel(self): return sel_item(self)

    def purchase(self): pass

class Timeout(ShopItem):
    def __init__(self, interaction: discord.Interaction, t: Token):
        self.interaction = interaction
        self.t = t
        super().__init__(
            emoji="❌",
            name="Timeout",
            dur=60,
            price=50,
            desc="Prevents user from interacting with this server for specified time"
        )

    def sel(self): return sel_item(self)

    def purchase(self): pass