#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности подписки на канал
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent / "src"))

from utils.subscription_checker import get_subscription_checker
from config.settings import get_settings

async def test_subscription_checker():
    """Тестирует функциональность проверки подписки."""
    print("🧪 Тестирование функциональности проверки подписки...")
    
    settings = get_settings()
    
    # Проверяем настройки
    print(f"📺 Канал для проверки: @{settings.required_channel_username}")
    print(f"🔧 Проверка подписок включена: {settings.subscription_check_enabled}")
    print(f"⏰ TTL кэша: {settings.subscription_cache_ttl} секунд")
    
    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    try:
        # Инициализация subscription checker
        checker = await get_subscription_checker(settings.telegram_bot_token)
        print("✅ Subscription checker инициализирован")
        
        # Получаем статистику
        stats = await checker.get_subscription_stats()
        print(f"📊 Статистика:")
        print(f"   - Пользователи в белом списке: {stats['whitelisted_users']}")
        print(f"   - Кэшированные статусы: {stats['cached_statuses']}")
        
        # Тестируем проверку подписки (с вашим user_id)
        test_user_id = 123456789  # Замените на ваш user_id для тестирования
        print(f"\n🔍 Тестирование проверки подписки для пользователя {test_user_id}...")
        
        is_subscribed = await checker.is_user_subscribed(test_user_id)
        print(f"✅ Результат: {'подписан' if is_subscribed else 'не подписан'}")
        
        # Тестируем принудительную проверку
        print(f"\n🔄 Принудительная проверка...")
        is_subscribed_forced = await checker.is_user_subscribed(test_user_id, force_check=True)
        print(f"✅ Результат принудительной проверки: {'подписан' if is_subscribed_forced else 'не подписан'}")
        
        # Обновленная статистика
        stats_after = await checker.get_subscription_stats()
        print(f"\n📊 Статистика после тестирования:")
        print(f"   - Пользователи в белом списке: {stats_after['whitelisted_users']}")
        print(f"   - Кэшированные статусы: {stats_after['cached_statuses']}")
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Запуск тестирования функциональности подписки...")
    print("=" * 50)
    
    # Убеждаемся, что переменные окружения загружены
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_subscription_checker()) 