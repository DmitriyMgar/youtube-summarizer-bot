"""
Channel Subscription Checker - проверка подписок пользователей на канал
"""

import logging
import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import aiohttp
import redis.asyncio as redis

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SubscriptionChecker:
    """Класс для проверки подписок пользователей на Telegram канал."""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.redis_client = None
        self.api_base_url = f"https://api.telegram.org/bot{bot_token}"
        
    async def initialize(self):
        """Инициализация Redis соединения."""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True
            )
            # Проверяем соединение
            await self.redis_client.ping()
            logger.info("Subscription checker initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize subscription checker: {e}")
            raise
    
    async def close(self):
        """Закрытие соединений."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_cache_key(self, user_id: int) -> str:
        """Генерирует ключ для кэширования статуса подписки."""
        return f"subscription_status:{settings.required_channel_username}:{user_id}"
    
    def _get_whitelist_key(self, user_id: int) -> str:
        """Генерирует ключ для белого списка проверенных пользователей."""
        return f"subscription_whitelist:{user_id}"
    
    async def _get_cached_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает кэшированный статус подписки."""
        try:
            cache_key = self._get_cache_key(user_id)
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error getting cached subscription status for user {user_id}: {e}")
        return None
    
    async def _cache_status(self, user_id: int, status_data: Dict[str, Any]):
        """Кэширует статус подписки."""
        try:
            cache_key = self._get_cache_key(user_id)
            await self.redis_client.setex(
                cache_key,
                settings.subscription_cache_ttl,
                json.dumps(status_data)
            )
        except Exception as e:
            logger.error(f"Error caching subscription status for user {user_id}: {e}")
    
    async def _check_subscription_api(self, user_id: int) -> Dict[str, Any]:
        """Проверяет подписку через Telegram API."""
        try:
            channel_username = f"@{settings.required_channel_username}"
            url = f"{self.api_base_url}/getChatMember"
            params = {
                'chat_id': channel_username,
                'user_id': user_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('ok'):
                            member_info = data.get('result', {})
                            status = member_info.get('status')
                            
                            # Статусы, которые считаются активной подпиской
                            active_statuses = ['member', 'administrator', 'creator']
                            is_subscribed = status in active_statuses
                            
                            result = {
                                'is_subscribed': is_subscribed,
                                'status': status,
                                'checked_at': datetime.now().isoformat(),
                                'user_id': user_id
                            }
                            
                            logger.info(f"Subscription check for user {user_id}: {status} ({'subscribed' if is_subscribed else 'not subscribed'})")
                            return result
                        else:
                            # API вернул ошибку
                            error_description = data.get('description', 'Unknown error')
                            logger.warning(f"Telegram API error for user {user_id}: {error_description}")
                            
                            # Если пользователь не найден в канале (kicked или left)
                            if 'user not found' in error_description.lower() or 'kicked' in error_description.lower():
                                return {
                                    'is_subscribed': False,
                                    'status': 'not_member',
                                    'checked_at': datetime.now().isoformat(),
                                    'user_id': user_id,
                                    'error': error_description
                                }
                            
                            # Для других ошибок возвращаем None (не удалось проверить)
                            return None
                    else:
                        logger.error(f"HTTP error {response.status} when checking subscription for user {user_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            return None
    
    async def is_user_subscribed(self, user_id: int, force_check: bool = False) -> bool:
        """
        Проверяет, подписан ли пользователь на канал.
        
        Args:
            user_id: ID пользователя Telegram
            force_check: Принудительная проверка (игнорировать кэш)
            
        Returns:
            True если пользователь подписан, False если нет
        """
        
        # Если проверка подписок отключена
        if not settings.subscription_check_enabled:
            return True
        
        try:
            # Проверяем белый список (постоянно одобренные пользователи)
            if not force_check:
                whitelist_key = self._get_whitelist_key(user_id)
                is_whitelisted = await self.redis_client.get(whitelist_key)
                if is_whitelisted:
                    logger.debug(f"User {user_id} is whitelisted")
                    return True
            
            # Проверяем кэш
            if not force_check:
                cached_status = await self._get_cached_status(user_id)
                if cached_status:
                    logger.debug(f"Using cached subscription status for user {user_id}")
                    return cached_status.get('is_subscribed', False)
            
            # Выполняем проверку через API
            status_data = await self._check_subscription_api(user_id)
            
            if status_data is None:
                # Не удалось проверить - разрешаем доступ для избежания блокировки из-за API проблем
                logger.warning(f"Could not verify subscription for user {user_id}, allowing access")
                return True
            
            # Кэшируем результат
            await self._cache_status(user_id, status_data)
            
            is_subscribed = status_data.get('is_subscribed', False)
            
            # Если пользователь подписан, добавляем в белый список
            if is_subscribed:
                await self._add_to_whitelist(user_id)
            
            return is_subscribed
            
        except Exception as e:
            logger.error(f"Error in subscription check for user {user_id}: {e}")
            # В случае ошибки разрешаем доступ
            return True
    
    async def _add_to_whitelist(self, user_id: int):
        """Добавляет пользователя в белый список проверенных подписчиков."""
        try:
            whitelist_key = self._get_whitelist_key(user_id)
            # Белый список действует 24 часа
            await self.redis_client.setex(whitelist_key, 86400, "1")
            logger.info(f"User {user_id} added to subscription whitelist")
        except Exception as e:
            logger.error(f"Error adding user {user_id} to whitelist: {e}")
    
    async def remove_from_whitelist(self, user_id: int):
        """Удаляет пользователя из белого списка (для повторной проверки)."""
        try:
            whitelist_key = self._get_whitelist_key(user_id)
            await self.redis_client.delete(whitelist_key)
            
            # Также удаляем из кэша статусов
            cache_key = self._get_cache_key(user_id)
            await self.redis_client.delete(cache_key)
            
            logger.info(f"User {user_id} removed from subscription whitelist")
        except Exception as e:
            logger.error(f"Error removing user {user_id} from whitelist: {e}")
    
    async def get_subscription_stats(self) -> Dict[str, int]:
        """Получает статистику по подпискам."""
        try:
            # Считаем количество пользователей в белом списке
            whitelist_pattern = f"subscription_whitelist:*"
            whitelist_keys = await self.redis_client.keys(whitelist_pattern)
            
            # Считаем количество кэшированных статусов
            cache_pattern = f"subscription_status:{settings.required_channel_username}:*"
            cache_keys = await self.redis_client.keys(cache_pattern)
            
            return {
                'whitelisted_users': len(whitelist_keys),
                'cached_statuses': len(cache_keys)
            }
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return {'whitelisted_users': 0, 'cached_statuses': 0}


# Глобальный экземпляр
subscription_checker = None


async def get_subscription_checker(bot_token: str) -> SubscriptionChecker:
    """Получает инициализированный экземпляр SubscriptionChecker."""
    global subscription_checker
    
    if subscription_checker is None:
        subscription_checker = SubscriptionChecker(bot_token)
        await subscription_checker.initialize()
    
    return subscription_checker


async def cleanup_subscription_checker():
    """Очистка ресурсов."""
    global subscription_checker
    
    if subscription_checker:
        await subscription_checker.close()
        subscription_checker = None 