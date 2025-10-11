import random
from html2image import Html2Image
from disnake.ext import commands, tasks
from main import rules, get_rule_info, check_roles, collusers, collservers
import disnake
from jinja2 import Template
import io
from PIL import Image
import os
from datetime import datetime, timedelta
import pymongo

cooldowns = {}
hti = Html2Image()



class RankCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.inter = disnake.ApplicationCommandInteraction
        with open('./static/profile.html', 'r', encoding='utf-8') as file:
            self.template = Template(file.read())
        self.role_award = {
            5: 519925709603471381,
            10: 519925711113289748,
            15: 521760576423329794,
            20: 519925714309349377,
            25: 519925715458719799,
            30: 519925716331134976,
            35: 862727316479148065,
            40: 896481674114785300,
            45: 896481824199573574,
            50: 896481809972461690,
            55: 896482036079005737,
            60: 896482158636585040,
            65: 519925718767894531
        }

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     for guild in self.bot.guilds:
    #         if guild.id == 489867322039992320:
    #             for member in guild.members:
    #                 collusers.update_one({"id": member.id, "guild_id": 489867322039992320},
    #                                      {"$set": {"experience": 0}}, upsert=True)
    #                 collusers.update_one({"id": member.id, "guild_id": 489867322039992320},
    #                                      {"$set": {"level": 0}}, upsert=True)
    #                 print(f"Member ID: {member.id} added.")

    async def on_update_experience(self, id, guild_id, level, before, after):
        first_level = 100
        experience_to_level = first_level + (100 * level)
        experience = collusers.find_one({"id": id, "guild_id": guild_id})["experience"]
        print(level)
        if experience > experience_to_level:
            unnecessary_experience = experience - experience_to_level
            level += 1
            collusers.update_one({'id': id, 'guild_id': guild_id}, {"$inc": {"level": 1}})
            collusers.update_one({'id': id, 'guild_id': guild_id}, {"$set": {"experience": unnecessary_experience}})
            collusers.update_one({'id': id, 'guild_id': guild_id}, {"$inc": {"balance": 50 * level}})
            try:
                if self.role_award[level]:
                    guild_id = self.bot.get_guild(guild_id)
                    role = guild_id.get_role(self.role_award[level])
                    member = guild_id.get_member(id)
                    await member.add_roles(role)
                    await member.remove_roles(guild_id.get_role(self.role_award[level - 5]))
            except:
                print('Role not found')
            print(
                f'Updated experience and level, {unnecessary_experience}, {level}, balance incremented on {50 * level}')
        else:
            print('<')

    def render_profile_card(self, template_path, output_path, **variables):
        """
        Рендерит HTML карточку профиля с переданными переменными

        Args:
            template_path: путь к HTML шаблону
            output_path: путь для сохранения результата
            **variables: переменные для подстановки
        """
        rendered_html = self.template.render(**variables)

        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(rendered_html)

        print(f"Карточка сохранена в: {output_path}")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        print('RankCog: Moment')
        if message.author.bot:
            print('RankCog: Message author - bot')
            return
        if len(message.content.split()) < 2:
            print('RankCog: Words in message < 2')
            return

        now = datetime.now()
        user_id = message.author.id
        guild_id = message.guild.id
        experience = collusers.find_one({"id": user_id, "guild_id": guild_id})["experience"]
        level = collusers.find_one({"id": user_id, "guild_id": guild_id})["level"]
        experience_symbol = random.uniform(1, 2)
        multiplier = collservers.find_one({'_id': guild_id})['multiplier']
        if user_id in cooldowns:
            last_used = cooldowns[user_id]
            if now - last_used < timedelta(seconds=45):
                time_left = timedelta(seconds=45) - (now - last_used)
                print(f'RankCog: Timeleft: {time_left}')
                return
        total_experience = len(message.content.split()) * experience_symbol * multiplier

        if total_experience > 50:
            total_experience = 50

        total_experience = round(total_experience, 0)
        collusers.update_one({'id': message.author.id, "guild_id": message.guild.id}, {"$inc": {"experience": total_experience}})
        await self.on_update_experience(user_id, guild_id, level, experience, total_experience)
        cooldowns[user_id] = now
        print('RankCog: Experience successfully updated.')

    @commands.slash_command(name='rank')
    async def rank(self, inter: disnake.ApplicationCommandInteraction, участник: disnake.Member = None):
        await inter.response.defer(ephemeral=True)
        if участник:
            user_id = участник.id
            name = участник.display_name
            url = участник.display_avatar.url
            role = участник.top_role
        else:
            user_id = inter.author.id
            name = inter.author.display_name
            url = inter.author.display_avatar.url
            role = inter.author.top_role
        guild_id = inter.guild.id
        experience = collusers.find_one({"id": user_id, "guild_id": guild_id})["experience"]
        level = collusers.find_one({"id": user_id, "guild_id": guild_id})["level"]

        higher_level_count = collusers.count_documents({
            'level': {'$gt': level}
        })

        position = higher_level_count + 1
        role_color = role.color

        variables = {
            'avatar_url': f'{url}?size=80',
            'avatar_fallback': 'Unknown',  # Инициалы для fallback аватара
            'username': name,
            'level': level,
            'current_xp': int(experience),
            'max_xp': 100 + (level * 100),
            'progress_percentage': (experience / (100 + (100 * level))) * 100,  # Процент для progress bar
            'rank': position,
            'role_color': role_color,
            'role': role.name,
            'percentage': int(round((experience / (100 + (100 * level))) * 100, 0))
        }

        self.render_profile_card('./static/profile.html', './static/final_profile.html', **variables)

        hti.screenshot(html_file='./static/final_profile.html', save_as='profile.png', size=[324,380])
        with Image.open('./profile.png') as img:
            # Координаты: left, top, right, bottom
            img_buffer = io.BytesIO()
            cropped_img = img.crop((0, 0, 320, 360))  # x1, y1, x2, y2
            cropped_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
        await inter.edit_original_response(file=disnake.File(img_buffer, filename='cropped_profile.png'))



def setup(bot):
    bot.add_cog(RankCog(bot))
    print("RankCog is ready")