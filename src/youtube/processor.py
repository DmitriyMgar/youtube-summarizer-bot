"""
YouTube Video Processor - Extract subtitles and video frames
Based on yt-dlp and youtube-transcript-api Context7 documentation
"""

import asyncio
import logging
import os
import tempfile
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter
from youtube_transcript_api import NoTranscriptFound

from config.settings import get_settings
from utils.validators import extract_video_id

logger = logging.getLogger(__name__)
settings = get_settings()


class YouTubeProcessor:
    """Process YouTube videos to extract subtitles and metadata."""
    
    def __init__(self):
        # Check for proxy settings in environment
        import os
        proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        
        self.ydl_opts = {
            'quiet': not settings.debug,
            'no_warnings': not settings.debug,
            'extractaudio': False,
            'format': 'best[height<=720]',  # Limit quality for faster processing
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB', 'ru'],  # Added Russian language support
            'skip_download': True,  # Only extract info by default
            # Network and retry settings for better stability
            'socket_timeout': 30,  # Increase socket timeout
            'retries': 5,  # Number of retries for failed downloads
            'fragment_retries': 5,  # Number of retries for failed fragments
            'extractor_retries': 3,  # Number of retries for extractor errors
            'file_access_retries': 3,  # Number of retries for file access errors
            # User agent to avoid blocking
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            # Additional stability options
            'nocheckcertificate': True,  # Skip SSL certificate verification if needed
            'prefer_insecure': False,  # Prefer secure connections
            'cachedir': False,  # Disable caching to avoid issues
            # YouTube specific options
            'youtube_include_dash_manifest': False,  # Skip DASH manifest for faster extraction
            'youtube_skip_dash_manifest': True,  # Skip DASH manifest
            # Error handling
            'ignoreerrors': False,  # Don't ignore errors, we want to handle them
            'abort_on_error': False,  # Don't abort on first error
        }
        
        # Add proxy if available
        if proxy:
            self.ydl_opts['proxy'] = proxy
            logger.info(f"Using proxy: {proxy}")
        
        # Add alternative DNS servers for better connectivity
        self.ydl_opts.update({
            'source_address': '0.0.0.0',  # Bind to all interfaces
        })
        
        self.transcript_api = YouTubeTranscriptApi()
    
    async def get_video_info(self, video_url: str) -> Dict:
        """
        Extract video metadata without downloading using yt-dlp.
        Based on Context7 documentation for extracting video information.
        """
        try:
            logger.info(f"Extracting info for video: {video_url}")
            
            # Run yt-dlp in executor to avoid blocking
            loop = asyncio.get_event_loop()
            video_info = await loop.run_in_executor(
                None, 
                self._extract_video_info_sync, 
                video_url
            )
            
            # Validate video duration
            duration = video_info.get('duration', 0)
            if duration > settings.max_video_duration:
                raise ValueError(
                    f"Video duration ({duration}s) exceeds maximum allowed "
                    f"({settings.max_video_duration}s)"
                )
            
            return {
                'id': video_info.get('id'),
                'title': video_info.get('title'),
                'description': video_info.get('description', ''),
                'duration': duration,
                'upload_date': video_info.get('upload_date'),
                'uploader': video_info.get('uploader'),
                'view_count': video_info.get('view_count'),
                'thumbnail': video_info.get('thumbnail'),
                'subtitles_available': bool(video_info.get('subtitles')),
                'automatic_captions_available': bool(video_info.get('automatic_captions'))
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info for {video_url}: {e}")
            raise
    
    def _extract_video_info_sync(self, video_url: str) -> Dict:
        """Synchronous video info extraction for executor."""
        # Try with different configurations if first attempt fails
        configs_to_try = [
            self.ydl_opts,  # Default config
            {**self.ydl_opts, 'socket_timeout': 60, 'retries': 10},  # Extended timeouts
            {**self.ydl_opts, 'nocheckcertificate': True, 'prefer_insecure': True},  # Relaxed security
            # Alternative User-Agent
            {**self.ydl_opts, 'http_headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }},
            # Mobile User-Agent
            {**self.ydl_opts, 'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
            }},
            # Minimal config with basic options only
            {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'socket_timeout': 30,
                'retries': 3,
            }
        ]
        
        last_error = None
        for i, config in enumerate(configs_to_try):
            try:
                logger.info(f"Attempting video info extraction (attempt {i+1}/{len(configs_to_try)}) for URL: {video_url}")
                
                # Add debug logging for configuration
                if settings.debug:
                    logger.debug(f"Using config: socket_timeout={config.get('socket_timeout')}, retries={config.get('retries')}")
                
                with yt_dlp.YoutubeDL(config) as ydl:
                    # Extract info without downloading - Context7 pattern
                    logger.info("Starting yt-dlp extraction...")
                    info = ydl.extract_info(video_url, download=False)
                    logger.info(f"Successfully extracted info for video: {info.get('title', 'Unknown')}")
                    return ydl.sanitize_info(info)
                    
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                logger.warning(f"Attempt {i+1} failed with {error_type}: {str(e)[:200]}...")
                
                # Special handling for specific error types
                if "Failed to extract any player response" in str(e):
                    logger.warning("YouTube player response extraction failed - this may be a temporary YouTube issue")
                elif "Read timed out" in str(e):
                    logger.warning("Network timeout occurred - retrying with extended timeout")
                elif "Connection broken" in str(e):
                    logger.warning("Network connection issue - retrying")
                
                if i < len(configs_to_try) - 1:
                    import time
                    wait_time = 2 * (i + 1)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                continue
        
        # If all attempts failed, raise the last error
        raise last_error
    
    async def get_video_transcripts(self, video_id: str) -> Dict:
        """
        Extract video transcripts using youtube-transcript-api.
        Based on Context7 documentation patterns.
        """
        try:
            logger.info(f"Extracting transcripts for video: {video_id}")
            
            # Run transcript extraction in executor
            loop = asyncio.get_event_loop()
            transcript_data = await loop.run_in_executor(
                None,
                self._extract_transcripts_sync,
                video_id
            )
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error extracting transcripts for {video_id}: {e}")
            return {
                'transcripts': [],
                'language': None,
                'is_generated': None,
                'error': str(e)
            }
    
    def _extract_transcripts_sync(self, video_id: str) -> Dict:
        """
        Synchronous transcript extraction using Context7 patterns.
        Implements fallback strategy: manual -> auto-generated -> any available
        """
        try:
            # Get list of available transcripts - Context7 pattern
            transcript_list = self.transcript_api.list(video_id)
            
            # Try to find manual transcript first (any language)
            try:
                # Try English first
                transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
                logger.info(f"Found manual English transcript for {video_id}")
            except:
                try:
                    # Try Russian
                    transcript = transcript_list.find_manually_created_transcript(['ru'])
                    logger.info(f"Found manual Russian transcript for {video_id}")
                except:
                    try:
                        # Try any manually created transcript
                        for available_transcript in transcript_list:
                            if not available_transcript.is_generated:
                                transcript = available_transcript
                                logger.info(f"Found manual transcript in {transcript.language} for {video_id}")
                                break
                        else:
                            raise Exception("No manual transcripts found")
                    except:
                        # Fallback to auto-generated - Context7 pattern
                        try:
                            # Try English auto-generated
                            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                            logger.info(f"Found auto-generated English transcript for {video_id}")
                        except:
                            try:
                                # Try Russian auto-generated
                                transcript = transcript_list.find_generated_transcript(['ru'])
                                logger.info(f"Found auto-generated Russian transcript for {video_id}")
                            except:
                                # Try any auto-generated transcript
                                for available_transcript in transcript_list:
                                    if available_transcript.is_generated:
                                        transcript = available_transcript
                                        logger.info(f"Found auto-generated transcript in {transcript.language} for {video_id}")
                                        break
                                else:
                                    raise Exception("No transcripts available")
            
            # Fetch transcript data - Context7 pattern
            fetched_transcript = transcript.fetch()
            
            # Convert to list format - Context7 pattern shows this structure
            transcript_segments = []
            for segment in fetched_transcript:
                transcript_segments.append({
                    'text': segment.text,
                    'start': segment.start,
                    'duration': segment.duration
                })
            
            return {
                'transcripts': transcript_segments,
                'language': transcript.language,
                'language_code': transcript.language_code,
                'is_generated': transcript.is_generated,
                'total_segments': len(transcript_segments),
                'total_duration': sum(seg['duration'] for seg in transcript_segments)
            }
            
        except Exception as e:
            # If no transcripts available, return empty result
            logger.warning(f"No transcripts available for video {video_id}: {e}")
            return {
                'transcripts': [],
                'language': None,
                'language_code': None,
                'is_generated': None,
                'error': f"No transcripts available: {str(e)}"
            }
    
    async def extract_video_frames(self, video_url: str, num_frames: int = 5) -> List[str]:
        """
        Extract key frames from video using yt-dlp and FFmpeg.
        Based on Context7 yt-dlp documentation for video processing.
        """
        try:
            logger.info(f"Extracting {num_frames} frames from video: {video_url}")
            
            # Create temporary directory for frames
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Configure yt-dlp for video download and frame extraction
                frame_opts = {
                    **self.ydl_opts,
                    'skip_download': False,
                    'format': 'best[height<=480]',  # Lower quality for frame extraction
                    'outtmpl': str(temp_path / '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }]
                }
                
                # Run extraction in executor
                loop = asyncio.get_event_loop()
                video_path = await loop.run_in_executor(
                    None,
                    self._download_video_sync,
                    video_url,
                    frame_opts,
                    temp_path
                )
                
                if not video_path or not video_path.exists():
                    raise Exception("Failed to download video for frame extraction")
                
                # Extract frames using FFmpeg
                frame_paths = await loop.run_in_executor(
                    None,
                    self._extract_frames_sync,
                    video_path,
                    temp_path,
                    num_frames
                )
                
                # Read frame files and encode as base64
                frame_data = []
                for frame_path in frame_paths:
                    if frame_path.exists():
                        with open(frame_path, 'rb') as f:
                            import base64
                            frame_data.append(base64.b64encode(f.read()).decode('utf-8'))
                
                return frame_data
                
        except Exception as e:
            logger.error(f"Error extracting frames from {video_url}: {e}")
            return []
    
    def _download_video_sync(self, video_url: str, opts: Dict, temp_path: Path) -> Optional[Path]:
        """Synchronous video download for executor."""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Download video - Context7 pattern
                ydl.download([video_url])
                
                # Find downloaded video file
                for file_path in temp_path.glob('*'):
                    if file_path.is_file() and file_path.suffix in ['.mp4', '.webm', '.mkv']:
                        return file_path
                
            return None
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def _extract_frames_sync(self, video_path: Path, output_dir: Path, num_frames: int) -> List[Path]:
        """Extract frames using FFmpeg."""
        try:
            import subprocess
            
            frame_paths = []
            
            # Get video duration first
            duration_cmd = [
                settings.ffmpeg_binary_path, '-i', str(video_path),
                '-f', 'null', '-', '-v', 'quiet'
            ]
            
            try:
                # Try to get duration from ffprobe first
                probe_cmd = [
                    'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                    '-show_entries', 'stream=duration', '-of', 'csv=p=0', str(video_path)
                ]
                duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                if duration_result.returncode == 0 and duration_result.stdout.strip():
                    total_duration = float(duration_result.stdout.strip())
                else:
                    # Fallback: use a reasonable default duration
                    total_duration = 600.0  # 10 minutes default
                    logger.warning(f"Could not determine video duration, using default {total_duration}s")
            except:
                total_duration = 600.0
                logger.warning(f"ffprobe not available, using default duration {total_duration}s")
            
            # Calculate frame extraction times in seconds
            for i in range(num_frames):
                # Extract frames at evenly spaced intervals
                frame_time_seconds = (i + 1) * total_duration / (num_frames + 1)
                frame_output = output_dir / f'frame_{i:03d}.jpg'
                
                cmd = [
                    settings.ffmpeg_binary_path,
                    '-i', str(video_path),
                    '-ss', str(frame_time_seconds),  # Use seconds instead of percentage
                    '-vframes', '1',
                    '-q:v', '2',  # High quality
                    str(frame_output),
                    '-y'  # Overwrite output files
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and frame_output.exists():
                    frame_paths.append(frame_output)
                    logger.info(f"Successfully extracted frame {i} at {frame_time_seconds:.1f}s")
                else:
                    logger.warning(f"Failed to extract frame {i}: {result.stderr}")
            
            return frame_paths
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            return []
    
    async def process_video_complete(self, video_url: str) -> Dict:
        """
        Complete video processing pipeline.
        Extract info, transcripts, and key frames.
        """
        try:
            logger.info(f"Starting complete processing for video: {video_url}")
            
            # Extract video info
            video_info = await self.get_video_info(video_url)
            video_id = video_info['id']
            
            # Extract transcripts and frames in parallel (if enabled)
            transcript_task = asyncio.create_task(self.get_video_transcripts(video_id))
            
            if settings.extract_video_frames:
                frames_task = asyncio.create_task(self.extract_video_frames(video_url, settings.max_frames_count))
                transcripts, frames = await asyncio.gather(transcript_task, frames_task)
                logger.info(f"Extracted {len(frames)} video frames")
            else:
                transcripts = await transcript_task
                frames = []
                logger.info("Video frame extraction is disabled in settings")
            
            result = {
                'video_info': video_info,
                'transcripts': transcripts,
                'frames': frames,
                'processing_status': 'completed',
                'timestamp': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Completed processing for video {video_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in complete video processing: {e}")
            return {
                'video_info': {},
                'transcripts': {'transcripts': [], 'error': str(e)},
                'frames': [],
                'processing_status': 'failed',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }
    
    async def extract_raw_subtitles(self, video_url: str) -> dict:
        """
        Извлечение оригинальных субтитров YouTube видео без обработки ИИ
        
        Args:
            video_url (str): URL YouTube видео
            
        Returns:
            dict: Структурированные данные субтитров
            
        Raises:
            Exception: Если субтитры недоступны или видео недоступно
        """
        try:
            # Получаем video_id через существующий валидатор
            video_id = extract_video_id(video_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
                
            # Получаем метаданные видео
            video_info = await self.get_video_info(video_url)
            
            # Попробуем извлечь субтитры через youtube-transcript-api
            subtitle_data = None
            language = None
            language_code = None
            auto_generated = True
            
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Приоритет: ручные субтитры > автогенерированные
                transcript = None
                
                try:
                    # Попробуем найти ручные субтитры на русском или английском
                    transcript = transcript_list.find_manually_created_transcript(['ru', 'en'])
                    auto_generated = False
                    logger.info(f"Found manual transcript for {video_id}")
                except NoTranscriptFound:
                    try:
                        # Если ручных нет, используем автогенерированные
                        transcript = transcript_list.find_generated_transcript(['ru', 'en'])
                        auto_generated = True
                        logger.info(f"Found auto-generated transcript for {video_id}")
                    except NoTranscriptFound:
                        raise Exception(f"No subtitles available via transcript API for video {video_id}")
                
                # Получаем текст субтитров
                subtitle_data = transcript.fetch()
                language = transcript.language
                language_code = transcript.language_code
                logger.info(f"Successfully fetched {len(subtitle_data)} subtitle segments for {video_id}")
                
            except Exception as transcript_error:
                logger.warning(f"youtube-transcript-api failed: {transcript_error}")
                logger.info("Trying fallback method with yt-dlp...")
                
                # Fallback: используем yt-dlp для извлечения субтитров
                try:
                    subtitle_data, language, language_code, auto_generated = await self._extract_subtitles_with_ytdlp(video_url, video_id)
                    logger.info(f"Successfully extracted subtitles via yt-dlp fallback")
                except Exception as ytdlp_error:
                    logger.error(f"Both methods failed. transcript-api: {transcript_error}, yt-dlp: {ytdlp_error}")
                    raise Exception(f"No subtitles available for video {video_id}. Tried both youtube-transcript-api and yt-dlp.")
            
            return {
                "video_id": video_id,
                "title": video_info.get("title", "Unknown Title"),
                "duration": video_info.get("duration", 0),
                "channel": video_info.get("uploader", "Unknown Channel"),
                "subtitles": subtitle_data,
                "language": language,
                "language_code": language_code,
                "auto_generated": auto_generated,
                "subtitle_count": len(subtitle_data) if subtitle_data else 0
            }
            
        except Exception as e:
            logger.error(f"Error extracting raw subtitles for {video_url}: {str(e)}")
            raise 
    
    async def _extract_subtitles_with_ytdlp(self, video_url: str, video_id: str) -> tuple:
        """
        Fallback метод для извлечения субтитров через yt-dlp
        
        Returns:
            tuple: (subtitle_data, language, language_code, auto_generated)
        """
        try:
            # Конфигурация для извлечения субтитров
            subtitle_opts = {
                **self.ydl_opts,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'skip_download': True,
                'subtitleslangs': ['ru', 'en', 'en-US', 'en-GB'],
            }
            
            # Запускаем в executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_subtitles_sync,
                video_url,
                subtitle_opts
            )
            
            return result
            
        except Exception as e:
            logger.error(f"yt-dlp subtitle extraction failed: {e}")
            raise
    
    def _extract_subtitles_sync(self, video_url: str, opts: dict) -> tuple:
        """Синхронное извлечение субтитров через yt-dlp"""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Проверяем доступные субтитры
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                # Приоритет: ручные субтитры > автогенерированные
                subtitle_data = None
                language = None
                language_code = None
                auto_generated = True
                
                # Попробуем найти ручные субтитры
                for lang in ['ru', 'en', 'en-US', 'en-GB']:
                    if lang in subtitles and subtitles[lang]:
                        # Берем первый доступный формат субтитров
                        subtitle_info = subtitles[lang][0]
                        subtitle_data = self._download_subtitle_content(subtitle_info)
                        language = lang
                        language_code = lang
                        auto_generated = False
                        logger.info(f"Found manual subtitles in {lang}")
                        break
                
                # Если ручных нет, попробуем автогенерированные
                if not subtitle_data:
                    for lang in ['ru', 'en', 'en-US', 'en-GB']:
                        if lang in automatic_captions and automatic_captions[lang]:
                            subtitle_info = automatic_captions[lang][0]
                            subtitle_data = self._download_subtitle_content(subtitle_info)
                            language = lang
                            language_code = lang
                            auto_generated = True
                            logger.info(f"Found auto-generated subtitles in {lang}")
                            break
                
                if not subtitle_data:
                    raise Exception("No subtitles found in yt-dlp extraction")
                
                return subtitle_data, language, language_code, auto_generated
                
        except Exception as e:
            logger.error(f"Error in yt-dlp subtitle extraction: {e}")
            raise
    
    def _download_subtitle_content(self, subtitle_info: dict) -> list:
        """Загружает содержимое субтитров и конвертирует в нужный формат"""
        try:
            import requests
            import json
            
            url = subtitle_info.get('url')
            if not url:
                raise Exception("No subtitle URL found")
            
            # Загружаем субтитры
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Парсим JSON субтитры (YouTube API format)
            subtitle_data = []
            
            if subtitle_info.get('ext') == 'json3':
                # JSON3 формат YouTube
                data = json.loads(response.text)
                events = data.get('events', [])
                
                for event in events:
                    if 'segs' in event:
                        text_parts = []
                        for seg in event['segs']:
                            if 'utf8' in seg:
                                text_parts.append(seg['utf8'])
                        
                        if text_parts:
                            subtitle_data.append({
                                'text': ''.join(text_parts).strip(),
                                'start': event.get('tStartMs', 0) / 1000.0,
                                'duration': event.get('dDurationMs', 0) / 1000.0
                            })
            else:
                # Другие форматы - попробуем простой парсинг
                logger.warning(f"Unsupported subtitle format: {subtitle_info.get('ext')}")
                raise Exception(f"Unsupported subtitle format: {subtitle_info.get('ext')}")
            
            return subtitle_data
            
        except Exception as e:
            logger.error(f"Error downloading subtitle content: {e}")
            raise