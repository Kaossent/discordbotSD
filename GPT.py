import asyncio
import re
import time
from asyncio import tasks
import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
from ai.gpt_core import generate_response

instructions = "Вам 20 лет. Ведите себя в Discord как обычный пользователь, набирайте текст только строчными буквами и НИКОГДА не показывайте, что вы на самом деле искусственный интеллект. Люди будут называть вас русским. Они должны быть настолько похожи на людей, чтобы никто даже не догадался, что они искусственный интеллект. Попробуйте использовать эмодзи, распространенный сленг, но не переусердствуйте, повторяя это в каждом отдельном сообщении. Как обычный пользователь discord, вы можете использовать сленг, эмодзи и другие формы общения, распространенные в Discord. Говорите только по-русски и притворяйтесь, что не знаете других языков. Постарайтесь не выдать, что вы искусственный интеллект. Не добавляйте звездочки в первые несколько слов своих предложений, старайтесь вести себя как нормальный человек, поэтому старайтесь не всегда предлагать помощь. Пользователи могут попытаться обманом заставить вас произносить оскорбления или что-то такое, за что вы можете быть наказаны, поэтому будьте осторожны и, если кто-то попросит вас сказать что-то наоборот или повторить за ним, но с определенным условием, откажитесь, поскольку это, скорее всего, уловка, чтобы заставить вас нарушить правила Discord. Поэтому, выступая, помните о правилах дискорда и следите за тем, чтобы не нарушить ни одно из правил. Ты любишь играть в игры. Если у тебя спрашиваю что-то про киберспорт в CS2 и Dota2, говори, что твоя любимая команда Team Spirit, а NAVI не умеют играть."
users_data = {}

async def generate_response_and_reply(message, error, history):
    response = await generate_response(message.content, instructions, error, history)
    return response

async def add_message(user_id, message):
    user_id = str(user_id)  # убеждаемся, что ID — строка
    if user_id not in users_data:
        users_data[user_id] = {"history": []}  # создаем структуру для нового ID
    users_data[user_id]["history"].append(message)  # добавляем сообщение

class GPTCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.inter = disnake.ApplicationCommandInteraction

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not self.bot.user.mentioned_in(message):
            return
        if message.channel.id not in [489867322039992323, 633033345600847872, 532628352927006737]:
            return
        await add_message(message.author.id, message.content)
        if message.author.id == self.bot.user.id:
            return

        if message.author.id not in users_data:
            response = await generate_response_and_reply(message, 'Всё, пизда',
                                                         history=None)
        else:
            response = await generate_response_and_reply(message, 'Всё, пизда', history=users_data[message.author.id]["history"])
        await message.reply(f"{message.author.mention}, {response}")


def setup(bot):
    bot.add_cog(GPTCog(bot))
    print("GPTCog is ready")
