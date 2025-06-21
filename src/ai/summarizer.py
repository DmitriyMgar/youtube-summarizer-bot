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

IMPORTANT LANGUAGE INSTRUCTIONS:
1. First priority: Always respond in the USER'S PREFERRED LANGUAGE as specified in the request
2. If user prefers Russian - respond in Russian regardless of video language
3. If user prefers English - respond in English regardless of video language  
4. If no user language preference is specified, match the video's transcript language

You will receive:
1. Video metadata (title, description, duration, etc.)
2. Complete transcript with timestamps  
3. Key video frames (if available)
4. User's preferred language setting

Create a summary that includes:
- Executive Summary (2-3 sentences)
- Key Points (bullet points of main topics)
- Detailed Summary (structured narrative)
- Timestamps of important segments
- Action items or takeaways (if applicable)

Format your response as structured text that's easy to read and professionally formatted.

Remember: ALWAYS prioritize the user's language preference over the video's original language!"""

        self.user_prompt_template = """Please summarize this YouTube video in the USER'S PREFERRED LANGUAGE: {user_language}

**Video Information:**
- Title: {title}
- Duration: {duration_formatted}
- Uploader: {uploader}
- Upload Date: {upload_date}
- Description: {description}
- Transcript Language: {transcript_language}
- USER'S PREFERRED LANGUAGE: {user_language}

**Video Transcript:**
{transcript_text}

**Frame Analysis:**
{frame_analysis}

