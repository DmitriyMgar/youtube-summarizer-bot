#!/bin/bash
cd /home/botuser/youtube-summarizer-bot

# Остановка бота
sudo systemctl stop youtube-bot.service

# Создание бэкапа
cp .env .env.backup

# Обновление кода (если через Git)
git pull origin main

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Восстановление конфигурации
cp .env.backup .env

# Запуск бота
sudo systemctl start youtube-bot.service

# Проверка статуса
sudo systemctl status youtube-bot.service

echo "Бот успешно обновлен!"