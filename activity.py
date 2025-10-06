import disnake
from pymongo import MongoClient, errors
from disnake.ext import commands, tasks
import os
import asyncio
import time
from disnake import RawReactionActionEvent
import datetime
import disnake
from datetime import datetime, timedelta
from main import cluster
import pytz

collusers = cluster.server.users
collservers = cluster.server.servers


def check_value(inter, guild):
    result = collusers.update_one(
        {"id": inter, "guild_id": guild, "settings": {"$exists": False}},
        {"$set": {}}
    )
    collusers.update_one(
        {"id": inter, "guild_id": guild},
        {"$set": {"settings.reputation_notification": True}})


class ActivityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_count = {}
        self.update_leaderboard.start()
        self.rep_up_id = 1234218072433365102
        self.rep_down_id = 1234218095116288154
        self.reaction_limit = 5  # Лимит реакций в день для каждого участника
        self.reset_reaction_count.start()

    @tasks.loop(seconds=3600)
    async def update_leaderboard(self):
        if self.message_count:
            top_user = max(self.message_count, key=self.message_count.get)  # по ключу в словаре ищем чела
            messages = self.message_count[top_user]
            if top_user == 'Никто':
                user = 'Никто'
            user = self.bot.get_user(top_user)
            user = user.mention
            self.message_count = {}  # Обнуляем словарь для статы
            self.message_count['Никто'] = 0
            guild = self.bot.get_guild(489867322039992320)
            channel = self.bot.get_channel(944562833901899827)
            tstamp = int(datetime.now().timestamp())
            embed = disnake.Embed(color=0xd800f5)
            embed.set_author(name='Самый активный', icon_url=guild.icon.url)
            embed.set_thumbnail(url="https://i.imgur.com/64ibjZo.gif")
            embed.add_field(name='Участник:', value=f'{user}', inline=True)
            embed.add_field(name='Количество сообщений:', value=f'{messages}', inline=True)
            embed.add_field(name='', value=f'<t:{tstamp - 3600}:t> - <t:{tstamp}:t>', inline=False)
            await channel.send(embed=embed)

    @commands.slash_command(name='topuser', description='Показывает самого активного участника за последний час', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def topuser(self, inter: disnake.ApplicationCommandInteraction):
        if inter.type == disnake.InteractionType.application_command:
            try:
                await inter.response.defer()
            except:
                return

            top_user = max(self.message_count, key=self.message_count.get)  # по ключу в словаре ищем чела
            messages = self.message_count[top_user]
            if top_user == 'Никто':
                user = 'Никто'
            user = self.bot.get_user(top_user)
            user = user.mention
            embed = disnake.Embed(color=0xd800f5)
            embed.set_author(name='Самый активный', icon_url=inter.guild.icon.url)
            embed.set_thumbnail(url="https://i.imgur.com/64ibjZo.gif")
            embed.add_field(name='Участник:', value=f'{user}', inline=True)
            embed.add_field(name='Количество сообщений:', value=f'{messages}', inline=True)
            try:
                await inter.edit_original_response(embed=embed)
            except:
                await inter.response.send_message(embed=embed, ephemeral=True)
        else:
            await inter.send('error')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.message_count:
            self.message_count[message.author.id] += 1
        else:
            self.message_count[message.author.id] = 1

    async def update_reputation(self, user_id, guild_id, amount):
        collusers.update_one(
            {"id": user_id, "guild_id": guild_id},
            {"$inc": {"reputation": amount}}
        )

    async def check_reaction_limit(self, user_id, guild_id):
        user_data = collusers.find_one({"id": user_id, "guild_id": guild_id})
        if not user_data:
            return False
        return user_data.get("reaction_count", 0) >= self.reaction_limit

    async def increment_reaction_count(self, user_id, guild_id):
        collusers.update_one(
            {"id": user_id, "guild_id": guild_id},
            {"$inc": {"reaction_count": 1}}
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        if payload.emoji.id not in [self.rep_up_id, self.rep_down_id]:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        author_id = message.author.id
        guild_id = payload.guild_id
        user_id = payload.user_id

        check_value(author_id, guild_id)

        if author_id == user_id:
            # Удалить реакцию, если пользователь пытается повысить/понизить репутацию самому себе
            await message.remove_reaction(payload.emoji, payload.member)
            return

        guild = self.bot.get_guild(guild_id)
        author = guild.get_member(author_id)
        user = guild.get_member(user_id)
        query = {"id": author_id, "guild_id": guild_id}

        projection = {'_id': 0, "settings.reputation_notification": 1}

        result = collusers.find_one(query, projection)
        if result:
            await author.send(f'вам добавили репутацию через сообщение {message.jump_url}')

        if await self.check_reaction_limit(user_id, guild_id):
            await message.remove_reaction(payload.emoji, payload.member)
            return

        await self.increment_reaction_count(user_id, guild_id)

        if payload.emoji.id == self.rep_up_id:
            # Увеличиваем репутацию на 1 и сохраняем, кто поставил реакцию
            await self.update_reputation(author_id, guild_id, 1)
            collusers.find_one_and_update({'id': author.id, 'guild_id': guild.id},
                                          {'$set': {'last_reputation': user.id}})
        elif payload.emoji.id == self.rep_down_id:
            # Уменьшаем репутацию на 1 и также сохраняем, кто поставил реакцию
            await self.update_reputation(author_id, guild_id, -1)
            collusers.find_one_and_update({'id': author.id, 'guild_id': guild.id},
                                          {'$set': {'last_reputation': user.id}})

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if payload.emoji.id not in [self.rep_up_id, self.rep_down_id]:
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        author_id = message.author.id
        guild_id = payload.guild_id
        user_id = payload.user_id
        guild = self.bot.get_guild(guild_id)
        user = guild.get_member(user_id)
        check_value(author_id, guild_id)
        user_reaction = guild.get_member(author_id)
        if author_id == user_id:
            # Если пользователь удаляет реакцию на своё собственное сообщение, ничего не делаем
            return

        query = {"id": author_id, "guild_id": guild_id}

        projection = {'_id': 0, "settings.reputation_notification": 1}

        result = collusers.find_one(query, projection)
        if result:
            await user_reaction.send(f'в@m понизили репутацию через сообщение {message.jump_url}')

        if await self.check_reaction_limit(user_id, guild_id):
            return

        if payload.emoji.id == self.rep_up_id:
            await self.update_reputation(author_id, guild_id, -1)
        elif payload.emoji.id == self.rep_down_id:
            await self.update_reputation(author_id, guild_id, 1)

    @tasks.loop(hours=1)
    async def reset_reaction_count(self):
        now = datetime.now(pytz.timezone('Europe/Kiev'))
        if now.hour == 0:
            collusers.update_many(
                {},
                {"$set": {"reaction_count": 0}}
            )
            print("Сброс 'Reaction counts' в 00:00 по Киеву")

    @commands.slash_command(name='reputation', description='Выводит репутацию участника', contexts=disnake.InteractionContextTypes(guild=True, bot_dm=False, private_channel=False))
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def reputation(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member = None):
        if disnake.InteractionResponse:
            await inter.response.defer(ephemeral=True)

        if участник is None:
            участник = inter.author

        # Get user reputation from the database
        user_data = collusers.find_one({'id': участник.id, 'guild_id': inter.guild.id})
        if not user_data:
            await inter.edit_original_message(content="Пользователь не найден в базе данных.")
            return

        rep = user_data.get('reputation', 0)  # Default to 0 if not found

        # Function to determine reputation title
        def get_reputation_title(reputation):
            if -9 <= reputation < 20:
                return "Нормальный"
            elif 20 <= reputation <= 49:
                return "Хороший"
            elif 50 <= reputation <= 99:
                return "Очень хороший"
            elif 100 <= reputation <= 159:
                return "Замечательный"
            elif 160 <= reputation <= 229:
                return "Прекрасный"
            elif 230 <= reputation <= 309:
                return "Уважаемый"
            elif 310 <= reputation <= 399:
                return "Потрясающий"
            elif reputation >= 400:
                return "Живая Легенда"
            elif -10 >= reputation >= -19:
                return "Сомнительный"
            elif -20 >= reputation >= -29:
                return "Плохой"
            elif -30 >= reputation >= -39:
                return "Очень плохой"
            elif -40 >= reputation >= -49:
                return "Ужасный"
            elif -50 >= reputation >= -59:
                return "Отвратительный"
            elif -60 >= reputation >= -79:
                return "Презираемый"
            elif -80 >= reputation >= -99:
                return "Изгой"
            elif reputation <= -100:
                return "Враг общества"
            else:
                return "Неизвестный"

        reputation_title = get_reputation_title(rep)

        # Determine last reputation giver
        if collusers.count_documents({'id': inter.author.id, 'guild_id': inter.guild.id}) == 1:
            last_rep_id = user_data.get('last_reputation', None)
            if last_rep_id:
                last_rep_member = inter.guild.get_member(last_rep_id)
                last_rep = last_rep_member.mention if last_rep_member else 'Неизвестный пользователь'
            else:
                last_rep = 'Нет'
        else:
            last_rep = 'Нет'

        # Determine embed color and emoji based on reputation
        if rep >= 0:
            embed_color = 0x1eff00  # Зеленый цвет для положительной репутации
            rep_emoji = "<:rep_up:1278690709855010856>"
        else:
            embed_color = 0xff0000  # Красный цвет для отрицательной репутации
            rep_emoji = "<:rep_down:1278690717652357201>"

        embed = disnake.Embed(
            title="Репутация пользователя",
            description=f"Информация о репутации {участник.mention}",
            color=embed_color,
        )
        embed.set_thumbnail(url=участник.display_avatar.url)
        embed.add_field(name="⭐ Репутация", value=f"{rep} {rep_emoji}", inline=True)
        embed.add_field(name="Титул", value=reputation_title, inline=True)
        embed.add_field(name="\u200B", value="\u200B")  # Пустое поле для разделения
        embed.add_field(
            name="Последнее изменение репутации от",
            value=f"⭐ {last_rep}",
            inline=False
        )
        embed.set_footer(text="Используйте эмодзи для управления репутацией", icon_url=inter.guild.icon.url)
        await inter.edit_original_message(embed=embed)


def setup(bot):
    bot.add_cog(ActivityCog(bot))
    print("ActivityCog is ready")
