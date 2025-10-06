import time
from asyncio import tasks
import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from pymongo import MongoClient
from main import cluster, check_roles, format_duration, convert_to_seconds
from .economy import format_time
from disnake import Interaction
import asyncio
import aiohttp
from googletrans import Translator

current_datetime = datetime.today()

collusers = cluster.server.users
collservers = cluster.server.servers
collbans = cluster.server.bans
collpromos = cluster.server.promos

whitelisted_guild_id = 489867322039992320  # ID сервера, который бот должен оставить

emoji = "<a:rumbick:1271085088142262303>"
boost_emoji = "<a:rainbowboost:1326163578193186926>"
boost_emoji2 = "<a:nitroboost:1326162624412651560>"
staff_emoji = "<:staff:1328823175965966336>"
person_emoji = "<:Person:1328819605032009730>"
bot_emoji = "<:bot:1328825270664171593>"
join_emoji = "<:join:1328819575718154250>"
left_emoji = "<:leave:1328819591790596230>"
members_emoji = "<:members:1328819564741398600>"
channel_category = "<:channel_category:1328819541488439306>"
channel_voice = "<:channel_voice:1328819529509240893>"
channel_text = "<:channel_text:1328819519602430003>"
channel_stage = "<:channel_stage:1328819504939143188>"
channels_and_roles = "<:Channels_And_Roles:1328819492519936041>"
card_emoji = "<:CreditCard:1328819415407530016>"
transfer_emoji = "<:transfer:1328819434441412629>"
booster_emoji = "<:booster_orange:1328819470776406119>"
animated_emoji = "<a:jeb_spinning:1328819481278943242>"
mute_emoji = "<:mute:1328819360378261618>"
unmute_emoji = "<:unmute:1328819328124194846>"
ban_emoji = "<:ban:1328819339842818128>"
unban_emoji = "<:unban:1328819350899265676>"
warn_emoji = "<:warn:1328819314421268480>"
case_emoji = "<a:case:1328819303474139166>"
omegabox_emoji = "<:omegabox:1328819287779049573>"
commands_emoji = "<:commands:1328819178919956562>"
moder_emoji = "<:moder:1328823132617965650>"
cash_emoji = "<a:cash:1328819168505757829>"
nitro_emoji = "<:Nitro:1328819157697036308>"
pinknitro_emoji = "<:Pink_nitro:1328819148146479226>"
rubynitro_emoji = "<:Nitro_Ruby:1328819135169171497>"
ticket_emoji = "<:MegaPig_Ticket:1328819119273021520>"
rep_up_emoji = "<:rep_up:1234218072433365102>"
rep_down_emoji = "<:rep_down:1234218095116288154>"

async def get_joke():
    url = "https://official-joke-api.appspot.com/random_joke"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                joke_data = await response.json()
                joke = f"{joke_data['setup']} {joke_data['punchline']}"

                # Перевод с помощью Google Translate (с использованием await)
                translator = Translator()
                joke_translated = await translator.translate(joke, src='en', dest='ru')  # Используем await

                return joke_translated.text  # Доступ к переведенному тексту
            return "Не удалось получить шутку. Попробуйте позже."

class ReplyView(disnake.ui.View):
    def __init__(self, sender: disnake.User):
        super().__init__(timeout=None)
        self.sender = sender  # Пользователь, которому пересылаем ответ

    @disnake.ui.button(label="Ответить", style=disnake.ButtonStyle.primary)
    async def reply_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.send_modal(ReplyModal(self.sender))

