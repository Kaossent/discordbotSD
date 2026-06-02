# discordbotSD

Discord-бот для сервера на базе [disnake](https://github.com/DisnakeDevs/disnake) с MongoDB, GPT-интеграцией, системой рангов, экономикой и модерацией.

## Стек

- Python 3.11
- disnake 2.10.1
- MongoDB (pymongo)
- g4f (GPT)
- Pillow + html2image (генерация изображений)
- Docker

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Kaossent/discordbotSD.git
cd discordbotSD
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
```

Заполнить `.env`:

```
TOKEN=твой_discord_bot_token
MONGODB=mongodb+srv://user:pass@cluster.mongodb.net/dbname
```

### 3a. Запуск через Docker (рекомендуется для production)

```bash
docker compose up -d --build
```

Логи:
```bash
docker compose logs -f
```

Остановка:
```bash
docker compose down
```

### 3b. Запуск без Docker

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Структура проекта

```
discordbotSD/
├── main.py              # Точка входа, события бота
├── requirements.txt     # Зависимости
├── Dockerfile
├── docker-compose.yml
├── .env.example         # Шаблон переменных окружения
├── cogs/                # Команды и события (20 когов)
│   ├── rank.py
│   ├── economy.py
│   ├── banner.py
│   ├── GPT.py
│   └── ...
├── ai/                  # GPT-логика
│   ├── gpt_core.py
│   └── ...
├── img/                 # Изображения
├── static/              # Статика для html2image
└── resource/            # Ресурсы
```

---

## Переменные окружения

| Переменная | Описание |
|---|---|
| `TOKEN` | Discord Bot Token ([получить](https://discord.com/developers/applications)) |
| `MONGODB` | MongoDB connection string |

---

## Требования к боту (Discord)

- Intents: все включены (Privileged: Members + Message Content)
- Permissions: Administrator (или точечно по нужным когам)
