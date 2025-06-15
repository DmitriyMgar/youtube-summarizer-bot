"""
YouTube Video Summarizer Bot - Telegram Command Handlers
Based on python-telegram-bot Context7 documentation patterns
"""

import logging
import re
from typing import List
from telegram import Update, BotCommand
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

from config.settings import get_settings
from utils.validators import is_valid_youtube_url, extract_video_id
from processing_queue.manager import QueueManager
from youtube.processor import YouTubeProcessor
from localization import get_message, set_language

logger = logging.getLogger(__name__)
settings = get_settings()


class BotHandlers:
    """Collection of Telegram bot command and message handlers."""
    
    def __init__(self, queue_manager: QueueManager, youtube_processor: YouTubeProcessor):
        self.queue_manager = queue_manager
        self.youtube_processor = youtube_processor
        # Set language from settings
        set_language(settings.language)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - welcome message and bot introduction."""
        user = update.effective_user
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


def get_command_handlers(queue_manager: QueueManager, youtube_processor: YouTubeProcessor) -> List:
    """Get list of command handlers for the bot."""
    handlers = BotHandlers(queue_manager, youtube_processor)
    
    return [
        CommandHandler("start", handlers.start_command),
        CommandHandler("help", handlers.help_command),
        CommandHandler("summarize", handlers.summarize_command),
        CommandHandler("status", handlers.status_command),
        CommandHandler("formats", handlers.formats_command),
        CommandHandler("cancel", handlers.cancel_command),
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
                BotCommand("cancel", commands.get("cancel", "Отменить текущий запрос"))
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
        BotCommand("cancel", "Отменить текущий запрос на обработку")
    ] 