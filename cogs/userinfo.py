import time
from asyncio import tasks
import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from pymongo import MongoClient
from datetime import datetime
from main import cluster
from .economy import format_time

current_datetime = datetime.today()

collusers = cluster.server.users
collservers = cluster.server.servers
collbans = cluster.server.bans
collpromos = cluster.server.promos

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
def check_value(inter):
    result = collusers.update_one(
        {"id": inter.author.id, "guild_id": inter.guild.id, "settings": {"$exists": False}},
        {"$set": {}}
    )
    collusers.update_one(
        {"id": inter.author.id, "guild_id": inter.guild.id, 'settings.reputation_notification': {"$exists": False}},
        {"$set": {"settings.reputation_notification": False}})


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name='user-info', description='Выводит основную информацию об участнике')
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def user(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member = None):
        if inter.type == disnake.InteractionType.application_command:
            try:
                await inter.response.defer(ephemeral=True)
            except Exception as e:
                print(f"Error deferring response: {e}")
                return

        if участник is None:
            участник = inter.author
            settings = True

        embed = disnake.Embed(title=f"Информация об участнике ``{участник.name}``:", url="",
                              description="", color=0x00b7ff, timestamp=datetime.now())
        embed.set_author(name=f"{участник.display_name}",
                         icon_url=f"https://media0.giphy.com/media/epyCv3K3uvRXw4LaPY/giphy.gif")
        embed.set_thumbnail(url=участник.avatar.url if участник.avatar else участник.default_avatar.url)

        def get_user_info(member):
            try:
                user_data = collusers.find_one({'id': member.id, 'guild_id': inter.guild.id})
                warns_count = user_data.get('warns', 0)
                if warns_count == 0:
                    warns_count = "Не имеется"
                ban = user_data.get('ban', 'False')
                ban = 'Заблокирован' if ban == 'True' else 'Не заблокирован'
                mute = 'Замучен' if member.current_timeout else 'Не замучен'
                highest_role = sorted(member.roles, key=lambda r: r.position, reverse=True)[0]
                registration_time = member.created_at
                join_time = member.joined_at
                temporary_roles = user_data.get('role_ids', [])
                number_of_roles = user_data.get('number_of_roles', 0)
                if number_of_roles == 0:
                    number_of_roles = 'Не имеется'
                message_count = user_data.get('message_count', 0)
                time_in_voice = user_data.get('time_in_voice', 0)
                balance = round(user_data.get('balance', 0), 2)
                number_of_deal = user_data.get('number_of_deal', 0)
                reputation = user_data.get('reputation', 0)
                bumps = user_data.get('bumps', 0)
                opened_cases = user_data.get('opened_cases', 0)
                promocodes = user_data.get('promocodes', 0)
                keys = user_data.get('keys', 0)

                return warns_count, ban, mute, highest_role, registration_time, join_time, temporary_roles, number_of_roles, message_count, time_in_voice, balance, number_of_deal, reputation, bumps, opened_cases, promocodes, keys
            except Exception as e:
                print(f"Error getting user info: {e}")
                return ('Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', 'Неизвестно', "Неизвестно")

        warns_count, ban, mute, highest_role, registration_time, join_time, temporary_roles, number_of_roles, message_count, time_in_voice, balance, number_of_deal, reputation, bumps, opened_cases, promocodes, keys = get_user_info(
            участник)

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

        reputation_title = get_reputation_title(reputation)

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

        formatted_total_time = format_time(time_in_voice)

        def format_minutes(minutes):
            if 11 <= minutes % 100 <= 19:
                return "минут"
            elif minutes % 10 == 1:
                return "минута"
            elif 2 <= minutes % 10 <= 4:
                return "минуты"
            else:
                return "минут"

        # Определение статуса пользователя
        status_dict = {
            disnake.Status.online: "<:ONLINE:1328819073764560956> ``В сети``",
            disnake.Status.offline: "<:OFFLINE:1328819062431547412> Не в сети",
            disnake.Status.idle: "<:IDLE:1328819089074032721> ``Неактивен``",
            disnake.Status.dnd: "<:DO_NOT_DISTURB:1328819105192607774> ``Не беспокоить``"
        }
        status = status_dict.get(участник.status, "Неизвестно")
        voice_channel = участник.voice.channel.mention if участник.voice and участник.voice.channel else "Не в голосовом канале"
        current_game = None
        for activity in участник.activities:
            if isinstance(activity, disnake.Game):
                current_game = activity.name
                break

        check_value(inter)
        query = {"id": inter.author.id, "guild_id": inter.guild_id}

        projection = {'_id': 0, "settings.reputation_notification": 1}

        result = collusers.find_one(query, projection)
        result = result["settings"]["reputation_notification"]
        print(result)
        if result:
            options = [
                disnake.SelectOption(label=f"🟢 Оповещение об изменении репутации",
                                     description="Оповещение об изменении репутации. Статус: 🟢", value="1"),
            ]
        else:
            options = [
                disnake.SelectOption(label=f"🔴 Оповещение об из менении репутации",
                                     description="Оповещение об изменении репутации. Статус: 🔴", value="1"),
            ]

        # Создаем select menu
        select_menu = disnake.ui.Select(
            placeholder="Поменять настройки...",
            min_values=1,
            max_values=1,
            options=options,
        )

        async def select_callback(interaction: disnake.MessageInteraction):
            await interaction.response.defer(ephemeral=True)
            result2 = collusers.find_one(query, projection)
            result2 = result2["settings"]["reputation_notification"]
            if select_menu.values[0] == "1":
                if interaction.author.id != inter.author.id:
                    await interaction.followup.send('проверка на долбоеба не пройдена', ephemeral=True)
                if result2:
                    collusers.update_one(
                        {"id": interaction.author.id, "guild_id": interaction.guild.id},
                        {"$set": {"settings.reputation_notification": False}})
                    await interaction.followup.send('вы изменили настройку (выключено)', ephemeral=True)
                else:
                    collusers.update_one(
                        {"id": interaction.author.id, "guild_id": interaction.guild.id},
                        {"$set": {"settings.reputation_notification": True}})
                    await interaction.followup.send('вы изменили настройку (включено)', ephemeral=True)


                result1 = collusers.find_one(query, projection)
                result1 = result1["settings"]["reputation_notification"]

                if result1:
                    options1 = [
                        disnake.SelectOption(label=f"🟢 Оповещение об изменении репутации",
                                             description="Оповещение об изменении репутации. Статус: 🟢", value="1"),
                    ]
                else:
                    options1 = [
                        disnake.SelectOption(label=f"🔴 Оповещение об из менении репутации",
                                             description="Оповещение об изменении репутации. Статус: 🔴", value="1"),
                    ]

                # Создаем select menu
                select_menu1 = disnake.ui.Select(
                    placeholder="Поменять настройки...",
                    min_values=1,
                    max_values=1,
                    options=options1,
                )

                select_menu1.callback = select_callback

                # Создаем view и добавляем в него select menu
                view1 = disnake.ui.View()
                view1.add_item(select_menu1)

                await inter.edit_original_response(embed=embed, view=view1)

        try:
            embed.add_field(name=f'',
                            value=f'**Основная роль:** {highest_role.mention if highest_role else "``Неизвестно``"}',
                            inline=False)
            embed.add_field(name=f'', value=f'**👁️‍🗨️ Статус:** {status}', inline=False)
            if участник.voice and участник.voice.channel:
                embed.add_field(name=f'',
                                value=f'**🔊️ Голосовой канал:** {voice_channel}', inline=False)
            if current_game:
                embed.add_field(name=f'', value=f'**🎮 Играет в:** ``{current_game}``', inline=False)
            embed.add_field(name=f'',
                            value=f'**🌍 Зарегистрирован:\n** <t:{int(registration_time.timestamp())}:F> (<t:{int(registration_time.timestamp())}:R>)',
                            inline=True)
            embed.add_field(name=f'',
                            value=f'**🌎 Присоединился:\n** <t:{int(join_time.timestamp())}:F> (<t:{int(join_time.timestamp())}:R>)',
                            inline=True)
            embed.add_field(name='', value='', inline=False)
            if reputation >= 0:
                rep_emoji = "<:rep_up:1234218072433365102>"
            else:
                rep_emoji = "<:rep_down:1234218095116288154>"
            embed.add_field(name=f'', value=f'**⭐ Репутация:** ``{reputation}`` {rep_emoji} - ``{reputation_title}``',
                            inline=False)
            embed.add_field(name=f'', value=f'**🖊️ Сообщений:\n** ``{message_count}``', inline=True)
            embed.add_field(name=f'',
                            value=f'**🎤 Голосовая активность:\n** ``{formatted_total_time}``',
                            inline=True)
            embed.add_field(name='', value='', inline=False)
            embed.add_field(name=f'', value=f'**💸 Баланс:** ``{balance}``{emoji}', inline=True)
            embed.add_field(name=f'', value=f'**💼 Сделок:** ``{number_of_deal}``', inline=True)
            embed.add_field(name='', value='', inline=False)
            embed.add_field(name=f'', value=f'{ticket_emoji} **Промокодов:** ``{promocodes}``', inline=True)
            embed.add_field(name=f'', value=f'🆙 **Бампов:** ``{bumps}``', inline=True)
            embed.add_field(name='', value='', inline=False)
            embed.add_field(name=f'', value=f'🔑 **Ключей:** ``{keys}``', inline=True)
            embed.add_field(name=f'', value=f'{omegabox_emoji} **Открыто якщиков:** ``{opened_cases}``', inline=True)



            # Проверка перед выводом секции с предупреждениями, баном, мутом и временными ролями
            if warns_count != "Не имеется" or ban != "Не заблокирован" or mute != "Не замучен" or number_of_roles != "Не имеется":
                embed.add_field(name=f'', value=f'-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-',
                                inline=False)
            if warns_count != "Не имеется":
                embed.add_field(name=f'', value=f'**⚠️ Предупреждений:\n** ``{warns_count}``', inline=True)
            if ban != "Не заблокирован":
                embed.add_field(name=f'', value=f'**🔒 Бан:\n** ``{ban}``', inline=True)
            if mute != "Не замучен":
                embed.add_field(name=f'', value=f'**🙊 Мут:\n** ``{mute}``', inline=True)
            if number_of_roles != "Не имеется":
                embed.add_field(name=f'', value=f'**🕒 Временных ролей:\n** ``{number_of_roles}``', inline=True)

            if temporary_roles:
                for role_info in temporary_roles:
                    role_id = role_info.get('role_ids')
                    expires_at = role_info.get('expires_at')
                    role = inter.guild.get_role(role_id)
                    if role:
                        embed.add_field(
                            name=f'',
                            value=f'{role.mention} - истекает: <t:{int(expires_at)}:R>',
                            inline=False
                        )
            embed.set_footer(text=f'ID: {участник.id}')

            if участник == inter.author:
                select_menu.callback = select_callback

                # Создаем view и добавляем в него select menu
                view = disnake.ui.View()
                view.add_item(select_menu)

                await inter.edit_original_response(embed=embed, view=view)
            else:
                await inter.edit_original_response(embed=embed)
        except Exception as e:
            print(f"Error editing response: {e}")

            if участник == inter.author:
                select_menu.callback = select_callback

                # Создаем view и добавляем в него select menu
                view = disnake.ui.View()
                view.add_item(select_menu)

                await inter.response.send_message(embed=embed, ephemeral=True, view=view)
            else:
                await inter.response.send_message(embed=embed, ephemeral=True)



def setup(bot):
    bot.add_cog(InfoCog(bot))
    print("InfoCog is ready")