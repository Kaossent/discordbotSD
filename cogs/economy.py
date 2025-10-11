import disnake
from pymongo import MongoClient, errors, collection
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import os
import asyncio
import time
import random
import math
import re
from main import cluster
from main import rules, get_rule_info, check_roles
from ai.promo import create_rumbicks
from ai.process_role import process_role

collusers = cluster.server.users
collservers = cluster.server.servers

cooldowns = {}
voice_timestamps = {}
mute_timestamps = {}
total_time = {}
emoji = "<a:rumbick:1271085088142262303>"

def format_duration(value):
    if value == 1:
        return "1 румбик"
    elif 2 <= value <= 4:
        return f"`{value}` румбика"
    else:
        return f"`{value}` румбиков"
def format_rumbick(value):
    emoji = "<a:rumbick:1271085088142262303>"
    return f"{value}{emoji}"

def create_error_embed(message: str) -> disnake.Embed:
    embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
    embed.add_field(name='Произошла ошибка', value=f'Ошибка: {message}')
    embed.set_thumbnail(url="https://media2.giphy.com/media/AkGPEj9G5tfKO3QW0r/200.gif")
    embed.set_footer(text='Ошибка')
    return embed


def format_time(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    time_components = []
    if days > 0:
        time_components.append(f'{int(days)} д')
    if hours > 0:
        time_components.append(f'{int(hours)} ч')
    if minutes > 0:
        time_components.append(f'{int(minutes)} мин')
    if seconds > 0 or not time_components:
        time_components.append(f'{int(seconds)} сек')

    return ', '.join(time_components)

def format_duration(self, time_str):
    """Форматирование длительности в строку."""
    try:
        value = int(time_str[:-1])
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")

    unit = time_str[-1]
    if unit == 'д' or unit == 'd':
        return f"{value} дней"
    elif unit == 'ч' or unit == 'h':
        return f"{value} часов"
    elif unit == 'м' or unit == 'm':
        return f"{value} минут"
    elif unit == 'с' or unit == 's':
        return f"{value} секунд"
    else:
        raise ValueError(f"Invalid time unit: {time_str[-1]}")

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_booster.start()
        self.excluded_channels = {1070322967634006057, 532628352927006737, 944562833901899827, 1270673733178101801}
        self.excluded_roles = {
            518505773022838797,  # Администратор
            580790278697254913,  # Ст. Модератор
            702593498901381184,  # Модератор
            1044314368717897868,  # Diamond
            757930494301044737,  # Server Booster
        }
        self.options = [
            disnake.SelectOption(label=f"💎 Diamond", description="Даёт эксклюзивные возможности", value="1"),
            disnake.SelectOption(label=f"⭐️ Gold", description="Даёт эксклюзивные возможности", value="2"),
            disnake.SelectOption(label="🙋‍♂️ Возможность сменить никнейм",
                                 description="Вы получаете возможность один раз сменить никнейм",
                                 value="3"),
            disnake.SelectOption(label="🚀 Глобальный бустер румбиков x2",
                                 description="Увеличивает зароботок Румбиков вдвое", value="4"),
            disnake.SelectOption(label=f"🔑 Мистический ключ", description="Даёт возможность открыть загадочный ящик", value="5")
        ]
        self.options_2 = [
                    disnake.ui.Button(label="🚀 Активировать на 1 день", style=disnake.ButtonStyle.secondary,
                                      custom_id='1_day'),
                    disnake.ui.Button(label="🚀 Активировать на 3 дня", style=disnake.ButtonStyle.primary, custom_id='3_days'),
                    disnake.ui.Button(label="🚀 Активировать на 7 дней", style=disnake.ButtonStyle.success, custom_id='7_days')
                ]
        self.role_award = {
            5: 519925709603471381,
            10: 519925711113289748,
            15: 521760576423329794,
            20: 519925714309349377,
            25: 519925715458719799,
            30: 519925716331134976,
            35: 862727316479148065,
            40: 896481674114785300,
            45: 896481824199573574,
            50: 896481809972461690,
            55: 896482036079005737,
            60: 896482158636585040,
            65: 519925718767894531
        }

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):

        if message.author.bot:
            if message.channel.id == 1070322967634006057 or message.channel.id == 1235294532409495555:
                if message.embeds:
                    message_embed = str(message.embeds[0].description)
                    author_interaction = None

                    if 'Bump done!' in message_embed or 'Время фиксации апа:' in message_embed or 'Ви успішно лайкнули сервер.' in message_embed or 'Вы успешно лайкнули сервер.' in message_embed or 'You successfully liked the server.' in message_embed or 'Успешный Up!' in message_embed:
                        author_interaction = message.interaction.author

                    elif 'Запущенная команда: `/up`' in message_embed:
                        author_interaction = message.author.guild.get_member_named(message.embeds[0].author.name)

                    elif 'Server bumped by' in message_embed:
                        mention_pattern = r"<@!?(\d+)>"
                        mentions = re.findall(mention_pattern, message_embed)
                        if mentions:
                            author_interaction = await message.author.guild.fetch_member(mentions[0])

                    if author_interaction:
                        multiplier = collservers.find_one({'_id': message.author.guild.id})['multiplier']
                        money_to_give = random.uniform(5, 10)
                        money_to_give1 = money_to_give * multiplier
                        money_to_give2 = round(money_to_give1, 2)

                        collusers.find_one_and_update({'id': author_interaction.id, 'guild_id': message.guild.id}, {'$inc': {'balance': money_to_give2, 'bumps': 1}}, upsert=True)
                        collservers.update_one({"_id": message.guild.id}, {"$inc": {"bumps": 1, "total_rumbicks": money_to_give2}}, upsert=True)
                        embed = disnake.Embed(title='Успешный бамп!', colour=0xffbb00, timestamp=datetime.now())
                        embed.set_thumbnail(url='https://cdn.pixabay.com/animation/2023/06/13/15/13/15-13-13-522_512.gif')
                        embed.add_field(name=f'', value=f'{author_interaction.mention}, Спасибо что помогаете нашему серверу становиться лучше!\n'
                                              f'В знак благодарности Вы получаете `{money_to_give2}`{emoji}!')
                        base_chance = 5  # Базовый шанс %
                        adjusted_chance = base_chance * multiplier  # Увеличенный шанс
                        if random.randint(1, 100) <= adjusted_chance:  # Проверяем вероятность
                            embed.add_field(name='', value='Вам так же выпал `1🔑` от MysteryBox!', inline=False)
                            collusers.find_one_and_update(
                                {'id': author_interaction.id, 'guild_id': message.guild.id}, {'$inc': {'keys': 1}}, upsert=True)
                        embed.set_author(name=f'{author_interaction.display_name}',
                                         icon_url=author_interaction.avatar.url)
                        embed.set_footer(text=message.author.guild.name, icon_url=message.author.guild.icon.url)
                        channel = self.bot.get_channel(1070322967634006057)
                        await channel.send(embed=embed)
        else:
            # Update message count
            if message.channel.id not in self.excluded_channels:
                collusers.find_one_and_update(
                    {'id': message.author.id, 'guild_id': message.guild.id},
                    {'$inc': {'message_count': 1}},
                    upsert=True
                )
                collservers.update_one(
                    {"_id": message.guild.id},
                    {"$inc": {"messages": 1}},
                    upsert=True
                )

            now = datetime.now()
            user_id = message.author.id
            if len(message.content) > 3:

                if user_id in cooldowns:
                    last_used = cooldowns[user_id]
                    if now - last_used < timedelta(seconds=15):
                        time_left = timedelta(seconds=15) - (now - last_used)
                        return

                multiplier = collservers.find_one({'_id': message.author.guild.id})['multiplier']
                money_to_give = random.uniform(0.5, 1)
                money_to_give1 = money_to_give * multiplier
                money_to_give2 = round(money_to_give1, 2)
                collusers.find_one_and_update({'id': message.author.id}, {'$inc': {'balance': money_to_give2}})
                collservers.update_one(
                    {"_id": message.author.guild.id},
                    {"$inc": {"chat_rumbicks": money_to_give2, "total_rumbicks": money_to_give2}},
                    upsert=True
                )
                cooldowns[user_id] = now

    @commands.slash_command(name='balance', description='Показывает баланс участника',
                            aliases=['баланс', 'счет', 'остаток', 'credit', 'amount', 'sum'], contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def balance(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member = None):
        await inter.response.defer(ephemeral=True)

        if участник is None:
            участник = inter.author

        user_data = collusers.find_one({"id": участник.id})
        if user_data:
            balance = round(user_data.get('balance', 0), 2)
            balance_formatted = format_rumbick(balance)

            embed = disnake.Embed(title=f'', color=0x00ff00)
            embed.set_author(name=f"{участник.display_name}", icon_url=участник.display_avatar.url)
            embed.set_thumbnail(
                url="https://64.media.tumblr.com/31756ec986051798604d9697fa0e7d99/tumblr_pxuqjiK9Hn1sftgzko1_400.gif")
            embed.add_field(name='Баланс:', value=f'{balance_formatted}', inline=False)
            embed.set_footer(text=f'Баланс', icon_url=inter.guild.icon.url)
            embed.timestamp = datetime.now()
            await inter.edit_original_response(embed=embed)
        else:
            await inter.edit_original_response(content="Не удалось найти данные пользователя.")

    @commands.slash_command(name='pay', description='Перевод румбиков другому участнику',
                            aliases=['перевод', 'give', 'transfer'], contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def pay(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member, количество: int):
        # Проверка на минимальную сумму перевода
        if количество < 10:
            error_message = f"Вы не можете перевести меньше ``10`` {emoji}"
            embed = create_error_embed(error_message)
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # Проверка на попытку перевести самому себе
        if участник.id == inter.author.id:
            embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
            error_message = "Вы не можете перевести румбики самому себе."
            embed = create_error_embed(error_message)
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        await inter.response.defer()

        # Определение исключительных ролей на комиссию
        role_gold = 1303396950481174611  # Gold

        balance = collusers.find_one({"id": inter.author.id})['balance']

        # Проверка на наличие роли-исключения у отправителя
        is_sender_excluded = any(role.id in self.excluded_roles for role in inter.author.roles)

        if balance >= количество:
            # Вычисление комиссии (если отправитель не исключен)
            if is_sender_excluded:
                amount_after_commission = количество
                commission_amount = 0
            elif role_gold in [role.id for role in inter.author.roles]:
                commission = 0.05  # 5% комиссии
                human_commision = 5
                amount_after_commission = количество * (1 - commission)
                commission_amount = количество - amount_after_commission
            else:
                commission = 0.1  # 10% комиссии
                human_commision = 10
                amount_after_commission = количество * (1 - commission)
                commission_amount = количество - amount_after_commission

            # Обновление баланса отправителя и получателя
            collusers.find_one_and_update({'id': inter.author.id}, {"$inc": {"balance": -количество}})
            collusers.find_one_and_update({'id': участник.id}, {"$inc": {"balance": amount_after_commission}})
            collusers.find_one_and_update({'id': участник.id}, {'$inc': {'number_of_deal': 1}})
            collusers.find_one_and_update({'id': inter.author.id}, {'$inc': {'number_of_deal': 1}})
            collservers.update_one({"_id": inter.guild.id}, {"$inc": {"deals": 1}}, upsert=True)
            collservers.update_one({"_id": inter.guild.id}, {"$inc": {"transfers": 1}}, upsert=True)

            formatted_amount = format_rumbick(round(количество, 2))
            formatted_amount_after_commission = format_rumbick(round(amount_after_commission, 2))
            formatted_commission_amount = format_rumbick(round(commission_amount, 2))

            embed = disnake.Embed(title=f'Сделка `{inter.author.display_name}` ⇾ `{участник.display_name}`',
                                  color=0x00ff00)
            embed.set_author(name=f"{участник.display_name}", icon_url=участник.display_avatar.url)
            embed.set_thumbnail(
                url="https://64.media.tumblr.com/31756ec986051798604d9697fa0e7d99/tumblr_pxuqjiK9Hn1sftgzko1_400.gif")
            embed.add_field(name='Отправитель', value=f'{inter.author.mention}', inline=True)
            embed.add_field(name='Получатель:', value=f'{участник.mention}', inline=True)
            embed.add_field(name='Сумма сделки:', value=f'{formatted_amount}', inline=True)

            if commission_amount > 0:
                embed.add_field(name='Комиссия:', value=f'{human_commision}% ({formatted_commission_amount})', inline=True)
                embed.add_field(name='Итоговая сумма:', value=f'{formatted_amount_after_commission}', inline=True)
            else:
                embed.add_field(name='Комиссия:', value=f'0%', inline=True)

            embed.set_footer(text=f'Получатель: {участник.name}', icon_url=участник.avatar.url)
            embed.timestamp = datetime.now()
            await inter.edit_original_response(embed=embed)

        else:
            unformatted = int(количество) - balance
            formatted = format_duration(unformatted)
            error_message = f"У Вас не хватает еще {formatted} для перевода."
            embed = create_error_embed(error_message)
            await inter.followup.send(embed=embed, ephemeral=True)

    @commands.slash_command(name="change", description="Изменяет указанное поле участника")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def change(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member,
                     поле: str = commands.Param(
                         choices=[
                             "balance",
                             "keys",
                             "reputation",
                             "message_count",
                             "time_in_voice",
                             "reaction_count",
                             "number_of_deal",
                             "number_of_roles",
                             "bumps",
                             "opened_cases",
                             "promocodes",
                         ]
                     ),
                     действие: str = commands.Param(choices=["добавить (+)", "отнять (-)", "установить (=)"]),
                     значение: str = None,
                     ):
        def format_duration(time_str):
            """Форматирование длительности в строку."""
            try:
                value = int(time_str[:-1])
            except ValueError:
                raise ValueError(f"Неверный формат времени: {time_str}")

            unit = time_str[-1]
            if unit in ['д', 'd']:
                return value * 86400  # дней в секунды
            elif unit in ['ч', 'h']:
                return value * 3600  # часов в секунды
            elif unit in ['м', 'm']:
                return value * 60  # минут в секунды
            elif unit in ['с', 's']:
                return value  # секунды
            else:
                raise ValueError(f"Неверная единица времени: {unit}")

        # Проверка существования пользователя в базе данных
        user_data = collusers.find_one({"id": участник.id})
        if not user_data:
            await inter.response.send_message(
                f"Участник {участник.mention} не найден в базе данных.", ephemeral=True
            )
            return

        # Проверка и преобразование значения
        if поле != "balance":
            if поле == "time_in_voice":
                try:
                    значение = format_duration(значение)
                except ValueError as e:
                    await inter.response.send_message(str(e), ephemeral=True)
                    return
            else:
                if not значение.isdigit():
                    await inter.response.send_message(
                        f"Для поля {поле} необходимо указать целое число.", ephemeral=True
                    )
                    return
                значение = int(значение)
        else:
            try:
                значение = float(значение)
            except ValueError:
                await inter.response.send_message(
                    "Для поля balance необходимо указать число.", ephemeral=True
                )
                return

        # Получение текущего значения указанного поля
        current_value = user_data.get(поле, 0.0)
        new_value = current_value

        # Изменение значения в зависимости от действия
        if действие == "добавить (+)":
            new_value += значение
            collusers.find_one_and_update({"id": участник.id}, {"$inc": {поле: значение}})
            action_text = f"**добавили** ``{значение}``"
        elif действие == "отнять (-)":
            new_value -= значение
            collusers.find_one_and_update({"id": участник.id}, {"$inc": {поле: -значение}})
            action_text = f"**отняли** ``{значение}``"
        elif действие == "установить (=)":
            new_value = значение
            collusers.find_one_and_update({"id": участник.id}, {"$set": {поле: значение}})
            action_text = f"**установили** значение на ``{значение}``"

        # Создание Embed для ответа
        embed = disnake.Embed(color=0x00FF00)
        embed.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
        embed.add_field(name="",
                        value=f"Вы {action_text} для поля **{поле}** у {участник.mention}. Теперь его значение: {new_value}",
                        inline=False)
        embed.set_footer(text=f"Поле {поле} участника {участник.display_name} изменено",
                         icon_url=участник.display_avatar.url)
        embed.timestamp = datetime.now()
        await inter.response.send_message(embed=embed, ephemeral=True)

        # Логирование изменений
        log_channel = await self.bot.fetch_channel(944562833901899827)
        log_embed = disnake.Embed(color=0x00FF00)
        log_embed.set_author(name="Изменение поля", icon_url=inter.user.display_avatar.url)
        log_embed.add_field(name="Администратор:", value=inter.user.mention, inline=True)
        log_embed.add_field(name="Участник:", value=участник.mention, inline=True)
        log_embed.add_field(name="Поле:", value=поле, inline=True)
        log_embed.add_field(name="Действие:", value=действие, inline=True)
        log_embed.add_field(name="Значение:", value=f"{значение}", inline=True)
        log_embed.add_field(name="Старое значение:", value=f"{current_value}", inline=True)
        log_embed.add_field(name="Новое значение:", value=f"{new_value}", inline=True)
        log_embed.set_footer(text=f"ID Участника: {участник.id}")
        log_embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
        log_embed.timestamp = datetime.now()
        await log_channel.send(embed=log_embed)

    @commands.slash_command(name='store', description='Магазин ролей и специальных возможностей за Румбики',
                            aliases=['shop', 'магазин', 'лавка', 'рынок'], contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def store(self, inter: disnake.ApplicationCommandInteraction):
        if inter.type == disnake.InteractionType.application_command:
            try:
                await inter.response.defer(ephemeral=True)
            except:
                return
        diamond = inter.guild.get_role(1044314368717897868)
        gold = inter.guild.get_role(1303396950481174611)
        user_data = collusers.find_one({"id": inter.author.id})
        if user_data:
            balance = round(user_data.get('balance', 0), 2)
            balance_formatted = format_rumbick(balance)
        else:
            balance_formatted = '0'
        embed = disnake.Embed(title='', color=0x4169E1)
        embed.set_author(name='Магазин сервера', icon_url=inter.guild.icon.url)
        embed.set_thumbnail(url='https://i.gifer.com/origin/63/6309237109affef229b14c3c5dc7308b_w200.gif')
        embed.add_field(name='Для просмотра дополнительной информации и цен о товаре, выберете его в выпадающем меню выбора товаров!', value=f'', inline=False)
        embed.add_field(name=f'**1. 💎 Diamond**',
                        value=f'Даёт эксклюзивные возможности (все возможности роли ⭐️ Gold и больше). Подробнее с возможностями можно ознакомиться при выборе товара.\n**Цена покупки:** ``499``{emoji} | ``899``{emoji} | ``1199``{emoji}\n **Содержит в себе:** Роль - {diamond.mention}',
                        inline=False)
        embed.add_field(name=f'**2. ⭐️ Gold**',
                        value=f'Даёт эксклюзивные возможности. Подробнее с возможностями можно ознакомиться при выборе товара.\n**Цена покупки:** ``249``{emoji} | ``449``{emoji} | ``599``{emoji}\n **Содержит в себе:** Роль - {gold.mention}',
                        inline=False)
        embed.add_field(name=f'**3. 🙋‍♂️ Смена никнейма**',
                        value=f'Даёт единоразовую возможность сменить свой отображаемый никнейм на сервере.\n**Цена покупки:** ``49``{emoji}\n**Содержит в себе:** Возможность смены __отображаемого__ никнейма на сервере.',
                        inline=False)
        embed.add_field(name=f'**4. 🚀 Глобальный бустер румбиков x2**',
                        value=f'Вдвое увеличивает зароботок с активнисти в голосовых каналах и текстовых чатах.\n**Цена покупки:** ``199``{emoji} | ``499``{emoji} | ``999``{emoji}\n**Содержит в себе:** Глобальный бустер румбиков x2.',
                        inline=False)
        embed.add_field(name=f'**5. 🔑 Мистический ключ**',
                        value=f'Покрытый загадочными рунами, этот ключ открывает мистический ящик с редкими сокровищами. Готов ли ты узнать, что внутри?\n**Цена покупки:** от ``49``{emoji} за штуку'
                              f'\n**Содержит в себе:** Возможность открыть **загадочный ящик** с помощью команды ``/mystery-box open``. Кто знает, что скрывается внутри?',
                        inline=False)
        embed.add_field(name='', value='')
        embed.add_field(name='', value=f'**Ваш текущий баланс:** {balance_formatted}', inline=False)



        # Создаем select menu
        select_menu = disnake.ui.Select(
            placeholder="Выбрать предмет для покупки...",
            min_values=1,
            max_values=1,
            options=self.options,
        )

        async def select_callback(interaction: disnake.MessageInteraction):
            global embed1
            if select_menu.values[0] == "1":
                embed1 = disnake.Embed(color=0x4169E1)
                embed1.set_author(name=f'Выберите длительность {diamond.name}', icon_url=inter.guild.icon.url)
                embed1.set_thumbnail(url='https://i.gifer.com/origin/63/6309237109affef229b14c3c5dc7308b_w200.gif')
                embed1.add_field(name='',
                                 value=f'{diamond.mention} - Роль-привилегия, предоставляющая уникальные возможности для самых активных и преданных участников. С этой ролью вы получите полный доступ к эксклюзивным функциям сервера.',
                                 inline=False)
                embed1.add_field(
                    name="**Привилегии:**",
                    value=(
                         "```"
                        "✅ 👤 Уникальное отображение в списке участников\n"
                        "✅ ⭐️ Уникальная иконка возле ника\n"
                        "✅ 🔒 Эксклюзивный доступ к VIP-каналу\n"
                        "✅ 📜 Полный доступ к Журналу аудита\n"
                        "✅ ✏️ Неограниченное и бесплатное изменение никнейма\n"
                        "✅ 🛡️ Полное игнорирование системы автомодерации\n"
                        "✅ ⏱️ Убран кулдаун между использованием команд\n"
                        "✅ 📆 Сокращение срока предупреждений на 10 дней при нарушениях\n"
                        "✅ 💸 Нулевая комиссия при переводе Румбиков\n"
                        "✅ 🏷️ Возможность установить статус канала"
                        "```"
                    ), inline=False)
                embed1.add_field(name='', value='')
                embed1.add_field(name='**Стоимость**',
                                 value=f'* {diamond.mention}\n * {diamond.mention} (на 30 дней) - 499{emoji}\n * {diamond.mention} (на 60 дней) - ~~1000~~ 899{emoji} **На 10% выгоднее!**\n * {diamond.mention} (на 90 дней) - ~~1500~~ 1199{emoji} **На 20% выгоднее!**',
                                 inline=False)
                embed1.add_field(name='Обратите внимание:',
                                 value=f'Если у вас уже есть роль {diamond.mention}, при повторной покупке её срок действия будет продлён.',
                                 inline=False)
                embed1.add_field(name='', value='')
                embed1.add_field(name='', value=f'**Ваш текущий баланс:** {balance_formatted}', inline=False)

                components = [
                    disnake.ui.Button(label=f"💎 Купить на 30 дней", style=disnake.ButtonStyle.secondary,
                                      emoji=diamond.emoji, custom_id='30'),
                    disnake.ui.Button(label=f"💎 Купить на 60 дней", style=disnake.ButtonStyle.primary,
                                      emoji=diamond.emoji, custom_id='60'),
                    disnake.ui.Button(label=f"💎 Купить на 90 дней", style=disnake.ButtonStyle.green,
                                      emoji=diamond.emoji, custom_id='90')
                ]

                # Обрабатываем нажатие кнопк

                async def button_callback(interaction: disnake.MessageInteraction):
                    button_id = interaction.component.custom_id
                    diamond_role_id = 1044314368717897868  # ID роли "Diamond"

                    if button_id == '30':
                        await process_role(interaction, self.bot, cost=499, duration=2678400, role_id=diamond_role_id,
                                           ephemeral=True)
                    elif button_id == '60':
                        await process_role(interaction, self.bot, cost=899, duration=5097600, role_id=diamond_role_id,
                                           ephemeral=True)
                    elif button_id == '90':
                        await process_role(interaction, self.bot, cost=1199, duration=7776000, role_id=diamond_role_id,
                                           ephemeral=True)

                for button in components:
                    button.callback = button_callback

                view = disnake.ui.View(timeout=None)
                for button in components:
                    view.add_item(button)

                await interaction.response.send_message(embed=embed1, ephemeral=True, view=view)

            if select_menu.values[0] == "2":  # gold
                embed1 = disnake.Embed(color=0x4169E1)
                embed1.set_author(name=f'Выберите длительность {gold.name}', icon_url=inter.guild.icon.url)
                embed1.set_thumbnail(url='https://i.gifer.com/origin/63/6309237109affef229b14c3c5dc7308b_w200.gif')
                embed1.add_field(name='',
                                 value=f'{diamond.mention} - Роль-привилегия, предоставляющая уникальные возможности для самых активных и преданных участников. С этой ролью вы получите ограниченный доступ к эксклюзивным функциям сервера.',
                                 inline=False)
                embed1.add_field(
                    name="**Привилегии:**",
                    value=(
                        "```"
                        "✅ 👤 Уникальное отображение в списке участников\n"
                        "✅ ⭐️ Уникальная иконка возле ника\n"
                        "✅ 🔒 Эксклюзивный доступ к VIP-каналу\n"
                        "❌ 📜 Полный доступ к Журналу аудита\n"
                        "❌ ✏️ Неограниченное и бесплатное изменение никнейма\n"
                        "❌ 🛡️ Полное игнорирование системы автомодерации\n"
                        "✅ ⏱️ Убран кулдаун между использованием команд\n"
                        "❌ 📆 Сокращение срока предупреждений на 10 дней при нарушениях\n"
                        "✅ 💸 Комиссия при переводе Румбиков снижена до 5%\n"
                        "✅ 🏷️ Возможность установить статус канала"
                        "```"
                    ), inline=False)
                embed1.add_field(name='**Стоимость**',
                                 value=f'* {gold.mention}\n * {gold.mention} (на 30 дней) - 249{emoji}\n * {gold.mention} (на 60 дней) - ~~500~~ 449{emoji} **На 10% выгоднее!**\n * {gold.mention} (на 90 дней) - ~~750~~ 599{emoji} **На 20% выгоднее!**',
                                 inline=False)
                embed1.add_field(name='Обратите внимание:',
                                 value=f'Если у вас уже есть роль {gold.mention}, при повторной покупке её срок действия будет продлён.',
                                 inline=False)
                embed1.add_field(name='', value='')
                embed1.add_field(name='', value=f'**Ваш текущий баланс:** {balance_formatted}', inline=False)

                components = [
                    disnake.ui.Button(label=f"⭐️ Купить на 30 дней", style=disnake.ButtonStyle.secondary,
                                      emoji=diamond.emoji, custom_id='30'),
                    disnake.ui.Button(label=f"⭐️ Купить на 60 дней", style=disnake.ButtonStyle.primary,
                                      emoji=diamond.emoji, custom_id='60'),
                    disnake.ui.Button(label=f"⭐️ Купить на 90 дней", style=disnake.ButtonStyle.green,
                                      emoji=diamond.emoji, custom_id='90')
                ]

                # Обрабатываем нажатие кнопки

                async def button_callback(interaction: disnake.MessageInteraction):
                    button_id = interaction.component.custom_id
                    gold_role_id = 1303396950481174611  # ID роли "Gold"

                    if button_id == '30':
                        await process_role(interaction, self.bot, cost=249, duration=2678400, role_id=gold_role_id,
                                           ephemeral=True)
                    elif button_id == '60':
                        await process_role(interaction, self.bot, cost=449, duration=5097600, role_id=gold_role_id,
                                           ephemeral=True)
                    elif button_id == '90':
                        await process_role(interaction, self.bot, cost=599, duration=7776000, role_id=gold_role_id,
                                           ephemeral=True)

                for button in components:
                    button.callback = button_callback

                view = disnake.ui.View(timeout=None)
                for button in components:
                    view.add_item(button)

                await interaction.response.send_message(embed=embed1, ephemeral=True, view=view)

            if select_menu.values[0] == "3":
                nikname_price = 49
                if collusers.find_one({'id': inter.author.id})['balance'] < nikname_price:
                    error_message = "У вас не хватает румбиков для покупки."
                    embed = create_error_embed(error_message)
                    await inter.edit_original_response(embed=embed)
                    return
                collusers.update_many({'id': inter.author.id}, {'$inc': {'number_of_deal': 1}})
                collusers.find_one_and_update({'id': interaction.author.id}, {'$inc': {'balance': -nikname_price}})
                collservers.update_one({"_id": inter.guild.id}, {"$inc": {"deals": 1}}, upsert=True)
                collservers.update_one({"_id": inter.guild.id}, {"$inc": {"wasted_rumbiks": nikname_price}}, upsert=True)
                components = disnake.ui.TextInput(
                    label=f"Никнейм",
                    custom_id="nickname",
                    style=disnake.TextInputStyle.short,
                    placeholder="Введите новый никнейм",
                    required=True,
                    min_length=1,
                    max_length=32,
                )

                modal = disnake.ui.Modal(
                    title="Смена никнейма",
                    custom_id="my_modal",
                    components=[components]
                )
                await interaction.response.send_modal(modal=modal)


            if select_menu.values[0] == "4":
                global_booster_price_map = {
                    '1_day': 199,
                    '3_days': 499,
                    '7_days': 999
                }


                def get_day_word(day_count):
                    if day_count == 1:
                        return 'день'
                    elif day_count in [2, 3, 4]:
                        return 'дня'
                    else:
                        return 'дней'

                async def button_callback(interaction: disnake.MessageInteraction):
                    button_id = interaction.component.custom_id
                    cost = global_booster_price_map[button_id]
                    duration_map = {
                        '1_day': 86400,
                        '3_days': 259200,
                        '7_days': 604800
                    }
                    duration = duration_map[button_id]
                    day_count = int(button_id.split('_')[0])

                    if collusers.find_one({'id': interaction.author.id})['balance'] < cost:
                        error_message = "У вас не хватает румбиков для покупки."
                        embed = create_error_embed(error_message)
                        await interaction.send(embed=embed, ephemeral=True)
                        return

                    # Получение данных сервера
                    server_data = collservers.find_one({'_id': interaction.author.guild.id})
                    current_timestamp = server_data['global_booster_timestamp']
                    current_time = int(datetime.now().timestamp())
                    admin_multiplier = server_data['admin_booster_multiplier']

                    if current_timestamp != 0 and current_timestamp > current_time:
                        # Продление бустера
                        new_timestamp = current_timestamp + duration
                        extend_embed = disnake.Embed(
                            description=f"**Срок действия активного глобального бустера Румбиков продлён на {day_count} {get_day_word(day_count)}.**\n Теперь все участники смогут дольше наслаждаться бустером.",
                            color=0x00ff00,
                            timestamp=datetime.now()
                        )
                        extend_embed.set_author(name="Бустер румбиков продлён!",
                                                icon_url="https://i.imgur.com/vlX2dxG.gif")
                        extend_embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
                        extend_embed.set_footer(text="Покупка прошла успешно",
                                                icon_url=interaction.guild.icon.url)

                        await interaction.send(embed=extend_embed, ephemeral=True)

                        # Обновление списка активировавших бустер
                        collservers.find_one_and_update(
                            {'_id': interaction.author.guild.id},
                            {'$addToSet': {'global_booster_activated_by': interaction.author.id}}
                        )
                    else:
                        # Покупка бустера и обновление множителя
                        new_timestamp = current_time + duration
                        purchase_embed = disnake.Embed(
                            description=f"**Вы успешно приобрели бустер румбиков x2 на {day_count} {get_day_word(day_count)}.**\n Теперь все участники будут получать вдвое больше Румбиков за активность в чатах и голосовых каналах.",
                            color=0x00ff00,
                            timestamp=datetime.now()
                        )
                        purchase_embed.set_author(name="Бустер румбиков приобретён!",
                                                  icon_url="https://i.imgur.com/vlX2dxG.gif")
                        purchase_embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
                        purchase_embed.set_footer(text="Покупка прошла успешно",
                                                  icon_url=interaction.guild.icon.url)
                        await interaction.send(embed=purchase_embed, ephemeral=True)

                        # Проверка и обновление глобального множителя бустера
                        if admin_multiplier == 1 or admin_multiplier == 0:
                            new_multiplier = 2  # Если админский бустер 1x или 0x, то устанавливаем 2
                        else:
                            new_multiplier = admin_multiplier + 1  # Добавляем только 1 к текущему админскому множителю

                        collservers.find_one_and_update(
                            {'_id': interaction.author.guild.id},
                            {'$set': {'multiplier': new_multiplier}}
                        )

                        # Обновление списка активировавших бустер
                        collservers.find_one_and_update(
                            {'_id': interaction.author.guild.id},
                            {'$addToSet': {'global_booster_activated_by': interaction.author.id}}
                        )

                    # Обновление информации о бустере в базе данных
                    collservers.find_one_and_update(
                        {'_id': interaction.author.guild.id},
                        {
                            '$set': {
                                'global_booster_timestamp': new_timestamp,
                                'global_booster_multiplier': 2
                            }
                        }
                    )

                    # Обновление баланса пользователя и количества сделок
                    collusers.update_one({'id': interaction.author.id}, {'$inc': {'number_of_deal': 1}})
                    collusers.find_one_and_update({'id': interaction.author.id}, {'$inc': {'balance': -cost}})
                    collservers.update_one({"_id": inter.guild.id}, {"$inc": {"deals": 1}}, upsert=True)
                    collservers.update_one({"_id": inter.guild.id}, {"$inc": {"wasted_rumbiks": cost}}, upsert=True)

                    # Уведомление в канале сервера
                    channel = interaction.author.guild.get_channel(489867322039992323)
                    if current_timestamp != 0 and current_timestamp > current_time:
                        # Уведомление о продлении бустера
                        server_embed = disnake.Embed(
                            title="Бустер румбиков x2 продлён!",
                            description=f"{interaction.author.mention} __продлил__ глобальный бустер румбиков ``x2`` на ``{day_count} {get_day_word(day_count)}``!\nНовый срок окончания бустера: <t:{new_timestamp}:R>.\n **Поблагодарим добряка в чате!**",
                            color=0x00faff,
                            timestamp=datetime.now()
                        )
                        server_embed.set_author(name=f"{inter.user.display_name}", icon_url=f"{inter.user.avatar.url}")
                        server_embed.set_thumbnail(url='https://i.imgur.com/vlX2dxG.gif')
                        server_embed.set_footer(text=f'Продление глобального бустера', icon_url=inter.guild.icon.url)
                    else:
                        # Уведомление о покупке бустера
                        server_embed = disnake.Embed(
                            title="Бустер румбиков x2 активирован!",
                            description=f"{interaction.author.mention} __активировал__ глобальный бустер румбиков ``x2`` на ``{day_count} {get_day_word(day_count)}``!\nБустер закончится <t:{new_timestamp}:R>.\n **Поблагодарим добряка в чате!**",
                            color=0x00faff,
                            timestamp=datetime.now()
                        )
                        server_embed.set_author(name=f"{inter.user.display_name}", icon_url=f"{inter.user.avatar.url}")
                        server_embed.set_thumbnail(url='https://i.imgur.com/vlX2dxG.gif')
                        server_embed.set_footer(text=f'Активация глобального бустера', icon_url=inter.guild.icon.url)
                    await channel.send(embed=server_embed)

                for button in self.options_2:
                    button.callback = button_callback

                view = disnake.ui.View(timeout=None)
                for button in self.options_2:
                    view.add_item(button)

                embed = disnake.Embed(color=0x4169E1)
                embed.set_author(name=f'Выберите длительность Бустера', icon_url=inter.guild.icon.url)
                embed.set_thumbnail(url='https://i.gifer.com/origin/63/6309237109affef229b14c3c5dc7308b_w200.gif')
                embed.add_field(name='', value='**Глобальный бустер румбиков** — Вдвое увеличивает заработок с активности в голосовых каналах и текстовых чатах.')
                embed.add_field(name='Выберите желаемую длительность для активации глобального бустера румбиков x2:',
                                value='', inline=False)
                embed.add_field(name='**Стоимость:**',
                                value=f'* Глобальный бустер х2\n * Бустер (на 1 день) - 199{emoji}\n * Бустер (на 3 дня) - ~~600~~ 499{emoji} **На 17% выгоднее!**\n * Бустер (на 7 дней) - ~~1400~~ 999{emoji} **На 29% выгоднее!**',
                                inline=False)
                embed.add_field(name='Обратите внимание:',
                                value=f'Если глобальный бустер румбиков уже активен, при повторной покупке его срок действия будет продлён.',
                                inline=False)
                embed.add_field(name='', value='')
                embed.add_field(name='', value=f'**Ваш текущий баланс:** {balance_formatted}', inline=False)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            if select_menu.values[0] == "5":
                user_data = collusers.find_one({'id': inter.author.id})
                keys_count = user_data.get('keys', 0)
                embed1 = disnake.Embed(color=0x4169E1)
                embed1.set_author(name=f'Выберите количество ключей', icon_url=inter.guild.icon.url)
                embed1.set_thumbnail(url='https://i.gifer.com/origin/63/6309237109affef229b14c3c5dc7308b_w200.gif')
                embed1.add_field(name='',
                                 value=f'Мистический ключ - этот таинственный ключ покрыт древними рунами, мерцающими в полумраке. Никто не знает, откуда он появился, но говорят, что он способен открыть **мистический ящик**, хранящий в себе невероятные секреты и редкие сокровища. Отважишься ли ты узнать, что скрывается внутри?',
                                 inline=False)
                embed1.add_field(name='Что можеть выпасть?',
                                 value='```🔑 Ключи для открытия новых ящиков.\n'
                                       '💎 Роли уровня Diamond и Gold от 1 до 180 дней.\n'
                                       '💰 Различные суммы Румбиков от 1 до 5000.\n'
                                       '🔇 Забавный "приз" в виде временного мьюта от 1 до 40 минут.\n'
                                       '😔 И, конечно, шанс на то, что ящик окажется пустым.```')
                embed1.add_field(name='', value='Подробнее о шансах: ``/mystery-box list``', inline=False)
                embed1.add_field(name='**Стоимость:**',
                                 value=f'* 🔑️ Ключ\n * от **1🔑️+** = 49{emoji}\n * от **5🔑️+** = ~~250~~ 236{emoji} **На 5% выгоднее!**\n * от **10🔑️+** = ~~500~~ 449{emoji} **На 10% выгоднее!**\n * от **50🔑️+** = ~~2500~~ 2125{emoji} **На 15% выгоднее!**\n * от **100🔑️+** = ~~5000~~ 3999{emoji} **На 20% выгоднее!**\n * от **200🔑️+** = ~~10000~~ 6999{emoji} **На 30% выгоднее!**',
                                 inline=False)
                embed1.add_field(name='Обратите внимание:',
                                 value=f'Чем больше ключей вы покупаете - тем выгоднее!',
                                 inline=False)
                embed1.add_field(name='', value='')
                embed1.add_field(name='', value=f'**Количество ключей:** {keys_count}🔑', inline=False)
                embed1.add_field(name='', value=f'**Ваш текущий баланс:** {balance_formatted}', inline=False)

                components = [
                    disnake.ui.Button(label=f"Выбрать количество для покупки", style=disnake.ButtonStyle.blurple,
                                      emoji="🔑", custom_id='30'),
                ]

                # Убедитесь, что класс KeyModal объявлен заранее
                class KeyModal(disnake.ui.Modal):
                    def __init__(self):
                        components = [
                            disnake.ui.TextInput(
                                label="Введите количество ключей",
                                placeholder="Чем больше - тем выгоднее!",
                                custom_id="key_amount",
                                style=disnake.TextInputStyle.short,
                            )
                        ]
                        super().__init__(title="Покупка ключей", custom_id="key_modal", components=components)

                    async def callback(self, interaction: disnake.ModalInteraction):
                        key_amount = int(interaction.text_values["key_amount"])
                        price = calculate_discounted_price(key_amount)

                        user_data = collusers.find_one({'id': interaction.author.id})
                        if user_data['balance'] < price:
                            error_message = "У вас не хватает румбиков для покупки."
                            embed = create_error_embed(error_message)
                            await interaction.send(embed=embed, ephemeral=True)
                            return

                        # Создаем подтверждающий embed
                        embed_confirm = disnake.Embed(
                            title="Подтверждение покупки",
                            description=f"Вы действительно хотите приобрести **{key_amount}**🔑 ключей за **{price}**{emoji}?",
                            color=0x00ff00
                        )

                        # Кнопка подтверждения
                        class ConfirmView(disnake.ui.View):
                            def __init__(self):
                                super().__init__(timeout=300)

                                button_confirm = disnake.ui.Button(
                                    label="✅ Подтвердить",
                                    style=disnake.ButtonStyle.green,
                                    custom_id="confirm_purchase"
                                )
                                button_confirm.callback = self.confirm_purchase
                                self.add_item(button_confirm)

                            async def confirm_purchase(self, button_interaction: disnake.MessageInteraction):
                                collusers.update_many({'id': interaction.author.id},
                                                      {'$inc': {'number_of_deal': 1}})
                                collusers.find_one_and_update({'id': interaction.author.id},
                                                              {'$inc': {'balance': -price}})
                                collusers.update_many({'id': interaction.author.id}, {'$inc': {'keys': key_amount}})
                                collservers.update_one({"_id": interaction.guild.id}, {"$inc": {"deals": 1}},
                                                       upsert=True)
                                collservers.update_one({"_id": interaction.guild.id},
                                                       {"$inc": {"wasted_rumbiks": price}}, upsert=True)

                                embed_success = disnake.Embed(
                                    description=f"Вы приобрели **{key_amount}**🔑 ключей за **{price}**{emoji}\nИспользуйте команду ``/mystery-box open``, чтобы открыть **мистический ящик**.",
                                    colour=0x00ff00,
                                    timestamp=datetime.now()
                                )
                                embed_success.set_author(name="Вы успешно приобрели Ключи!",
                                                         icon_url="https://i.imgur.com/vlX2dxG.gif")
                                embed_success.set_thumbnail(
                                    url="https://www.emojiall.com/images/240/telegram/2705.gif")
                                embed_success.set_footer(text="Покупка прошла успешно",
                                                         icon_url=interaction.guild.icon.url)

                                await button_interaction.response.edit_message(embed=embed_success, view=None)

                        view_confirm = ConfirmView()
                        await interaction.send(embed=embed_confirm, view=view_confirm, ephemeral=True)

                async def button_callback(inter: disnake.MessageInteraction):
                    await inter.response.send_modal(KeyModal())

                components[0].callback = button_callback

                view = disnake.ui.View()
                for component in components:
                    view.add_item(component)

                await interaction.response.send_message(embed=embed1, view=view, ephemeral=True)

            def calculate_discounted_price(key_amount):
                base_price = 50  # Цена за 1 ключ без скидки

                if 1 <= key_amount <= 4:
                    return key_amount * base_price - 1  # Без скидки
                elif 5 <= key_amount <= 9:
                    discount = 0.05  # 5% скидка
                elif 10 <= key_amount <= 49:
                    discount = 0.10  # 10% скидка
                elif 50 <= key_amount <= 99:
                    discount = 0.15  # 15% скидка
                elif 100 <= key_amount <= 199:
                    discount = 0.20  # 20% скидка
                else:  # 200 и более
                    discount = 0.30  # 30% скидка

                discounted_price_per_key = base_price * (1 - discount)
                return round(key_amount * discounted_price_per_key - 1)  # Округляем до ближайшего целого

        select_menu.callback = select_callback

        # Создаем view и добавляем в него select menu
        view = disnake.ui.View()
        view.add_item(select_menu)

        # Отправляем сообщение с view

        await inter.edit_original_response(embed=embed, view=view)


    async def on_update_experience(self, id, guild_id, level, before, after):
        first_level = 100
        experience_to_level = first_level + (100 * level)
        experience = collusers.find_one({"id": id, "guild_id": guild_id})["experience"]
        print(level)
        if experience > experience_to_level:
            unnecessary_experience = experience - experience_to_level
            level += 1
            collusers.update_one({'id': id, 'guild_id': guild_id}, {"$inc": {"level": 1}})
            collusers.update_one({'id': id, 'guild_id': guild_id}, {"$set": {"experience": unnecessary_experience}})
            collusers.update_one({'id': id, 'guild_id': guild_id}, {"$inc": {"balance": 50 * level}})
            try:
                if self.role_award[level]:
                    guild_id = self.bot.get_guild(guild_id)
                    role = guild_id.get_role(self.role_award[level])
                    member = guild_id.get_member(id)
                    await member.add_roles(role)
                    await member.remove_roles(guild_id.get_role(self.role_award[level - 5]))
            except:
                print('Role not found')
            print(
                f'Updated experience and level, {unnecessary_experience}, {level}, balance incremented on {50 * level}')
        else:
            print('<')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        global time_in_voice, multiplier
        print('Onvoice')

        if member.bot:
            return
        experience_minute = 0.5
        channel = member.guild.get_channel(944562833901899827)
        afk_channel_id = 516299058348818433
        now = int(datetime.now().timestamp())

        # Check if the user is in mute before entering the channel
        if after.channel is not None and after.self_mute:
            if member.id not in mute_timestamps:
                mute_timestamps[member.id] = []
            if not mute_timestamps[member.id] or mute_timestamps[member.id][-1][1] is not None:
                mute_timestamps[member.id].append((now, None))

        # Mute status changed
        if before.self_mute != after.self_mute:
            if not after.self_mute:
                if member.id in mute_timestamps and mute_timestamps[member.id][-1][1] is None:
                    mute_timestamps[member.id][-1] = (mute_timestamps[member.id][-1][0], now)

        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            voice_timestamps[member.id] = now

        # User left a voice channel
        elif before.channel is not None and after.channel is None:
            join_time = voice_timestamps.pop(member.id, None)
            if join_time:
                leave_time = now
                duration = leave_time - join_time

                # Calculate total mute time
                total_mute_time = 0
                if member.id in mute_timestamps:
                    for mute_start, mute_end in mute_timestamps[member.id]:
                        if mute_end is None:
                            mute_end = leave_time
                        total_mute_time += mute_end - mute_start
                    duration -= total_mute_time
                    mute_timestamps.pop(member.id, None)

                if member.id in total_time:
                    total_time[member.id] += duration + total_mute_time
                else:
                    total_time[member.id] = duration + total_mute_time

                # Handle leaving voice channel other than AFK
                if before.channel.id != afk_channel_id:
                    minutes = round(total_time[member.id] / 60, 2)
                    rumbiks = round(duration / 60 * 0.1, 2)
                    experience = int(round(duration / 60 * experience_minute,0))

                    multiplier = collservers.find_one({'_id': member.guild.id})['multiplier']
                    if rumbiks > 0.01:
                        collusers.find_one_and_update({'id': member.id, 'guild_id': member.guild.id}, {'$inc': {'balance': rumbiks * multiplier}})
                        collservers.update_one({"_id": member.guild.id}, {"$inc": {"voice_rumbiks": rumbiks * multiplier, "total_rumbicks": rumbiks * multiplier}}, upsert=True)
                    if experience >= 1:
                        level = collusers.find_one({'id': member.id, 'guild_id': member.guild.id})['level']
                        collusers.update_one({'id': member.id, 'guild_id': member.guild.id}, {"$inc": {'experience': experience * multiplier}})
                        await self.on_update_experience(member.id, member.guild.id, level, 0, 0)

                    if multiplier > 1:
                        rumbikswithboost = rumbiks * multiplier
                    else:
                        rumbikswithboost = None

                    # Update total voice time in seconds
                    collusers.find_one_and_update({'id': member.id}, {'$inc': {'time_in_voice': total_time[member.id]}})
                    collservers.update_one({"_id": member.guild.id}, {"$inc": {"time_in_voice": total_time[member.id]}}, upsert=True)
                    time_in_voice = collusers.find_one({'id': member.id})['time_in_voice']

                    # Use the helper function to format the duration
                    formatted_duration = format_time(duration)
                    formatted_total_time = format_time(total_time[member.id])
                    formatted_time_in_voice = format_time(time_in_voice)

                    embed = disnake.Embed(color=0xe70404, timestamp=datetime.now())
                    embed.set_thumbnail(url='https://i.imgur.com/B0w8aJT.gif')
                    embed.add_field(
                        name='**Голосовая активность:**',
                        value=(
                            f'Участник: `{member.display_name}` ({member.mention})\n'
                            f'Время в войсе: с <t:{join_time}:T> до <t:{leave_time}:T>\n'
                            f'Время (без учёта мута): `{formatted_duration}`\n'
                            f'Время (всего): `{formatted_total_time}`\n'
                            f'{f"**Выдано с учетом бустера:** `{rumbikswithboost}`{emoji}" if multiplier > 1 else f"**Выдано:** `{rumbiks}`{emoji}"}\n'
                            f'Опыта с учетом бустера: **{experience}**\n'
                            f'Общее время в войсе: `{formatted_time_in_voice}`'
                        )
                    )
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}", icon_url=member.guild.icon.url)
                    thread = member.guild.get_thread(1270673733178101801)
                    await thread.send(embed=embed)
                    total_time[member.id] = 0

        # User switched voice channels
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            join_time = voice_timestamps.pop(member.id, None)
            if join_time:
                leave_time = now
                duration = leave_time - join_time

                # Calculate total mute time
                total_mute_time = 0
                if member.id in mute_timestamps:
                    for mute_start, mute_end in mute_timestamps[member.id]:
                        if mute_end is None:
                            mute_end = leave_time
                        total_mute_time += mute_end - mute_start
                    duration -= total_mute_time
                    mute_timestamps.pop(member.id, None)

                if member.id in total_time:
                    total_time[member.id] += duration + total_mute_time
                else:
                    total_time[member.id] = duration + total_mute_time

                # Save time spent in previous channel before moving to AFK
                if after.channel.id == afk_channel_id:
                    minutes = round(duration / 60, 2)
                    rumbiks = round(duration / 60 * 0.1, 2)

                    multiplier = collservers.find_one({'_id': member.guild.id})['multiplier']
                    if rumbiks > 0.01:
                        collusers.find_one_and_update({'id': member.id}, {'$inc': {'balance': rumbiks * multiplier}})
                        collservers.update_one({"_id": member.guild.id},{"$inc": {"voice_rumbiks": rumbiks * multiplier}, "total_rumbicks": rumbiks * multiplier}, upsert=True)
                    if multiplier > 1:
                        rumbikswithboost = rumbiks * multiplier
                    else:
                        rumbikswithboost = None

                    # Update total voice time in seconds
                    collusers.find_one_and_update({'id': member.id}, {'$inc': {'time_in_voice': total_time[member.id]}})
                    collservers.update_one({"_id": member.guild.id}, {"$inc": {"time_in_voice": total_time[member.id]}}, upsert=True)
                    time_in_voice = collusers.find_one({'id': member.id})['time_in_voice']

                    # Use the helper function to format the duration
                    formatted_duration = format_time(duration)
                    formatted_total_time = format_time(total_time[member.id])
                    formatted_time_in_voice = format_time(time_in_voice)

                    embed = disnake.Embed(color=0xe70404, timestamp=datetime.now())
                    embed.set_thumbnail(
                        url='https://i.imgur.com/B0w8aJT.gif')
                    embed.add_field(
                        name='**Голосовая активность:**',
                        value=(
                            f'Участник: `{member.display_name}` ({member.mention})\n'
                            f'Время в войсе: с <t:{join_time}:T> до <t:{leave_time}:T>\n'
                            f'Время (без учёта мута): `{formatted_duration}`\n'
                            f'Время (всего): `{formatted_total_time}`\n'
                            f'{f"**Выдано с учетом бустера:** `{rumbikswithboost}`{emoji}" if multiplier > 1 else f"**Выдано:** `{rumbiks}`{emoji}"}\n'
                            f'Общее время в войсе: `{formatted_time_in_voice}`'
                        )
                    )
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}", icon_url=member.guild.icon.url)
                    thread = member.guild.get_thread(1270673733178101801)
                    await thread.send(embed=embed)
                    total_time[member.id] = 0
            voice_timestamps[member.id] = now

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
        else:
            raise ValueError(f"Invalid time unit: {time_str[-1]}")

    @tasks.loop(seconds=500)
    async def check_booster(self):
        server_id = 489867322039992320
        server_data = collservers.find_one({'_id': server_id})

        timestamp_booster = server_data['booster_timestamp']
        global_timestamp_booster = server_data['global_booster_timestamp']
        global_booster_multiplier = server_data['global_booster_multiplier']
        event_booster_multiplier = server_data['admin_booster_multiplier']  # заменено
        current_multiplier = server_data['multiplier']  # Получаем текущий общий множитель
        timestamp_now = int(datetime.now().timestamp())

        async def send_message_on_booster_end(booster_type, multiplier):
            channel = self.bot.get_channel(489867322039992323)
            guild = self.bot.get_guild(server_id)  # Получаем объект сервера
            icon_url = guild.icon.url if guild.icon else None  # Получаем URL иконки, если она установлена

            embed = disnake.Embed(
                title=f"{booster_type} бустер закончился.",
                description=f"Срок действия бустера истёк.\n```Текущий общий множитель: x{multiplier}```",
                color=0xff0000,
                timestamp = datetime.now()
            )
            embed.set_thumbnail(url='https://i.imgur.com/vlX2dxG.gif')
            embed.set_footer(text=f'Жаль, что приятные вещи не вечны.', icon_url=icon_url)
            await channel.send(embed=embed)

        if timestamp_booster != 0 and global_timestamp_booster == 0:
            if timestamp_booster < timestamp_now:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'booster_timestamp': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': 1}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_multiplier': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_activated_by': []}})
                await send_message_on_booster_end("Ивентовый", 1)  # передаем 1 как множитель
                return

        elif timestamp_booster == 0 and global_timestamp_booster != 0:
            if timestamp_now > global_timestamp_booster:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': 1}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_timestamp': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_multiplier': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_activated_by': []}})
                await send_message_on_booster_end("Глобальный", 1)  # передаем 1 как множитель
                return

        elif timestamp_booster != 0 and global_timestamp_booster != 0:
            if timestamp_now > global_timestamp_booster and timestamp_now > timestamp_booster:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_timestamp': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_multiplier': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'booster_timestamp': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': 1}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_multiplier': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_activated_by': []}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_activated_by': []}})
                await send_message_on_booster_end("Ивентовый и глобальный", 1)  # передаем 1 как множитель
                return

            elif timestamp_now > global_timestamp_booster and timestamp_now < timestamp_booster:
                new_multiplier = event_booster_multiplier
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': new_multiplier}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_timestamp': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_multiplier': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_activated_by': []}})
                await send_message_on_booster_end("Глобальный", new_multiplier)  # передаем новый множитель
                return

            elif timestamp_now > timestamp_booster and timestamp_now < global_timestamp_booster:
                new_multiplier = global_booster_multiplier
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': new_multiplier}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'booster_timestamp': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_multiplier': 0}})
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_activated_by': []}})
                await send_message_on_booster_end("Ивентовый", new_multiplier)  # передаем новый множитель
                return

        if timestamp_booster != 0 and timestamp_now > timestamp_booster:
            if global_timestamp_booster == 0 or timestamp_now > global_timestamp_booster:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': 1}})
                current_multiplier = 1
            else:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': global_booster_multiplier}})
                current_multiplier = global_booster_multiplier

            collservers.find_one_and_update({'_id': server_id}, {'$set': {'booster_timestamp': 0}})
            collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_multiplier': 0}})
            collservers.find_one_and_update({'_id': server_id}, {'$set': {'admin_booster_activated_by': []}})
            await send_message_on_booster_end("Ивентовый", current_multiplier)  # передаем текущий множитель
            return

        if global_timestamp_booster != 0 and timestamp_now > global_timestamp_booster:
            if timestamp_booster == 0 or timestamp_now > timestamp_booster:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': 1}})
                current_multiplier = 1
            else:
                collservers.find_one_and_update({'_id': server_id}, {'$set': {'multiplier': event_booster_multiplier}})
                current_multiplier = event_booster_multiplier

            collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_timestamp': 0}})
            collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_multiplier': 0}})
            collservers.find_one_and_update({'_id': server_id}, {'$set': {'global_booster_activated_by': []}})
            await send_message_on_booster_end("Глобальный", current_multiplier)  # передаем текущий множитель
            return

    @commands.slash_command(name='booster', description='Включает бустер румбиков', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def booster(self, inter: disnake.ApplicationCommandInteraction, множитель: int, длительность: str,
                      ивент: str = ''):
        try:
            # Преобразование длительности в секунды
            длительность_в_секундах = self.convert_to_seconds(длительность)
        except Exception as e:
            embed = disnake.Embed(color=0xe70404)
            embed.add_field(name='Произошла ошибка', value='Ошибка в конвертации в секунды')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return

        # Сохранение текущего времени и расчёт времени окончания бустера
        timestamp = int(datetime.now().timestamp()) + длительность_в_секундах
        server_data = collservers.find_one({'_id': inter.author.guild.id})
        global_booster_active = server_data['global_booster_timestamp'] != 0 and server_data[
            'global_booster_timestamp'] > int(datetime.now().timestamp())

        if global_booster_active:
            # Уменьшаем общий множитель на 1 при активном глобальном бустере
            новый_множитель = server_data['multiplier'] + int(множитель) - 1
        else:
            новый_множитель = int(множитель)

        collservers.find_one_and_update(
            {'_id': inter.author.guild.id},
            {
                '$set': {
                    'multiplier': новый_множитель,
                    'booster_timestamp': int(timestamp),
                    'admin_booster_multiplier': int(множитель)
                }
            }
        )
        collservers.find_one_and_update(
            {'_id': inter.author.guild.id},
            {'$addToSet': {'admin_booster_activated_by': inter.author.id}},
        )

        # Форматирование длительности в строку для отображения
        длительность_в_строке = self.format_duration(длительность)

        # Создание embed сообщения
        embed = disnake.Embed(
            title="Бустер румбиков активирован!",
            description=f"Вы успешно активировали ивентовый бустер румбиков ``x{множитель}`` на **{длительность_в_строке}**!\nБустер закончится <t:{timestamp}:R>.",
            color=0xfa00ff,
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{inter.author.display_name}", icon_url=f"{inter.author.avatar.url}")
        embed.set_thumbnail(url='https://i.imgur.com/vlX2dxG.gif')
        embed.set_footer(text=f'Активация ивентового бустера', icon_url=inter.guild.icon.url)
        if ивент:
            embed.add_field(name='Ивент:', value=ивент, inline=False)
        embed.add_field(name='', value=f'```Текущий общий множитель: x{новый_множитель}```', inline=False)

        await inter.response.send_message(embed=embed, ephemeral=True)

        channel = await self.bot.fetch_channel(489867322039992323)
        log_embed = disnake.Embed(
            title="Бустер румбиков активирован!",
            description=f"{inter.author.mention} __активировал__ ивентовый бустер румбиков ``x{множитель}`` на **{длительность_в_строке}**!\nБустер закончится <t:{timestamp}:R>.",
            color=0xfa00ff,
            timestamp=datetime.now()
        )
        log_embed.set_author(name=f"{inter.author.display_name}", icon_url=inter.author.display_avatar.url)
        log_embed.set_thumbnail(url='https://i.imgur.com/vlX2dxG.gif')
        log_embed.set_footer(text=f'Активация ивентового бустера', icon_url=inter.guild.icon.url)
        # Если указано название ивента, добавляем его в embed
        if ивент:
            log_embed.add_field(name='Ивент:', value=ивент, inline=False)
        log_embed.add_field(name='', value=f'```Текущий общий множитель: x{новый_множитель}```', inline=False)

        await channel.send(embed=log_embed)


    @commands.slash_command(name="boosters", description="Показывает текущие активные бустеры", contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def boosters(self, inter: disnake.ApplicationCommandInteraction):
        server_id = inter.guild_id
        server_data = collservers.find_one({'_id': server_id})

        # Извлечение информации о бустерах
        admin_booster_multiplier = server_data.get('admin_booster_multiplier', 0)
        admin_booster_activated_by = server_data.get('admin_booster_activated_by', [])
        booster_timestamp = server_data.get('booster_timestamp', 0)

        global_booster_multiplier = server_data.get('global_booster_multiplier', 0)
        global_booster_activated_by = server_data.get('global_booster_activated_by', [])
        global_booster_timestamp = server_data.get('global_booster_timestamp', 0)

        multiplier = server_data.get('multiplier', 1)


        embed = disnake.Embed(title="Активные бустеры румбиков на данный момент:", color=0x00ff00)
        embed.set_thumbnail(url='https://i.imgur.com/vlX2dxG.gif')
        embed.set_footer(text=f'Активные бустеры румбиков', icon_url=inter.guild.icon.url)
        embed.timestamp = datetime.now()

        # Серверный бустер (администраторский)
        if booster_timestamp > int(datetime.now().timestamp()):
            users_admin_booster = ', '.join([f'<@{user_id}>' for user_id in admin_booster_activated_by])
            time_remaining_admin = f"<t:{booster_timestamp}:R>"
            embed.add_field(
                name="Ивентовый бустер:",
                value=f"**Активировал:** {users_admin_booster}\n"
                      f"**Множитель:** ``x{admin_booster_multiplier}``\n"
                      f"**Истекает через:** {time_remaining_admin}",
                inline=False
            )

        # Глобальный бустер
        if global_booster_timestamp > int(datetime.now().timestamp()):
            users_global_booster = ', '.join([f'<@{user_id}>' for user_id in global_booster_activated_by])
            time_remaining_global = f"<t:{global_booster_timestamp}:R>"
            embed.add_field(
                name="Глобальный бустер",
                value=f"**Активировал:** {users_global_booster}\n"
                      f"**Множитель:** ``x{global_booster_multiplier}``\n"
                      f"**Истекает через:** {time_remaining_global}",
                inline=False
            )
            embed.add_field(name='', value='')

        # Если нет активных бустеров
        if len(embed.fields) == 0:  # Only the multiplier field exists
            embed.description = "На данный момент нет активных бустеров."
            embed.clear_fields()  # Clear the multiplier field if no boosters are active

        # Общий множитель
        embed.add_field(
            name="",
            value=f"```Текущий общий множитель: x{multiplier}```",
            inline=False
        )

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if inter.custom_id == "my_modal":
            nickname = inter.text_values["nickname"]
            await inter.author.edit(nick=nickname)
            await inter.response.send_message('Никнейм успешно изменён.', ephemeral=True)


    @commands.user_command(name='balance')
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def balinuser(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User):
        await self.balance(inter, user)


def setup(bot):
    bot.add_cog(EconomyCog(bot))
    print("EconomyCog is ready")