CRITICAL: Generate the summary in {user_language}. This is the user's preferred language setting. Even if the video is in {transcript_language}, create the summary in {user_language} as requested by the user. Please provide a comprehensive summary following the format specified in the system prompt."""

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
        
        # Get transcript language info
        transcript_language = transcripts.get('language', 'Unknown')
        if transcript_language == 'Unknown' and transcripts.get('language_code'):
            # Map language codes to full names
            language_map = {
                'ru': 'Russian',
                'en': 'English',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese',
                'zh': 'Chinese',
                'ja': 'Japanese',
                'ko': 'Korean'
            }
            transcript_language = language_map.get(transcripts.get('language_code', ''), transcripts.get('language_code', 'Unknown'))
        
        # Get user's preferred language from settings
        user_language_code = settings.language
        user_language = 'Russian' if user_language_code == 'ru' else 'English'
        
        return self.user_prompt_template.format(
            title=video_info.get('title', 'Unknown Title'),
            duration_formatted=duration_formatted,
            uploader=video_info.get('uploader', 'Unknown'),
            upload_date=video_info.get('upload_date', 'Unknown'),
            description=description,
            transcript_text=transcript_text,
            frame_analysis=frame_analysis,
            transcript_language=transcript_language,
            user_language=user_language
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
                
                # Detect section headers (both English and Russian)
                line_lower = line.lower()
                
                # Executive Summary / Исполнительное резюме
                if any(header in line_lower for header in [
                    'executive summary', 'summary', 'исполнительное резюме', 'резюме', 'краткое содержание', 'краткое изложение', 'основная мысль'
                ]):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'executive_summary'
                    current_content = []
                    continue
                
                # Key Points / Ключевые моменты
                elif any(header in line_lower for header in [
                    'key points', 'main points', 'highlights', 'ключевые моменты', 'основные моменты', 'главные точки', 'ключевые пункты', 'важные моменты'
                ]):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'key_points'
                    current_content = []
                    continue
                
                # Detailed Summary / Подробное резюме
                elif any(header in line_lower for header in [
                    'detailed summary', 'detailed', 'overview', 'подробное резюме', 'подробное содержание', 'детальное резюме', 'полное изложение', 'подробное изложение'
                ]):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'detailed_summary'
                    current_content = []
                    continue
                
                # Timestamps / Временные метки
                elif any(header in line_lower for header in [
                    'timestamp', 'time', 'segments', 'временные метки', 'важные временные метки', 'временная разметка', 'временные отрезки', 'метки времени'
                ]):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'timestamps'
                    current_content = []
                    continue
                
                # Takeaways / Действия/Выводы
                elif any(header in line_lower for header in [
                    'takeaway', 'action', 'conclusion', 'действия', 'выводы', 'заключение', 'рекомендации', 'итоги', 'что делать'
                ]):
                    if current_section and current_content:
                        sections[current_section] = self._join_section_content(current_section, current_content)
                    current_section = 'takeaways'
                    current_content = []
                    continue
                
                # Skip markdown headers and bold formatting
                elif line.startswith('**') and line.endswith(':**'):
                    continue
                elif line.startswith('#'):
                    continue
                
                # Add content to current section
                if current_section:
                    # Clean up the line
                    cleaned_line = line.lstrip('•-* ').strip()
                    if cleaned_line:
                        current_content.append(cleaned_line)
                elif line and not line.startswith('**'):
                    # If no section detected yet, treat as executive summary
                    if not sections['executive_summary']:
                        sections['executive_summary'] = line
            
            # Handle remaining content
            if current_section and current_content:
                sections[current_section] = self._join_section_content(current_section, current_content)
            
            # Ensure we have at least some content
            if not sections['executive_summary'] and not sections['detailed_summary']:
                # Use the full text as executive summary if parsing failed
                sections['executive_summary'] = summary_text[:500] + '...' if len(summary_text) > 500 else summary_text
            
            # Clean up empty sections
            for key in ['executive_summary', 'detailed_summary']:
                if isinstance(sections[key], str):
                    sections[key] = sections[key].strip()
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}")
            return {
                'executive_summary': summary_text[:500] + '...' if len(summary_text) > 500 else summary_text,
                'detailed_summary': summary_text,
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

    async def summarize(self, transcript_data: dict) -> dict:
        """
        Создание конспекта на основе транскрипта
        
        Args:
            transcript_data: Данные транскрипта от YouTubeProcessor
            
        Returns:
            dict: Структурированный конспект
        """
        try:
            # Подготавливаем данные для суммаризации
            prepared_content = self._prepare_content(transcript_data)
            
            # Создаем промпт
            prompt = self._build_prompt(prepared_content, transcript_data)
            
            # Отправляем запрос к OpenAI
            response = await self._make_request(prompt)
            
            # Парсим и структурируем ответ
            structured_summary = self._parse_response(response)
            
            return {
                "video_id": transcript_data["video_id"],
                "title": transcript_data["title"],
                "channel": transcript_data["channel"],
                "duration": transcript_data["duration"],
                "summary": structured_summary,
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model_name,
                "language": transcript_data.get("language", "auto")
            }
            
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}")
            raise

    async def correct_transcript(self, subtitle_data: dict) -> dict:
        """
        Исправление субтитров с помощью ИИ
        
        Args:
            subtitle_data: Данные субтитров из extract_raw_subtitles
            
        Returns:
            dict: Исправленные субтитры с сохранением временных меток
        """
        try:
            # Подготавливаем текст для ИИ обработки
            raw_text = self._prepare_text_for_correction(subtitle_data["subtitles"])
            
            # Создаем промпт для коррекции
            correction_prompt = self._build_correction_prompt(raw_text, subtitle_data)
            
            # Отправляем запрос к OpenAI
            response = await self._make_correction_request(correction_prompt)
            
            # Парсим ответ и восстанавливаем временные метки
            corrected_subtitles = self._parse_corrected_response(response, subtitle_data["subtitles"])
            
            # Возвращаем обновленные данные
            result = subtitle_data.copy()
            result["subtitles"] = corrected_subtitles
            result["corrected"] = True
            result["correction_method"] = "ai_grammar_fix"
            
            return result
            
        except Exception as e:
            logger.error(f"Error correcting transcript: {str(e)}")
            raise

    def _prepare_text_for_correction(self, subtitles: list) -> str:
        """Подготовка текста субтитров для ИИ коррекции"""
        # Группируем короткие фразы в предложения
        sentences = []
        current_sentence = []
        
        for i, subtitle in enumerate(subtitles):
            text = subtitle.text if hasattr(subtitle, 'text') else subtitle["text"]
            text = text.strip()
            
            if not text:
                continue
                
            # Добавляем маркер временной метки для сохранения структуры
            marked_text = f"[{i}]{text}"
            current_sentence.append(marked_text)
            
            # Если предложение заканчивается или достигли лимита
            if text.endswith(('.', '!', '?')) or len(current_sentence) >= 5:
                sentences.append(' '.join(current_sentence))
                current_sentence = []
        
        # Добавляем остатки
        if current_sentence:
            sentences.append(' '.join(current_sentence))
        
        return '\n'.join(sentences)

    def _build_correction_prompt(self, text: str, subtitle_data: dict) -> str:
        """Создание промпта для коррекции субтитров"""
        language = subtitle_data.get("language", "русский")
        auto_generated = subtitle_data.get("auto_generated", True)
        
        correction_type = "автоматически сгенерированных" if auto_generated else "ручных"
        
        prompt = f"""
Задача: Исправить грамматику, пунктуацию и структуру текста {correction_type} субтитров видео.

Видео: "{subtitle_data.get('title', 'Неизвестно')}"
Язык: {language}
Тип субтитров: {correction_type}

ВАЖНО: 
1. Сохраняй маркеры [номер] в начале каждого сегмента - они нужны для синхронизации
2. Исправляй только грамматику, пунктуацию и структуру предложений
3. НЕ изменяй смысл и содержание
4. НЕ добавляй новую информацию
5. Объединяй короткие фразы в полные предложения где это логично
6. Убирай повторы и заикания
7. Улучшай читаемость, сохраняя естественность речи

Исходный текст субтитров:
{text}

Исправленный текст:"""

        return prompt

    async def _make_correction_request(self, prompt: str) -> str:
        """Отправка запроса к OpenAI для коррекции"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты эксперт по редактированию текстов. Твоя задача - улучшить качество субтитров, сохраняя их смысл и структуру временных меток."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.3,  # Низкая температура для более точной коррекции
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error during correction: {str(e)}")
            raise

    def _parse_corrected_response(self, corrected_text: str, original_subtitles: list) -> list:
        """Парсинг исправленного текста и восстановление временных меток"""
        corrected_segments = []
        lines = corrected_text.split('\n')
        
        # Создаем словарь для быстрого поиска оригинальных данных
        original_map = {}
        for i, subtitle in enumerate(original_subtitles):
            original_map[i] = subtitle
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Ищем маркеры [номер] в тексте
            import re
            markers = re.findall(r'\[(\d+)\]', line)
            
            if markers:
                # Получаем первый маркер как основу для временной метки
                base_index = int(markers[0])
                
                # Убираем все маркеры из текста
                cleaned_text = re.sub(r'\[\d+\]', '', line).strip()
                
                if cleaned_text and base_index in original_map:
                    # Создаем новый сегмент с исправленным текстом
                    original = original_map[base_index]
                    
                    corrected_segment = {
                        "start": original.start if hasattr(original, 'start') else original["start"],
                        "duration": original.duration if hasattr(original, 'duration') else original["duration"],
                        "text": cleaned_text
                    }
                    
                    corrected_segments.append(corrected_segment)
        
        # Если что-то пошло не так, возвращаем оригинал
        if not corrected_segments:
            logger.warning("Failed to parse corrected subtitles, returning original")
            return original_subtitles
        
        return corrected_segments 