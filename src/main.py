"""
YouTube Video Summarizer Bot - Main Application
Integrates all components with proper async handling
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from telegram import Bot
from telegram.ext import Application, ApplicationBuilder

from config.settings import get_settings
from bot.handlers import get_command_handlers, get_bot_commands
from processing_queue.manager import QueueManager
from youtube.processor import YouTubeProcessor
from ai.summarizer import VideoSummarizer
from documents.generator import DocumentGenerator
from utils.logging_config import setup_logging
from localization import get_message, set_language
from analytics.logger import get_activity_logger
from analytics.models import VideoProcessingEvent

logger = logging.getLogger(__name__)
settings = get_settings()


class YouTubeSummarizerBot:
    """Main bot application class."""
    
    def __init__(self):
        self.application = None
        self.queue_manager = QueueManager()
        self.youtube_processor = YouTubeProcessor()
        self.video_summarizer = VideoSummarizer()
        self.document_generator = DocumentGenerator()
        self.processing_task = None
        # Set language from settings
        set_language(settings.language)
    
    async def initialize(self):
        """Initialize all bot components."""
        try:
            logger.info(f"Initializing {settings.bot_name} v{settings.bot_version}")
            
            # Initialize queue manager
            await self.queue_manager.initialize()
            
            # Create Telegram application - Context7 pattern
            self.application = ApplicationBuilder().token(settings.telegram_bot_token).build()
            
            # Add command handlers
            handlers = await get_command_handlers(self.queue_manager, self.youtube_processor)
            for handler in handlers:
                self.application.add_handler(handler)
            
            # Set bot commands for Telegram UI
            bot_commands = get_bot_commands()
            await self.application.bot.set_my_commands(bot_commands)
            
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def start_processing_worker(self):
        """Start the background processing worker."""
        async def process_requests():
            """Background task to process video requests."""
            while True:
                try:
                    # Get next request from queue
                    request = await self.queue_manager.get_next_request()
                    
                    if request:
                        logger.info(f"Processing request for user {request.user_id}, video {request.video_id}")
                        await self.process_video_request(request)
                    else:
                        # No requests, wait a bit
                        await asyncio.sleep(1)
                        
                    # Periodic cleanup
                    if hasattr(self, '_last_cleanup'):
                        if asyncio.get_event_loop().time() - self._last_cleanup > 300:  # 5 minutes
                            await self.queue_manager.cleanup_expired_requests()
                            self._last_cleanup = asyncio.get_event_loop().time()
                    else:
                        self._last_cleanup = asyncio.get_event_loop().time()
                        
                except Exception as e:
                    logger.error(f"Error in processing worker: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
        
        # Start the processing task
        self.processing_task = asyncio.create_task(process_requests())
        logger.info("Background processing worker started")
    
    async def process_video_request(self, request):
        """Process a video summarization request."""
        start_time = asyncio.get_event_loop().time()
        success = False
        error_message = None
        video_info = {}
        tokens_used = 0
        summary_data = {}
        subtitle_data = {}
        
        try:
            # Notify user that processing has started
            await self.send_processing_update(
                request.chat_id,
                "🔄 Processing started! Extracting video content..."
            )
            
            # Step 1: Process YouTube video
            video_data = await self.youtube_processor.process_video_complete(request.video_url)
            
            if video_data['processing_status'] == 'failed':
                raise Exception(f"Video processing failed: {video_data.get('error', 'Unknown error')}")
            
            video_info = video_data.get('video_info', {})
            
            # Step 2: Process based on operation type
            if request.operation_type in ['raw_subtitles', 'corrected_subtitles']:
                # For subtitle operations, skip AI processing and create subtitle document
                if request.operation_type == 'corrected_subtitles':
                    # Notify AI processing for corrected subtitles
                    await self.send_processing_update(
                        request.chat_id,
                        get_message("processing_ai_summary")
                    )
                    
                    # Prepare subtitle data for AI correction
                    transcripts = video_data.get('transcripts', {})
                    video_info = video_data.get('video_info', {})
                    
                    subtitle_data_for_ai = {
                        'title': video_info.get('title', 'Unknown Video'),
                        'channel': video_info.get('uploader', 'Unknown'),
                        'video_id': video_info.get('id', ''),
                        'language': transcripts.get('language', 'Unknown'),
                        'language_code': transcripts.get('language_code', ''),
                        'auto_generated': transcripts.get('is_generated', True),
                        'subtitles': transcripts.get('transcripts', []),
                        'duration': video_info.get('duration', 0)
                    }
                    
                    # Process subtitles with AI correction
                    corrected_data = await self.video_summarizer.correct_transcript(subtitle_data_for_ai)
                    if not corrected_data.get('subtitles'):
                        raise Exception("AI subtitle correction failed: No corrected subtitles returned")
                    
                    tokens_used = corrected_data.get('tokens_used', 0)
                    # Use corrected transcript for document generation
                    corrected_transcripts = {
                        'language': corrected_data.get('language', 'Unknown'),
                        'language_code': corrected_data.get('language_code', ''),
                        'is_generated': corrected_data.get('auto_generated', True),
                        'transcripts': corrected_data.get('subtitles', [])
                    }
                    
                    subtitle_data = {
                        'title': video_info.get('title', 'Unknown Video'),
                        'channel': video_info.get('uploader', 'Unknown'),
                        'duration': video_info.get('duration', 0),
                        'video_id': video_info.get('id', ''),
                        'language': corrected_transcripts.get('language', 'Unknown'),
                        'language_code': corrected_transcripts.get('language_code', ''),
                        'auto_generated': corrected_transcripts.get('is_generated', True),
                        'subtitles': corrected_transcripts.get('transcripts', []),
                        'corrected': True,
                        'correction_method': 'AI Enhancement'
                    }
                else:
                    # Raw subtitles - no AI processing needed
                    video_info = video_data.get('video_info', {})
                    transcripts = video_data.get('transcripts', {})
                    
                    subtitle_data = {
                        'title': video_info.get('title', 'Unknown Video'),
                        'channel': video_info.get('uploader', 'Unknown'),
                        'duration': video_info.get('duration', 0),
                        'video_id': video_info.get('id', ''),
                        'language': transcripts.get('language', 'Unknown'),
                        'language_code': transcripts.get('language_code', ''),
                        'auto_generated': transcripts.get('is_generated', True),
                        'subtitles': transcripts.get('transcripts', []),
                        'corrected': False
                    }
                
                # Notify document creation
                await self.send_processing_update(
                    request.chat_id,
                    get_message("processing_document")
                )
                
                # Step 3: Generate subtitle document
                document_path = await self.document_generator.create_subtitles_document(
                    subtitle_data=subtitle_data,
                    output_format=request.output_format
                )
                
            else:
                # For summarization, use the full AI pipeline
                # Notify progress
                await self.send_processing_update(
                    request.chat_id,
                    get_message("processing_ai_summary")
                )
                
                # Step 2: Generate AI summary
                summary_data = await self.video_summarizer.summarize_video(video_data)
                
                if summary_data['processing_status'] == 'failed':
                    raise Exception(f"AI summarization failed: {summary_data.get('error', 'Unknown error')}")
                
                tokens_used = summary_data.get('tokens_used', 0)
                
                # Notify progress
                await self.send_processing_update(
                    request.chat_id,
                    get_message("processing_document")
                )
                
                # Step 3: Generate summary document
                document_path = await self.document_generator.create_document(
                    video_data=video_data,
                    summary_data=summary_data,
                    output_format=request.output_format
                )
            
            if not document_path or not document_path.exists():
                raise Exception("Document generation failed")
            
            # Step 4: Send completed document
            if request.operation_type in ['raw_subtitles', 'corrected_subtitles']:
                await self.send_completed_subtitle_document(request, document_path, video_data, subtitle_data)
            else:
                await self.send_completed_document(request, document_path, video_data, summary_data)
            
            # Mark request as completed
            await self.queue_manager.complete_request(request.user_id, success=True)
            
            success = True
            logger.info(f"Successfully completed processing for user {request.user_id}")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error processing request for user {request.user_id}: {e}")
            
            # Send error message to user
            await self.send_error_message(request.chat_id, str(e))
            
            # Mark request as completed (with error)
            await self.queue_manager.complete_request(request.user_id, success=False)
        
        finally:
            # Log video processing event
            processing_time = asyncio.get_event_loop().time() - start_time
            
            try:
                video_id = request.video_id or "unknown"
                title = video_info.get('title', 'Unknown Video')
                duration = video_info.get('duration', 0)
                
                event = VideoProcessingEvent(
                    timestamp=datetime.now(),
                    user_id=request.user_id,
                    video_id=video_id,
                    video_url=request.video_url,
                    title=title,
                    duration=duration,
                    output_format=request.output_format or 'txt',  # Защита от None
                    processing_time=processing_time,
                    success=success,
                    error_message=error_message,
                    tokens_used=tokens_used
                )
                
                activity_logger = get_activity_logger()
                activity_logger.log_video_processing(event)
                
            except Exception as log_error:
                logger.error(f"Failed to log video processing event: {log_error}")
    
    async def send_processing_update(self, chat_id: int, message: str):
        """Send processing status update to user."""
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Error sending update to chat {chat_id}: {e}")
    
    async def send_completed_document(self, request, document_path: Path, video_data: dict, summary_data: dict):
        """Send completed summary document to user."""
        try:
            video_info = video_data.get('video_info', {})
            summary = summary_data.get('summary', {})
            
            # Prepare completion message
            duration = f"{video_info.get('duration', 0) // 60}:{video_info.get('duration', 0) % 60:02d}"
            completion_message = get_message(
                "completion_message",
                title=video_info.get('title', 'Unknown Title'),
                duration=duration,
                ai_model=summary_data.get('ai_model', settings.openai_model),
                tokens_used=summary_data.get('tokens_used', 0),
                executive_summary=summary.get('executive_summary', 'Summary not available.')[:200]
            )
            
            # Send document
            with open(document_path, 'rb') as doc_file:
                await self.application.bot.send_document(
                    chat_id=request.chat_id,
                    document=doc_file,
                    filename=document_path.name,
                    caption=completion_message,
                    parse_mode='Markdown'
                )
            
            # Clean up temporary file
            try:
                document_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temporary file {document_path}: {e}")
                
        except Exception as e:
            logger.error(f"Error sending completed document: {e}")
            await self.send_error_message(request.chat_id, get_message("document_send_failed"))

    async def send_completed_subtitle_document(self, request, document_path: Path, video_data: dict, subtitle_data: dict):
        """Send completed subtitle document to user."""
        try:
            video_info = video_data.get('video_info', {})
            
            # Prepare completion message for subtitles
            duration = f"{video_info.get('duration', 0) // 60}:{video_info.get('duration', 0) % 60:02d}"
            
            if subtitle_data.get('corrected', False):
                # Message for corrected subtitles
                completion_message = f"""
