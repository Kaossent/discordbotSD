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

class BannerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.member_count = 0
        self.booster_count = 0
        self.level_count = 0
        self.guild = bot.get_guild(489867322039992320)
        self.banner_change.start()


    @tasks.loop(minutes=3)
    async def banner_change(self):
        print('banner change')
        guild = self.bot.get_guild(489867322039992320)
        memb_count = guild.member_count
        if self.member_count != memb_count or len(self.guild.premium_subscribers) != self.booster_count or self.level_count != self.guild.premium_subscription_count:
            member_count, booster_count, level_count = self.guild.member_count, self.guild.premium_subscription_count, self.guild.premium_tier
            print(member_count, booster_count, level_count)
            self.member_count = member_count
            self.booster_count = booster_count
            self.level_count = level_count
            img = Image.open("./resource/960x540.jpg").convert("RGBA")

            # get a font
            fnt = ImageFont.truetype("./resource/ggsansl.ttf", 102)
            font = ImageFont.truetype("./resource/ggsansl.ttf", 84)

            d = ImageDraw.Draw(img)

            d.text((595, 370), str(member_count), font=fnt, fill=(255, 255, 255), align='center')
            d.text((200, 375), str(booster_count), font=fnt, fill=(255, 255, 255), align='center')
            d.text((350, 375), str(level_count), font=font, fill=(255, 255, 255), align='center')

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            # Установка баннера
            await self.guild.edit(banner=buffer.read())


def setup(bot):
    bot.add_cog(BannerCog(bot))
    print('BannerCog loaded')