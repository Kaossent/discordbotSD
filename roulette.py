import disnake
from disnake.ext import commands
import random
from pymongo import MongoClient, errors, collection
from main import cluster, create_error_embed
from datetime import datetime, timedelta
from ai.process_role import process_role
import asyncio
from .economy import format_duration, format_rumbick, emoji
from disnake import ui

last_spin_times = {}

collusers = cluster.server.users
collservers = cluster.server.servers


def check_value(inter):
    result = collusers.update_one(
        {"id": inter.author.id, "guild_id": inter.guild.id, "keys": {"$exists": False}},
        {"$set": {"keys": 0}}  # Значение для поля age
    )
def seconds_to_dhm(seconds):
    days = seconds // 86400  # 86400 секунд в одном дне
    hours = (seconds % 86400) // 3600  # 3600 секунд в одном часе
    minutes = (seconds % 3600) // 60  # 60 секунд в одной минуте

    return int(days), int(hours), int(minutes)

class RewardsView(ui.View):
    def __init__(self, cog, inter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cog = cog
        self.inter = inter
        self.sorted = False

    @ui.button(label="♻️ Сортировать по шансам", style=disnake.ButtonStyle.green)
    async def sort_button(self, button: ui.Button, interaction: disnake.MessageInteraction):
        # Переключаем состояние сортировки
        self.sorted = not self.sorted
        button.label = "♻️ Показать в обычном порядке" if self.sorted else "♻️ Сортировать по шансам"

        # Получаем список наград и сортируем их при необходимости
        roulette_options = self.cog.get_roulette_options()
        if self.sorted:
            roulette_options = sorted(roulette_options, key=lambda x: x['chance'], reverse=True)

        # Форматируем список наград
        formatted_list = self.cog.format_rewards_list(roulette_options)

        # Обновляем эмбед
        embed = disnake.Embed(
            title="Список наград и их шансы",
            description=formatted_list,
            color=0xffff00,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url='https://i.pinimg.com/originals/f2/43/fc/f243fcb6032c81ca9870d098ee7587ba.gif')
        embed.set_footer(text="Удачи!", icon_url=self.inter.guild.icon.url)

        await interaction.response.edit_message(embed=embed, view=self)

class RouletteCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.allowed_channel_id = 1279413707981455422

    def get_roulette_options(self):
        return [
            {'name': '😔 Пусто', 'chance': 15, 'field': 'none', 'value': None},
            {'name': '🔇 Мут от 1 до 5 минут', 'chance': 5, 'field': 'mute', 'value': (1, 5)},
            {'name': '🔇 Мут от 5 до 10 минут', 'chance': 3, 'field': 'mute', 'value': (5, 10)},
            {'name': '🔇 Мут от 10 до 20 минут', 'chance': 1, 'field': 'mute', 'value': (10, 20)},
            {'name': '🔇 Мут от 20 до 40 минут', 'chance': 0.5, 'field': 'mute', 'value': (20, 40)},
            {'name': f'{emoji} От 1 до 25', 'chance': 26.4, 'field': 'currency', 'value': (1, 25)},
            {'name': f'{emoji} От 25 до 50', 'chance': 17.7, 'field': 'currency', 'value': (25, 50)},
            {'name': f'{emoji} От 50 до 100', 'chance': 6.4, 'field': 'currency', 'value': (50, 100)},
            {'name': f'{emoji} От 100 до 200', 'chance': 2.5, 'field': 'currency', 'value': (100, 200)},
            {'name': f'{emoji} От 200 до 500', 'chance': 0.75, 'field': 'currency', 'value': (200, 500)},
            {'name': f'{emoji} От 500 до 1000', 'chance': 0.3, 'field': 'currency', 'value': (500, 1000)},
            {'name': f'{emoji} От 1000 до 2000', 'chance': 0.04, 'field': 'currency', 'value': (1000, 2000)},
            {'name': f'{emoji} От 2000 до 3000', 'chance': 0.01, 'field': 'currency', 'value': (2000, 3000)},
            {'name': f'{emoji} От 3000 до 4000', 'chance': 0.005, 'field': 'currency', 'value': (3000, 4000)},
            {'name': f'{emoji} От 4000 до 5000', 'chance': 0.001, 'field': 'currency', 'value': (4000, 5000)},
            {'name': '⭐️ Gold на 1-3 дня', 'chance': 7, 'field': 'gold', 'value': (1, 3)},
            {'name': '⭐️ Gold на 3-7 дней', 'chance': 4.5, 'field': 'gold', 'value': (3, 7)},
            {'name': '⭐️ Gold на 7-14 дней', 'chance': 2.5, 'field': 'gold', 'value': (7, 14)},
            {'name': '⭐️ Gold на 14-30 дней', 'chance': 1, 'field': 'gold', 'value': (14, 30)},
            {'name': '⭐️ Gold на 30-60 дней', 'chance': 0.35, 'field': 'gold', 'value': (30, 60)},
            {'name': '⭐️ Gold на 60-90 дней', 'chance': 0.1, 'field': 'gold', 'value': (60, 90)},
            {'name': '⭐️ Gold на 90-180 дней', 'chance': 0.025, 'field': 'gold', 'value': (90, 180)},
            {'name': '💎 Diamond на 1-3 дня', 'chance': 4, 'field': 'diamond', 'value': (1, 3)},
            {'name': '💎 Diamond на 3-7 дней', 'chance': 2.25, 'field': 'diamond', 'value': (3, 7)},
            {'name': '💎 Diamond на 7-14 дней', 'chance': 1.25, 'field': 'diamond', 'value': (7, 14)},
            {'name': '💎 Diamond на 14-30 дней', 'chance': 0.5, 'field': 'diamond', 'value': (14, 30)},
            {'name': '💎 Diamond на 30-60 дней', 'chance': 0.175, 'field': 'diamond', 'value': (30, 60)},
            {'name': '💎 Diamond на 60-90 дней', 'chance': 0.04, 'field': 'diamond', 'value': (60, 90)},
            {'name': '💎 Diamond на 90-180 дней', 'chance': 0.005, 'field': 'diamond', 'value': (90, 180)},
            {'name': '🔑 От 1 до 3', 'chance': 1.5, 'field': 'keys', 'value': (1, 3)},
            {'name': '🔑 От 3 до 5', 'chance': 0.75, 'field': 'keys', 'value': (3, 5)},
            {'name': '🔑 От 5 до 10', 'chance': 0.4, 'field': 'keys', 'value': (5, 10)},
            {'name': '🔑 От 10 до 30', 'chance': 0.035, 'field': 'keys', 'value': (10, 30)},
            {'name': '🔑 От 30 до 60', 'chance': 0.01, 'field': 'keys', 'value': (30, 60)},
            {'name': '🔑 От 60 до 100', 'chance': 0.0035, 'field': 'keys', 'value': (60, 100)}
        ]

    def format_rewards_list(self, options):
        formatted_list = ""
        for option in options:
            formatted_list += f"**{option['name']}** — ``{option['chance']}%``\n"
        return formatted_list

    @commands.slash_command(name="mystery-box", description="Загадочный ящик с наградами")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def mystery_box(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @mystery_box.sub_command(name='open', description='Открыть загадочный ящик')
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def open_box(self, inter: disnake.ApplicationCommandInteraction):
        check_value(inter)

        if collusers.find_one({'id': inter.author.id, 'guild_id': inter.author.guild.id})['keys'] <= 0:
            await inter.send('У Вас нет ключей.', ephemeral=True)
            return
        else:
            collusers.update_one(
                {'id': inter.author.id, 'guild_id': inter.author.guild.id},
                {'$inc': {'keys': -1, 'opened_cases': 1}},
                upsert=True
            )
            collservers.update_one(
                {"_id": inter.guild.id},
                {"$inc": {"opened_cases": 1}},
                upsert=True
            )

        roulette_options = self.get_roulette_options()

        # Создаём взвешенный список элементов
        scale_factor = 100  # Масштабируем шансы
        weighted_items = []
        for option in roulette_options:
            scaled_chance = int(option['chance'] * scale_factor)
            if scaled_chance > 0:
                weighted_items.extend([option] * scaled_chance)

        # Если шансы всех элементов равны 0, возвращаем None
        if not weighted_items:
            return None

        # Выбираем случайный элемент
        selected_option = random.choice(weighted_items)

        # Генерация значения в зависимости от типа поля
        if isinstance(selected_option['value'], tuple):
            if selected_option['field'] == 'keys':
                prize_value = random.randint(*selected_option['value'])
            else:
                prize_value = round(random.uniform(*selected_option['value']), 2)
                if selected_option['field'] in ['gold', 'diamond']:
                    prize_value = int(prize_value * 86400)  # Преобразуем дни в секунды
        else:
            prize_value = selected_option['value']

        # Формируем информацию о выигрыше
        prize = {
            "name": selected_option['name'],
            "field": selected_option['field'],
            "value": prize_value
        }

        embed_loading = disnake.Embed(title="Открываем Mystery Box...", color=0x00ff00, timestamp=datetime.now())
        embed_loading.set_image(url='https://media.tenor.com/6BWKxLc307kAAAAj/gift-box.gif')
        await inter.send(embed=embed_loading, ephemeral=True)

        await asyncio.sleep(4.5)  # Задержка в 4.5 секунды

        if prize['field'] == 'currency':
            collusers.find_one_and_update(
                {'id': inter.author.id, 'guild_id': inter.author.guild.id},
                {'$inc': {'balance': prize['value']}}
            )
            prize_text = f"{prize['value']}{emoji}"
        elif prize['field'] == 'diamond':
            role_id = 1044314368717897868
            await process_role(inter, self.bot, 0, prize['value'], role_id, ephemeral=True)
            days, hours, minutes = seconds_to_dhm(prize['value'])
            formatted_time = f"`{days} дней и {hours} часов`"
            role = inter.guild.get_role(role_id)
            prize_text = f"Роль {role.mention} на {formatted_time}"
        elif prize['field'] == 'gold':
            role_id = 1303396950481174611
            await process_role(inter, self.bot, 0, prize['value'], role_id, ephemeral=True)
            days, hours, minutes = seconds_to_dhm(prize['value'])
            formatted_time = f"`{days} дней и {hours} часов`"
            role = inter.guild.get_role(role_id)
            prize_text = f"Роль {role.mention} на {formatted_time}"
        elif prize['field'] == 'mute':
            try:
                dur = timedelta(minutes=prize['value'])
                await inter.author.timeout(duration=dur)
                prize_text = f"Мут на ``{prize['value']} минут`` 🔇"
            except Exception as e:
                print(f"Ошибка при установке таймаута: {e}")
                prize_text = "Ошибка с мутом. Попробуйте снова."
        elif prize['field'] == 'keys':
            collusers.find_one_and_update(
                {'id': inter.author.id, 'guild_id': inter.author.guild.id},
                {'$inc': {'keys': prize['value']}}
            )
            prize_text = f"{prize['value']} ключей 🔑"

        elif prize['field'] == 'none':
            prize_text = "К сожалению, ящик оказался пустым 😔"

        else:
            # Если тип награды неизвестен, устанавливаем безопасное значение
            prize_text = "Неизвестная награда. Пожалуйста, свяжитесь с администратором"

        # Формирование сообщения с результатом
        embed = disnake.Embed(title="Вы успешно открыли Mystery Box!", color=0xffff00, timestamp=datetime.now())
        embed.set_thumbnail(url='https://i.pinimg.com/originals/f2/43/fc/f243fcb6032c81ca9870d098ee7587ba.gif')
        embed.add_field(name="Ваша награда:", value=f'{prize_text}.', inline=False)
        keys = collusers.find_one({'id': inter.author.id, 'guild_id': inter.author.guild.id})['keys']
        embed.set_footer(text=f'У вас осталось: {keys}🔑', icon_url=inter.guild.icon.url)
        await inter.edit_original_message(embed=embed)

    @mystery_box.sub_command(name='list', description='Список доступных наград')
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def list_rewards(self, inter: disnake.ApplicationCommandInteraction):
        # Получаем начальный список наград
        roulette_options = self.get_roulette_options()
        formatted_list = self.format_rewards_list(roulette_options)

        # Создаём эмбед
        embed = disnake.Embed(
            title="Список наград и их шансы",
            description=formatted_list,
            color=0xffff00,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url='https://i.pinimg.com/originals/f2/43/fc/f243fcb6032c81ca9870d098ee7587ba.gif')
        embed.set_footer(text="Удачи!", icon_url=inter.guild.icon.url)

        # Добавляем кнопки через RewardsView
        view = RewardsView(self, inter)
        await inter.send(embed=embed, view=view, ephemeral=True)


def setup(bot):
    bot.add_cog(RouletteCog(bot))
    print('Roulette Cog is Ready!')
