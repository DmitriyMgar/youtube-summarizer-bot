"""
AI Video Summarizer - OpenAI Integration
Based on OpenAI Context7 documentation patterns for chat completions
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoSummarizer:
    """AI-powered video summarization using OpenAI API."""
    
    def __init__(self):
        # Initialize OpenAI client - Context7 pattern
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key
        )
        
        # Summarization prompts
        self.system_prompt = """You are an expert video content summarizer. Your task is to analyze YouTube video content and create comprehensive, well-structured summaries.

You will receive:
1. Video metadata (title, description, duration, etc.)
2. Complete transcript with timestamps
3. Key video frames (if available)

Create a summary that includes:
- Executive Summary (2-3 sentences)
- Key Points (bullet points of main topics)
- Detailed Summary (structured narrative)
- Timestamps of important segments
- Action items or takeaways (if applicable)

Format your response as structured text that's easy to read and professionally formatted."""

        self.user_prompt_template = """Please summarize this YouTube video:

**Video Information:**
- Title: {title}
- Duration: {duration_formatted}
- Uploader: {uploader}
- Upload Date: {upload_date}
- Description: {description}

**Video Transcript:**
{transcript_text}

**Frame Analysis:**
{frame_analysis}

Please provide a comprehensive summary following the format specified in the system prompt."""

    async def summarize_video(self, video_data: Dict) -> Dict:
        """
        Generate AI summary of video content.
        Uses OpenAI chat completions API - Context7 pattern.
        """
        try:
            logger.info(f"Starting AI summarization for video {video_data.get('video_info', {}).get('id', 'unknown')}")
            
            # Prepare content for AI analysis
            formatted_content = self._format_video_content(video_data)
            
            # Create chat completion request - Context7 pattern
            completion = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": formatted_content}
                ],
                max_tokens=settings.openai_max_tokens,
                temperature=0.3,  # Lower temperature for more consistent summaries
                stream=False
            )
            
            # Extract summary from response - Context7 pattern
            summary_text = completion.choices[0].message.content
            
            # Parse and structure the summary
            structured_summary = self._parse_summary_response(summary_text)
            
            # Add metadata
            result = {
                'summary': structured_summary,
                'ai_model': settings.openai_model,
                'tokens_used': completion.usage.total_tokens if completion.usage else 0,
                'timestamp': datetime.utcnow().isoformat(),
                'video_id': video_data.get('video_info', {}).get('id'),
                'processing_status': 'completed'
            }
            
            logger.info(f"Completed AI summarization, tokens used: {result['tokens_used']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI summarization: {e}")
            return {
                'summary': {
                    'executive_summary': 'Failed to generate summary due to AI processing error.',
                    'error': str(e)
                },
                'processing_status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _format_video_content(self, video_data: Dict) -> str:
        """Format video data for AI analysis."""
        video_info = video_data.get('video_info', {})
        transcripts = video_data.get('transcripts', {})
        frames = video_data.get('frames', [])
        
        # Format duration
        duration = video_info.get('duration', 0)
        duration_formatted = f"{duration // 60}:{duration % 60:02d}"
        
        # Format transcript
        transcript_text = self._format_transcript(transcripts.get('transcripts', []))
        
        # Analyze frames (if available)
        frame_analysis = self._analyze_frames(frames) if frames else "No frames available for analysis."
        
        # Truncate description if too long
        description = video_info.get('description', '')[:500]
        if len(video_info.get('description', '')) > 500:
            description += '...'
        
        return self.user_prompt_template.format(
            title=video_info.get('title', 'Unknown Title'),
            duration_formatted=duration_formatted,
            uploader=video_info.get('uploader', 'Unknown'),
            upload_date=video_info.get('upload_date', 'Unknown'),
            description=description,
            transcript_text=transcript_text,
            frame_analysis=frame_analysis
        )
    
    def _format_transcript(self, transcript_segments: List[Dict]) -> str:
        """Format transcript segments with timestamps."""
        if not transcript_segments:
            return "No transcript available."
        
        formatted_lines = []
        for segment in transcript_segments:
            timestamp = self._format_timestamp(segment.get('start', 0))
            text = segment.get('text', '').strip()
            if text:
                formatted_lines.append(f"[{timestamp}] {text}")
        
        # Limit transcript length to prevent token overflow
        full_transcript = '\n'.join(formatted_lines)
        if len(full_transcript) > 8000:  # Rough character limit
            # Truncate and add notice
            truncated = full_transcript[:8000]
            last_newline = truncated.rfind('\n')
            if last_newline > 0:
                truncated = truncated[:last_newline]
            full_transcript = truncated + '\n\n[Transcript truncated for length...]'
        
        return full_transcript
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _analyze_frames(self, frames: List[str]) -> str:
        """Provide basic frame analysis description."""
        if not frames:
            return "No frames available for analysis."
        
        return f"Video contains {len(frames)} key frames extracted for visual context analysis. " \
               f"These frames provide visual information to supplement the transcript analysis."
    
    def _parse_summary_response(self, summary_text: str) -> Dict:
        """Parse AI response into structured summary."""
        try:
            # Try to extract structured sections from the response
            sections = {
                'executive_summary': '',
                'key_points': [],
                'detailed_summary': '',
                'timestamps': [],
                'takeaways': [],
                'raw_summary': summary_text
            }
            
            lines = summary_text.split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect section headers
                line_lower = line.lower()
                if any(header in line_lower for header in ['executive summary', 'summary']):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'executive_summary'
                    current_content = []
                elif any(header in line_lower for header in ['key points', 'main points', 'highlights']):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'key_points'
                    current_content = []
                elif any(header in line_lower for header in ['detailed summary', 'detailed', 'overview']):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'detailed_summary'
                    current_content = []
                elif any(header in line_lower for header in ['timestamp', 'time', 'segments']):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'timestamps'
                    current_content = []
                elif any(header in line_lower for header in ['takeaway', 'action', 'conclusion']):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'takeaways'
                    current_content = []
                else:
                    # Add content to current section
                    if current_section:
                        current_content.append(line)
                    elif not sections['executive_summary'] and line:
                        # If no section detected, treat as executive summary
                        sections['executive_summary'] = line
            
            # Handle remaining content
            if current_section and current_content:
                sections[current_section] = self._join_section_content(current_section, current_content)
            
            # Ensure we have at least some content
            if not sections['executive_summary'] and not sections['detailed_summary']:
                sections['executive_summary'] = summary_text[:300] + '...' if len(summary_text) > 300 else summary_text
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}")
            return {
                'executive_summary': summary_text[:300] + '...' if len(summary_text) > 300 else summary_text,
                'raw_summary': summary_text,
                'parse_error': str(e)
            }
    
    def _join_section_content(self, section: str, content: List[str]) -> str:
        """Join section content appropriately."""
        if section in ['key_points', 'timestamps', 'takeaways']:
            # For list-type sections, return as list items
            return [item.lstrip('•-* ') for item in content if item.strip()]
        else:
            # For text sections, join as paragraphs
            return '\n'.join(content)
    
    async def analyze_video_sentiment(self, video_data: Dict) -> Dict:
        """
        Optional: Analyze video sentiment and tone.
        Additional AI analysis using Context7 patterns.
        """
        try:
            transcripts = video_data.get('transcripts', {})
            if not transcripts.get('transcripts'):
                return {'sentiment': 'neutral', 'confidence': 0.0, 'error': 'No transcript available'}
            
            # Create a simplified sentiment analysis request
            transcript_text = ' '.join([
                segment.get('text', '') 
                for segment in transcripts.get('transcripts', [])[:20]  # First 20 segments only
            ])
            
            completion = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "Analyze the sentiment and tone of this video transcript. Respond with: sentiment (positive/negative/neutral), confidence (0-1), and brief explanation."},
                    {"role": "user", "content": f"Transcript: {transcript_text[:1000]}"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            response = completion.choices[0].message.content
            
            return {
                'sentiment_analysis': response,
                'tokens_used': completion.usage.total_tokens if completion.usage else 0
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {'sentiment': 'neutral', 'confidence': 0.0, 'error': str(e)} 