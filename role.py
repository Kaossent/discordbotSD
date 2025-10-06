import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from pymongo import MongoClient
from main import cluster
from main import rules, get_rule_info, check_roles
from datetime import datetime, timedelta
from collections import defaultdict
import disnake
from disnake.ext import commands
from disnake.ui import View, Button
from datetime import datetime


current_datetime = datetime.today()

collusers = cluster.server.users
collservers = cluster.server.servers

class TempRolesPaginator(View):
    def __init__(self, pages: list[str], requester: disnake.Member):
        super().__init__(timeout=120)
        self.pages = pages
        self.requester = requester
        self.current_page = 0

        self.message = None
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()

        if self.current_page > 0:
            self.add_item(Button(label="⬅️ Назад", style=disnake.ButtonStyle.primary, custom_id="prev_page"))
        if self.current_page < len(self.pages) - 1:
            self.add_item(Button(label="Вперёд ➡️", style=disnake.ButtonStyle.primary, custom_id="next_page"))

    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("Только автор запроса может управлять страницами.",
                                                    ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)

    @disnake.ui.button(label="⬅️ Назад", style=disnake.ButtonStyle.primary, custom_id="prev_page", row=0)
    async def previous(self, button: Button, interaction: disnake.MessageInteraction):
        self.current_page -= 1
        self.update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(label="Вперёд ➡️", style=disnake.ButtonStyle.primary, custom_id="next_page", row=0)
    async def next(self, button: Button, interaction: disnake.MessageInteraction):
        self.current_page += 1
        self.update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        embed = disnake.Embed(
            title=f"🕓 Временные роли (страница {self.current_page + 1}/{len(self.pages)})",
            description=self.pages[self.current_page],
            color=0x3498DB,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Запросил: {self.requester.display_name}",
                         icon_url=self.requester.display_avatar.url)
        return embed


