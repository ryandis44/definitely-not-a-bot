import asyncio
import openai
import discord
import re
from tunables import tunables, GLOBAL_EMBED_COLOR
from Database.GuildObjects import MikoMember

openai.api_key = tunables('OPENAI_API_KEY')

class MikoGPT:
    def __init__(self, u: MikoMember, client: discord.Client, prompt: str):
        self.u = u
        self.client = client
        self.prompt = prompt.split()
        self.response = {
            'type': "NORMAL", # NORMAL, SERIOUS, IMAGE
            'data': None
        }
        self.__sanitize_prompt()
    
    async def respond(self, message: discord.Message=None, interaction: discord.Interaction=None) -> None:
    
        if message is not None:
            msg = await message.reply(content=tunables('LOADING_EMOJI'), mention_author=False, silent=True)
        elif interaction is not None:
            msg = await interaction.original_response()
        else:
            print("Error [OpenAI.ai.MikoGPT:respond()]: Could not respond because a 'Message' or 'Interaction' object was not passed.")
            return
    
        try:
            block = asyncio.to_thread(self.__openai_interaction)
            await block

            if len(self.response['data']) >= 750 or self.response['type'] == "IMAGE":
                embed = self.__embed()
                content = self.u.user.mention
            else:
                embed = None
                content = self.response['data']

            await msg.edit(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=True
                )
            )
            self.u.increment_statistic('REPLY_TO_MENTION_OPENAI')
        except Exception as e:
            print(f">> OpenAI Response Error: {e}")
            self.u.increment_statistic('REPLY_TO_MENTION_OPENAI_REJECT')
            await msg.edit(
                content=f"{tunables('GENERIC_APP_COMMAND_ERROR_MESSAGE')[:-1]}: {e}"
            )
        
    
    def __sanitize_prompt(self) -> None:
        '''
        Clean up prompt and remove 'i:' and 's:'

        Determine whether response type is
        'IMAGE' or 'SERIOUS', if neither,
        keep type as 'NORMAL'
        '''
        
        for i, word in enumerate(self.prompt):
            if word in [f"<@{str(self.client.user.id)}>"]:
                # Remove word mentioning Miko
                # Mention does not have to be first word
                self.prompt.pop(i)
        
        if re.search('s:', self.prompt[0]):
            if self.prompt[0] == "s:":
                self.prompt.pop(0)
            else:
                self.prompt[0] = self.prompt[0][2:]
            self.response['type'] = "SERIOUS"
        if re.search('i:', self.prompt[0]):
            if self.prompt[0] == "i:":
                self.prompt.pop(0)
            else:
                self.prompt[0] = self.prompt[0][2:]
            self.response['type'] = "IMAGE"
    
    def __openai_interaction(self) -> None:
        prompt = ' '.join(self.prompt)

        if self.response['type'] != "IMAGE":
            
            role = tunables('OPENAI_RESPONSE_ROLE_DEFAULT')
            match self.response['type']:
                case 'SERIOUS' | 'IMAGE':
                    role = tunables('OPENAI_RESPONSE_ROLE_DEFAULT')
                
                case _:
                    if self.u.profile.feature_enabled('REPLY_TO_MENTION_OPENAI_SARCASTIC'):
                        role = tunables('OPENAI_RESPONSE_ROLE_SARCASTIC')
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                        {"role": "system", "content": role},
                        {"role": "user", "content": prompt}
                    ]
                )
        else:
            resp = openai.Image.create(
                prompt=prompt,
                n=1,
                size="256x256"
            )

        
        if self.response['type'] != "IMAGE":
            r = r"^.+(\n){2}(.|\n)*$"
            text = resp.choices[0].message.content
            if re.match(r, text):
                self.response['data'] = f"`{' '.join(self.prompt)}`\n{text}"
                
            else: self.response['data'] = text
        else:
            url = resp.data[0].url
            self.response['data'] = url 
    
    def __embed(self) -> discord.Embed:
        temp = []

        if self.response['type'] != "IMAGE":
            temp.append(
                "```\n"
                f"{self.response['data']}\n"
                "```"
            )
        else:
            temp.append(
                f"__Prompt__: `{' '.join(self.prompt)}`"
            )
        
        embed = discord.Embed(
            description=''.join(temp),
            color=GLOBAL_EMBED_COLOR
        )
        embed.set_author(
            icon_url=self.u.user_avatar,
            name=f"Generated by {self.u.username}"
        )
        embed.set_footer(
            text=f"{self.client.user.name} OpenAI/ChatGPT Integration [Beta]"
        )
        if self.response['type'] == "IMAGE":
            embed.set_image(
                url=self.response['data']
            )
        return embed