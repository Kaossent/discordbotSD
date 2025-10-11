import random

from disnake.ui import View
from html2image import Html2Image
from disnake.ext import commands, tasks
from main import rules, get_rule_info, check_roles, collusers, collservers, collgiveways
import disnake
from jinja2 import Template
import io
from PIL import Image
import os
from datetime import datetime, timedelta
import pymongo

hti = Html2Image()

class GivewayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not self.check_giveways.is_running():
            self.check_giveways.start()
        with open('./static/giveway.html', 'r', encoding='utf-8') as file:
            self.template = Template(file.read())

    def convert_to_seconds(self, time_str):
        try:
            value = int(time_str[:-1])
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")

        unit = time_str[-1]
        if unit == 'д' or unit == 'd':
            return value * 24 * 60 * 60
        elif unit == 'ч' or unit == 'h':
            return value * 60 * 60
        elif unit == 'м' or unit == 'm':
            return value * 60
        elif unit == 'с' or unit == 's':
            return value


    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            values = {
                '_id': guild.id,
                'giveways': [],
                'active_giveways': 0,
                'ended_giveways': 0,
                "count_giveways": 0
            }
            if collgiveways.count_documents({"_id": guild.id}) == 0:
                collgiveways.insert_one(values)
                print(f'Added {guild.id} n givw1ays collection.')

    def render_profile_card(self, template_path, output_path, **variables):
        """
        Рендерит HTML карточку профиля с переданными переменными

        Args:
            template_path: путь к HTML шаблону
            output_path: путь для сохранения результата
            **variables: переменные для подстановки
        """
        rendered_html = self.template.render(**variables)

        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(rendered_html)

        print(f"Карточка сохранена в: {output_path}")

    @tasks.loop(seconds=60)
    async def check_giveways(self):
        print('GivewayCog: Checking giveways..')
        for guild in self.bot.guilds:
            print(f'GivewayCog: {guild.name}')
            giveways = collgiveways.find_one({"_id": guild.id})['giveways']
            for giveway in giveways:
                winners = []
                print(int(giveway['duration']) < int(datetime.now().timestamp()))
                if int(giveway['duration']) < int(datetime.now().timestamp()):
                    members = giveway['members']
                    count_winners = giveway['winners']
                    if len(members) < giveway['winners']:
                        count_winners = len(members)
                    for i in range(count_winners):
                        winner = random.choice(members)
                        winners.append(winner)
                        members.remove(winner)
                    channel = guild.get_channel(giveway['channel_id'])
                    await channel.send(f'Победители {winners}')
                    users = []
                    for winner in winners:
                        winner = self.bot.get_user(winner)
                        users.append(winner)
                        try:
                            await winner.send(giveway['prize'])
                        except:
                            channel = guild.get_channel(944562833901899827)
                            await channel.send(f'Сын шлюхи {winner.mention} не получил приз')
                    collgiveways.update_one({'_id': guild.id},
                                            {'$pull': {'giveways': {'giveway_id': giveway['giveway_id']}}})
                    collgiveways.update_one({'_id': guild.id}, {'$inc': {'active_giveways': -1}})
                    collgiveways.update_one({'_id': guild.id}, {'$inc': {'ended_giveways': 1}})
                    variables = {
                        'winners': users,
                        'avatar': guild.icon.url
                    }
                    self.render_profile_card('./static/giveway.html', output_path='./static/giveway_final.html',
                                             **variables)
                    hti.screenshot(html_file='./static/giveway_final.html', save_as='giveway.png', size=[324, 380])
                    with Image.open('./giveway.png') as img:
                        # Координаты: left, top, right, bottom
                        img_buffer = io.BytesIO()
                        print(count_winners)
                        if count_winners == 1:
                            cropped_img = img.crop((786, 383, 1100, 602))  # x1, y1, x2, y2
                        elif count_winners == 2:
                            cropped_img = img.crop((791, 347, 1112, 638))  # x1, y1, x2, y2
                        elif count_winners == 3:
                            cropped_img = img.crop((791, 311, 1112, 674))  # x1, y1, x2, y2
                        else:
                            return
                        cropped_img.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                    await channel.send(file=disnake.File(img_buffer, filename='giveway.png'))






    @commands.slash_command(name='giveway')
    @check_roles('staff')
    async def giveway(self, inter):
        pass

    class ParticipateView(View):
        def __init__(self, giveway_id: int):
            super().__init__(timeout=None)
            self.giveway_id = giveway_id

        @disnake.ui.button(label="Участвовать", style=disnake.ButtonStyle.primary, emoji="🎯")
        async def participate_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            await interaction.response.defer(ephemeral=True)

            count = collgiveways.count_documents({"_id": interaction.guild.id,
                                         'giveways': {
                '$elemMatch': {
                    'giveway_id': self.giveway_id,
                    'members': interaction.user.id,
                }
            }})

            if count == 0:
                collgiveways.update_one({'_id': interaction.guild.id, 'giveways.giveway_id': self.giveway_id},
                                        {'$push': {'giveways.$.members': interaction.user.id}})

                await interaction.followup.send(
                    f"{interaction.user.mention}, вы успешно зарегистрировались для участия!", ephemeral=True
                )
            else:
                await interaction.followup.send(f'Вы ужeе участвуете.', ephemeral=True)

        @disnake.ui.button(label='Участники', style=disnake.ButtonStyle.success)
        async def members(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            global string
            await interaction.response.defer(ephemeral=True)

            members = collgiveways.find_one(
                {
                    "_id": interaction.guild.id,
                    "giveways": {
                        "$elemMatch": {
                            "giveway_id": self.giveway_id
                        }
                    }
                },
                {
                    "giveways.$": 1  # Возвращаем только соответствующий гиввей
                }
            )['giveways'][0]['members']
            mentions = []
            for member in members:
                mentions.append(f'<@{member}>')
            result = '\n'.join(mentions)
            await interaction.followup.send(f'Members:\n{result}', ephemeral=True)


    @giveway.sub_command(name='create')
    @check_roles('staff')
    async def giveway_create(self, inter, победителей: int, название_приза: str, приз: str, длительность: str, канал: disnake.TextChannel):
        await inter.response.defer(ephemeral=True)
        now = int(datetime.now().timestamp())
        duration = self.convert_to_seconds(длительность)
        duration = now + duration

        user = inter.author
        guild_id = inter.guild.id

        collgiveways.update_one({'_id': inter.guild.id}, {'$inc': {'active_giveways': 1}})
        count_giveways = collgiveways.find_one({'_id': inter.guild.id})['count_giveways']
        collgiveways.update_one({'_id': inter.guild.id}, {'$inc': {'count_giveways': 1}})

        view = self.ParticipateView(giveway_id=count_giveways + 1)
        message = await канал.send('Розыгрыш', view=view)

        giveway_value = {
            'giveway_id': count_giveways + 1,
            'creator': user.id,
            'winners': победителей,
            'duration': duration,
            'channel_id': канал.id,
            'message_id': message.id,
            'name_of_prize': название_приза,
            'prize': приз,
            'members': []
        }
        collgiveways.update_one({'_id': guild_id}, {'$push': {'giveways': giveway_value}})

        await inter.edit_original_response(f'{длительность}, {now}, {duration}')



def setup(bot):
    bot.add_cog(GivewayCog(bot))
    print("GivewayCog is ready")