✅ **Субтитры исправлены и готовы!**

🎬 **{video_info.get('title', 'Unknown Title')}**
⏱️ **Длительность:** {duration}
✨ **Обработка:** {subtitle_data.get('correction_method', 'AI Enhancement')}
📄 **Формат:** {request.output_format.upper()}

📁 Документ прикреплен ниже!
                """.strip()
            else:
                # Message for raw subtitles  
                completion_message = f"""
✅ **Субтитры извлечены и готовы!**

🎬 **{video_info.get('title', 'Unknown Title')}**
⏱️ **Длительность:** {duration}
📝 **Тип:** Оригинальные субтитры
📄 **Формат:** {request.output_format.upper()}

📁 Документ прикреплен ниже!
                """.strip()
            
            # Send document
            with open(document_path, 'rb') as doc_file:
                await self.application.bot.send_document(
                    chat_id=request.chat_id,
                    document=doc_file,
                    filename=document_path.name,
                    caption=completion_message,
                    parse_mode='Markdown'
                )
            
            # Clean up temporary file
            try:
                document_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temporary file {document_path}: {e}")
                
        except Exception as e:
            logger.error(f"Error sending completed subtitle document: {e}")
            await self.send_error_message(request.chat_id, get_message("document_send_failed"))
    
    async def send_error_message(self, chat_id: int, error_message: str):
        """Send error message to user."""
        try:
            error_text = get_message("processing_failed", error_message=error_message)
            
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=error_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending error message to chat {chat_id}: {e}")
    
    async def run(self):
        """Run the bot."""
        try:
            # Initialize bot
            await self.initialize()
            
            # Start background processing worker
            await self.start_processing_worker()
            
            # Start the bot
            logger.info("Starting YouTube Summarizer Bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Bot shutdown requested by user")
        except Exception as e:
            logger.error(f"Fatal error in bot: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        try:
            logger.info("Shutting down bot...")
            
            # Cancel processing task
            if self.processing_task:
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            
            # Close queue manager
            await self.queue_manager.close()
            
            # Stop the application
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            logger.info("Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def async_main():
    """Async main function."""
    # Setup logging
    setup_logging(settings.log_level)
    
    # Create and run bot
    bot = YouTubeSummarizerBot()
    await bot.run()


def main():
    """Main entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 