import disnake
from pymongo import MongoClient, errors
from disnake.ext import commands
from datetime import datetime
import os
import asyncio
import time
from dotenv import load_dotenv
import sys
from disnake.errors import HTTPException
from disnake.utils import format_dt


load_dotenv()
bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all(), reload=True)
bot.member_cache_flags = disnake.MemberCacheFlags.all()
cluster = MongoClient(os.getenv('MONGODB'))
collusers = cluster.server.users
collservers = cluster.server.servers
collpromos = cluster.server.promos
collreports = cluster.server.reports
collgiveways = cluster.server.giveways

ROLE_CATEGORIES = {
    "admin": [518505773022838797, 580790278697254913],  # ID ролей администраторов: admin, chief
    "moder": [518505773022838797, 580790278697254913, 702593498901381184],  # ID ролей модераторов: admin, chief, moder
    "staff": [518505773022838797, 580790278697254913, 702593498901381184, 1229337640839413813],  # ID ролей стаффа: admin, chief, moder, dev
    "premium": [518505773022838797, 580790278697254913, 702593498901381184, 1229337640839413813, 757930494301044737, 1044314368717897868, 1303396950481174611],  # ID премиум-ролей: admin, chief, moder, dev booster, diamond, gold
    "chied": [518505773022838797, 580790278697254913, 702593498901381184, 1229337640839413813, 757930494301044737, 1044314368717897868, 1303396950481174611],  # ID премиум-ролей: admin, chief, moder, dev booster, diamond, gold
}

rules = {
    "1.1": "1.1> Обман/попытка обмана Администрации сервера, грубое оспаривание действий Администрации сервера",
    "1.2": "1.2> Распространение личной информации без согласия",
    "1.3": "1.3> Обход правил сервера с помощью мультиаккаунта и любым другим способом",
    "1.4": "1.4> Транслирование или отправка контента, предназначенного для лиц старше 18 лет",
    "1.5": "1.5> Использование недопустимого никнейма или аватара",
    "1.6": "1.6> Подделка доказательств против участников/Администрации",
    "2.1": "2.1> Флуд, спам, чрезмерное упоминание ролей или участника",
    "2.2": "2.2> Оскорбления участников и их близких родственников",
    "2.3": "2.3> Оскорбление или неуважительное отношение к Администрации и серверу",
    "2.4": "2.4> Проведение политической или религиозной агитации, обсуждение военных действий, оскорбление стран, наций и субкультур",
    "2.5": "2.5> Реклама сторонних проектов, сайтов, каналов и т.д.",
    "3.1": "3.1> Крики, шумы, помехи, транслирование музыки не через бота, неадекватное поведение, использование программ для изменения голоса",
    "3.2": "3.2> Многочисленные перемещения по голосовым каналам, быстрое включение/выключение демонстрации экрана",
    "3.3": "3.3> AFK-фарм Румбиков ◊"
}

