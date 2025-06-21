"""
Тесты для функции извлечения субтитров без ИИ обработки
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.youtube.processor import YouTubeProcessor
from src.utils.subtitle_formatter import SubtitleFormatter
from src.bot.handlers import BotHandlers


class TestRawSubtitles:
    """Тесты для функции извлечения субтитров"""
    
    @pytest.fixture
    def sample_subtitle_data(self):
        """Тестовые данные субтитров"""
        return {
            "video_id": "dQw4w9WgXcQ",
            "title": "Test Video Title",
            "duration": 212,
            "channel": "Test Channel",
            "subtitles": [
                {"start": 0.0, "duration": 3.0, "text": "Hello world"},
                {"start": 3.0, "duration": 2.0, "text": "This is a test"},
                {"start": 5.0, "duration": 4.0, "text": "Testing subtitles"}
            ],
            "language": "English",
            "language_code": "en",
            "auto_generated": False,
            "subtitle_count": 3
        }
    
    @pytest.mark.asyncio
    async def test_extract_raw_subtitles_success(self, sample_subtitle_data):
        """Тест успешного извлечения субтитров"""
        processor = YouTubeProcessor()
        
        with patch('src.youtube.processor.YouTubeTranscriptApi') as mock_api, \
             patch.object(processor, 'get_video_info') as mock_get_info, \
             patch('src.youtube.processor.extract_video_id') as mock_extract_id:
            
            # Настраиваем mock для extract_video_id
            mock_extract_id.return_value = "dQw4w9WgXcQ"
            
            # Настраиваем mock для get_video_info
            mock_get_info.return_value = {
                "title": "Test Video Title",
                "duration": 212,
                "uploader": "Test Channel"
            }
            
            # Настраиваем mock для transcript API
            mock_transcript = Mock()
            mock_transcript.fetch.return_value = sample_subtitle_data["subtitles"]
            mock_transcript.language = "English"
            mock_transcript.language_code = "en"
            
            mock_transcript_list = Mock()
            mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript
            mock_api.list_transcripts.return_value = mock_transcript_list
            
            # Тестируем
            result = await processor.extract_raw_subtitles("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            
            assert result["video_id"] == "dQw4w9WgXcQ"
            assert len(result["subtitles"]) == 3
            assert result["language"] == "English"
            assert result["auto_generated"] == False
    
    def test_subtitle_formatter_plain_text(self, sample_subtitle_data):
        """Тест форматирования в простой текст"""
        formatter = SubtitleFormatter()
        result = formatter.format_for_file(sample_subtitle_data)
        
        assert isinstance(result, str)
        assert "Test Video Title" in result
        assert "Hello world" in result
        assert "Test Channel" in result
    
    def test_subtitle_formatter_message_splitting(self):
        """Тест генерации файла с длинными субтитрами"""
        formatter = SubtitleFormatter()
        
        # Создаем длинные субтитры
        long_subtitles = {
            "video_id": "test",
            "title": "Long Video",
            "duration": 3600,
            "channel": "Test Channel",
            "subtitles": [
                {"start": i, "duration": 1.0, "text": f"Very long subtitle text segment number {i} " * 20}
                for i in range(50)
            ],
            "language": "English",
            "language_code": "en",
            "auto_generated": False,
            "subtitle_count": 50
        }
        
        result = formatter.format_for_file(long_subtitles)
        
        # Должен быть один файл со всем содержимым
        assert isinstance(result, str)
        assert len(result) > 1000  # Должен быть достаточно длинным
        assert "Long Video" in result
    
    @pytest.mark.asyncio
    async def test_raw_subtitles_command_no_url(self):
        """Тест команды без URL"""
        # Создаем mock объекты
        update = Mock()
        context = Mock()
        queue_manager = Mock()
        youtube_processor = Mock()
        
        handlers = BotHandlers(queue_manager, youtube_processor)
        
        # Настраиваем mock для пользователя (разрешенный пользователь)  
        update.effective_user.id = 123456  # Добавляем конкретный ID
        update.message.text = "/raw_subtitles"
        update.message.reply_text = AsyncMock()
        context.args = []
        
        # Мокаем настройки без ограничений по пользователям
        with patch('src.bot.handlers.settings') as mock_settings:
            mock_settings.allowed_users_list = None  # Нет ограничений
            
            await handlers.raw_subtitles_command(update, context)
            
            # Должно быть отправлено сообщение с инструкцией
            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args[0]
            assert "usage" in call_args[0].lower() or "использование" in call_args[0].lower()
    
    def test_subtitle_formatter_header_creation(self, sample_subtitle_data):
        """Тест создания заголовка с метаинформацией"""
        formatter = SubtitleFormatter()
        header = formatter._create_header(sample_subtitle_data)
        
        assert "Test Video Title" in header
        assert "Test Channel" in header
        assert "👤 Ручные" in header  # Для ручных субтитров
        assert "Сегментов: 3" in header
    
    def test_subtitle_formatter_auto_generated_header(self):
        """Тест заголовка для автогенерированных субтитров"""
        formatter = SubtitleFormatter()
        auto_data = {
            "video_id": "test",
            "title": "Auto Video",
            "duration": 120,
            "channel": "Auto Channel",
            "subtitles": [],
            "language": "Russian",
            "language_code": "ru",
            "auto_generated": True,
            "subtitle_count": 0
        }
        
        header = formatter._create_header(auto_data)
        assert "🤖 Автогенерированные" in header
    
    def test_format_duration(self):
        """Тест форматирования длительности"""
        formatter = SubtitleFormatter()
        
        # Тест различных длительностей
        assert "0:03:32" in formatter._format_duration(212)  # 3 минуты 32 секунды
        assert "1:00:00" in formatter._format_duration(3600)  # 1 час
    
    def test_format_seconds_to_timestamp(self):
        """Тест конвертации секунд в timestamp"""
        formatter = SubtitleFormatter()
        
        assert formatter._seconds_to_timestamp(0) == "00:00"
        assert formatter._seconds_to_timestamp(90) == "01:30"
        assert formatter._seconds_to_timestamp(3661) == "61:01"  # Более часа
    
    def test_subtitle_formatter_file_content(self, sample_subtitle_data):
        """Тест содержимого файла субтитров"""
        formatter = SubtitleFormatter()
        result = formatter.format_for_file(sample_subtitle_data)
        
        # Проверяем структуру файла
        lines = result.split('\n')
        
        # Должен содержать заголовок с метаданными
        assert any("Test Video Title" in line for line in lines)
        assert any("Test Channel" in line for line in lines)
        assert any("👤 Ручные" in line for line in lines)
        assert any("Сегментов: 3" in line for line in lines)
        
        # Должен содержать текст субтитров
        assert "Hello world" in result
        assert "This is a test" in result
        assert "Testing subtitles" in result


if __name__ == "__main__":
    pytest.main([__file__]) 