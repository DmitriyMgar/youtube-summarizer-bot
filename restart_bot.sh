#!/bin/bash

echo "🔄 Перезапуск YouTube SummaryBot..."
echo "=" * 50

cd /home/botuser/youtube-summarizer-bot

# Проверка текущего статуса
echo "📊 Текущий статус сервиса:"
sudo systemctl status youtube-bot.service --no-pager -l

echo ""
echo "🛑 Остановка бота..."
sudo systemctl stop youtube-bot.service

# Ждем несколько секунд для корректной остановки
echo "⏳ Ожидание завершения процессов..."
sleep 5

# Проверяем, что сервис остановлен
if sudo systemctl is-active --quiet youtube-bot.service; then
    echo "⚠️  Принудительная остановка..."
    sudo systemctl kill youtube-bot.service
    sleep 2
fi

echo "🚀 Запуск бота..."
sudo systemctl start youtube-bot.service

# Ждем немного для инициализации
echo "⏳ Ожидание инициализации..."
sleep 3

# Проверка статуса запуска
echo ""
echo "📊 Статус после перезапуска:"
if sudo systemctl is-active --quiet youtube-bot.service; then
    echo "✅ Бот успешно запущен!"
    sudo systemctl status youtube-bot.service --no-pager -l
else
    echo "❌ Ошибка запуска бота!"
    echo "📋 Последние логи:"
    sudo journalctl -u youtube-bot.service --no-pager -l --since "1 minute ago"
    exit 1
fi

echo ""
echo "🎉 Перезапуск завершен успешно!" 