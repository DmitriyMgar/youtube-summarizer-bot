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

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class YouTubeProcessor:
    """Process YouTube videos to extract subtitles and metadata."""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': not settings.debug,
            'no_warnings': not settings.debug,
            'extractaudio': False,
            'format': 'best[height<=720]',  # Limit quality for faster processing
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB', 'ru'],  # Added Russian language support
            'skip_download': True,  # Only extract info by default
        }
        
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
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            # Extract info without downloading - Context7 pattern
            info = ydl.extract_info(video_url, download=False)
            return ydl.sanitize_info(info)
    
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
            
            # Extract transcripts and frames in parallel
            transcript_task = asyncio.create_task(self.get_video_transcripts(video_id))
            frames_task = asyncio.create_task(self.extract_video_frames(video_url, 3))
            
            transcripts, frames = await asyncio.gather(transcript_task, frames_task)
            
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