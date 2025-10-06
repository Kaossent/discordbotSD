import time
from asyncio import tasks
import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from pymongo import MongoClient
from main import rules, get_rule_info, check_roles, collusers, collservers


class MuteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rules = rules

    def get_rule_info(self, причина):
        if причина in self.rules:
            reason = self.rules[str(причина)]
            return reason
        else:
            reason = причина
            return reason

    def format_duration(self, time_str):
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

    @commands.slash_command(name='mute', description='Запрещает писать в чат и подключаться к голосовым каналам участнику', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def mute(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member, время: str, причина='Не указана'):
        if inter.type == disnake.InteractionType.application_command:
            await inter.response.defer()

            try:
                причина = self.get_rule_info(причина)
                formatted_duration = self.format_duration(время)
                seconds = self.convert_to_seconds(время)
            except ValueError as e:
                await inter.send(f"Ошибка в конвертации.")
                return

            duration = timedelta(seconds=seconds)
            current_timestamp = int(datetime.now().timestamp() + seconds)
            await участник.timeout(duration=duration)
            collservers.update_one({"_id": inter.guild.id}, {"$inc": {"mutes": 1}},
                                   upsert=True)

            embed = disnake.Embed(
                description=f"Участнику {участник.mention} запрещенно писать в чат и подключаться к голосовым каналам на ``{formatted_duration}``\n Причина: **{причина}**.",
                colour=0xff8800,
                timestamp=datetime.now()
            )

            embed.set_author(name=f"{inter.author.display_name}",
                             icon_url=f"{inter.author.display_avatar.url}")

            embed.set_thumbnail(
                url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")

            embed.set_footer(text="Мут")
            try:
                await inter.edit_original_response(embed=embed)
            except:
                await inter.response.send_message(embed=embed)

            embed = disnake.Embed(title="ShadowDragons", url="https://discord.com/invite/KE3psXf",
                                  description="", color=0xff8800, timestamp=datetime.now())
            embed.set_author(name="Вы были замучены!", icon_url=inter.guild.icon.url)
            embed.set_thumbnail(
                url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")
            embed.add_field(name="",
                            value=f"Вам запрещенно писать в чат и подключаться к голосовым каналам на сервере **{inter.guild.name}**!",
                            inline=False)
            embed.add_field(name="Модератор:", value=f"{inter.author.mention}", inline=False)
            embed.add_field(name="Причина:", value=причина, inline=False)
            embed.add_field(name="Истекает через:", value=f"{formatted_duration} (<t:{current_timestamp}:R>)", inline=False)
            embed.add_field(name="Подать апелляцию:", value=f"<#1044571685900259389>", inline=False)
            embed.set_footer(text="Пожалуйста, будьте внимательны!")
            try:
                await участник.send(embed=embed)
            except:
                pass

            channel = await self.bot.fetch_channel(944562833901899827)  # Ищем канал по id #логи

            embed = disnake.Embed(title="", url="",
                                  description="", color=0xff8800, timestamp=datetime.now())
            embed.add_field(name="", value=f"Участник {участник.name} ({участник.mention}) был замучен!",
                            inline=False)
            embed.set_thumbnail(
                url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")
            embed.add_field(name="Модератор:", value=f"*{inter.author.name}* ({inter.author.mention})", inline=True)
            embed.add_field(name="Участник:", value=f"*{участник}* ({участник.mention})", inline=True)
            embed.add_field(name="Канал:", value=f"{inter.channel.mention}", inline=True)
            embed.add_field(name="Время:", value=f"{formatted_duration} (<t:{current_timestamp}:R>)", inline=True)
            embed.add_field(name="Причина:", value=причина, inline=True)
            embed.set_footer(text=f"ID участника: {участник.id}")
            await channel.send(embed=embed)

    @commands.slash_command(name='unmute', description='Снимает запрет писать в чат и подключаться к голосовым каналам у участника', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def unmute(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member):
        if inter.type == disnake.InteractionType.application_command:
            await inter.response.defer()

            # Проверяем, есть ли у участника действующий mute (timeout)
            if участник.timeout is None:
                await inter.send(f"Участник {участник.mention} не находится в мьюте.", ephemeral=True)
                return

            # Снимаем тайм-аут с участника
            await участник.timeout(duration=None)
            collservers.update_one({"_id": inter.guild.id}, {"$inc": {"unmutes": 1}},
                                   upsert=True)

            # Создание embed для уведомления о разбане в чате
            embed = disnake.Embed(
                description=f"Участнику {участник.mention} разрешено писать в чат и подключаться к голосовым каналам.",
                colour=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=f"{inter.author.display_name}", icon_url=f"{inter.author.display_avatar.url}")
            embed.set_thumbnail(url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")
            embed.set_footer(text="Размут")

            try:
                await inter.edit_original_response(embed=embed)
            except:
                await inter.response.send_message(embed=embed)

            # Отправляем сообщение участнику в ЛС
            embed = disnake.Embed(title="ShadowDragons", url="https://discord.com/invite/KE3psXf",
                                  description="", color=0x00ff00, timestamp=datetime.now())
            embed.set_author(name="Вы были размучены!", icon_url=inter.guild.icon.url)
            embed.set_thumbnail(url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")
            embed.add_field(name="", value=f"Вам снова разрешено писать в чат и подключаться к голосовым каналам на сервере **{inter.guild.name}**!", inline=False)
            embed.add_field(name="Модератор:", value=f"{inter.author.mention}", inline=False)
            embed.set_footer(text="Пожалуйста, соблюдайте правила сервера!")
            try:
                await участник.send(embed=embed)
            except:
                pass

            # Логирование действия размута в канал логов
            channel = await self.bot.fetch_channel(944562833901899827)  # Канал для логов
            embed = disnake.Embed(title="", url="",
                                  description="", color=0x00ff00, timestamp=datetime.now())
            embed.add_field(name="", value=f"Участник {участник.name} ({участник.mention}) был размучен!", inline=False)
            embed.set_thumbnail(url="https://media4.giphy.com/media/4A2MFWNlGaGUJcyhlE/giphy.gif")
            embed.add_field(name="Модератор:", value=f"*{inter.author.name}* ({inter.author.mention})", inline=True)
            embed.add_field(name="Участник:", value=f"*{участник}* ({участник.mention})", inline=True)
            embed.add_field(name="Канал:", value=f"{inter.channel.mention}", inline=True)
            embed.set_footer(text=f"ID участника: {участник.id}")
            await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(MuteCog(bot))
    print("MuteCog is ready")