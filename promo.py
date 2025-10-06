import string

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
from cogs.warn import convert_to_seconds
from cogs.promocode import generate_random_code
from main import cluster

collpromos = cluster.server.promos
collusers = cluster.server.users
collservers = cluster.server.servers


async def create_rumbicks(self, inter, количество_румбиков: int, количество_активаций: int, длительность: str = None, код: str = None):
    код = код or generate_random_code()  # Генерация промокода, если он не задан
    expires_at = None

    if длительность:
        try:
            expires_at = int(time.time()) + convert_to_seconds(длительность)
        except ValueError as e:
            await inter.response.send_message(f"Ошибка в формате времени: {e}", ephemeral=True)
            return

    # Получаем текущий ID и увеличиваем его
    promo_data = collpromos.find_one_and_update(
        {'_id': inter.guild.id},
        {'$inc': {'counter': 1}},
        upsert=True,
        return_document=True
    )
    promo_id = promo_data.get('counter', 1)

    # Создаем промокод
    collpromos.update_one(
        {'_id': inter.guild.id},
        {'$set': {
            f'promos.{код}': {
                'id': promo_id,
                'rumbicks': количество_румбиков,
                'type': 'rumbicks',
                'activations': количество_активаций,
                'expires_at': expires_at,
                'create_id': inter.author.id,
                'users': []
            }
        }},
        upsert=True
    )
    return код
