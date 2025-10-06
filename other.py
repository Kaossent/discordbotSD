import time
from asyncio import tasks
import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from g4f.requests import aiohttp
from pymongo import MongoClient
from datetime import datetime
from main import cluster, check_roles, convert_to_seconds
from .economy import format_time
from googletrans import Translator
current_datetime = datetime.today()

collusers = cluster.server.users
collservers = cluster.server.servers
collbans = cluster.server.bans
collpromos = cluster.server.promos

async def get_joke(type):
    url = f"https://v2.jokeapi.dev/joke/{type}?amount=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                translator = Translator()
                if data["type"] == "twopart":
                    setup = await translator.translate(data["setup"], src="en", dest="ru")
                    delivery = await translator.translate(data["delivery"], src="en", dest="ru")
                    return setup.text, delivery.text

                elif data["type"] == "single":
                    joke = await translator.translate(data["joke"], src="en", dest="ru")
                    return joke.text, None

            return None, None

class TopEnum(disnake.enums.Enum):
    Программирование = 'Programming'
    Тёмный_юмор = 'Dark'
    Жуткий = 'Spooky'
    Рождественский = 'Christmas'


class JokeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="joke", description="Получить случайную шутку")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def joke(self, inter: disnake.ApplicationCommandInteraction, тип: TopEnum = commands.Param(default='Any', description="Выберите тип шутки")):
        setup, delivery = await get_joke(тип)
        if delivery is None:
            await inter.response.send_message(f"{setup}", ephemeral=True)
        else:
            await inter.response.send_message(f"{setup}\n{delivery}", ephemeral=True)

    @commands.slash_command(name="channel", description="Управление каналом")
    @check_roles("admin", "chief")
    async def channel(self, inter: disnake.ApplicationCommandInteraction):
        pass  # Заглушка для основной команды

    @channel.sub_command(name="lock", description="Закрыть канал от отправки сообщений")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def lock(self, inter: disnake.ApplicationCommandInteraction, канал: disnake.TextChannel = None):
        канал = канал or inter.channel
        overwrite = канал.overwrites_for(inter.guild.default_role)
        overwrite.send_messages = False
        await канал.set_permissions(inter.guild.default_role, overwrite=overwrite)
        await inter.response.send_message(f"Канал {канал.mention} закрыт от отправки сообщений.", ephemeral=True)

    @channel.sub_command(name="unlock", description="Открыть канал для отправки сообщений")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def unlock(self, inter: disnake.ApplicationCommandInteraction, канал: disnake.TextChannel = None):
        канал = канал or inter.channel
        overwrite = канал.overwrites_for(inter.guild.default_role)
        overwrite.send_messages = True
        await канал.set_permissions(inter.guild.default_role, overwrite=overwrite)
        await inter.response.send_message(f"Канал {канал.mention} открыт для отправки сообщений.", ephemeral=True)

    @channel.sub_command(name="slowmode", description="Установить слоумод в канале")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def slowmode(self, inter: disnake.ApplicationCommandInteraction, канал: disnake.TextChannel = None,
                       время: int = None):
        канал = канал or inter.channel
        await канал.edit(slowmode_delay=время or 0)
        if время:
            await inter.response.send_message(f"Слоумод {время} секунд установлен в канале {канал.mention}.",
                                              ephemeral=True)
        else:
            await inter.response.send_message(f"Слоумод отключён в канале {канал.mention}.", ephemeral=True)

    @channel.sub_command(name="clear", description="Очистить сообщения в канале")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def clear(self, inter: disnake.ApplicationCommandInteraction, количество: int, длительность: str = None,
                    канал: disnake.TextChannel = None, участник: disnake.Member = None):
        канал = канал or inter.channel
        after_time = None
        if длительность:
            after_time = disnake.utils.utcnow() - timedelta(seconds=convert_to_seconds(длительность))

        def check(msg):
            return (участник is None or msg.author == участник)

        удаленные = await канал.purge(limit=количество, after=after_time, check=check)
        await inter.response.send_message(f"Удалено {len(удаленные)} сообщений в канале {канал.mention}.",
                                          ephemeral=True)

    @commands.slash_command(name="nikname", description="Управление никнеймом пользователя")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def nikname(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @nikname.sub_command(name="change", description="Изменить никнейм пользователя")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def change(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member, new_nickname: str):
        try:
            await member.edit(nick=new_nickname)
            await inter.response.send_message(f"Никнейм пользователя {member.mention} изменён на `{new_nickname}`.",
                                              ephemeral=True)
        except disnake.Forbidden:
            await inter.response.send_message("У меня недостаточно прав для изменения никнейма!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Ошибка: {e}", ephemeral=True)

    @nikname.sub_command(name="reset", description="Сбросить никнейм пользователя")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("modstaff")
    async def reset(self, inter: disnake.ApplicationCommandInteraction, member: disnake.Member):
        try:
            await member.edit(nick=None)
            await inter.response.send_message(f"Никнейм пользователя {member.mention} сброшен.", ephemeral=True)
        except disnake.Forbidden:
            await inter.response.send_message("У меня недостаточно прав для изменения никнейма!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Ошибка: {e}", ephemeral=True)

    import disnake
    from disnake.ext import commands

    @commands.slash_command(name='embed', description="Создать embed и отправить его участнику в ЛС с возможностью ответов")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    @check_roles("admin", "chief")
    async def embed(
            self,
            inter: disnake.ApplicationCommandInteraction,
            участник: disnake.Member,
            title: str = None,
            description: str = None,
            color: str = "blue",
            image: str = None,
            thumbnail: str = None,
            footer: str = None,
            button_label: str = None,
            button_url: str = None,
            reply_button: bool = True
    ):
        # Определяем цвет
        color_dict = {
            "red": disnake.Color.red(),
            "green": disnake.Color.green(),
            "blue": disnake.Color.blue(),
            "yellow": disnake.Color.yellow(),
            "purple": disnake.Color.purple(),
            "orange": disnake.Color.orange(),
        }

        if color.startswith("#"):  # Если передан HEX цвет
            try:
                embed_color = disnake.Color(int(color[1:], 16))
            except ValueError:
                await inter.response.send_message("❌ Неверный формат цвета. Используйте #RRGGBB или стандартные цвета.")
                return
        else:
            embed_color = color_dict.get(color.lower(), disnake.Color.blue())

            # Создаем Embed
        embed = disnake.Embed(title=title, description=description, color=embed_color)

        if image:
            embed.set_image(url=image)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        if footer:
            embed.set_footer(text=footer)

        # Создаем кнопки
        view = disnake.ui.View()

        if reply_button:
            view.add_item(disnake.ui.Button(label="Ответить", style=disnake.ButtonStyle.primary, custom_id="reply"))

        if button_label and button_url:
            view.add_item(disnake.ui.Button(label=button_label, url=button_url))

        # Отправляем сообщение в ЛС
        try:
            await участник.send(embed=embed, view=view if view.children else None)
            await inter.response.send_message(f"✅ Embed успешно отправлен {участник.mention}!", ephemeral=True)
        except disnake.Forbidden:
            await inter.response.send_message(
                f"❌ Не удалось отправить сообщение {участник.mention}, возможно, у него закрыты ЛС.", ephemeral=True)

    @commands.slash_command(name='move')
    @check_roles("modstaff")
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def move(self, inter: disnake.ApplicationCommandInteraction, first_channel: disnake.VoiceChannel, channel_to_move: disnake.VoiceChannel):
        await inter.response.defer(ephemeral=True)
        if first_channel == channel_to_move:
            await inter.edit_original_response('Каналы не могут совпадать.')
            return

        if first_channel.members == []:
            await inter.edit_original_response('В канале нет участников.')
            return

        for member in first_channel.members:
            await member.move_to(channel_to_move)
        await inter.edit_original_response('Задание успешно выполнено.')



def setup(bot):
    bot.add_cog(JokeCog(bot))
    print("OtherCog is ready")