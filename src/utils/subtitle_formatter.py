"""
Subtitle Formatter for YouTube Video Summarizer Bot
Formats subtitles for Telegram delivery
"""

from typing import List, Dict, Any
import textwrap
from datetime import timedelta


class SubtitleFormatter:
    """Форматирование субтитров для отправки в Telegram"""
    
    MAX_MESSAGE_LENGTH = 4000  # Лимит Telegram с запасом
    
    def __init__(self):
        self.current_format = "plain"  # plain, timestamps, structured
    
    def format_for_telegram(self, subtitle_data: Dict[str, Any]) -> List[str]:
        """
        Основной метод форматирования субтитров для Telegram
        
        Args:
            subtitle_data: Данные субтитров из extract_raw_subtitles
            
        Returns:
            List[str]: Список сообщений для отправки
        """
        # Создаем заголовок с метаинформацией
        header = self._create_header(subtitle_data)
        
        # Форматируем текст субтитров
        formatted_text = self._format_subtitle_text(subtitle_data["subtitles"])
        
        # Объединяем заголовок и текст
        full_text = f"{header}\n{formatted_text}"
        
        # Разбиваем на части если необходимо
        return self._split_into_messages(full_text, header)
    
    def _create_header(self, data: Dict[str, Any]) -> str:
        """Создание заголовка с метаинформацией"""
        duration_str = self._format_duration(data["duration"])
        auto_gen_str = "🤖 Автогенерированные" if data["auto_generated"] else "👤 Ручные"
        
        header = (
            f"📺 **{data['title']}**\n"
            f"📺 {data['channel']}\n"
            f"⏱ Длительность: {duration_str}\n"
            f"🗣 Язык: {data['language']} ({data['language_code']})\n"
            f"📝 Тип: {auto_gen_str}\n"
            f"📊 Сегментов: {data['subtitle_count']}\n"
            f"{'─' * 30}"
        )
        
        return header
    
    def _format_subtitle_text(self, subtitles: List[Dict]) -> str:
        """Форматирование текста субтитров"""
        if self.current_format == "timestamps":
            return self._format_with_timestamps(subtitles)
        else:
            return self._format_plain_text(subtitles)
    
    def _format_plain_text(self, subtitles: List[Dict]) -> str:
        """Простой текстовый формат без временных меток"""
        text_parts = []
        current_paragraph = []
        
        for subtitle in subtitles:
            # Поддержка как словарей, так и объектов FetchedTranscriptSnippet
            if hasattr(subtitle, 'text'):
                text = subtitle.text.strip()
            else:
                text = subtitle.get("text", "").strip()
                
            if not text:
                continue
                
            # Группируем короткие фразы в абзацы
            current_paragraph.append(text)
            
            # Если предложение заканчивается точкой или достигли лимита
            if text.endswith(('.', '!', '?')) or len(current_paragraph) >= 3:
                text_parts.append(' '.join(current_paragraph))
                current_paragraph = []
        
        # Добавляем остатки
        if current_paragraph:
            text_parts.append(' '.join(current_paragraph))
        
        return '\n\n'.join(text_parts)
    
    def _format_with_timestamps(self, subtitles: List[Dict]) -> str:
        """Форматирование с временными метками"""
        formatted_lines = []
        
        for subtitle in subtitles:
            # Поддержка как словарей, так и объектов FetchedTranscriptSnippet
            if hasattr(subtitle, 'start'):
                start_time = self._seconds_to_timestamp(subtitle.start)
                text = subtitle.text.strip()
            else:
                start_time = self._seconds_to_timestamp(subtitle.get("start", 0))
                text = subtitle.get("text", "").strip()
            
            if text:
                formatted_lines.append(f"[{start_time}] {text}")
        
        return '\n'.join(formatted_lines)
    
    def _split_into_messages(self, full_text: str, header: str) -> List[str]:
        """Разбивка длинного текста на сообщения"""
        if len(full_text) <= self.MAX_MESSAGE_LENGTH:
            return [full_text]
        
        messages = []
        lines = full_text.split('\n')
        header_lines = header.split('\n')
        content_lines = lines[len(header_lines):]
        
        current_message = header
        message_count = 0
        total_messages = self._estimate_message_count(content_lines)
        
        for line in content_lines:
            # Проверяем, поместится ли строка в текущее сообщение
            test_message = f"{current_message}\n{line}"
            
            if len(test_message) <= self.MAX_MESSAGE_LENGTH:
                current_message = test_message
            else:
                # Добавляем номер части к заголовку
                if message_count > 0:
                    part_header = f"📄 Часть {message_count + 1}/{total_messages}\n{'─' * 30}"
                    current_message = current_message.replace(header, part_header)
                
                messages.append(current_message)
                message_count += 1
                
                # Начинаем новое сообщение
                part_header = f"📄 Часть {message_count + 1}/{total_messages}\n{'─' * 30}"
                current_message = f"{part_header}\n{line}"
        
        # Добавляем последнее сообщение
        if current_message.strip():
            if message_count > 0:
                part_header = f"📄 Часть {message_count + 1}/{total_messages}\n{'─' * 30}"
                current_message = current_message.replace(header, part_header)
            messages.append(current_message)
        
        return messages
    
    def _estimate_message_count(self, lines: List[str]) -> int:
        """Приблизительная оценка количества сообщений"""
        total_chars = sum(len(line) for line in lines)
        return max(1, (total_chars // self.MAX_MESSAGE_LENGTH) + 1)
    
    def _format_duration(self, seconds: int) -> str:
        """Форматирование длительности видео"""
        return str(timedelta(seconds=seconds))
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Конвертация секунд в timestamp формат MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def format_for_file(self, subtitle_data: Dict[str, Any]) -> str:
        """
        Форматирование субтитров для сохранения в TXT файл
        
        Args:
            subtitle_data: Данные субтитров из extract_raw_subtitles
            
        Returns:
            str: Полный текст для записи в файл
        """
        # Создаем заголовок с метаинформацией
        header = self._create_header(subtitle_data)
        
        # Форматируем текст субтитров
        formatted_text = self._format_subtitle_text(subtitle_data["subtitles"])
        
        # Объединяем заголовок и текст
        full_text = f"{header}\n\n{formatted_text}"
        
        return full_text 