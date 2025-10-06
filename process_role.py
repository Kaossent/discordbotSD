import disnake
from pymongo import MongoClient, errors, collection
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import os
import asyncio
import time
import random
import math
import re
from main import cluster

collusers = cluster.server.users
collservers = cluster.server.servers


cooldowns = {}
voice_timestamps = {}
mute_timestamps = {}
total_time = {}
emoji = "<a:rumbick:1271085088142262303>"


def create_error_embed(message: str) -> disnake.Embed:
    embed = disnake.Embed(color=0xff0000, timestamp=datetime.now())
    embed.add_field(name='Произошла ошибка', value=f'Ошибка: {message}')
    embed.set_thumbnail(url="https://media2.giphy.com/media/AkGPEj9G5tfKO3QW0r/200.gif")
    embed.set_footer(text='Ошибка')
    return embed

async def process_role(interaction, bot, cost, duration, role_id, ephemeral=False):
    user_id = interaction.author.id
    guild_id = interaction.author.guild.id
    diamond_role_id = 1044314368717897868  # Specific ID for the "Diamond" role

    # Проверяем баланс
    user_data = collusers.find_one({'id': user_id})
    if user_data['balance'] < cost:
        error_message = "У вас не хватает румбиков для покупки."
        embed = create_error_embed(error_message)
        await interaction.send(embed=embed, ephemeral=ephemeral)
        return

    # Обновляем баланс и сделки
    collusers.update_many({'id': user_id}, {'$inc': {'number_of_deal': 1}})
    collusers.find_one_and_update({'id': user_id}, {'$inc': {'balance': -cost}})

    # Получаем роль по ID (Diamond)
    role = disnake.utils.get(interaction.guild.roles, id=role_id)
    if role is None:
        error_message = "Роль не найдена. Пожалуйста свяжитесь с Администратором."
        embed = create_error_embed(error_message)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Получаем пользователя (author of interaction)
    member = interaction.author

    if duration is None:
        new_expiry = "бесконечно"
        embed = disnake.Embed(
            description=f"Вы получили роль {role.name}, которая длится **бесконечно**.",
            colour=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_author(name=f"Вы успешно получили рoль {role.name}!",
                         icon_url=interaction.author.avatar.url)
        embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
        embed.set_footer(text="Роль успешно получена",
                         icon_url=interaction.guild.icon.url)
        await interaction.send(embed=embed, ephemeral=ephemeral)
        await interaction.author.add_roles(role)
    else:
        # Вычисляем новый срок длительности роли
        new_expiry = int((datetime.now() + timedelta(seconds=duration)).timestamp())

        # Проверяем наличие роли у участника
        if role.id == role_id and role in member.roles:
            # Retrieve the current expiry time for the role from the database
            role_info = collusers.find_one(
                {"id": user_id, "guild_id": guild_id, "role_ids.role_ids": role.id},
                {"role_ids.$": 1}
            )
            if role_info and "role_ids" in role_info:
                current_expiry = role_info["role_ids"][0]["expires_at"]
                remaining_time = max(0, current_expiry - int(datetime.now().timestamp()))
                new_expiry = int(datetime.now().timestamp()) + remaining_time + duration

            # Обновляем срок длительности роли в базе
            collusers.update_one(
                {"id": user_id, "guild_id": guild_id, "role_ids.role_ids": role.id},
                {"$set": {"role_ids.$.expires_at": new_expiry}}
            )
            embed = disnake.Embed(
                description=f"**Срок действия роли {role.name} продлен до:** <t:{new_expiry}:R>.\n ",
                colour=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name="Срок действия роли продлен!",
                             icon_url=interaction.author.avatar.url)
            embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
            embed.set_footer(text="Продление прошло успешно",
                             icon_url=interaction.guild.icon.url)
            await interaction.send(embed=embed, ephemeral=ephemeral)

        else:
            # Выдаем роль участнику
            await interaction.author.add_roles(role)
            embed = disnake.Embed(
                description=f"**Вы получили роль {role.name}, которая заканчивается: <t:{new_expiry}:R>.**",
                colour=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_author(name=f"Вы успешно получиили рoль {role.name}!",
                             icon_url=interaction.author.avatar.url)
            embed.set_thumbnail(url="https://www.emojiall.com/images/240/telegram/2705.gif")
            embed.set_footer(text="Роль успешно получена",
                             icon_url=interaction.guild.icon.url)
            await interaction.send(embed=embed, ephemeral=ephemeral)

            # Обновляем базу с новой длительностью роли
            collusers.update_one(
                {"id": user_id, "guild_id": guild_id},
                {
                    "$push": {"role_ids": {"role_ids": role.id, "expires_at": new_expiry}},
                    "$inc": {"number_of_roles": 1}
                },
                upsert=True
            )

    # Создаем и отправлем embed в логи
    channel = await bot.fetch_channel(944562833901899827)
    if new_expiry != "бесконечно":
        new_expiry = f"<t:{new_expiry}:R>"
    log_embed = disnake.Embed(color=0x00d5ff, timestamp=datetime.now())
    log_embed.add_field(name="",
                        value=f"Участник **{interaction.author.name}** ({interaction.author.mention}) получил роль ``{role.name}``",
                        inline=False)
    log_embed.set_thumbnail(
        url="https://media0.giphy.com/media/udvEcwFgNFboJWcHIB/giphy.gif?cid=6c09b952rqyuahrevsqie1hpf23xpwj9wdnqeyturtonwmhn&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=ts")
    log_embed.add_field(name="Модератор:", value=f"**Магазин** ({interaction.author.mention})",
                        inline=True)
    log_embed.add_field(name="Канал:", value=f"{interaction.channel.mention}", inline=True)
    log_embed.add_field(name="Длительность:", value=f"({new_expiry})", inline=True)
    log_embed.set_footer(text=f'ID Участника: {interaction.author.id}', icon_url=interaction.author.display_avatar.url)
    await channel.send(embed=log_embed)

