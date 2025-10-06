import time
from asyncio import tasks
import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from pymongo import MongoClient
from main import rules, get_rule_info, check_roles, create_error_embed
from main import cluster
from ai.process_role import process_role
import random
import string
from .warn import convert_to_seconds, format_duration
from disnake.ui import Button, View

collpromos = cluster.server.promos
collusers = cluster.server.users
collservers = cluster.server.servers

emoji = "<a:rumbick:1271085088142262303>"

def convert_seconds_to_time_string(seconds):
    if seconds >= 86400:  # дни
        value = seconds // 86400
        return f"{value}d"
    elif seconds >= 3600:  # часы
        value = seconds // 3600
        return f"{value}h"
    elif seconds >= 60:  # минуты
        value = seconds // 60
        return f"{value}m"
    else:  # секунды
        return f"{seconds}s"


def generate_random_code():
    """Генерирует случайный промокод в формате SD-XXXXX-XXXXX-XXXXX."""
    parts = [
        'SD',  # Первые два символа
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)),
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)),
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)),
    ]
    return '-'.join(parts)

class Promo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='promocode', description='Взаимодействие с промокодами', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def promo(self, inter):
        pass

    @promo.sub_command(name='create-role', description='Создать промокод на роль')
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def create_role(
            self, inter, роль: disnake.Role, количество_активаций: int = 1, длительность: str = None,
            длительность_роли: str = None, код: str = None
    ):
        # Если количество_активаций равно 0, устанавливаем его в 999999 (бесконечно)
        if количество_активаций == 0:
            количество_активаций = 'Бесконечно'

        код = код or generate_random_code()  # Генерация промокода, если он не задан
        expires_at = None
        expires_role = None

        if длительность:
            try:
                expires_at = int(time.time()) + convert_to_seconds(длительность)
            except ValueError as e:
                await inter.response.send_message(f"Ошибка в формате времени: {e}", ephemeral=True)
                return

        if длительность_роли:
            try:
                expires_role = convert_to_seconds(длительность_роли)
                formatted_duration = format_duration(длительность_роли)  # Преобразование длительности в читаемый формат
            except ValueError as e:
                await inter.response.send_message(f"Ошибка в формате времени: {e}", ephemeral=True)
                return
        else:
            expires_role = None
            formatted_duration = "бесконечная"

        # Получаем текущий ID и увеличиваем его
        promo_data = collpromos.find_one_and_update(
            {'_id': inter.guild.id},
            {'$inc': {'counter': 1}},
            upsert=True,
            return_document=True
        )
        promo_id = promo_data.get('counter', 1)

        # Создаем промокод
        collpromos.update_one(
            {'_id': inter.guild.id},
            {'$set': {
                f'promos.{код}': {
                    'id': promo_id,
                    'role_id': роль.id,
                    'type': 'role',
                    'activations': количество_активаций,
                    'expires_at': expires_at,
                    'create_id': inter.author.id,
                    'expires_role': expires_role,
                    'users': []
                }
            }},
            upsert=True
        )

        expiry_message = (
            f"срок его действия истекает <t:{expires_at}:R>" if expires_at else "срок его действия **бесконечный**"
        )
        embed = disnake.Embed(title="Промокод успешно создан!", color=0x0000ff)
        embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
        embed.add_field(
            name="Информация о промокоде",
            value=(
                f"Промокод на роль ``{роль}`` с длительностью роли **{formatted_duration}** успешно создан: "
                f"```{код}``` Его количество активаций: ``{количество_активаций}``\n А {expiry_message}"
            ),
            inline=False
        )
        embed.set_footer(text=f'Уникальный номер промокода: #{promo_id}', icon_url=inter.guild.icon.url)
        embed.timestamp = datetime.now()
        await inter.response.send_message(embed=embed, ephemeral=True)

    @promo.sub_command(name='create-rumbicks', description='Создать промокод на румбики')
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def create_rumbicks(
            self, inter, количество_румбиков: int, количество_активаций: int = 1, длительность: str = None,
            код: str = None
    ):
        # Если количество_активаций равно 0, устанавливаем его в 999999 (бесконечно)
        if количество_активаций == 0:
            количество_активаций = 'Бесконечно'

        код = код or generate_random_code()  # Генерация промокода, если он не задан
        expires_at = None
        expires_role = None

        if длительность:
            try:
                expires_at = int(time.time()) + convert_to_seconds(длительность)
            except ValueError as e:
                error_message = f"Ошибка в формате времени: {e}"
                embed = create_error_embed(error_message)
                await inter.response.send_message(embed=embed, ephemeral=True)
                return

        # Получаем текущий ID и увеличиваем его
        promo_data = collpromos.find_one_and_update(
            {'_id': inter.guild.id},
            {'$inc': {'counter': 1}},
            upsert=True,
            return_document=True
        )
        promo_id = promo_data.get('counter', 1)

        # Создаем промокод
        collpromos.update_one(
            {'_id': inter.guild.id},
            {'$set': {
                f'promos.{код}': {
                    'id': promo_id,
                    'rumbicks': количество_румбиков,
                    'type': 'rumbicks',
                    'activations': количество_активаций,
                    'expires_at': expires_at,
                    'create_id': inter.author.id,
                    'users': []
                }
            }},
            upsert=True
        )

        expiry_message = (
            f"срок его действия истекает <t:{expires_at}:R>" if expires_at else " срок его действия **бесконечный**"
        )
        embed = disnake.Embed(title="Промокод успешно создан!", color=0x0000ff)
        embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
        embed.add_field(name='',
                        value=f"Промокод на ``{количество_румбиков}``{emoji} успешно создан: ```{код}``` Его количество активаций: ``{количество_активаций}``\n А {expiry_message}",
                        inline=False)
        embed.set_footer(text=f'Уникальный номер промокода: #{promo_id}', icon_url=inter.guild.icon.url)
        embed.timestamp = datetime.now()
        await inter.response.send_message(embed=embed, ephemeral=True)

    @promo.sub_command(name='create-keys', description='Создать промокод на ключи')
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def create_keys(
            self, inter, количество_ключей: int, количество_активаций: int = 1, длительность: str = None,
            код: str = None
    ):
        # Если количество_активаций равно 0, устанавливаем его в 999999 (бесконечно)
        if количество_активаций == 0:
            количество_активаций = 'Бесконечно'

        код = код or generate_random_code()  # Генерация промокода, если он не задан
        expires_at = None
        expires_role = None

        if длительность:
            try:
                expires_at = int(time.time()) + convert_to_seconds(длительность)
            except ValueError as e:
                error_message = f"Ошибка в формате времени: {e}"
                embed = create_error_embed(error_message)
                await inter.response.send_message(embed=embed, ephemeral=True)
                return

        # Получаем текущий ID и увеличиваем его
        promo_data = collpromos.find_one_and_update(
            {'_id': inter.guild.id},
            {'$inc': {'counter': 1}},
            upsert=True,
            return_document=True
        )
        promo_id = promo_data.get('counter', 1)

        # Создаем промокод
        collpromos.update_one(
            {'_id': inter.guild.id},
            {'$set': {
                f'promos.{код}': {
                    'id': promo_id,
                    'keys': количество_ключей,
                    'type': 'keys',
                    'activations': количество_активаций,
                    'expires_at': expires_at,
                    'create_id': inter.author.id,
                    'users': []
                }
            }},
            upsert=True
        )

        expiry_message = (
            f"срок его действия истекает <t:{expires_at}:R>" if expires_at else " срок его действия **бесконечный**"
        )
        embed = disnake.Embed(title="Промокод успешно создан!", color=0x0000ff)
        embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
        embed.add_field(name='',
                        value=f"Промокод на ``{количество_ключей}``🔑 успешно создан: ```{код}``` Его количество активаций: ``{количество_активаций}``\n А {expiry_message}",
                        inline=False)
        embed.set_footer(text=f'Уникальный номер промокода: #{promo_id}', icon_url=inter.guild.icon.url)
        embed.timestamp = datetime.now()
        await inter.response.send_message(embed=embed, ephemeral=True)
        return код

    @promo.sub_command(name='use', description='Использовать промокод')
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def use(self, inter, код: str):
        await inter.response.defer(ephemeral=True)
        promo_data = collpromos.find_one(
            {'_id': inter.guild.id, f'promos.{код}': {'$exists': True}}
        )

        if not promo_data:
            error_message = "Такого промокода не существует, либо истёк его срок действия."
            embed = create_error_embed(error_message)
            await inter.edit_original_response(embed=embed)
            return

        promo = promo_data['promos'][код]

        # Проверяем срок действия
        if promo.get('expires_at') and promo['expires_at'] < int(time.time()):
            collpromos.update_one(
                {'_id': inter.guild.id},
                {'$unset': {f'promos.{код}': 1}}
            )
            error_message = "Срок действия промокода истёк."
            embed = create_error_embed(error_message)
            await inter.edit_original_response(embed=embed)
            return

        # Проверяем, активирован ли промокод пользователем
        if inter.author.id in [user['id'] for user in promo['users']]:
            error_message = "Вы уже активировали этот промокод."
            embed = create_error_embed(error_message)
            await inter.edit_original_response(embed=embed)
            return

        # Обработка по типу промокода
        if promo['type'] == 'rumbicks':
            collusers.update_one(
                {'id': inter.author.id},
                {'$inc': {'balance': promo['rumbicks']}}
            )
            embed = disnake.Embed(title="Вы успешно активировали промокод!", color=0x0000ff, timestamp=datetime.now())
            embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
            embed.add_field(name='Награда:', value=f'Вы получили ``{promo["rumbicks"]}``{emoji}.')
            embed.set_footer(text=f'Промокод', icon_url=inter.guild.icon.url)

        elif promo['type'] == 'keys':
            collusers.update_one(
                {'id': inter.author.id},
                {'$inc': {'keys': promo['keys']}}
            )
            embed = disnake.Embed(title="Вы успешно активировали промокод!", color=0x0000ff, timestamp=datetime.now())
            embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
            embed.add_field(name='Награда:', value=f'Вы получили ``{promo["keys"]}``🔑.')
            embed.set_footer(text=f'Промокод', icon_url=inter.guild.icon.url)

        elif promo['type'] == 'role':
            role = inter.guild.get_role(promo['role_id'])
            role_id = collpromos.find_one({'_id': inter.guild.id})['promos'][код]['role_id']
            role = inter.guild.get_role(role_id)
            on_time = collpromos.find_one({'_id': inter.guild.id})['promos'][код]['expires_role']

            if on_time is None:
                formatted_duration = "бесконечная"
            else:
                try:
                    # Преобразуем секунды в строку с единицей измерения
                    time_str = convert_seconds_to_time_string(on_time)
                    # Форматируем строку в человеко-читаемый формат
                    formatted_duration = format_duration(time_str)
                except ValueError:
                    formatted_duration = "Некорректная длительность"

            await process_role(inter, self.bot, 0, on_time, role_id, ephemeral=True)

            user_data = collusers.find_one({'id': inter.author.id}, {'role_ids': 1})
            role_info = next(
                (r for r in user_data.get('role_ids', []) if r['role_ids'] == role_id),
                None
            )

            if role_info:
                expires_at = (
                    "бесконечно" if not role_info.get('expires_at')
                    else f"<t:{role_info['expires_at']}:R>"
                )
            else:
                expires_at = "**бесконечно**"


            embed = disnake.Embed(title="Вы успешно активировали промокод!", color=0x0000ff, timestamp=datetime.now())
            embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
            embed.add_field(name='Награда:', value=f'Вам выдана роль ``{role.name}`` на ``{formatted_duration}``.\n Роль истекает через: {expires_at}.')
            embed.set_footer(text=f'Промокод', icon_url=inter.guild.icon.url)
        else:
            error_message = "Неизвестный тип промокода."
            embed = create_error_embed(error_message)

        collusers.update_one(
            {'id': inter.author.id, 'guild_id': inter.author.guild.id},
            {'$inc': {'promocodes': 1}},
            upsert=True
        )
        collservers.update_one({"_id": inter.guild.id}, {"$inc": {"activation_promos": 1}},
                               upsert=True)

        # Проверяем, ограничено ли количество активаций
        update_query = {
            '$push': {f'promos.{код}.users': {'id': inter.author.id}}
        }

        # Если активации не бесконечны, уменьшаем их количество
        if promo['activations'] != 'Бесконечно':
            update_query['$inc'] = {f'promos.{код}.activations': -1}

        # Обновляем данные промокода
        collpromos.update_one(
            {'_id': inter.guild.id},
            update_query
        )

        # Удаляем промокод, если активации закончились
        if promo['activations'] != 'Бесконечно':
            # Преобразуем активации в число, если это возможно
            activations = int(promo['activations'])
            if activations - 1 <= 0:
                collpromos.update_one(
                    {'_id': inter.guild.id},
                    {'$unset': {f'promos.{код}': 1}}
                )

        await inter.edit_original_response(embed=embed)

    @promo.sub_command(name="list", description="Список промокодов")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def list_promos(self, inter):
        # Получаем все промокоды
        result = collpromos.find_one({'_id': inter.guild.id})
        if not result:
            await inter.response.send_message("Нет активных промокодов.")
            return

        promos = result.get('promos', {})
        promo_list = []
        current_time = int(time.time())  # Текущее время в секундах

        # Перевод типов на русский и сбор информации о промокодах
        for код, данные in promos.items():
            promo_id = данные.get('id', '—')
            creator_id = данные.get('create_id', '—')
            creator = inter.guild.get_member(creator_id)
            creator_mention = creator.mention if creator else f"Неизвестный пользователь (ID: {creator_id})"
            promo_type = данные.get('type', 'Неизвестно').strip()
            activations = данные.get('activations', 0)
            expires_at = данные.get('expires_at')
            expires_text = f"<t:{int(expires_at)}:R>" if expires_at else "Бессрочно"

            # Проверка на истечение срока действия
            if expires_at and current_time > expires_at:
                # Удаление просроченного промокода из базы
                collpromos.update_one(
                    {'_id': inter.guild.id},
                    {'$unset': {f'promos.{код}': 1}}
                )
                continue  # Переходим к следующему промокоду

            # Перевод типа на русский
            if promo_type == 'rumbicks':
                promo_type_ru = "Румбики"
                capacity = f"``{данные.get('rumbicks', 0)}``{emoji}"
            elif promo_type == 'keys':
                promo_type_ru = "Ключи"
                capacity = f"``{данные.get('keys', 0)}``🔑"
            elif promo_type == 'role':
                promo_type_ru = "Роль"
                role_id = данные.get('role_id')
                role = inter.guild.get_role(role_id)
                role_name = role.name if role else 'Неизвестная роль'
                duration_seconds = данные.get('expires_role', 0)

                if duration_seconds:
                    time_str = convert_seconds_to_time_string(duration_seconds)
                    formatted_duration = format_duration(time_str)
                    capacity = f"Роль: ``{role_name}`` на **{formatted_duration}**"
                else:
                    capacity = f"Роль: ``{role_name}`` на **Бессрочно**"
            else:
                promo_type_ru = "Неизвестный тип"
                capacity = "Неизвестно"

            # Получение списка пользователей, которые активировали промокод
            users = данные.get('users', [])
            activated_by = (
                ", ".join(
                    inter.guild.get_member(user['id']).mention if inter.guild.get_member(
                        user['id']) else f"Неизвестный (ID: {user['id']})"
                    for user in users
                )
                if users
                else "Никто"
            )

            promo_list.append({
                'код': код,
                'promo_id': promo_id,
                'promo_type': promo_type_ru,
                'activations': activations,
                'creator_mention': creator_mention,
                'expires_text': expires_text,
                'capacity': capacity,
                'activated_by': activated_by
            })

        # Если нет активных промокодов
        if not promo_list:
            embed = disnake.Embed(title="Список промокодов", color=0x0000ff, timestamp=datetime.now())
            embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url)
            embed.add_field(name='Список промокодов пуст:', value='На данный момент нет активных промокодов.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # Формируем вывод в одном эмбеде
        embed = disnake.Embed(title="Список промокодов", color=0x0000ff, timestamp=datetime.now())
        embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url)
        for promo in promo_list[:5]:  # Выводим первые 5 промокодов
            embed.add_field(
                name=f"ID: {promo['promo_id']}\n",
                value=f"**Промокод:** ``{promo['код']}``\n"
                      f"**Тип:** {promo['promo_type']}\n"
                      f"**Вместимость:** {promo['capacity']}\n"
                      f"**Создатель:** {promo['creator_mention']}\n"
                      f"**Активирован:** {promo['activated_by']}\n"
                      f"**Окончание действия:** {promo['expires_text']}\n"
                      f"**Оставшиеся активации:** {promo['activations']}",
                inline=False
            )
            embed.add_field(name="", value="", inline=False)

        # Если промокодов больше 5, добавляем кнопки для переключения страниц
        if len(promo_list) > 5:
            current_page = 1
            total_pages = (len(promo_list) // 5) + (1 if len(promo_list) % 5 != 0 else 0)

            view = View()

            # Кнопки для переключения страниц
            async def update_page(interaction: disnake.MessageInteraction):
                nonlocal current_page

                if interaction.component.custom_id == "next_page" and current_page < total_pages:
                    current_page += 1
                elif interaction.component.custom_id == "prev_page" and current_page > 1:
                    current_page -= 1

                embed = disnake.Embed(title="Список промокодов", color=0x0000ff, timestamp=datetime.now())
                embed.set_thumbnail(url='https://media4.giphy.com/media/V1ItMnx6o84XYrlPmt/giphy.gif')
                embed.set_footer(text=f"Страница {current_page}/{total_pages}", icon_url=interaction.guild.icon.url)
                start_index = (current_page - 1) * 5
                end_index = start_index + 5
                for promo in promo_list[start_index:end_index]:
                    embed.add_field(
                        name=f"ID: {promo['promo_id']}",
                        value=f"Промокод: ``{promo['код']}``\n"
                              f"**Тип:** {promo['promo_type']}\n"
                              f"**Вместимость:** {promo['capacity']}\n"
                              f"**Создатель:** {promo['creator_mention']}\n"
                              f"**Активирован:** {promo['activated_by']}\n"
                              f"**Окончание действия:** {promo['expires_text']}\n"
                              f"**Оставшиеся активации:** {promo['activations']}",
                        inline=False
                    )
                    embed.add_field(name="", value="", inline=False)

                await interaction.response.edit_message(embed=embed, view=view)

            next_button = Button(label="Вперед →", custom_id="next_page")
            prev_button = Button(label="← Назад", custom_id="prev_page")

            next_button.callback = update_page
            prev_button.callback = update_page

            view.add_item(prev_button)
            view.add_item(next_button)

            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await inter.response.send_message(embed=embed, ephemeral=True)

    @promo.sub_command(name="delete", description="Удалить промокод по ID или коду")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def delete_promocode(self, inter, promo_id: str = None, promo_code: str = None):
        if not promo_id and not promo_code:
            error_message = "Укажите ID или код промокода для удаления."
            embed = create_error_embed(error_message)
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        result = collpromos.find_one({'_id': inter.guild.id})
        if not result:
            error_message = "Нет активных промокодов."
            embed = create_error_embed(error_message)
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        promos = result.get('promos', {})
        promo_to_delete = None

        # Удаление по ID
        if promo_id:
            for code, data in promos.items():
                if str(data.get('id')) == promo_id:  # Преобразуем ID в строку, если это необходимо
                    promo_to_delete = code
                    break

        # Удаление по коду
        if promo_code and promo_to_delete is None:
            if promo_code in promos:
                promo_to_delete = promo_code

        if promo_to_delete:
            # Удаление промокода
            collpromos.update_one(
                {'_id': inter.guild.id},
                {'$unset': {f'promos.{promo_to_delete}': 1}}
            )
            embed = disnake.Embed(title="Промокод успешно удалён!", color=0x0000ff, timestamp=datetime.now())
            embed.set_thumbnail(url='https://www.emojiall.com/images/240/telegram/2705.gif')
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url)
            embed.add_field(name="", value=f"Промокод с кодом `{promo_to_delete}` был удален.", inline=False)
            await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            error_message = "Промокод с таким ID или кодом не найден."
            embed = create_error_embed(error_message)
            await inter.response.send_message(embed=embed, ephemeral=True)
def setup(bot):
    bot.add_cog(Promo(bot))
    print("PromoCog is ready")
