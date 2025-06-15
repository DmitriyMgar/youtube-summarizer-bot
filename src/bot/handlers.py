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

logger = logging.getLogger(__name__)
settings = get_settings()


class BotHandlers:
    """Collection of Telegram bot command and message handlers."""
    
    def __init__(self, queue_manager: QueueManager, youtube_processor: YouTubeProcessor):
        self.queue_manager = queue_manager
        self.youtube_processor = youtube_processor
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - welcome message and bot introduction."""
        user = update.effective_user
        welcome_message = f"""
🎥 **{settings.bot_name}** v{settings.bot_version}

Hello {user.first_name}! 👋

I can help you summarize YouTube videos using AI. Just send me a YouTube URL and I'll:

🔍 Extract subtitles and key frames
🤖 Generate an AI-powered summary  
📄 Create a downloadable document

**Commands:**
/start - Show this welcome message
/help - Get detailed help
/summarize <YouTube URL> - Summarize a video
/status - Check processing status
/formats - See available output formats

**Supported formats:** {', '.join(settings.supported_formats)}

Just send me a YouTube URL to get started! 🚀
        """
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"User {user.id} ({user.username}) started the bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - detailed usage instructions."""
        help_text = f"""
📖 **{settings.bot_name} - Help Guide**

**How to use:**
1. Send me any YouTube URL
2. Choose your preferred output format
3. Wait for AI processing (1-5 minutes)
4. Download your summary document

**Supported URLs:**
• youtube.com/watch?v=VIDEO_ID
• youtu.be/VIDEO_ID
• m.youtube.com/watch?v=VIDEO_ID

**Commands:**
• `/summarize <URL>` - Process a specific video
• `/status` - Check current processing queue
• `/formats` - View available document formats
• `/cancel` - Cancel your current request

**Limits:**
• Maximum video length: {settings.max_video_duration // 60} minutes
• Rate limit: {settings.rate_limit_messages} requests per {settings.rate_limit_window} seconds

**Privacy:**
• Videos are processed temporarily and not stored
• Only subtitles and key frames are extracted
• Your data is not shared with third parties

Need more help? Contact the bot administrator.
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def formats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /formats command - show available output formats."""
        formats_text = f"""
📄 **Available Output Formats**

**Supported formats:**
"""
        
        format_descriptions = {
            'txt': '📝 Plain text (.txt) - Simple, readable format',
            'docx': '📄 Word Document (.docx) - Rich formatting with headings',
            'pdf': '📕 PDF Document (.pdf) - Professional formatted output'
        }
        
        for fmt in settings.supported_formats:
            if fmt in format_descriptions:
                formats_text += f"• {format_descriptions[fmt]}\n"
        
        formats_text += f"\n**Default format:** {settings.default_format.upper()}"
        formats_text += "\n\nYou can specify format when requesting: `/summarize <URL> format:<format>`"
        
        await update.message.reply_text(
            formats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - show processing queue status."""
        user_id = update.effective_user.id
        queue_status = await self.queue_manager.get_user_status(user_id)
        
        if queue_status:
            status_text = f"""
⏳ **Processing Status**

**Your request:**
• Video ID: `{queue_status['video_id']}`
• Status: {queue_status['status']}
• Position in queue: {queue_status['position']}
• Estimated time: {queue_status['estimated_time']} minutes

Please wait for processing to complete...
            """
        else:
            status_text = """
✅ **No Active Requests**

You don't have any videos currently being processed.
Send me a YouTube URL to start a new summary!
            """
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def summarize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /summarize command with URL parameter."""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a YouTube URL.\n\nUsage: `/summarize <YouTube URL>`",
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
                    if requested_format in settings.supported_formats:
                        output_format = requested_format
                    else:
                        await update.message.reply_text(
                            f"❌ Unsupported format: {requested_format}\n\n"
                            f"Available formats: {', '.join(settings.supported_formats)}"
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
                "❌ This doesn't appear to be a valid YouTube URL.\n\n"
                "Please send a valid YouTube URL or use /help for more information."
            )
    
    async def process_youtube_url(self, update: Update, url: str, output_format: str) -> None:
        """Process a YouTube URL for summarization."""
        user = update.effective_user
        
        # Security check - validate allowed users
        if settings.allowed_users and user.id not in settings.allowed_users:
            await update.message.reply_text(
                "❌ Sorry, you are not authorized to use this bot."
            )
            logger.warning(f"Unauthorized user {user.id} ({user.username}) attempted to use bot")
            return
        
        # Rate limiting check
        if not await self.queue_manager.check_rate_limit(user.id):
            await update.message.reply_text(
                f"❌ Rate limit exceeded. Please wait {settings.rate_limit_window} seconds between requests."
            )
            return
        
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            await update.message.reply_text(
                "❌ Could not extract video ID from URL. Please check the URL and try again."
            )
            return
        
        # Queue size check
        if await self.queue_manager.get_queue_size() >= settings.max_queue_size:
            await update.message.reply_text(
                "❌ Processing queue is full. Please try again later."
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
                f"✅ **Video queued for processing!**\n\n"
                f"📹 Video ID: `{video_id}`\n"
                f"📄 Output format: {output_format.upper()}\n"
                f"⏱️ Estimated processing time: 2-5 minutes\n\n"
                f"I'll send you the summary document when it's ready! 🚀",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"User {user.id} queued video {video_id} for processing")
            
        except Exception as e:
            logger.error(f"Error queuing video {video_id} for user {user.id}: {e}")
            await update.message.reply_text(
                "❌ An error occurred while queuing your request. Please try again later."
            )
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command - cancel user's current request."""
        user_id = update.effective_user.id
        
        if await self.queue_manager.cancel_user_request(user_id):
            await update.message.reply_text(
                "✅ Your processing request has been cancelled."
            )
        else:
            await update.message.reply_text(
                "❌ No active processing request found to cancel."
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
    return [
        BotCommand("start", "Start the bot and see welcome message"),
        BotCommand("help", "Get detailed help and usage instructions"),
        BotCommand("summarize", "Summarize a YouTube video"),
        BotCommand("status", "Check processing status"),
        BotCommand("formats", "View available output formats"),
        BotCommand("cancel", "Cancel current processing request")
    ] 