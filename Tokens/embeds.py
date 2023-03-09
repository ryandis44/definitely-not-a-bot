import discord
from tunables import tunables, GLOBAL_EMBED_COLOR
from Tokens.TokenClass import Token

def token_shop(items, t: Token):
    
    
    temp = []
    temp.append(f"Your Tokens: :coin: `{t.tokens:,} {'Tokens' if t.tokens != 1 else 'Token'}`")

    for i, item in enumerate(items):
        item = item
        temp.append("\n\n")
        temp.append(f"• ")
        temp.append(f"{item.emoji} ")
        temp.append(f"{item} ")
        temp.append(f"`{item.dur_formatted}` ")
        temp.append(f"~ ")
        temp.append(f"**{item.price:,} {'Tokens' if item.price != 1 else 'Token'}**")
        temp.append("\n")
        temp.append(f"\u200b \u200b _{item.desc}_")

    
    embed = discord.Embed (
        title = f'Token Shop',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    return embed

def sel_item(item) -> discord.Embed:
    temp = []

    temp.append("Are you sure you wish to purchase:\n\n")
    temp.append(f"• {item.emoji} {item} `{item.dur_formatted}` for **{item.price} {'Tokens' if item.price != 1 else 'Token'}**")
    temp.append("?")

    embed = discord.Embed (
        title = f'Purchase Item',
        color = GLOBAL_EMBED_COLOR,
        description=f"{''.join(temp)}"
    )
    return embed

def item_purchased(item):
    temp = []

    temp.append("You Purchased:\n\n")
    temp.append(f"• {item.emoji} {item} `{item.dur_formatted}` for **{item.price} {'Tokens' if item.price != 1 else 'Token'}**")

    embed = discord.Embed (
        title = f'Item Purchased',
        color = discord.Color.green(),
        description=f"{''.join(temp)}"
    )
    return embed