"""
YouTube Video Summarizer Bot - Telegram Command Handlers
Based on python-telegram-bot Context7 documentation patterns
"""

import logging
import re
import asyncio
import tempfile
import os
from typing import List
from telegram import Update, BotCommand
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest

from config.settings import get_settings
from utils.validators import is_valid_youtube_url, extract_video_id
from utils.subtitle_formatter import SubtitleFormatter
from utils.subscription_checker import get_subscription_checker
from processing_queue.manager import QueueManager
from youtube.processor import YouTubeProcessor
from localization import get_message, set_language
from analytics.decorators import log_user_activity

logger = logging.getLogger(__name__)
settings = get_settings()

def escape_markdown(text: str) -> str:
    """Escape special Markdown characters in text."""
    # Characters that need escaping in Telegram MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

class BotHandlers:
    """Collection of Telegram bot command and message handlers."""
    
    def __init__(self, queue_manager: QueueManager, youtube_processor: YouTubeProcessor):
        self.queue_manager = queue_manager
        self.youtube_processor = youtube_processor
        self.subscription_checker = None
        # Set language from settings
        set_language(settings.language)
        
        # Инициализируем AI summarizer для работы с исправлением субтитров
        from src.ai.summarizer import VideoSummarizer
        self.summarizer = VideoSummarizer()
    
    async def initialize_subscription_checker(self):
        """Инициализация проверки подписок."""
        if settings.subscription_check_enabled:
            self.subscription_checker = await get_subscription_checker(settings.telegram_bot_token)
    
    def _is_authorized_user(self, user_id: int) -> bool:
        """Проверяет авторизацию пользователя"""
        return not settings.allowed_users_list or user_id in settings.allowed_users_list
    
    async def _check_subscription_access(self, user_id: int) -> bool:
        """Проверяет доступ пользователя на основе подписки на канал."""
        if not settings.subscription_check_enabled or not self.subscription_checker:
            return True
        
        try:
            return await self.subscription_checker.is_user_subscribed(user_id)
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            # В случае ошибки разрешаем доступ, чтобы не блокировать пользователей
            return True
    
    @log_user_activity("start")
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - welcome message and bot introduction."""
        user = update.effective_user
        
        # Проверяем подписку на канал
        if not await self._check_subscription_access(user.id):
            # Экранируем подчеркивания для Markdown
            escaped_username = settings.required_channel_username.replace('_', '\\_')
            subscription_message = get_message(
                "subscription_required",
                channel_username=escaped_username
            )
            await update.message.reply_text(
                subscription_message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"User {user.id} ({user.username}) denied access - not subscribed to channel")
            return
        
        welcome_message = get_message(
            "welcome_message",
            bot_name=settings.bot_name,
            bot_version=settings.bot_version,
            first_name=user.first_name,
            supported_formats=', '.join(settings.supported_formats_list)
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user.id} ({user.username}) started the bot")
    
    @log_user_activity("help")
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - detailed usage instructions."""
        help_text = get_message(
            "help_text",
            bot_name=settings.bot_name,
            max_duration=settings.max_video_duration // 60,
            rate_limit_messages=settings.rate_limit_messages,
            rate_limit_window=settings.rate_limit_window
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML
        )
    
    @log_user_activity("formats")
    async def formats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /formats command - show available output formats."""
        formats_text = get_message("formats_title") + "\n\n"
        formats_text += get_message("formats_supported") + "\n"
        
        for fmt in settings.supported_formats_list:
            description = get_message(f"format_descriptions.{fmt}")
            if description and not description.startswith("Missing"):
                formats_text += f"• {description}\n"
        
        formats_text += "\n" + get_message("formats_default", default_format=settings.default_format.upper())
        formats_text += "\n\n" + get_message("formats_specify")
        
        await update.message.reply_text(
            formats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    @log_user_activity("status")
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - show processing queue status."""
        user_id = update.effective_user.id
        queue_status = await self.queue_manager.get_user_status(user_id)
        
        if queue_status:
            status_text = get_message(
                "status_processing",
                video_id=queue_status['video_id'],
                status=queue_status['status'],
                position=queue_status['position'],
                estimated_time=queue_status['estimated_time']
            )
        else:
            status_text = get_message("status_no_requests")
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    @log_user_activity("summarize")
    async def summarize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /summarize command with URL parameter."""
        if not context.args:
            await update.message.reply_text(
                get_message("error_no_url"),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        url = context.args[0]
        output_format = settings.default_format
        
        # Check for format specification
        if len(context.args) > 1:
            for arg in context.args[1:]:
                if arg.startswith('format:'):
                    requested_format = arg.split(':', 1)[1].lower()
                    if requested_format in settings.supported_formats_list:
                        output_format = requested_format
                    else:
                        await update.message.reply_text(
                            get_message(
                                "error_unsupported_format",
                                format=requested_format,
                                available_formats=', '.join(settings.supported_formats_list)
                            )
                        )
                        return
        
        await self.process_youtube_url(update, url, output_format)
    
    @log_user_activity("url_message")
    async def handle_youtube_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle direct YouTube URL messages."""
        url = update.message.text.strip()
        
        if is_valid_youtube_url(url):
            await self.process_youtube_url(update, url, settings.default_format)
        else:
            await update.message.reply_text(
                get_message("error_invalid_url")
            )
    
    async def process_youtube_url(self, update: Update, url: str, output_format: str) -> None:
        """Process a YouTube URL for summarization."""
        user = update.effective_user
        
        # Проверяем подписку на канал
        if not await self._check_subscription_access(user.id):
            # Экранируем подчеркивания для Markdown
            escaped_username = settings.required_channel_username.replace('_', '\\_')
            subscription_message = get_message(
                "subscription_required",
                channel_username=escaped_username
            )
            await update.message.reply_text(
                subscription_message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.warning(f"User {user.id} ({user.username}) denied access - not subscribed to channel")
            return
        
        # Security check - validate allowed users
        if settings.allowed_users_list and user.id not in settings.allowed_users_list:
            await update.message.reply_text(
                get_message("error_unauthorized")
            )
            logger.warning(f"Unauthorized user {user.id} ({user.username}) attempted to use bot")
            return
        
        # Rate limiting check
        if not await self.queue_manager.check_rate_limit(user.id):
            await update.message.reply_text(
                get_message("error_rate_limit", rate_limit_window=settings.rate_limit_window)
            )
            return
        
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            await update.message.reply_text(
                get_message("error_extract_video_id")
            )
            return
        
        # Queue size check
        if await self.queue_manager.get_queue_size() >= settings.max_queue_size:
            await update.message.reply_text(
                get_message("error_queue_full")
            )
            return
        
        # Add to processing queue
        try:
            await self.queue_manager.add_request(
                user_id=user.id,
                video_id=video_id,
                video_url=url,
                output_format=output_format,
                chat_id=update.effective_chat.id
            )
            
            await update.message.reply_text(
                get_message(
                    "success_queued",
                    video_id=video_id,
                    output_format=output_format.upper()
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"User {user.id} queued video {video_id} for processing")
            
        except Exception as e:
            logger.error(f"Error queuing video {video_id} for user {user.id}: {e}")
            await update.message.reply_text(
                get_message("error_general")
            )
    
    @log_user_activity("cancel")
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command - cancel user's current request."""
        user_id = update.effective_user.id
        
        if await self.queue_manager.cancel_user_request(user_id):
            await update.message.reply_text(
                get_message("success_cancelled")
            )
        else:
            await update.message.reply_text(
                get_message("error_no_cancel")
            )
    
    @log_user_activity("raw_subtitles")
    async def raw_subtitles_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /raw_subtitles для извлечения субтитров без ИИ обработки
        """
        try:
            user_id = update.effective_user.id
            message_text = update.message.text.strip()
            
            # Проверяем подписку на канал
            if not await self._check_subscription_access(user_id):
                # Экранируем подчеркивания для Markdown
                escaped_username = settings.required_channel_username.replace('_', '\\_')
                subscription_message = get_message(
                    "subscription_required",
                    channel_username=escaped_username
                )
                await update.message.reply_text(
                    subscription_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.warning(f"User {user_id} denied access to raw_subtitles - not subscribed to channel")
                return
            
            # Проверяем авторизацию пользователя
            if not self._is_authorized_user(user_id):
                await update.message.reply_text(
                    get_message("error_unauthorized"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Извлекаем URL из команды
            parts = message_text.split(maxsplit=1)
            if len(parts) < 2:
                await update.message.reply_text(
                    get_message("raw_subtitles_usage"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            video_url = parts[1].strip()
            
            # Валидация URL
            if not is_valid_youtube_url(video_url):
                await update.message.reply_text(
                    get_message("invalid_youtube_url"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Отправляем индикатор "печатает"
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING
            )
            
            # Уведомляем о начале обработки
            processing_message = await update.message.reply_text(
                get_message("raw_subtitles_processing"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Извлекаем субтитры
            subtitle_data = await self.youtube_processor.extract_raw_subtitles(video_url)
            
            # Форматируем для файла
            formatter = SubtitleFormatter()
            file_content = formatter.format_for_file(subtitle_data)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # Удаляем сообщение о процессе
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id
            )
            
            # Создаем имя файла на основе названия видео
            safe_title = "".join(c for c in subtitle_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Ограничиваем длину
            filename = f"{safe_title}_subtitles.txt"
            
            # Отправляем файл
            with open(temp_file_path, 'rb') as file:
                # Экранируем специальные символы в названиях для Markdown
                safe_title = escape_markdown(subtitle_data['title'])
                safe_channel = escape_markdown(subtitle_data['channel'])
                safe_language = escape_markdown(subtitle_data['language'])
                
                await update.message.reply_document(
                    document=file,
                    filename=filename,
                    caption=f"📝 **Субтитры извлечены**\n\n"
                           f"🎥 {safe_title}\n"
                           f"📺 {safe_channel}\n"
                           f"🗣 {safe_language} ({'🤖 Автогенерированные' if subtitle_data['auto_generated'] else '👤 Ручные'})\n"
                           f"📊 Сегментов: {subtitle_data['subtitle_count']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Удаляем временный файл
            try:
                os.unlink(temp_file_path)
            except:
                pass
            
            # Логируем успешную обработку
            logger.info(f"Raw subtitles file sent successfully for user {user_id}, video: {subtitle_data['video_id']}")
            
        except Exception as e:
            # Удаляем сообщение о процессе если есть ошибка
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id
                )
            except:
                pass
            
            # Определяем тип ошибки и отправляем соответствующее сообщение
            error_msg = str(e).lower()
            if "no subtitles" in error_msg or "transcript" in error_msg:
                await update.message.reply_text(
                    get_message("raw_subtitles_not_found"),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.warning(f"No subtitles available for URL: {video_url}")
            elif "unavailable" in error_msg or "private" in error_msg:
                await update.message.reply_text(
                    get_message("video_unavailable"), 
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.warning(f"Video unavailable: {video_url}")
            elif "file" in error_msg or "document" in error_msg:
                await update.message.reply_text(
                    get_message("raw_subtitles_file_error"),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.error(f"File creation/send error for video {video_url}: {str(e)}")
            else:
                # Экранируем специальные символы в тексте ошибки
                safe_error = escape_markdown(str(e))
                await update.message.reply_text(
                    get_message("raw_subtitles_error", error=safe_error),
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.error(f"Unexpected error in raw_subtitles command: {str(e)}", exc_info=True)

    @log_user_activity("corrected_subtitles")
    async def corrected_subtitles_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /corrected_subtitles для извлечения и исправления субтитров
        """
        try:
            user_id = update.effective_user.id
            message_text = update.message.text.strip()
            
            # Проверяем подписку на канал
            if not await self._check_subscription_access(user_id):
                # Экранируем подчеркивания для Markdown
                escaped_username = settings.required_channel_username.replace('_', '\\_')
                subscription_message = get_message(
                    "subscription_required",
                    channel_username=escaped_username
                )
                await update.message.reply_text(
                    subscription_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.warning(f"User {user_id} denied access to corrected_subtitles - not subscribed to channel")
                return
            
            # Проверяем авторизацию пользователя
            if not self._is_authorized_user(user_id):
                await update.message.reply_text(
                    get_message("error_unauthorized"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Извлекаем URL из команды
            parts = message_text.split(maxsplit=1)
            if len(parts) < 2:
                await update.message.reply_text(
                    get_message("corrected_subtitles_usage"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            video_url = parts[1].strip()
            
            # Валидация URL
            if not is_valid_youtube_url(video_url):
                await update.message.reply_text(
                    get_message("invalid_youtube_url"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Отправляем индикатор "печатает"
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING
            )
            
            # Уведомляем о начале обработки
            processing_message = await update.message.reply_text(
                get_message("corrected_subtitles_processing"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            try:
                # Извлекаем сырые субтитры
                subtitle_data = await self.youtube_processor.extract_raw_subtitles(video_url)
                
                # Исправляем субтитры с помощью ИИ
                corrected_data = await self.summarizer.correct_transcript(subtitle_data)
                
                # Форматируем для файла
                formatter = SubtitleFormatter()
                file_content = formatter.format_for_file(corrected_data)
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                # Удаляем сообщение о процессе
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id
                )
                
                # Создаем имя файла
                safe_title = "".join(c for c in corrected_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title[:50]
                filename = f"{safe_title}_corrected_subtitles.txt"
                
                # Отправляем файл
                with open(temp_file_path, 'rb') as file:
                    # Экранируем специальные символы в названиях для Markdown
                    safe_title = escape_markdown(corrected_data['title'])
                    safe_channel = escape_markdown(corrected_data['channel'])
                    safe_language = escape_markdown(corrected_data['language'])
                    
                    await update.message.reply_document(
                        document=file,
                        filename=filename,
                        caption=f"📝 **Исправленные субтитры**\n\n"
                               f"🎥 {safe_title}\n"
                               f"📺 {safe_channel}\n"
                               f"🗣 {safe_language} ({'🤖 Автогенерированные' if corrected_data['auto_generated'] else '👤 Ручные'})\n"
                               f"✨ Обработано ИИ для улучшения читаемости\n"
                               f"📊 Сегментов: {len(corrected_data['subtitles'])}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Удаляем временный файл
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
                # Логируем успешную обработку
                logger.info(f"Corrected subtitles file sent successfully for user {user_id}, video: {corrected_data['video_id']}")
                
            except Exception as e:
                # Удаляем сообщение о процессе если есть ошибка
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id
                    )
                except:
                    pass
                
                # Определяем тип ошибки и отправляем соответствующее сообщение
                error_msg = str(e).lower()
                if "no subtitles" in error_msg or "transcript" in error_msg:
                    await update.message.reply_text(
                        get_message("raw_subtitles_not_found"),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.warning(f"No subtitles available for URL: {video_url}")
                elif "unavailable" in error_msg or "private" in error_msg:
                    await update.message.reply_text(
                        get_message("video_unavailable"), 
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.warning(f"Video unavailable: {video_url}")
                elif "file" in error_msg or "document" in error_msg:
                    await update.message.reply_text(
                        get_message("corrected_subtitles_file_error"),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.error(f"File creation/send error for video {video_url}: {str(e)}")
                else:
                    # Экранируем специальные символы в тексте ошибки
                    safe_error = escape_markdown(str(e))
                    await update.message.reply_text(
                        get_message("corrected_subtitles_error", error=safe_error),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.error(f"Unexpected error in corrected_subtitles command: {str(e)}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Critical error in corrected_subtitles command: {str(e)}", exc_info=True)
            await update.message.reply_text(
                get_message("general_error"),
                parse_mode=ParseMode.MARKDOWN
            )


async def get_command_handlers(queue_manager: QueueManager, youtube_processor: YouTubeProcessor) -> List:
    """Get list of command handlers for the bot."""
    handlers = BotHandlers(queue_manager, youtube_processor)
    
    # Инициализируем проверку подписок
    await handlers.initialize_subscription_checker()
    
    return [
        CommandHandler("start", handlers.start_command),
        CommandHandler("help", handlers.help_command),
        CommandHandler("summarize", handlers.summarize_command),
        CommandHandler("status", handlers.status_command),
        CommandHandler("formats", handlers.formats_command),
        CommandHandler("cancel", handlers.cancel_command),
        CommandHandler("raw_subtitles", handlers.raw_subtitles_command),
        CommandHandler("corrected_subtitles", handlers.corrected_subtitles_command),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?:youtube\.com|youtu\.be)'),
            handlers.handle_youtube_url
        )
    ]


def get_bot_commands() -> List[BotCommand]:
    """Get list of bot commands for Telegram's command menu."""
    set_language(settings.language)  # Ensure language is set
    
    # Safely get command descriptions
    try:
        commands = get_message("commands")
        if isinstance(commands, dict):
            return [
                BotCommand("start", commands.get("start", "Запустить бота")),
                BotCommand("help", commands.get("help", "Получить помощь")),
                BotCommand("summarize", commands.get("summarize", "Создать изложение видео YouTube")),
                BotCommand("status", commands.get("status", "Проверить статус обработки")),
                BotCommand("formats", commands.get("formats", "Посмотреть доступные форматы")),
                BotCommand("cancel", commands.get("cancel", "Отменить текущий запрос")),
                BotCommand("raw_subtitles", commands.get("raw_subtitles", "Извлечь субтитры без ИИ обработки")),
                BotCommand("corrected_subtitles", commands.get("corrected_subtitles", "Извлечь и исправить субтитры"))
            ]
    except Exception as e:
        logger.warning(f"Error getting localized commands: {e}")
    
    # Fallback to Russian commands
    return [
        BotCommand("start", "Запустить бота и увидеть приветственное сообщение"),
        BotCommand("help", "Получить подробную справку и инструкции по использованию"),
        BotCommand("summarize", "Создать изложение видео YouTube"),
        BotCommand("status", "Проверить статус обработки"),
        BotCommand("formats", "Посмотреть доступные форматы вывода"),
        BotCommand("cancel", "Отменить текущий запрос на обработку"),
        BotCommand("raw_subtitles", "Извлечь субтитры без ИИ обработки"),
        BotCommand("corrected_subtitles", "Извлечь и исправить субтитры")
    ] 