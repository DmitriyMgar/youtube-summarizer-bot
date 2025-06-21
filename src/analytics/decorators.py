"""
Decorators for automatic user activity logging
"""

import time
import functools
from datetime import datetime
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

from .logger import get_activity_logger
from .models import UserActivity
from utils.validators import is_valid_youtube_url, extract_video_id


def log_user_activity(command_name: str = None):
    """
    Декоратор для автоматического логирования активности пользователей
    
    Args:
        command_name: Имя команды (если не указано, извлекается из функции)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            start_time = time.time()
            success = True
            error_message = None
            
            # Извлекаем информацию о пользователе
            user = update.effective_user
            chat = update.effective_chat
            message_text = update.message.text if update.message else ""
            
            # Определяем команду
            cmd_name = command_name or func.__name__.replace('_command', '').replace('_', '')
            
            # Извлекаем информацию о видео, если есть
            video_url = None
            video_id = None
            
            try:
                # Проверяем наличие URL в тексте сообщения
                if message_text and is_valid_youtube_url(message_text):
                    video_url = message_text.strip()
                    video_id = extract_video_id(video_url)
                elif context.args:
                    # Проверяем аргументы команды
                    for arg in context.args:
                        if is_valid_youtube_url(arg):
                            video_url = arg
                            video_id = extract_video_id(video_url)
                            break
            except:
                pass  # Игнорируем ошибки извлечения URL
            
            try:
                # Выполняем оригинальную функцию
                result = await func(self, update, context, *args, **kwargs)
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Логируем активность
                processing_time = time.time() - start_time
                
                activity = UserActivity(
                    timestamp=datetime.now(),
                    user_id=user.id,
                    username=user.username or "",
                    first_name=user.first_name or "",
                    last_name=user.last_name,
                    chat_id=chat.id,
                    command=cmd_name,
                    message_text=message_text,
                    video_url=video_url,
                    video_id=video_id,
                    processing_time=processing_time,
                    success=success,
                    error_message=error_message
                )
                
                try:
                    logger = get_activity_logger()
                    logger.log_user_activity(activity)
                except Exception as log_error:
                    # Не прерываем выполнение из-за ошибок логирования
                    import logging
                    logging.getLogger(__name__).error(f"Failed to log user activity: {log_error}")
            
            return result
        
        return wrapper
    return decorator 