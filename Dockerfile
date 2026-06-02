FROM python:3.11-slim

# Системные зависимости для html2image (Chromium) и Pillow
RUN apt-get update && apt-get install -y \
chromium \
chromium-driver \
fonts-liberation \
libglib2.0-0 \
libnss3 \
libgconf-2-4 \
libfontconfig1 \
libxss1 \
libappindicator1 \
libasound2 \
libatk1.0-0 \
libcups2 \
libdbus-1-3 \
libgdk-pixbuf2.0-0 \
libgtk-3-0 \
libx11-xcb1 \
libxcomposite1 \
libxcursor1 \
libxdamage1 \
libxext6 \
libxfixes3 \
libxi6 \
libxrandr2 \
libxrender1 \
libxtst6 \
ca-certificates \
wget \
--no-install-recommends && \
rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости отдельно для кэширования слоёв
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Не запускаем от root
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

CMD ["python", "main.py"]