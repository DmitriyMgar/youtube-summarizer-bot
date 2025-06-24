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
        
        # Инициализируем менеджер диалогов и клавиатуры
        from src.bot.conversation_manager import ConversationManager
        from src.bot.keyboards import InteractiveKeyboards, KeyboardUtils
        self.conversation_manager = ConversationManager()
        self.keyboards = InteractiveKeyboards()
        self.keyboard_utils = KeyboardUtils()
    
    async def initialize_subscription_checker(self):
        """Инициализация проверки подписок."""
        if settings.subscription_check_enabled:
            self.subscription_checker = await get_subscription_checker(settings.telegram_bot_token)
    
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
            await self.queue_manager.add_legacy_request(
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
            
            # Парсим аргументы команды
            if not context.args:
                await update.message.reply_text(
                    get_message("raw_subtitles_usage"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            video_url = context.args[0]
            output_format = settings.default_format
            
            # Проверяем на указание формата
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
            
            # Создаем документ в выбранном формате
            from src.documents.generator import DocumentGenerator
            doc_generator = DocumentGenerator()
            document_path = await doc_generator.create_subtitles_document(subtitle_data, output_format)
            
            if not document_path:
                raise Exception("Failed to create subtitles document")
            
            # Удаляем сообщение о процессе
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id
            )
            
            # Отправляем файл
            with open(document_path, 'rb') as file:
                # Экранируем специальные символы в названиях для Markdown
                safe_title = escape_markdown(subtitle_data['title'])
                safe_channel = escape_markdown(subtitle_data['channel'])
                safe_language = escape_markdown(subtitle_data['language'])
                
                await update.message.reply_document(
                    document=file,
                    filename=document_path.name,
                    caption=f"📝 **Субтитры извлечены ({output_format.upper()})**\n\n"
                           f"🎥 {safe_title}\n"
                           f"📺 {safe_channel}\n"
                           f"🗣 {safe_language} ({'🤖 Автогенерированные' if subtitle_data['auto_generated'] else '👤 Ручные'})\n"
                           f"📊 Сегментов: {subtitle_data['subtitle_count']}\n"
                           f"📄 Формат: {output_format.upper()}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Удаляем временный файл
            try:
                document_path.unlink()
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
            
            # Парсим аргументы команды
            if not context.args:
                await update.message.reply_text(
                    get_message("corrected_subtitles_usage"),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            video_url = context.args[0]
            output_format = settings.default_format
            
            # Проверяем на указание формата
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
                
                # Создаем документ в выбранном формате
                from src.documents.generator import DocumentGenerator
                doc_generator = DocumentGenerator()
                document_path = await doc_generator.create_subtitles_document(corrected_data, output_format)
                
                if not document_path:
                    raise Exception("Failed to create subtitles document")
                
                # Удаляем сообщение о процессе
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id
                )
                
                # Отправляем файл
                with open(document_path, 'rb') as file:
                    # Экранируем специальные символы в названиях для Markdown
                    safe_title = escape_markdown(corrected_data['title'])
                    safe_channel = escape_markdown(corrected_data['channel'])
                    safe_language = escape_markdown(corrected_data['language'])
                    
                    await update.message.reply_document(
                        document=file,
                        filename=document_path.name,
                        caption=f"📝 **Исправленные субтитры ({output_format.upper()})**\n\n"
                               f"🎥 {safe_title}\n"
                               f"📺 {safe_channel}\n"
                               f"🗣 {safe_language} ({'🤖 Автогенерированные' if corrected_data['auto_generated'] else '👤 Ручные'})\n"
                               f"✨ Обработано ИИ для улучшения читаемости\n"
                               f"📊 Сегментов: {len(corrected_data['subtitles'])}\n"
                               f"📄 Формат: {output_format.upper()}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Удаляем временный файл
                try:
                    document_path.unlink()
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
    
    # ============= NEW INTERACTIVE DIALOG METHODS =============
    
    @log_user_activity("url_dialog")
    async def handle_url_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle YouTube URL messages and start interactive dialog."""
        message = update.message
        user_id = message.from_user.id
        
        # Проверяем подписку на канал
        if not await self._check_subscription_access(user_id):
            escaped_username = settings.required_channel_username.replace('_', '\\_')
            subscription_message = get_message(
                "subscription_required",
                channel_username=escaped_username
            )
            await message.reply_text(
                subscription_message,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Извлекаем YouTube URLs из сообщения
        youtube_urls = self._extract_youtube_urls(message.text)
        
        if not youtube_urls:
            return  # Не YouTube URL, игнорируем
        
        # Берем первый URL если найдено несколько
        youtube_url = youtube_urls[0]
        
        # Валидируем URL
        if not is_valid_youtube_url(youtube_url):
            await message.reply_text(
                get_message("invalid_youtube_url"),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Уведомляем о обнаружении ссылки
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )
        
        processing_msg = await message.reply_text(
            get_message("url_detected"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Получаем информацию о видео
            video_title = await self._get_video_title(youtube_url)
            
            # Удаляем сообщение о проверке
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )
            
            # Создаем или обновляем сессию пользователя
            await self.conversation_manager.set_user_url(user_id, youtube_url, video_title)
            
            # Отправляем клавиатуру выбора операции
            keyboard = self.keyboards.get_operation_selection_keyboard()
            await message.reply_text(
                get_message("video_detected", title=video_title or "YouTube Video"),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id
                )
            except:
                pass
            
            error_msg = str(e).lower()
            if "unavailable" in error_msg or "private" in error_msg:
                await message.reply_text(
                    get_message("video_unavailable"),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                safe_error = escape_markdown(str(e))
                await message.reply_text(
                    get_message("error_processing_failed", error=safe_error),
                    parse_mode=ParseMode.MARKDOWN
                )
            logger.error(f"Error handling URL message: {e}")
    
    def _extract_youtube_urls(self, text: str) -> list[str]:
        """Extract YouTube URLs from message text."""
        youtube_patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://(?:m\.)?youtube\.com/watch\?v=[\w-]+',
            r'youtube\.com/watch\?v=[\w-]+',
            r'youtu\.be/[\w-]+'
        ]
        
        urls = []
        for pattern in youtube_patterns:
            found_urls = re.findall(pattern, text, re.IGNORECASE)
            # Добавляем https:// если отсутствует
            for url in found_urls:
                if not url.startswith('http'):
                    url = 'https://' + url
                urls.append(url)
        
        return urls
    
    async def _get_video_title(self, url: str) -> str:
        """Get video title for display."""
        try:
            # Используем существующий YouTube processor для получения метаданных
            video_id = extract_video_id(url)
            if video_id:
                # Простое извлечение названия без полной обработки
                metadata = await self.youtube_processor.get_video_info(url)
                return metadata.get('title', 'YouTube Video')[:100]  # Ограничиваем длину
        except Exception as e:
            logger.debug(f"Could not get video title: {e}")
        
        return 'YouTube Video'
    
    @log_user_activity("operation_selection")
    async def handle_operation_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle operation selection from inline keyboard."""
        query = update.callback_query
        user_id = query.from_user.id
        operation = query.data.replace('op_', '')
        
        # Подтверждаем callback query
        await query.answer()
        
        # Получаем сессию пользователя
        session = await self.conversation_manager.get_user_session(user_id)
        if not session or session.state.value != "awaiting_operation":
            await query.edit_message_text(
                get_message("session_expired"),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if operation == 'cancel':
            await self.conversation_manager.clear_user_session(user_id)
            await query.edit_message_text(
                get_message("operation_cancelled")
            )
            return
        
        # Обновляем сессию с выбранной операцией
        await self.conversation_manager.set_user_operation(user_id, operation)
        
        # Показываем выбор формата
        keyboard = self.keyboards.get_format_selection_keyboard()
        operation_display = self.keyboard_utils.get_operation_display_name(operation)
        
        await query.edit_message_text(
            get_message("operation_selected", operation=operation_display),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    @log_user_activity("format_selection")
    async def handle_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle format selection from inline keyboard."""
        query = update.callback_query
        user_id = query.from_user.id
        callback_data = query.data
        
        # Подтверждаем callback query
        await query.answer()
        
        # Получаем сессию пользователя
        session = await self.conversation_manager.get_user_session(user_id)
        if callback_data == 'back_to_operations':
            # Возвращаемся к выбору операции
            from src.bot.conversation_manager import ConversationState
            await self.conversation_manager.update_session_state(
                user_id, 
                ConversationState.AWAITING_OPERATION
            )
            
            keyboard = self.keyboards.get_operation_selection_keyboard()
            await query.edit_message_text(
                get_message("video_detected", title=session.video_title or "YouTube Video"),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return
        
        if callback_data == 'op_cancel':
            await self.conversation_manager.clear_user_session(user_id)
            await query.edit_message_text(
                get_message("operation_cancelled")
            )
            return
        
        # Обрабатываем выбор формата
        format_type = callback_data.replace('fmt_', '')
        await self.conversation_manager.set_user_format(user_id, format_type)
        
        # Начинаем обработку
        keyboard = self.keyboards.get_processing_keyboard()
        operation_display = self.keyboard_utils.get_operation_display_name(session.selected_operation)
        format_display = self.keyboard_utils.get_format_display_name(format_type)
        
        await query.edit_message_text(
            get_message(
                "processing_started",
                title=session.video_title or "YouTube Video",
                operation=operation_display,
                format=format_display
            ),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Получаем обновленную сессию и ставим запрос в очередь
        updated_session = await self.conversation_manager.get_user_session(user_id)
        await self._queue_interactive_request(updated_session, query.message.chat_id)
    
    @log_user_activity("processing_control")
    async def handle_processing_controls(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle processing control buttons (cancel processing)."""
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        
        if query.data == 'cancel_processing':
            # Отменяем обработку
            await self.queue_manager.cancel_user_request(user_id)
            await self.conversation_manager.clear_user_session(user_id)
            
            await query.edit_message_text(
                get_message("processing_cancelled")
            )
    
    async def _queue_interactive_request(self, session, chat_id: int) -> None:
        """Queue processing request based on session data."""
        try:
            # Импортируем здесь чтобы избежать циклических импортов
            from src.processing_queue.manager import ProcessingRequest
            
            # Проверяем что все данные заполнены
            if not session.selected_format:
                logger.error(f"Cannot queue request: format not selected for user {session.user_id}")
                return
            
            if not session.selected_operation:
                logger.error(f"Cannot queue request: operation not selected for user {session.user_id}")
                return
            
            request = ProcessingRequest(
                user_id=session.user_id,
                chat_id=chat_id,
                video_url=session.youtube_url,
                video_id=extract_video_id(session.youtube_url),
                output_format=session.selected_format,
                operation_type=session.selected_operation,  # Новое поле для типа операции
                is_interactive=True
            )
            
            await self.queue_manager.add_request(request)
            logger.info(f"Interactive request queued for user {session.user_id}: {session.selected_operation} in {session.selected_format}")
            
        except Exception as e:
            logger.error(f"Error queuing interactive request: {e}")
            # Можно добавить уведомление пользователя об ошибке


async def get_command_handlers(queue_manager: QueueManager, youtube_processor: YouTubeProcessor) -> List:
    """Get list of command handlers for the bot."""
    from telegram.ext import CallbackQueryHandler
    
    handlers = BotHandlers(queue_manager, youtube_processor)
    
    # Инициализируем проверку подписок
    await handlers.initialize_subscription_checker()
    
    return [
        # Command handlers
        CommandHandler("start", handlers.start_command),
        CommandHandler("help", handlers.help_command),
        CommandHandler("summarize", handlers.summarize_command),
        CommandHandler("status", handlers.status_command),
        CommandHandler("formats", handlers.formats_command),
        CommandHandler("cancel", handlers.cancel_command),
        CommandHandler("raw_subtitles", handlers.raw_subtitles_command),
        CommandHandler("corrected_subtitles", handlers.corrected_subtitles_command),
        
        # NEW: Interactive dialog handlers
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.handle_url_message
        ),
        
        # NEW: Callback query handlers for interactive interface
        CallbackQueryHandler(
            handlers.handle_operation_selection,
            pattern=r'^op_'
        ),
        CallbackQueryHandler(
            handlers.handle_format_selection,
            pattern=r'^(fmt_|back_to_|op_cancel)'
        ),
        CallbackQueryHandler(
            handlers.handle_processing_controls,
            pattern=r'^cancel_processing'
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
                BotCommand("status", commands.get("status", "Проверить статус обработки")),
                BotCommand("formats", commands.get("formats", "Посмотреть доступные форматы")),
                BotCommand("cancel", commands.get("cancel", "Отменить текущий запрос"))
            ]
    except Exception as e:
        logger.warning(f"Error getting localized commands: {e}")
    
    # Fallback to Russian commands
    return [
        BotCommand("start", "Запустить бота и увидеть приветственное сообщение"),
        BotCommand("help", "Получить подробную справку и инструкции по использованию"),
        BotCommand("status", "Проверить статус обработки"),
        BotCommand("formats", "Посмотреть доступные форматы вывода"),
        BotCommand("cancel", "Отменить текущий запрос на обработку")
    ] 