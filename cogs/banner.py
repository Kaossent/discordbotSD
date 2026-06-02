import os
from io import BytesIO

import disnake
import asyncio
import datetime
import random
import sys
from PIL import Image, ImageDraw
from PIL import ImageFont
from disnake.ext import commands, tasks
from main import cluster

collusers = cluster.server.users
collservers = cluster.server.servers

GUILD_ID = 489867322039992320

class BannerCog(commands.Cog):
def __init__(self, bot):
    self.bot = bot
    self.member_count = 0
    self.booster_count = 0
    self.level_count = 0
    # FIX: не инициализируем guild здесь — бот ещё не готов, get_guild вернёт None
    # guild получаем внутри banner_change после wait_until_ready
    self.banner_change.start()

@banner_change.before_loop
async def before_banner_change(self):
    # FIX: ждём полной готовности бота перед первым запуском задачи
    await self.bot.wait_until_ready()

@tasks.loop(minutes=3)
async def banner_change(self):
    print('banner change')
    # FIX: получаем guild внутри задачи, а не в __init__
    guild = self.bot.get_guild(GUILD_ID)
    if guild is None:
        print('BannerCog: guild not found, skipping')
        return

    memb_count = guild.member_count
    if (self.member_count != memb_count
            or len(guild.premium_subscribers) != self.booster_count
            or self.level_count != guild.premium_subscription_count):

        member_count = guild.member_count
        booster_count = guild.premium_subscription_count
        level_count = guild.premium_tier
        print(member_count, booster_count, level_count)
        self.member_count = member_count
        self.booster_count = booster_count
        self.level_count = level_count

        img = Image.open("./resource/960x540.jpg").convert("RGBA")

        fnt = ImageFont.truetype("./resource/ggsansl.ttf", 102)
        font = ImageFont.truetype("./resource/ggsansl.ttf", 84)

        d = ImageDraw.Draw(img)

        d.text((595, 370), str(member_count), font=fnt, fill=(255, 255, 255), align='center')
        d.text((200, 375), str(booster_count), font=fnt, fill=(255, 255, 255), align='center')
        d.text((350, 375), str(level_count), font=font, fill=(255, 255, 255), align='center')

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # FIX: обёртка в try/except — бот может не иметь прав или сервер не буст-уровня 2+
        try:
            await guild.edit(banner=buffer.read())
        except disnake.Forbidden:
            print('BannerCog: нет прав для смены баннера (нужен буст уровня 2+)')
        except disnake.HTTPException as e:
            print(f'BannerCog: ошибка при смене баннера: {e}')


def setup(bot):
bot.add_cog(BannerCog(bot))
print('BannerCog loaded')
