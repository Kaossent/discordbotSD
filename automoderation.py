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
import emoji
from ai.ai import generate_response

collusers = cluster.server.users
collservers = cluster.server.servers

user_last_messages = {}
flood_threshold = 20


def create_log_embed(bot, участник, message, mute_end_time, reason):
    embed = disnake.Embed(title="   ", url="",
                          description="", color=0xff8800, timestamp=datetime.now())
    embed.add_field(name="", value=f"Участник {участник.name} ({участник.mention}) был замучен!",
                    inline=False)
    embed.set_thumbnail(
        url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")
    embed.add_field(name="Автомодерация:", value=f"**{bot.user.name}** ({bot.user.mention})", inline=True)
    embed.add_field(name="Участник:", value=f"**{участник}** ({участник.mention})", inline=True)
    embed.add_field(name="Канал:", value=f"{message.channel.mention}", inline=True)
    embed.add_field(name="Время:", value=f"(<t:{int(mute_end_time.timestamp())}:F>)", inline=True)
    embed.add_field(name="Причина:", value=reason, inline=True)
    embed.set_footer(text=f"ID участника: {участник.id}")
    return embed


def create_error_embed(message: str) -> disnake.Embed:
    embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
    embed.add_field(name='Ваше сообщение удалено', value=f'**Причина:** {message}')
    embed.set_thumbnail(url="https://i.imgur.com/bugnSyX.gif")
    embed.set_footer(text='Автомодерация')
    return embed


def check_flood(user_id, message_text):
    current_time = time.time()  # Текущее время в секундах
    if user_id in user_last_messages:
        last_message_time, last_message_text, message_count = user_last_messages[user_id]

        # Проверяем, прошло ли время меньше, чем flood_threshold и одно и то же ли сообщение
        if current_time - last_message_time < flood_threshold and message_text == last_message_text:
            message_count += 1  # Увеличиваем счетчик одинаковых сообщений
        else:
            message_count = 1  # Если прошло больше времени или сообщение другое, сбрасываем счетчик

        # Если количество одинаковых сообщений больше или равно threshold, считаем флудом
        if message_count >= 3:
            return True  # Флуд обнаружен

    else:
        message_count = 1  # Если это первое сообщение, устанавливаем счетчик в 1

        # Обновляем данные пользователя (время, текст и счетчик)
    user_last_messages[user_id] = (current_time, message_text, message_count)
    return False  # Флуд не обнаружен


user_message_times = {}


def check_spam(user_id):
    current_time = time.time()
    if user_id not in user_message_times:
        user_message_times[user_id] = []

    # Очищаем сообщения старше 10 секунд
    user_message_times[user_id] = [
        timestamp for timestamp in user_message_times[user_id] if current_time - timestamp < 10
    ]

    # Добавляем текущее сообщение
    user_message_times[user_id].append(current_time)

    # Если сообщений больше 5 за 10 секунд — это спам
    return len(user_message_times[user_id]) > 5

def count_emojis(text):
    """Подсчитывает количество эмодзи в тексте."""
    return sum(1 for char in text if char in emoji.EMOJI_DATA)

def check_excessive_mentions(message: disnake.Message, limit: int = 6) -> bool:
    """
    Проверяет, превышает ли сообщение допустимое количество упоминаний.

    :param message: Объект сообщения.
    :param limit: Максимально допустимое количество упоминаний (по умолчанию 5).
    :return: True, если количество упоминаний превышает лимит, иначе False.
    """
    total_mentions = len(message.mentions) + len(message.role_mentions)
    return total_mentions > limit

class AutoModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_data = {}
        self.update.start()
        self.mute_duration = [
            (2, timedelta(minutes=1)),
            (3, timedelta(minutes=5)),
            (4, timedelta(minutes=15)),
            (5, timedelta(minutes=40)),
            (6, timedelta(hours=1)),
            (7, timedelta(hours=3)),
            (8, timedelta(hours=5)),
            (9, timedelta(hours=15))
        ]

    @tasks.loop(hours=24)
    async def update(self):
        self.user_data = {}

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.guild is None:
            return

        member = message.guild.get_member(message.author.id)
        channel = await self.bot.fetch_channel(944562833901899827)  # Ищем канал по id #логи
        upper_letter = 0
        roles = [
            message.guild.get_role(518505773022838797),  # admin
            message.guild.get_role(580790278697254913),  # chief
            message.guild.get_role(702593498901381184),  # moder
            message.guild.get_role(757930494301044737),  # booster
            message.guild.get_role(1044314368717897868),  # diamond
            # message.guild.get_role(1303396950481174611),  # gold
        ]

        if message.author.bot:
            return
        # Проверяем, есть ли у пользователя хотя бы одна из этих ролей
        if any(role in member.roles for role in roles):
            return

        # Проверка на слишком частые сообщения (спам)
        if check_spam(message.author.id):
            try:
                await message.delete()
            except:
                return
            if message.author.id in self.user_data:
                self.user_data[message.author.id] += 1
            else:
                self.user_data[message.author.id] = 1
            for count, timedelta_dur in self.mute_duration:
                if count == self.user_data[message.author.id]:
                    mute_end_time = datetime.now() + timedelta_dur  # Время окончания мьюта
                    await message.author.timeout(duration=timedelta_dur)
                    log_embed = create_log_embed(self.bot, message.author, message, mute_end_time,
                                                 'Слишком частые сообщения')
                    await channel.send(embed=log_embed)
            response = await generate_response(prompt=message.content, instructions='Ты модератор и должен обязательно на русском написать, что пользователь часто отправляет сообщения, адресуя это ему.', error='Слишком частые сообщения.\nТссссс... Зачем Вы ускоряетесь? Люди даже читать не успевают!')
            embed = create_error_embed(response)
            await message.channel.send(content=message.author.mention, embed=embed, delete_after=120)

        forbidden_links = [
            'https://youtu.be', 'https://www.youtube.com',
            'https://youtube.com', 'https://discord.gg', 'discord.gg'
        ]

        if any(link in message.content for link in forbidden_links) and message.channel.id != 1044571685900259389:
            try:
                await message.delete()
            except:
                return

            if message.author.id in self.user_data:
                self.user_data[message.author.id] += 1
            else:
                self.user_data[message.author.id] = 1
            for count, timedelta_dur in self.mute_duration:
                if count == self.user_data[message.author.id]:
                    mute_end_time = datetime.now() + timedelta_dur  # Время окончания мьюта
                    await message.author.timeout(duration=timedelta_dur)
                    log_embed = create_log_embed(self.bot, message.author, message, mute_end_time,
                                                 'Ссылки или приглашения')
                    await channel.send(embed=log_embed)
            response = await generate_response(prompt=message.content,
                                               instructions='Ты модератор и должен обязательно на русском написать, что пользователь отправляет ссылки или приглашения адресуя, это ему.',
                                               error='Ссылки или приглашения.\nРеклама — не здесь, а где-то там, но точно не тут, не в этом чатике, а в другом месте, там, где рекламируют!')
            embed = create_error_embed(response)
            await message.channel.send(content=message.author.mention, embed=embed, delete_after=120)

        if check_flood(message.author.id, message.content):
            try:
                await message.delete()
            except:
                return
            if message.author.id in self.user_data:
                self.user_data[message.author.id] += 1
            else:
                self.user_data[message.author.id] = 1
            for count, timedelta_dur in self.mute_duration:
                if count == self.user_data[message.author.id]:
                    mute_end_time = datetime.now() + timedelta_dur  # Время окончания мьюта
                    await message.author.timeout(duration=timedelta_dur)
                    log_embed = create_log_embed(self.bot, message.author, message, mute_end_time,
                                                 'Флуд одинаковыми сообщениями')
                    await channel.send(embed=log_embed)
            response = await generate_response(prompt=message.content,
                                               instructions='Ты модератор и должен обязательно на русском написать, что пользователь флудит одинаковыми сообщениями, адресуя это ему.',
                                               error='Флуд одинаковыми сообщениями.\n Мы поняли, поняли, зачем еще 10 раз повторять?')
            embed = create_error_embed(response)
            await message.channel.send(content=message.author.mention, embed=embed, delete_after=120)

        letters_of_words = list(message.content)
        for letter in letters_of_words:
            if letter.istitle():
                upper_letter += 1
        message_blank = message.content.replace(" ", "")
        if upper_letter >= 20 and (upper_letter / len(message_blank)) >= 0.8:
            await message.delete()
            response = await generate_response(prompt=message.content,
                                               instructions='Ты модератор и должен обязательно на русском написать, что пользователь использует слишком много верхнего регистра, адресуя это ему.',
                                               error='Чрезмерное использование верхнего регистра.\n ЗАЧЕМ ВЫ КРИЧИТЕ? Зачем нарушаете тишину?')
            embed = create_error_embed(response)
            await message.channel.send(embed=embed, delete_after=120)

        # Порог для количества эмодзи
        EMOJI_THRESHOLD = 15

        # Проверка на количество эмодзи
        emoji_count = count_emojis(message.content)

        if emoji_count > EMOJI_THRESHOLD:
            try:
                await message.delete()  # Удаляем сообщение
            except:
                return
            response = await generate_response(prompt=message.content,
                                               instructions='Ты модератор и должен обязательно на русском написать, '
                                                            'что пользователь использует отправляет слишком много эмодзи, адресуя это ему.',
                                               error=f'f"Слишком много эмодзи ({emoji_count}/{EMOJI_THRESHOLD}).\n'
                                                     f'Понимаю, вы эмоциональный человек, но давайте немного сократим '
                                                     f'их количество, чтобы сохранить сообщения читабельными."')
            embed = create_error_embed(response)
            await message.channel.send(content=message.author.mention, embed=embed, delete_after=120)

        # Проверка на чрезмерное количество упоминаний
        mention_limit = 6
        if check_excessive_mentions(message, mention_limit) and not 'https://' in message.content:
            try:
                await message.delete()
            except Exception as e:
                print(f"Ошибка удаления сообщения: {e}")
                return

            embed = create_error_embed(
                f"Слишком много упоминаний ({len(message.mentions) + len(message.role_mentions)} из {mention_limit} допустимых).\n Ну, давате еще весь сервер тут пинганите..."
            )
            await message.channel.send(content=message.author.mention, embed=embed, delete_after=120)

        max_word_length = 50
        if any(len(word) > max_word_length for word in message.content.split()):
            if 'https://' in message.content:
                return
            await message.delete()
            response = await generate_response(prompt=message.content,
                                               instructions='Ты модератор и должен обязательно на русском написать, '
                                                            'что пользователь отправляет слишком длинное слово, которое не существует, адресуя это ему.',
                                               error="Подозрительно длинное слово.\n Это новое слово, которое попадет "
                                                     "в книгу рекородов Гинесса как 'Самое длинное слово'? Или это "
                                                     "флуд символами? А возможно у Вас не работает пробел?")
            embed = create_error_embed(response)
            await message.channel.send(content=message.author.mention, embed=embed, delete_after=120)


def setup(bot):
    bot.add_cog(AutoModerationCog(bot))
    print("AutoModerationCog is ready")
