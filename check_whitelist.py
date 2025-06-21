#!/usr/bin/env python3
"""
Скрипт для проверки белого списка пользователей подписки на канал
"""

import asyncio
import sys
from pathlib import Path
import redis.asyncio as redis
from datetime import datetime, timedelta

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import get_settings

async def check_whitelist():
    """Проверяет белый список пользователей."""
    print("📋 Проверка белого списка подписчиков...")
    print("=" * 50)
    
    settings = get_settings()
    
    try:
        # Подключаемся к Redis
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        
        # Получаем все ключи белого списка
        whitelist_keys = await redis_client.keys("subscription_whitelist:*")
        
        if not whitelist_keys:
            print("📭 Белый список пуст")
            return
        
        print(f"👥 Пользователей в белом списке: {len(whitelist_keys)}")
        print("\n📝 Детали:")
        
        for key in whitelist_keys:
            # Извлекаем user_id из ключа
            user_id = key.split(":")[-1]
            
            # Получаем TTL (время до истечения)
            ttl = await redis_client.ttl(key)
            
            if ttl == -1:
                time_left = "Бессрочно"
            elif ttl == -2:
                time_left = "Истек"
            else:
                hours = ttl // 3600
                minutes = (ttl % 3600) // 60
                time_left = f"{hours}ч {minutes}м"
            
            print(f"  🆔 User ID: {user_id}")
            print(f"     ⏰ Время до истечения: {time_left}")
            print(f"     🔑 Redis key: {key}")
            print()
        
        # Дополнительная статистика
        print("📊 Дополнительная статистика:")
        
        # Проверяем кэшированные статусы
        cache_keys = await redis_client.keys(f"subscription_status:{settings.required_channel_username}:*")
        print(f"  💾 Кэшированных статусов: {len(cache_keys)}")
        
        # Показываем общие настройки
        print(f"  📺 Канал: @{settings.required_channel_username}")
        print(f"  🔧 Проверка включена: {settings.subscription_check_enabled}")
        print(f"  ⏱️ TTL кэша: {settings.subscription_cache_ttl} сек")
        
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")

async def clear_whitelist():
    """Очищает белый список (для тестирования)."""
    print("🗑️ Очистка белого списка...")
    
    settings = get_settings()
    
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        
        # Получаем все ключи
        whitelist_keys = await redis_client.keys("subscription_whitelist:*")
        cache_keys = await redis_client.keys(f"subscription_status:{settings.required_channel_username}:*")
        
        all_keys = whitelist_keys + cache_keys
        
        if all_keys:
            await redis_client.delete(*all_keys)
            print(f"✅ Удалено {len(all_keys)} записей")
        else:
            print("📭 Нечего удалять")
            
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")

async def add_test_user(user_id: int):
    """Добавляет тестового пользователя в белый список."""
    print(f"➕ Добавление пользователя {user_id} в белый список...")
    
    settings = get_settings()
    
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        
        # Добавляем в белый список на 24 часа
        key = f"subscription_whitelist:{user_id}"
        await redis_client.setex(key, 86400, "1")
        
        print(f"✅ Пользователь {user_id} добавлен в белый список на 24 часа")
        
        await redis_client.close()
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении: {e}")

if __name__ == "__main__":
    print("🔍 Управление белым списком подписчиков")
    print("=" * 50)
    
    # Загружаем переменные окружения
    from dotenv import load_dotenv
    load_dotenv()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "clear":
            asyncio.run(clear_whitelist())
        elif command == "add" and len(sys.argv) > 2:
            user_id = int(sys.argv[2])
            asyncio.run(add_test_user(user_id))
        else:
            print("Использование:")
            print("  python check_whitelist.py           # Показать белый список")
            print("  python check_whitelist.py clear     # Очистить белый список")
            print("  python check_whitelist.py add USER_ID  # Добавить пользователя")
    else:
        asyncio.run(check_whitelist()) 