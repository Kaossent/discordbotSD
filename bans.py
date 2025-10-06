import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from pymongo import MongoClient
from main import get_rule_info, check_roles  # список правил
from main import cluster

collusers = cluster.server.users
collservers = cluster.server.servers

class BansCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_ban.start()

    def get_rule_info(self, причина):
        return get_rule_info(причина)

    @tasks.loop(seconds=300)
    async def check_ban(self):
        current_timestamp = int(datetime.now().timestamp())
        expired_roles = collusers.find({"ban_timestamp": {"$lte": current_timestamp}})

        for user_data in expired_roles:
            try:
                guild_id = user_data["guild_id"]
                guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
                member_id = user_data["id"]
                if collusers.find_one({'id': member_id, 'guild_id': guild_id})["ban"] == "True":
                    member = guild.get_member(member_id) or await guild.fetch_member(member_id)
                    role = guild.get_role(1229075137374978119)
                    if role in member.roles:
                        await member.remove_roles(role)
                        collusers.update_one({"id": member_id, "guild_id": guild_id}, {"$set": {'ban_timestamp': 0, 'ban': 'False', 'ban_reason': None}})
                        embed = disnake.Embed(
                            title="ShadowDragons",
                            url="https://discord.com/invite/KE3psXf",
                            description="",
                            color=0x00ff40
                        )
                        embed.set_author(name='Вы были разблокированы!', icon_url=guild.icon.url)
                        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
                        embed.add_field(
                            name="",
                            value="Срок Вашего бана истёк!",
                            inline=False
                        )
                        embed.set_footer(text="Больше не нарушайте!")

                        if member:
                            await member.send(embed=embed)

                        channel = await self.bot.fetch_channel(944562833901899827)  # Ищем канал по id #логи
                        участник = await self.bot.fetch_user(member_id)
                        embed = disnake.Embed(title="Участник был разбанен!",
                                            description=f"Срок бана участника **{участник}** ({участник.mention}) истек!",
                                            colour=0x00ff40,
                                            timestamp=datetime.now())
                        embed.set_author(name='Участник разблокирован')
                        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
                        embed.set_footer(text="Разбан")
                        await channel.send(embed=embed)
            except:
                pass

    @check_ban.before_loop
    async def before_check_warns(self):
        await self.bot.wait_until_ready()

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
            raise ValueError(f"Invalid time unit: {unit}")

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
            raise ValueError(f"Invalid time unit: {unit}")

    @commands.slash_command(name="ban", description="Блокирует доступ к серверу", contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def ban(self, inter: disnake.GuildCommandInteraction, участник: disnake.Member, длительность: str, причина="Не указана"):
        if inter.type == disnake.InteractionType.application_command:
            await inter.response.defer()
            причина = self.get_rule_info(причина)

            try:
                formatted_duration = self.format_duration(длительность)
                value = self.convert_to_seconds(длительность)
            except ValueError as e:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка',
                                value=f'Ошибка: {e}\n Длительность указывается в:\n ``д/d-дни, ч/h-часы, м/m-минуты, с/s-секунды``')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text='Ошибка')
                await inter.response.send_message(embed=embed, ephemeral=True)
                return

            role = inter.guild.get_role(1229075137374978119)
            channel = inter.guild.get_channel(1042818334644768871)
            current_timestamp = int(datetime.now().timestamp() + value)
            cur = int(datetime.now().timestamp())

            query = {'id': участник.id, 'guild_id': inter.guild.id}
            update = {'$set': {'ban': 'True', 'ban_timestamp': current_timestamp, 'ban_reason': причина}}

            collusers.update_one(query, update)
            collservers.update_one({"_id": inter.guild.id}, {"$inc": {"bans": 1}},
                                   upsert=True)

            if участник.voice is not None and участник.voice.channel is not None:
                await участник.move_to(None)

            await участник.add_roles(role, reason=причина)
            embed = disnake.Embed(
                description=f"Участник {участник.mention} был забанен на ``{formatted_duration}``\n Причина: **{причина}**.",
                colour=0xff0000,
                timestamp=datetime.now())
            embed.set_author(name=f"{inter.author.display_name}", icon_url=f"{inter.author.display_avatar.url}")
            embed.set_thumbnail(
                url="https://media1.giphy.com/media/tMf6IV7q9m3pbKPybv/giphy.gif?cid=6c09b952x9el5v0keemitb9f7pe09b04fetyq2ft84dhizs1&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=s")
            embed.set_footer(text="Бан")
            try:
                await inter.edit_original_response(embed=embed)
            except:
                await inter.response.send_message(embed=embed)

        embed = disnake.Embed(title="ShadowDragons", url="https://discord.com/invite/KE3psXf",
                              description="", color=0xff0000, timestamp=datetime.now())
        embed.set_author(name="Вы были заблокированы!", icon_url=inter.guild.icon.url)
        embed.set_thumbnail(url="https://media1.giphy.com/media/tMf6IV7q9m3pbKPybv/giphy.gif?cid=6c09b952x9el5v0keemitb9f7pe09b04fetyq2ft84dhizs1&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=s")
        embed.add_field(name="", value=f"Вы были забанены на сервере **{inter.guild.name}**!",
                        inline=False)
        embed.add_field(name="Модератор:", value=f"{inter.author.mention}", inline=False)
        embed.add_field(name="Причина:", value=причина, inline=False)
        embed.add_field(name="Истекает через:", value=f"<t:{current_timestamp}:R>", inline=False)
        embed.add_field(name="Подать апелляцию:", value=f"<#1044571685900259389>", inline=False)
        embed.set_footer(text="Пожалуйста, будьте внимательны!")
        await участник.send(embed=embed)

        channel = await self.bot.fetch_channel(944562833901899827)  # Ищем канал по id #логи

        embed = disnake.Embed(title="", url="",
                              description="", color=0xff0000, timestamp=datetime.now())
        embed.add_field(name="", value=f"Участник {участник.name} ({участник.mention}) был забанен!",
                        inline=False)
        embed.set_thumbnail(url="https://media1.giphy.com/media/tMf6IV7q9m3pbKPybv/giphy.gif?cid=6c09b952x9el5v0keemitb9f7pe09b04fetyq2ft84dhizs1&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=s")
        embed.add_field(name="Модератор:", value=f"*{inter.author.name}* ({inter.author.mention})", inline=True)
        embed.add_field(name="Участник:", value=f"*{участник}* ({участник.mention})", inline=True)
        embed.add_field(name="Канал:", value=f"{inter.channel.mention}", inline=True)
        embed.add_field(name="Время:", value=f"{formatted_duration} (<t:{current_timestamp}:R>)", inline=True)
        embed.add_field(name="Причина:", value=причина, inline=True)
        embed.set_footer(text=f"ID участника: {участник.id}")
        await channel.send(embed=embed)

    @commands.slash_command(name='unban', description='Позволяет снять блокировку с пользователя.', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def unban(self, inter: disnake.GuildCommandInteraction, участник: disnake.Member):
        if inter.type == disnake.InteractionType.application_command:
            await inter.response.defer()
            bans = collusers.find_one({'id': участник.id, 'guild_id': inter.guild.id})['ban']
            if bans == 'False':
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка',
                                value=f'Участник сервера **{участник.mention}** не находится в блокировке.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                try:
                        await inter.edit_original_response(embed=embed)
                except:
                    await inter.response.send_message(embed=embed, ephemeral=True)
                return

        query = {'id': участник.id, 'guild_id': inter.guild.id}
        task = {'$set': {'ban': False, 'ban_timestamp': 0, 'ban_reason': None}}
        collusers.update_one(query, task)
        collservers.update_one({"_id": inter.guild.id}, {"$inc": {"unbans": 1}},
                               upsert=True)
        await участник.remove_roles(inter.guild.get_role(1229075137374978119))
        embed = disnake.Embed(
            description=f"Участник {участник.mention} был разбанен.",
            colour=0x00ff40,
            timestamp=datetime.now())
        embed.set_author(name=f"{inter.author.display_name}", icon_url=f"{inter.author.display_avatar.url}")
        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
        embed.set_footer(text="Разбан")
        await inter.edit_original_response(embed=embed)

        embed = disnake.Embed(title="ShadowDragons",
                              url="https://discord.com/invite/KE3psXf",
                              description="",
                              colour=0x00ff40,
                              timestamp=datetime.now())
        embed.set_author(name="Вы были разбанены!",icon_url=inter.guild.icon.url)
        embed.add_field(name="",
                        value=f"Блокировка на сервере **{inter.guild.name}** была снята\n **Модератором**: {inter.author.mention}!",
                        inline=False)
        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
        embed.set_footer(text="Приносим извинения за предоствленые неудобства!")

        await участник.send(embed=embed)

        channel = await self.bot.fetch_channel(944562833901899827)  # Ищем канал по id #логи

        embed = disnake.Embed(title="", url="",
                              description="", color=0x00ff40, timestamp=datetime.now())
        embed.add_field(name="", value=f"Участник {участник.name} ({участник.mention}) был разбанен!",
                        inline=False)
        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
        embed.add_field(name="Модератор:", value=f"*{inter.author.name}* ({inter.author.mention})", inline=True)
        embed.add_field(name="Участник:", value=f"*{участник}* ({участник.mention})", inline=True)
        embed.add_field(name="Канал:", value=f"{inter.channel.mention}", inline=True)
        embed.set_footer(text=f"ID участника: {участник.id}")
        await channel.send(embed=embed)

    @commands.slash_command(name="bans", description="Показывает список забаненных участников и время до разбана")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def bans(self, inter: disnake.GuildCommandInteraction):
        await inter.response.defer(ephemeral=True)

        # Получаем список забаненных участников из базы данных
        banned_users = list(collusers.find({'ban': 'True', 'guild_id': inter.guild.id}))

        # Проверяем, есть ли забаненные участники
        if not banned_users:
            embed = disnake.Embed(description="На данный момент нет забаненных участников.", color=0xff0000)
            embed.set_footer(text="Список грешников пуст", icon_url=inter.guild.icon.url)
            embed.set_thumbnail(
                url="https://media1.giphy.com/media/tMf6IV7q9m3pbKPybv/giphy.gif?cid=6c09b952x9el5v0keemitb9f7pe09b04fetyq2ft84dhizs1&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=s")
            await inter.edit_original_response(embed=embed)
            return

        embed = disnake.Embed(title="Забаненные участники", color=0xff0000, timestamp=datetime.now())
        embed.set_thumbnail(
            url="https://media1.giphy.com/media/tMf6IV7q9m3pbKPybv/giphy.gif?cid=6c09b952x9el5v0keemitb9f7pe09b04fetyq2ft84dhizs1&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=s")
        embed.set_footer(text="Список грешников", icon_url=inter.guild.icon.url)

        # Счетчик для нумерации участников
        count = 1

        # Проходим по каждому забаненному участнику и добавляем его в embed
        for user in banned_users:
            member = inter.guild.get_member(user['id'])
            if member is None:
                continue

            ban_timestamp = user.get('ban_timestamp', 0)
            remaining_time = ban_timestamp - int(datetime.now().timestamp())
            if remaining_time <= 0:
                # Если срок бана истек, снимаем бан и обновляем информацию в базе
                await member.remove_roles(disnake.utils.get(inter.guild.roles, id=1229075137374978119))  # роль бана
                collusers.update_one({'id': user['id'], 'guild_id': inter.guild.id},
                                     {'$unset': {'ban': "", 'ban_timestamp': "", 'ban_reason': ""}})
                continue

            # Формируем строку с оставшимся временем
            remaining = f"<t:{ban_timestamp}:R>"
            reason = user.get('ban_reason', 'Не указана')

            embed.add_field(name=f"",
                            value=f"``{count}.`` **{member.display_name}** ({member.mention})\n"
                                  f"Причина: ``{reason}``\nИстекает: {remaining}",
                            inline=False)

            # Увеличиваем счетчик
            count += 1

        if len(embed.fields) == 0:
            embed.description = "Все забаненные участники были разбанены."

        await inter.edit_original_response(embed=embed)


def setup(bot):
    bot.add_cog(BansCog(bot))
    print("BansCog is ready")