class Role(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_temp_roles.start()
        self.restricted_roles = [
            # ID ролей, которые нельзя выдать или снять
            1229075137374978119,  # Роль Banned
            1229337640839413813,  # Роль Разработчик
            702593498901381184,  # Роль Модератор
            1044314368717897868,  # Роль Diamond
            1303396950481174611   # Роль Gold
        ]
        self.moderator_role_id = 702593498901381184  # ID роли модератора

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

    @tasks.loop(seconds=350)  # Проверка каждые 350 сек
    async def check_temp_roles(self):
        current_time = int(datetime.now().timestamp())
        expired_roles = collusers.find({"role_ids.expires_at": {"$lte": current_time}})

        for user in expired_roles:
            guild_id = user["guild_id"]
            guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)

            for role_info in user["role_ids"]:
                if role_info["expires_at"] <= current_time:
                    try:
                        member = guild.get_member(user["id"]) or await guild.fetch_member(user["id"])
                        role = guild.get_role(role_info["role_ids"])

                        if member and role:
                            await member.remove_roles(role)
                            collusers.update_one(
                                {"id": user["id"], "guild_id": user["guild_id"]},
                                {"$pull": {"role_ids": {"role_ids": role_info["role_ids"]}}},
                            )
                            collusers.update_one(
                                {"id": user["id"], "guild_id": user["guild_id"]},
                                {"$inc": {"number_of_roles": -1}}
                            )
                            channel = await self.bot.fetch_channel(944562833901899827)
                            embed = disnake.Embed(title="Роль истекла", description="", color=0x00d5ff,
                                                  timestamp=datetime.now())
                            embed.add_field(name="",
                                            value=f"У участника **{member.name}** ({member.mention}) истек срок действия роли ``{role.name}``",
                                            inline=False)
                            embed.set_thumbnail(
                                url="https://media2.giphy.com/media/LOWmk9Vsl3LN3vXhET/giphy.gif")
                            embed.set_footer(text=f"ID участника: {member.id}")
                            await channel.send(embed=embed)
                    except:
                        pass

    @check_temp_roles.before_loop
    async def before_check_temp_roles(self):
        await self.bot.wait_until_ready()  # Ожидание готовности бота перед запуском цикла

    def is_admin_or_mod(self, user):
        # Проверяем, является ли пользователь администратором или модератором
        return any(role.permissions.administrator or role.id == self.moderator_role_id for role in user.roles)

    @commands.slash_command(name="role-give", description="Выдает роль участнику")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def rolegive(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member,
                       роль: disnake.Role, время: str = None,
                       причина: str = "Не указана"):  # Устанавливаем по умолчанию
        if inter.type == disnake.InteractionType.application_command:
            await inter.response.defer(ephemeral=True)

            if роль.id in self.restricted_roles and not self.is_admin_or_mod(inter.user):
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'У Вас недостаточно прав для выдачи роли {роль.name}.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)
                return

            if роль in участник.roles:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'У участника {участник.display_name} уже есть роль {роль.name}.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)
                return

            try:
                await участник.add_roles(роль)
                if время:
                    duration = self.convert_to_seconds(время)
                    expiry = datetime.now() + timedelta(seconds=duration)
                    expiry = int(expiry.timestamp())
                    collusers.update_one(
                        {"id": участник.id, "guild_id": inter.guild.id},
                        {
                            "$push": {"role_ids": {"role_ids": роль.id, "expires_at": expiry}},
                            "$inc": {"number_of_roles": 1}
                        },
                        upsert=True
                    )
                    formatted_duration = self.format_duration(время)
                    embed = disnake.Embed(color=0x00d5ff, timestamp=datetime.now())
                    embed.add_field(name="Роль выдана",
                                    value=f"Роль {роль.name} выдана {участник.display_name} и закончится <t:{expiry}:R>.")
                    embed.set_thumbnail(
                        url="https://media0.giphy.com/media/udvEcwFgNFboJWcHIB/giphy.gif?cid=6c09b952rqyuahrevsqie1hpf23xpwj9wdnqeyturtonwmhn&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=ts")
                    embed.add_field(name="Причина:", value=причина, inline=False)
                    await inter.edit_original_response(embed=embed)
                else:
                    embed = disnake.Embed(color=0x00d5ff, timestamp=datetime.now())
                    embed.add_field(name="Роль выдана",
                                    value=f"Роль {роль.name} выдана {участник.display_name} на неограниченное время.")
                    embed.set_thumbnail(
                        url="https://media0.giphy.com/media/udvEcwFgNFboJWcHIB/giphy.gif?cid=6c09b952rqyuahrevsqie1hpf23xpwj9wdnqeyturtonwmhn&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=ts")
                    embed.add_field(name="Причина:", value=причина, inline=False)
                    await inter.edit_original_response(embed=embed)

                    if роль.id == self.moderator_role_id:
                        embed = disnake.Embed(title="Shadow Dragons",
                                              url="https://discord.com/invite/KE3psXf",
                                              colour=0x005ef5,
                                              timestamp=datetime.now())
                        embed.set_author(name="Вы были назначены Модератором!",
                                         icon_url=inter.guild.icon.url)
                        embed.add_field(name="Мои поздравления!",
                                        value=f"Вы были назначены **Модератором** сервера ``{inter.guild.name}``!",
                                        inline=False)
                        embed.add_field(name="Причина:", value=причина, inline=False)
                        embed.add_field(name="Информация:",
                                        value="Вся нужная информация находится в закрепленном сообщении канала\n <#1150520720569401374>.",
                                        inline=False)
                        embed.add_field(name="FAQ - вся информация и часто задаваемые вопросы:",
                                        value="https://docs.google.com/document/d/1ViJJCVQxL4EYLAcMjkdm5odiWan29STs\n||Для доступа нужно заходить с почты, которую Вы указывали.||",
                                        inline=False)
                        embed.add_field(name="Система предупреждений персонала:",
                                        value="https://docs.google.com/spreadsheets/d/1coh1PzPXptGZzZY874Nylh4iZ2ftJyA0F-CA2dEFiNY/edit?gid=0#gid=0",
                                        inline=False)
                        immunity_end_time = datetime.now() + timedelta(days=7)
                        timestamp = int(immunity_end_time.timestamp())
                        embed.add_field(name="Испытательный срок:",
                                        value="Сейчас на Вас действует иммунитет в течении 7 дней, во время которого Вы не получите предупреждение за ошибки.\n"
                                              "||К этому не относятся: перебаны, перемуты, покрывательство, выход за рамки нормального поведения и другая чушь.||\n\n"
                                              f"Иммунитет истекает: <t:{timestamp}:R>",
                                        inline=False)
                        embed.add_field(name="Еmail:",
                                        value="Пожалуйста, укажите свой Email по кнопке ниже.\n Это требуется для того, чтобы получить доступ к файлу FAQ.\n"
                                              "||Ваш Email будет виден только Администрации | В случае неработоспособности кнопки, свяжитесь с Администрацией напрямую.||",
                                        inline=False)
                        embed.set_thumbnail(url="https://i.imgur.com/bugnSyX.gif")
                        embed.set_footer(text=f"Вас назначил: {inter.author.display_name}",
                                         icon_url=inter.author.display_avatar.url)

                        class EmailModal(disnake.ui.Modal):
                            def __init__(self, bot, участник):
                                self.bot = bot
                                self.участник = участник
                                components = [
                                    disnake.ui.TextInput(
                                        label="Email",
                                        custom_id="email",
                                        style=disnake.TextInputStyle.short,
                                        placeholder="example@example.com",
                                        required=True,
                                        min_length=10,
                                        max_length=50,
                                    )
                                ]
                                super().__init__(title="Указать Email", components=components)

                            async def callback(self, interaction: disnake.ModalInteraction):
                                email = interaction.text_values["email"]
                                await interaction.response.send_message('Загрузка...')
                                if '@' in str(email):
                                    button = EmailButton
                                    admin = inter.guild.get_role(518505773022838797)
                                    chief = inter.guild.get_role(580790278697254913)
                                    channel = self.bot.get_channel(944562833901899827)
                                    embed1 = disnake.Embed(title="Новый Email",
                                                           description=f"**{self.участник.display_name}** ({self.участник.mention}) указал свой Email:\n {email}",
                                                           color=0x00d5ff,
                                                           timestamp=datetime.now())
                                    embed1.set_thumbnail(url="https://media1.giphy.com/media/3osxY4mB281Du0F5E4/200w.gif")
                                    await channel.send(content=f"{admin.mention} и {chief.mention}", embed=embed1)
                                    await interaction.edit_original_response("Email успешно указан! Вскоре Администрация даст Вам доступ к просмотру файла.")
                                    button.disabled = True
                                else:
                                    await interaction.edit_original_response('Некорректная почта')

                        class EmailButton(disnake.ui.Button):
                            def __init__(self, bot, участник):
                                super().__init__(label="Указать Email", style=disnake.ButtonStyle.success,
                                                 custom_id="email_button")
                                self.bot = bot
                                self.участник = участник

                            async def callback(self, interaction: disnake.MessageInteraction):
                                await interaction.response.send_modal(EmailModal(self.bot, self.участник))

                        view = disnake.ui.View(timeout=None)
                        view.add_item(EmailButton(self.bot, участник))

                        try:
                            await участник.send(embed=embed, view=view)
                        except disnake.Forbidden:
                            embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                            embed.add_field(name="Ошибка",
                                            value=f"{участник.mention}, не удалось отправить вам ЛС. Пожалуйста, проверьте настройки конфиденциальности.")
                            await inter.send(embed=embed)

                # Логирование
                channel = await self.bot.fetch_channel(944562833901899827)
                embed = disnake.Embed(title="", url="", description="", color=0x00d5ff, timestamp=datetime.utcnow())
                embed.add_field(name="",
                                value=f"Участник **{участник.name}** ({участник.mention}) получил роль ``{роль.name}``",
                                inline=False)
                embed.set_thumbnail(
                    url="https://media0.giphy.com/media/udvEcwFgNFboJWcHIB/giphy.gif?cid=6c09b952rqyuahrevsqie1hpf23xpwj9wdnqeyturtonwmhn&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=ts")
                embed.add_field(name="Модератор:", value=f"**{inter.author.name}** ({inter.author.mention})",
                                inline=True)
                embed.add_field(name="Канал:", value=f"{inter.channel.mention}", inline=True)
                embed.add_field(name="Длительность:",
                                value=f"{formatted_duration} (<t:{expiry}:R>)" if время else "Неограниченное",
                                inline=True)
                embed.add_field(name="Причина:", value=причина, inline=False)
                embed.set_footer(text=f"ID участника: {участник.id}")
                await channel.send(embed=embed)

            except disnake.Forbidden:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'У меня недостаточно прав для выдачи роли {роль.name}.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)

            except disnake.HTTPException as e:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'Не удалось выдать роль из-за ошибки: {e}')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)

    @commands.slash_command(name="role-remove", description="Снимает роль у участника")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def roleremove(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member,
                         роль: disnake.Role, причина: str = "Не указана"):
        if inter.type == disnake.InteractionType.application_command:
            await inter.response.defer(ephemeral=True)

            # Проверка прав для удаления роли
            if роль.id in self.restricted_roles and not self.is_admin_or_mod(inter.user):
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'У Вас недостаточно прав для удаления роли {роль.name}.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)
                return

            # Проверка наличия роли у участника
            if роль not in участник.roles:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'У участника {участник.display_name} нет роли {роль.name}.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)
                return

            try:
                # Удаление роли у участника
                await участник.remove_roles(роль)
                collusers.update_one(
                    {"id": участник.id, "guild_id": inter.guild.id},
                    {"$pull": {"role_ids": {"role_ids": роль.id}}}
                )
                collusers.update_one(
                    {"id": участник.id, "guild_id": inter.guild.id},
                    {"$inc": {"number_of_roles": -1}}
                )

                # Сообщение о снятии роли
                embed = disnake.Embed(color=0x00d5ff, timestamp=datetime.now())
                embed.add_field(name="Роль удалена",
                                value=f"Роль {роль.name} была успешно снята с участника {участник.display_name}.")
                embed.set_thumbnail(url="https://media2.giphy.com/media/LOWmk9Vsl3LN3vXhET/giphy.gif")
                embed.add_field(name="Причина:", value=причина, inline=False)  # Используем по умолчанию
                await inter.edit_original_response(embed=embed)

                # Если роль была модератора, отправляем личное сообщение участнику
                if роль.id == self.moderator_role_id:
                    embed = disnake.Embed(title="Shadow Dragons",
                                          url="https://discord.com/invite/KE3psXf",
                                          colour=0x005ef5,
                                          timestamp=datetime.now())
                    embed.set_author(name="Вы были сняты с должности Модератора!",
                                     icon_url=inter.guild.icon.url)
                    embed.add_field(name="К моему сожалению!",
                                    value=f"Вы были сняты с **Модератора** сервера ``{inter.guild.name}``!",
                                    inline=False)
                    embed.add_field(name="Причина:", value=причина, inline=False)
                    embed.set_thumbnail(url="https://i.imgur.com/bugnSyX.gif")
                    embed.set_footer(text=f"Вас снял: {inter.author.display_name}",
                                     icon_url=inter.author.display_avatar.url)
                    try:
                        await участник.send(embed=embed)
                    except disnake.Forbidden:
                        embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                        embed.add_field(name="Ошибка",
                                        value=f"{участник.mention}, не удалось отправить вам ЛС. Пожалуйста, проверьте настройки конфиденциальности.")
                        await inter.send(embed=embed)

                # Логирование
                channel = await self.bot.fetch_channel(944562833901899827)
                embed = disnake.Embed(title="", url="", description="", color=0x00d5ff, timestamp=datetime.utcnow())
                embed.add_field(name="",
                                value=f"Участник **{участник.name}** ({участник.mention}) потерял роль ``{роль.name}``",
                                inline=False)
                embed.set_thumbnail(url="https://media2.giphy.com/media/LOWmk9Vsl3LN3vXhET/giphy.gif")
                embed.add_field(name="Модератор:", value=f"**{inter.author.name}** ({inter.author.mention})",
                                inline=True)
                embed.add_field(name="Канал:", value=f"{inter.channel.mention}", inline=True)
                embed.add_field(name="Причина:", value=причина, inline=False)  # Добавление причины в лог
                embed.set_footer(text=f"ID участника: {участник.id}")
                await channel.send(embed=embed)

            except disnake.Forbidden:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'У меня недостаточно прав для удаления роли {роль.name}.')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)

            except disnake.HTTPException as e:
                embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
                embed.add_field(name=f'Ошибка', value=f'Не удалось удалить роль из-за ошибки: {e}')
                embed.set_thumbnail(url="https://cdn.pixabay.com/animation/2022/12/26/19/45/19-45-56-484__480.png")
                embed.set_footer(text="Ошибка")
                await inter.edit_original_response(embed=embed)


    @commands.slash_command(name="temproles-list", description="Выводит список пользователей с временными ролями")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def temporary_roles(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)

        guild_id = inter.guild.id

        users_with_temp_roles = collusers.find({
            "guild_id": guild_id,
            "role_ids": {
                "$elemMatch": {"expires_at": {"$exists": True}}
            }
        })

        user_roles = defaultdict(list)

        for user_data in users_with_temp_roles:
            member_id = user_data.get("id")
            role_entries = user_data.get("role_ids", [])

            if not isinstance(role_entries, list):
                continue

            try:
                member = await inter.guild.fetch_member(member_id)
            except disnake.NotFound:
                continue

            for entry in role_entries:
                role_id = entry.get("role_ids")
                expires_at_ts = entry.get("expires_at")

                if not role_id or not expires_at_ts:
                    continue

                role = inter.guild.get_role(int(role_id))
                if not role:
                    continue

                expires_at = datetime.utcfromtimestamp(expires_at_ts)
                if expires_at <= datetime.utcnow():
                    continue

                user_roles[member].append((role, expires_at_ts))

        formatted_users = []

        for member, roles in user_roles.items():
            sorted_roles = sorted(roles, key=lambda r: (-r[0].position, r[1]))
            role_strings = [f"{role.mention} (до <t:{expires_at}:R>) \n" for role, expires_at in sorted_roles]
            soonest_expire = min(expires_at for _, expires_at in sorted_roles)
            formatted_users.append((
                soonest_expire,
                f"{member.mention}:\n" + " ".join(role_strings)
            ))

        formatted_users.sort(key=lambda x: x[0])
        user_lines = [line for _, line in formatted_users]

        if not user_lines:
            embed = disnake.Embed(
                title="🕓 Временные роли",
                description="Нет пользователей с активными временными ролями.",
                color=0x3498DB,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Запросил: {inter.user.display_name}", icon_url=inter.user.display_avatar.url)
            await inter.followup.send(embed=embed, ephemeral=True)
            return

        # Разбиваем на страницы по 10 строк
        pages = []
        page_size = 10
        for i in range(0, len(user_lines), page_size):
            page = "\n".join(user_lines[i:i + page_size])
            pages.append(page)

        view = TempRolesPaginator(pages, requester=inter.user)
        embed = view.create_embed()
        view.message = await inter.followup.send(embed=embed, view=view, ephemeral=True)


def setup(bot):
    bot.add_cog(Role(bot))
    print("RoleCog is ready")
