"""
YouTube Video Summarizer Bot - Main Application
Integrates all components with proper async handling
"""

import asyncio
import logging
import sys
from pathlib import Path

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
    
    async def initialize(self):
        """Initialize all bot components."""
        try:
            logger.info(f"Initializing {settings.bot_name} v{settings.bot_version}")
            
            # Initialize queue manager
            await self.queue_manager.initialize()
            
            # Create Telegram application - Context7 pattern
            self.application = ApplicationBuilder().token(settings.telegram_bot_token).build()
            
            # Add command handlers
            handlers = get_command_handlers(self.queue_manager, self.youtube_processor)
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
            
            # Notify progress
            await self.send_processing_update(
                request.chat_id,
                "🤖 Generating AI summary..."
            )
            
            # Step 2: Generate AI summary
            summary_data = await self.video_summarizer.summarize_video(video_data)
            
            if summary_data['processing_status'] == 'failed':
                raise Exception(f"AI summarization failed: {summary_data.get('error', 'Unknown error')}")
            
            # Notify progress
            await self.send_processing_update(
                request.chat_id,
                "📄 Creating document..."
            )
            
            # Step 3: Generate document
            document_path = await self.document_generator.create_document(
                video_data=video_data,
                summary_data=summary_data,
                output_format=request.output_format
            )
            
            if not document_path or not document_path.exists():
                raise Exception("Document generation failed")
            
            # Step 4: Send completed document
            await self.send_completed_document(request, document_path, video_data, summary_data)
            
            # Mark request as completed
            await self.queue_manager.complete_request(request.user_id, success=True)
            
            logger.info(f"Successfully completed processing for user {request.user_id}")
            
        except Exception as e:
            logger.error(f"Error processing request for user {request.user_id}: {e}")
            
            # Send error message to user
            await self.send_error_message(request.chat_id, str(e))
            
            # Mark request as completed (with error)
            await self.queue_manager.complete_request(request.user_id, success=False)
    
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
        """Send completed document to user."""
        try:
            video_info = video_data.get('video_info', {})
            summary = summary_data.get('summary', {})
            
            # Prepare completion message
            completion_message = f"""
✅ **Summary Complete!**

📹 **Video**: {video_info.get('title', 'Unknown Title')}
⏱️ **Duration**: {video_info.get('duration', 0) // 60}:{video_info.get('duration', 0) % 60:02d}
🤖 **AI Model**: {summary_data.get('ai_model', settings.openai_model)}
📊 **Tokens Used**: {summary_data.get('tokens_used', 0)}

**Quick Summary**:
{summary.get('executive_summary', 'Summary not available.')[:200]}...

📁 Document attached below!
            """
            
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
            await self.send_error_message(request.chat_id, "Document was created but failed to send.")
    
    async def send_error_message(self, chat_id: int, error_message: str):
        """Send error message to user."""
        try:
            error_text = f"""
❌ **Processing Failed**

An error occurred while processing your video:
{error_message}

Please try again or contact support if the issue persists.
            """
            
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
            await self.application.run_polling()
            
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
                await self.application.stop()
            
            logger.info("Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point."""
    # Setup logging
    setup_logging(settings.log_level)
    
    # Create and run bot
    bot = YouTubeSummarizerBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 