class RoleCheckFailure(commands.CheckFailure):
    """Исключение для ошибок проверки ролей."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
def check_roles(*categories):
    """Декоратор для проверки наличия роли из одной из указанных категорий."""
    async def predicate(interaction: disnake.ApplicationCommandInteraction):
        user_roles = [role.id for role in interaction.author.roles]
        allowed_roles = []
        for category in categories:
            allowed_roles.extend(ROLE_CATEGORIES.get(category, []))

        if any(role in user_roles for role in allowed_roles):
            return True

        # Получение упоминаний ролей, которых не хватает
        missing_roles_mentions = [f"<@&{role_id}>" for role_id in allowed_roles]
        role_list = ", ".join(missing_roles_mentions)

        raise RoleCheckFailure(f"У вас нет прав для использования этой команды. Необходимо иметь одну из этих ролей:\n {role_list}.")
    return commands.check(predicate)


def get_rule_info(rule_code):
    return rules.get(rule_code, rule_code)

async def safe_api_call(api_function, *args, **kwargs):
    try:
        return await api_function(*args, **kwargs)
    except HTTPException as e:
        if e.status == 429:
            retry_after = int(e.response.headers.get("Retry-After", 5))  # Задержка по умолчанию 5 секунд
            await asyncio.sleep(retry_after)
            return await safe_api_call(api_function, *args, **kwargs)
        else:
            raise
def create_error_embed(message: str) -> disnake.Embed:
    embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
    embed.add_field(name='Произошла ошибка', value=f'Ошибка: {message}')
    embed.set_thumbnail(url="https://media2.giphy.com/media/AkGPEj9G5tfKO3QW0r/200.gif")
    embed.set_footer(text='Ошибка')
    return embed

def convert_to_seconds(time_str):
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

def format_duration(time_str):
    try:
        value = int(time_str[:-1])
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")

    unit = time_str[-1]
    if unit == 'д' or unit == 'd':
        if value == 1:
            return "1 день"
        elif 2 <= value <= 4:
            return f"{value} дня"
        else:
            return f"{value} дней"
    elif unit == 'ч' or unit == 'h':
        if value == 1:
            return "1 час"
        elif 2 <= value <= 4:
            return f"{value} часа"
        else:
            return f"{value} часов"
    elif unit == 'м' or unit == 'm':
        if value == 1:
            return "1 минуту"
        elif 2 <= value <= 4:
            return f"{value} минуты"
        else:
            return f"{value} минут"
    elif unit == 'с' or unit == 's':
        if value == 1:
            return "1 секунду"
        elif 2 <= value <= 4:
            return f"{value} секунды"
        else:
            return f"{value} секунд"
    else:
        raise ValueError(f"Invalid time unit: {time_str[-1]}")

@bot.event
async def on_slash_command_error(inter: disnake.ApplicationCommandInteraction, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds_remaining = round(error.retry_after)
        embed = disnake.Embed(
            title="Подождите немного!",
            description=f"Эта команда находится в кулдауне. Попробуйте снова через **{seconds_remaining} секунд.**",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url="https://media2.giphy.com/media/AkGPEj9G5tfKO3QW0r/200.gif")
        if inter.response.is_done():
            await inter.edit_original_response(embed=embed)
        else:
            await inter.response.send_message(embed=embed, ephemeral=True)

    elif isinstance(error, RoleCheckFailure):
        # Обработка ошибки проверки ролей
        embed = disnake.Embed(
            title="Доступ запрещён!",
            description=error.message,
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url="https://media2.giphy.com/media/AkGPEj9G5tfKO3QW0r/200.gif")
        if inter.response.is_done():
            await inter.edit_original_response(embed=embed)
        else:
            await inter.response.send_message(embed=embed, ephemeral=True)

    else:
        # Общая обработка ошибок
        embed = disnake.Embed(
            title="Ошибка!",
            description="Произошла ошибка при выполнении команды. Попробуйте снова.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url="https://media2.giphy.com/media/AkGPEj9G5tfKO3QW0r/200.gif")
        if inter.response.is_done():
            await inter.edit_original_response(embed=embed)
        else:
            await inter.response.send_message(embed=embed, ephemeral=True)
        raise error


@bot.event
async def on_ready():
    print(f"Бот {bot.user} успешно запущен!\nID: {bot.user.id}")
    for guild in bot.guilds:
        for member in guild.members:
            values = {
                "id": member.id,
                "guild_id": guild.id,
                "nickname": member.display_name,
                "user_name": member.name,
                "balance": 0,
                "keys": 0,
                "opened_cases": 0,
                "reputation": 0,
                "reaction_count": 0,
                "promocodes": 0,
                "bumps": 0,
                "number_of_deal": 0,
                "message_count": 0,
                "time_in_voice": 0,
                "warns": 0,
                "reasons": [],
                "ban": 'False',
                "ban_timestamp": 0,
                "ban_reason": None,
                "number_of_roles": 0,
                "role_ids": [],
                "level": 0,
                "experience": 0
            }
            server_values = {
                "_id": guild.id,
                "booster_timestamp": 0,
                "admin_booster_multiplier": 0,
                "admin_booster_activated_by": [],
                "global_booster_timestamp": 0,
                "global_booster_multiplier": 0,
                "global_booster_activated_by": [],
                "multiplier": 1,
                "messages": 0,
                "time_in_voice": 0,
                "voice_rumbiks": 0,
                "chat_rumbicks": 0,
                "total_rumbicks": 0,
                "wasted_rumbiks": 0,
                "opened_cases": 0,
                "bumps": 0,
                "mutes": 0,
                "unmutes": 0,
                "case": 0,
                "warns": 0,
                "unwarns": 0,
                "bans": 0,
                "unbans": 0,
                "deals": 0,
                "commands_use": 0,
                "transfers": 0,
                "members_leave": 0,
                "members_join": 0,
                "activation_promos": 0,
                "rep_up": 0,
                "rep_down": 0,
                "reputation_count": 0
            }
            promo_values = {
                "_id": guild.id,
                "counter": 0,
                "promos": {}
            }
            report_values = {
                "_id": guild.id,
                "counter": 0,
                "reports": {}
            }

            if collusers.count_documents({"id": member.id, "guild_id": guild.id}) == 0:
                collusers.insert_one(values)
            if collservers.count_documents({"_id": guild.id}) == 0:
                collservers.insert_one(server_values)
            if collpromos.count_documents({"_id": guild.id}) == 0:
                collpromos.insert_one(promo_values)
            if collreports.count_documents({"_id": guild.id}) == 0:
                collreports.insert_one(report_values)


@bot.event
async def on_member_update(before, after):
    updates = {}
    if before.display_name != after.display_name:
        updates["nickname"] = after.display_name
    if before.name != after.name:
        updates["user_name"] = after.name

    if updates:
        collusers.update_one(
            {"id": after.id, "guild_id": after.guild.id},
            {"$set": updates}
        )


@bot.event
async def on_member_join(member):
    values = {
        "id": member.id,
        "guild_id": member.guild.id,
        "nickname": member.display_name,
        "user_name": member.name,
        "balance": 0,
        "keys": 0,
        "reputation": 0,
        "reaction_count": 0,
        "promocodes": 0,
        "bumps": 0,
        "number_of_deal": 0,
        "message_count": 0,
        "time_in_voice": 0,
        "warns": 0,
        "reasons": [],
        "ban": 'False',
        "ban_timestamp": 0,
        "ban_reason": None,
        "number_of_roles": 0,
        "role_ids": [],
        "level": 0,
        "experience": 0
    }

    if collusers.count_documents({"id": member.id, "guild_id": member.guild.id}) == 0:
        collusers.insert_one(values)

    # Отправка приветственного эмбед-сообщения
    channel = member.guild.get_thread(1279702475095412808)
    if channel:
        embed = disnake.Embed(
            title="Новый участник!",
            description=f"{member.display_name} ({member.mention}) присоединился на сервер.",
            color=disnake.Color.green(),
            timestamp=datetime.now()
        )
        # Используем относительное время для даты создания аккаунта
        embed.add_field(
            name="Дата регистрации аккаунта:",
            value=f"{format_dt(member.created_at, style='R')}",
            inline=False
        )
        await channel.send(embed=embed)
        collservers.update_one({"_id": member.guild.id}, {"$inc": {"members_join": 1}}, upsert=True)

@bot.event
async def on_member_remove(member):
    channel = member.guild.get_thread(1279702475095412808)
    if channel:
        embed = disnake.Embed(
            title="Участник покинул сервер",
            description=f"{member.display_name} ({member.mention}) покинул сервер.",
            color=disnake.Color.red(),
            timestamp=datetime.now()
        )
        # Используем относительное время для даты присоединения к серверу
        embed.add_field(
            name="Дата присоединения к серверу:",
            value=f"{format_dt(member.joined_at, style='R')}",
            inline=False
        )
        await channel.send(embed=embed)
        collservers.update_one({"_id": member.guild.id}, {"$inc": {"members_leave": 1}}, upsert=True)

@bot.event
async def on_interaction(interaction: disnake.ApplicationCommandInteraction):
    # Проверяем, является ли взаимодействие командой /slash
    if isinstance(interaction, disnake.ApplicationCommandInteraction):
        command_name = interaction.data.name
        user_display_name = interaction.author.display_name  # Получаем display_name пользователя
        print(f"Команда /{command_name} была вызвана пользователем {user_display_name}.")
        collservers.update_one({"_id": interaction.guild.id}, {"$inc": {"commands_use": 1}}, upsert=True)


@bot.event
async def on_guild_join(guild):
    server_values = {
        "_id": guild.id,
        "booster_timestamp": 0,
        "admin_booster_multiplier": 0,
        "admin_booster_activated_by": [],
        "global_booster_timestamp": 0,
        "global_booster_multiplier": 0,
        "global_booster_activated_by": [],
        "multiplier": 1,
        "messages": 0,
        "time_in_voice": 0,
        "voice_rumbiks": 0,
        "chat_rumbicks": 0,
        "total_rumbicks": 0,
        "wasted_rumbiks": 0,
        "opened_cases": 0,
        "bumps": 0,
        "mutes": 0,
        "unmutes": 0,
        "case": 0,
        "warns": 0,
        "unwarns": 0,
        "bans": 0,
        "unbans": 0,
        "deals": 0,
        "commands_use": 0,
        "transfers": 0,
        "members_leave": 0,
        "members_join": 0,
        "activation_promos": 0,
        "rep_up": 0,
        "rep_down": 0,
        "reputation_count": 0
    }

    if collservers.count_documents({"_id": guild.id}) == 0:
        collservers.insert_one(server_values)


# Загружаем расширения из папки "cogs"
for file in os.listdir("./cogs"):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.{file[:-3]}")

try:
    bot.run(os.getenv('TOKEN'))
except disnake.errors.HTTPException:
    print("\n\n\nBLOCKED BY RATE LIMITS\nRESTARTING NOW\n\n\n")
    sys("python main.py")
    sys('kill 1')