class ReplyModal(disnake.ui.Modal):
    def __init__(self, sender: disnake.User):
        components = [disnake.ui.TextInput(label="Введите ответ", custom_id="reply_text",
                                           style=disnake.TextInputStyle.paragraph)]
        super().__init__(title="Ответ", custom_id="reply_modal", components=components)
        self.sender = sender

    async def callback(self, interaction: disnake.ModalInteraction):
        text = interaction.text_values["reply_text"]
        embed = disnake.Embed(description=text, color=disnake.Color.blue())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

        try:
            await self.sender.send(embed=embed, view=ReplyView(interaction.user))
            await interaction.response.send_message("✅ Ответ отправлен!", ephemeral=True)
        except disnake.Forbidden:
            await interaction.response.send_message(
                "❌ Не удалось отправить сообщение. Возможно, у пользователя закрыты ЛС.", ephemeral=True)
class ServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_server_info.start()

    @commands.slash_command(name="servers-leave", description="Покинуть все серверы, кроме основного")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin")
    async def leave_all(self, interaction: disnake.ApplicationCommandInteraction):
        # Проверка, что команду вызывает пользователь с правами администратора
        if not interaction.author.guild_permissions.administrator:
            await interaction.response.send_message("У вас нет прав для выполнения этой команды.", ephemeral=True)
            return

        # Перебираем все серверы, на которых находится бот
        for guild in self.bot.guilds:
            if guild.id != whitelisted_guild_id:
                try:
                    # Удаляем все данные, связанные с сервером в базе данных
                    await self.delete_server_data(guild.id)

                    await guild.leave()  # Покидаем сервер, если ID не совпадает с разрешенным
                    print(f"Бот покинул сервер {guild.name} ({guild.id})")
                except disnake.Forbidden:
                    print(f"Бот не может покинуть сервер {guild.name} ({guild.id}), недостаточно прав.")
                except disnake.HTTPException as e:
                    print(f"Ошибка при попытке покинуть сервер {guild.name} ({guild.id}): {e}")

        await interaction.response.send_message("Бот покинул все серверы, кроме разрешенного.", ephemeral=True)

    async def delete_server_data(self, guild_id: int):
        """
        Функция для удаления всех данных, связанных с сервером в базе данных.
        """
        try:
            # Удаляем пользователей, связанные с данным сервером
            collusers.delete_many({"guild_id": guild_id})

            # Удаляем настройки сервера
            collservers.delete_one({"guild_id": guild_id})

            # Удаляем баны, связанные с данным сервером
            collbans.delete_many({"guild_id": guild_id})

            # Удаляем промокоды, связанные с данным сервером
            collpromos.delete_many({"guild_id": guild_id})

            print(f"Все данные для сервера {guild_id} успешно удалены из базы данных.")
        except Exception as e:
            print(f"Ошибка при удалении данных для сервера {guild_id}: {e}")



    @commands.slash_command(name='server-info', description="Показать информацию о сервере")
    async def server_info(self, inter: disnake.ApplicationCommandInteraction):
        guild = inter.guild
        guild_id = guild.id
        emoji = "<a:rumbick:1271085088142262303>"
        # Сбор данных из базы
        server_data = collservers.find_one({"_id": guild_id})
        server_data_promos = collpromos.find_one({"_id": guild_id})
        if not server_data:
            await inter.response.send_message("Данные о сервере отсутствуют в базе.", ephemeral=True)
            return

        # Сбор данных о сервере
        owner = guild.owner
        total_members = guild.member_count
        bots = len([member for member in guild.members if member.bot])
        humans = total_members - bots
        roles = len(guild.roles)
        channels = len(guild.channels)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        stage_channels = len(guild.stage_channels)
        categories = len(guild.categories)
        emojis = len(guild.emojis)
        static_emojis = len([emoji for emoji in guild.emojis if not emoji.animated])
        animated_emojis = len([emoji for emoji in guild.emojis if emoji.animated])
        boosts = guild.premium_subscription_count
        boost_tier = guild.premium_tier
        nitro_boosters = guild.premium_subscribers
        nitro_boosters_count = len(nitro_boosters)
        nitro_boosters_names = ", ".join(
            [member.mention for member in nitro_boosters]) if nitro_boosters else "Нет бустеров"
        created_at_timestamp = int(guild.created_at.timestamp())
        stickers = len(guild.stickers)

        # Форматирование данных из базы
        multiplier = server_data.get("multiplier", 1)
        opened_cases = server_data.get("opened_cases", 0)
        messages = server_data.get("messages", 0)
        bumps = server_data.get("bumps", 0)
        time_in_voice = format_time(server_data.get("time_in_voice", 0))
        voice_rumbiks = round(server_data.get("voice_rumbiks", 0), 2)
        chat_rumbicks = round(server_data.get("chat_rumbicks", 0), 2)
        total_rumbicks = round(server_data.get("total_rumbicks", 0), 2)
        mutes = server_data.get("mutes", 0)
        unmutes = server_data.get("unmutes", 0)
        bans = server_data.get("bans", 0)
        unbans = server_data.get("unbans", 0)
        warns = server_data.get("warns", 0)
        cases = server_data.get("case", 0)
        unwarns = server_data.get("unwarns", 0)
        deals = server_data.get("deals", 0)
        transfers = server_data.get("transfers", 0)
        wasted_rumbiks = round(server_data.get("wasted_rumbiks", 0), 2)
        members_join = server_data.get("members_join", 0)
        members_leave = server_data.get("members_leave", 0)
        commands_use = server_data.get("commands_use", 0)
        activation_promos = server_data.get("activation_promos", 0)
        created_promos = server_data_promos.get("counter", 0)
        rep_down = server_data.get("rep_down", 0)
        rep_up = server_data.get("rep_up", 0)
        rep_count = server_data.get("reputation_count", 0)

        # Роли для Staff сервера
        staff_roles = {
            "Администратор": 518505773022838797,
            "Гл. Модер": 580790278697254913,
            "Модер": 702593498901381184,
            "Разработчик": 1229337640839413813,
        }

        staff_info = ""
        for role_name, role_id in staff_roles.items():
            role = guild.get_role(role_id)
            if role:
                members_with_role = [member.mention for member in role.members]
                members_list = ", ".join(members_with_role) if members_with_role else "Никого"
                staff_info += f"**{role.mention}:** {members_list}\n"
            else:
                staff_info += f"**{role_name}:** Роль не найдена\n"

        # Формирование Embed
        embed = disnake.Embed(
            title=f"Информация о сервере: {guild.name}",
            color=disnake.Color.blurple(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"ID сервера: {guild.id}")
        embed.set_author(name=f"{guild.name}",
                         icon_url=f"https://media0.giphy.com/media/epyCv3K3uvRXw4LaPY/giphy.gif")

        embed.add_field(name="🌟 Основная информация:", value=(
            f"👑 **Владелец:** {owner.mention if owner else 'Неизвестно'}\n"
            f"📅 **Дата создания:** <t:{created_at_timestamp}:F>\n"
            f"{boost_emoji} **Уровень бустов:** {boost_tier}\n"
            f"{boost_emoji2} **Количество бустов:** {boosts}"
        ), inline=False)

        # Добавление информации о Staff
        embed.add_field(name=f"{staff_emoji} Staff сервера:", value=staff_info or "Нет информации", inline=False)

        embed.add_field(name="👥 Участники:", value=(
            f"{members_emoji} **Всего:** {total_members}\n"
            f"{person_emoji} **Люди:** {humans}\n"
            f"{bot_emoji} **Боты:** {bots}\n"
            f"{join_emoji} **Присоединились:** {members_join}\n"
            f"{left_emoji} **Покинули:** {members_leave}"
        ), inline=True)

        embed.add_field(name=f"{nitro_emoji} Nitro-бустеры:", value=(
            f"{pinknitro_emoji} **Количество:** {nitro_boosters_count}\n"
            f"{rubynitro_emoji} **Список:** {nitro_boosters_names}"
        ), inline=True)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name="💬 Каналы:", value=(
            f"{channels_and_roles} **Всего:** {channels}\n"
            f"{channel_text} **Текстовые:** {text_channels}\n"
            f"{channel_voice} **Голосовые:** {voice_channels}\n"
            f"{channel_stage} **Сценические:** {stage_channels}\n"
            f"{channel_category} **Категории:** {categories}"
        ), inline=True)
        embed.add_field(name="🎨 Персонализация:", value=(
            f"🤔 **Статичные эмодзи:** {static_emojis}\n"
            f"{animated_emoji} **Анимированные эмодзи:** {animated_emojis}\n"
            f"🤼 **Всего эмодзи:** {emojis}\n"
            f"🎭 **Всего ролей:** {roles}\n"
            f"🖼️ **Всего стикеров:** {stickers}"
        ), inline=True)

        embed.add_field(name='', value='', inline=False)
        # Статистика по румбикам
        embed.add_field(name=f"{emoji} Румбики:", value=(
            f"{booster_emoji} **Текущий множитель:** x{multiplier}\n"
            f"🎙️ **За голосовые:** {voice_rumbiks}\n"
            f"💬 **За текстовые:** {chat_rumbicks}\n"
            f"{cash_emoji} **Всего:** {total_rumbicks}\n"
            f"{card_emoji} **Потрачено:** {wasted_rumbiks}\n"
            f"🤝 ** Сделок совершено:** {deals}\n"
            f"{transfer_emoji} **Переводов совершено:** {transfers}"
        ), inline=True)

        # Статистика по мутам и банам
        embed.add_field(name=f"{moder_emoji} Модерация:", value=(
            f"{mute_emoji} **Муты:** {mutes}\n"
            f"{unmute_emoji} **Размуты:** {unmutes}\n"
            f"{ban_emoji} **Баны:** {bans}\n"
            f"{unban_emoji} **Разбаны:** {unbans}\n"
            f"{warn_emoji} **Предупреждения:** {warns}\n"
            f"{case_emoji} **Случаи:** {cases}\n"
            f"✅ **Снято предупреждений:** {unwarns}"
        ), inline=True)

        # Статистика по использованию команд
        embed.add_field(name="🛠️ Остальное:", value=f"{commands_emoji} **Команд использовано:** {commands_use}\n"
                                                    f"📝 **Всего сообщений:** {messages}\n"
                                                    f"🆙 **Всего Бампов:** {bumps}\n"
                                                    f"{omegabox_emoji} **Всего открыто ящиков:** {opened_cases}\n"
                                                    f"🎟️ **Создано промокодов:** {created_promos}\n"
                                                    f"{ticket_emoji} **Активировано промокодов:** {activation_promos}\n"
                                                    f"{rep_up_emoji} **Количество положительной репутации:** {rep_up}\n"
                                                    f"{rep_down_emoji} **Количество отрицательной репутации:** {rep_down}\n"
                                                    f"🌟 **Общее количество репутации:** {rep_count}\n"
                                                    f"🎤 **Общаяя голосовая статистика:** ``{time_in_voice}``",
                        inline=False)

        # Отправка Embed
        await inter.response.send_message(embed=embed, ephemeral=True)
    @tasks.loop(hours=1)
    async def update_server_info(self):
        guild = self.bot.get_guild(489867322039992320)
        guild_id = 489867322039992320
        channel = guild.get_channel(1069201052303380511)
        message = await channel.fetch_message(1329068901375541248)
        server_data = collservers.find_one({"_id": guild_id})
        server_data_promos = collpromos.find_one({"_id": guild_id})
        emoji = "<a:rumbick:1271085088142262303>"
        # Сбор данных о сервере
        owner = guild.owner
        total_members = guild.member_count
        bots = len([member for member in guild.members if member.bot])
        humans = total_members - bots
        roles = len(guild.roles)
        channels = len(guild.channels)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        stage_channels = len(guild.stage_channels)
        categories = len(guild.categories)
        emojis = len(guild.emojis)
        static_emojis = len([emoji for emoji in guild.emojis if not emoji.animated])
        animated_emojis = len([emoji for emoji in guild.emojis if emoji.animated])
        boosts = guild.premium_subscription_count
        boost_tier = guild.premium_tier
        nitro_boosters = guild.premium_subscribers
        nitro_boosters_count = len(nitro_boosters)
        nitro_boosters_names = ", ".join(
            [member.mention for member in nitro_boosters]) if nitro_boosters else "Нет бустеров"
        created_at_timestamp = int(guild.created_at.timestamp())
        stickers = len(guild.stickers)

        # Форматирование данных из базы
        multiplier = server_data.get("multiplier", 1)
        opened_cases = server_data.get("opened_cases", 0)
        messages = server_data.get("messages", 0)
        bumps = server_data.get("bumps", 0)
        time_in_voice = format_time(server_data.get("time_in_voice", 0))
        voice_rumbiks = round(server_data.get("voice_rumbiks", 0), 2)
        chat_rumbicks = round(server_data.get("chat_rumbicks", 0), 2)
        total_rumbicks = round(server_data.get("total_rumbicks", 0), 2)
        mutes = server_data.get("mutes", 0)
        unmutes = server_data.get("unmutes", 0)
        bans = server_data.get("bans", 0)
        unbans = server_data.get("unbans", 0)
        warns = server_data.get("warns", 0)
        cases = server_data.get("case", 0)
        unwarns = server_data.get("unwarns", 0)
        deals = server_data.get("deals", 0)
        transfers = server_data.get("transfers", 0)
        wasted_rumbiks = round(server_data.get("wasted_rumbiks", 0), 2)
        members_join = server_data.get("members_join", 0)
        members_leave = server_data.get("members_leave", 0)
        commands_use = server_data.get("commands_use", 0)
        activation_promos = server_data.get("activation_promos", 0)
        created_promos = server_data_promos.get("counter", 0)
        rep_down = server_data.get("rep_down", 0)
        rep_up = server_data.get("rep_up", 0)
        rep_count = server_data.get("reputation_count", 0)

        # Роли для Staff сервера
        staff_roles = {
            "Администратор": 518505773022838797,
            "Гл. Модер": 580790278697254913,
            "Модер": 702593498901381184,
            "Разработчик": 1229337640839413813,
        }

        staff_info = ""
        for role_name, role_id in staff_roles.items():
            role = guild.get_role(role_id)
            if role:
                members_with_role = [member.mention for member in role.members]
                members_list = ", ".join(members_with_role) if members_with_role else "Никого"
                staff_info += f"**{role.mention}:** {members_list}\n"
            else:
                staff_info += f"**{role_name}:** Роль не найдена\n"

        # Формирование Embed
        embed = disnake.Embed(
            title=f"Информация о сервере: {guild.name}",
            color=disnake.Color.blurple(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Последнее обновление информации")
        embed.set_author(name=f"{guild.name}",
                         icon_url=f"https://media0.giphy.com/media/epyCv3K3uvRXw4LaPY/giphy.gif")

        embed.add_field(name="🌟 Основная информация:", value=(
            f"👑 **Владелец:** {owner.mention if owner else 'Неизвестно'}\n"
            f"📅 **Дата создания:** <t:{created_at_timestamp}:F>\n"
            f"{boost_emoji} **Уровень бустов:** {boost_tier}\n"
            f"{boost_emoji2} **Количество бустов:** {boosts}"
        ), inline=False)

        # Добавление информации о Staff
        embed.add_field(name=f"{staff_emoji} Staff сервера:", value=staff_info or "Нет информации", inline=False)

        embed.add_field(name="👥 Участники:", value=(
            f"{members_emoji} **Всего:** {total_members}\n"
            f"{person_emoji} **Люди:** {humans}\n"
            f"{bot_emoji} **Боты:** {bots}\n"
            f"{join_emoji} **Присоединились:** {members_join}\n"
            f"{left_emoji} **Покинули:** {members_leave}"
        ), inline=True)

        embed.add_field(name=f"{nitro_emoji} Nitro-бустеры:", value=(
            f"{pinknitro_emoji} **Количество:** {nitro_boosters_count}\n"
            f"{rubynitro_emoji} **Список:** {nitro_boosters_names}"
        ), inline=True)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name="💬 Каналы:", value=(
            f"{channels_and_roles} **Всего:** {channels}\n"
            f"{channel_text} **Текстовые:** {text_channels}\n"
            f"{channel_voice} **Голосовые:** {voice_channels}\n"
            f"{channel_stage} **Сценические:** {stage_channels}\n"
            f"{channel_category} **Категории:** {categories}"
        ), inline=True)
        embed.add_field(name="🎨 Персонализация:", value=(
            f"🤔 **Статичные эмодзи:** {static_emojis}\n"
            f"{animated_emoji} **Анимированные эмодзи:** {animated_emojis}\n"
            f"🤼 **Всего эмодзи:** {emojis}\n"
            f"🎭 **Всего ролей:** {roles}\n"
            f"🖼️ **Всего стикеров:** {stickers}"
        ), inline=True)

        embed.add_field(name='', value='', inline=False)
        # Статистика по румбикам
        embed.add_field(name=f"{emoji} Румбики:", value=(
            f"{booster_emoji} **Текущий множитель:** x{multiplier}\n"
            f"🎙️ **За голосовые:** {voice_rumbiks}\n"
            f"💬 **За текстовые:** {chat_rumbicks}\n"
            f"{cash_emoji} **Всего:** {total_rumbicks}\n"
            f"{card_emoji} **Потрачено:** {wasted_rumbiks}\n"
            f"🤝 ** Сделок совершено:** {deals}\n"
            f"{transfer_emoji} **Переводов совершено:** {transfers}"
        ), inline=True)

        # Статистика по мутам и банам
        embed.add_field(name=f"{moder_emoji} Модерация:", value=(
            f"{mute_emoji} **Муты:** {mutes}\n"
            f"{unmute_emoji} **Размуты:** {unmutes}\n"
            f"{ban_emoji} **Баны:** {bans}\n"
            f"{unban_emoji} **Разбаны:** {unbans}\n"
            f"{warn_emoji} **Предупреждения:** {warns}\n"
            f"{case_emoji} **Случаи:** {cases}\n"
            f"✅ **Снято предупреждений:** {unwarns}"
        ), inline=True)

        # Статистика по использованию команд
        embed.add_field(name="🛠️ Остальное:", value=f"{commands_emoji} **Команд использовано:** {commands_use}\n"
                                                    f"📝 **Всего сообщений:** {messages}\n"
                                                    f"🆙 **Всего Бампов:** {bumps}\n"
                                                    f"{omegabox_emoji} **Всего открыто ящиков:** {opened_cases}\n"
                                                    f"🎟️ **Создано промокодов:** {created_promos}\n"
                                                    f"{ticket_emoji} **Активировано промокодов:** {activation_promos}\n"
                                                    f"{rep_up_emoji} **Количество положительной репутации:** {rep_up}\n"
                                                    f"{rep_down_emoji} **Количество отрицательной репутации:** {rep_down}\n"
                                                    f"🌟 **Общее количество репутации:** {rep_count}\n"
                                                    f"🎤 **Общаяя голосовая статистика:** ``{time_in_voice}``",
                        inline=False)

        # Обновление сообщения
        await message.edit(embed=embed)


    @update_server_info.before_loop
    async def before_update_server_info(self):
        """
        Ожидаем, пока бот полностью не подключится, прежде чем запускать цикл.
        """
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(ServerCog(bot))
    print("ServerCog is ready")
