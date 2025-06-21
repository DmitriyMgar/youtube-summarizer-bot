import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.ai.summarizer import VideoSummarizer
from src.bot.handlers import BotHandlers


class TestCorrectedSubtitles:
    """Тесты для функции исправления субтитров"""
    
    @pytest.fixture
    def sample_subtitle_data(self):
        """Тестовые данные субтитров для коррекции"""
        return {
            "video_id": "dQw4w9WgXcQ",
            "title": "Test Video Title",
            "duration": 212,
            "channel": "Test Channel",
            "subtitles": [
                {"start": 0.0, "duration": 3.0, "text": "hello world this is"},
                {"start": 3.0, "duration": 2.0, "text": "a test of the"},
                {"start": 5.0, "duration": 4.0, "text": "subtitle correction system"}
            ],
            "language": "English",
            "language_code": "en",
            "auto_generated": True,
            "subtitle_count": 3
        }
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock ответ от OpenAI"""
        return """[0]Hello world, this is [1]a test of the [2]subtitle correction system."""
    
    @pytest.mark.asyncio
    async def test_correct_transcript_success(self, sample_subtitle_data, mock_openai_response):
        """Тест успешной коррекции субтитров"""
        summarizer = VideoSummarizer()
        
        with patch.object(summarizer, '_make_correction_request', return_value=mock_openai_response):
            result = await summarizer.correct_transcript(sample_subtitle_data)
            
            assert result["corrected"] == True
            assert result["correction_method"] == "ai_grammar_fix"
            assert len(result["subtitles"]) > 0
            
            # Проверяем что временные метки сохранились
            first_subtitle = result["subtitles"][0]
            assert "start" in first_subtitle
            assert "duration" in first_subtitle
            assert "text" in first_subtitle
    
    def test_prepare_text_for_correction(self, sample_subtitle_data):
        """Тест подготовки текста для коррекции"""
        summarizer = VideoSummarizer()
        
        prepared_text = summarizer._prepare_text_for_correction(sample_subtitle_data["subtitles"])
        
        assert "[0]" in prepared_text
        assert "[1]" in prepared_text
        assert "[2]" in prepared_text
        assert "hello world this is" in prepared_text
    
    def test_build_correction_prompt(self, sample_subtitle_data):
        """Тест создания промпта для коррекции"""
        summarizer = VideoSummarizer()
        
        text = "[0]hello world [1]this is test"
        prompt = summarizer._build_correction_prompt(text, sample_subtitle_data)
        
        assert "Test Video Title" in prompt
        assert "English" in prompt
        assert "автоматически сгенерированных" in prompt
        assert "Сохраняй маркеры" in prompt
    
    def test_parse_corrected_response(self, sample_subtitle_data, mock_openai_response):
        """Тест парсинга исправленного ответа"""
        summarizer = VideoSummarizer()
        
        corrected_segments = summarizer._parse_corrected_response(
            mock_openai_response, 
            sample_subtitle_data["subtitles"]
        )
        
        assert len(corrected_segments) > 0
        
        # Проверяем что первый сегмент содержит нужные поля
        first_segment = corrected_segments[0]
        assert "start" in first_segment
        assert "duration" in first_segment
        assert "text" in first_segment
        assert "Hello world, this is" in first_segment["text"]
    
    @pytest.mark.asyncio
    async def test_corrected_subtitles_command_success(self):
        """Тест команды бота для исправленных субтитров"""
        # Создаем mock объекты
        update = Mock()
        context = Mock()
        
        update.effective_user.id = 12345
        update.message.text = "/corrected_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()
        update.effective_chat.id = 67890
        
        context.bot.send_chat_action = AsyncMock()
        context.bot.delete_message = AsyncMock()
        
        # Создаем обработчик
        handlers = BotHandlers(Mock(), Mock())
        
        # Mock авторизации
        handlers._is_authorized_user = Mock(return_value=True)
        
        # Mock успешного извлечения и коррекции субтитров
        mock_subtitle_data = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "channel": "Test Channel",
            "duration": 180,
            "subtitles": [{"start": 0.0, "duration": 3.0, "text": "Hello world"}],
            "language": "English",
            "language_code": "en",
            "auto_generated": True,
            "subtitle_count": 1,
            "corrected": True
        }
        
        handlers.youtube_processor.extract_raw_subtitles = AsyncMock(return_value=mock_subtitle_data)
        handlers.summarizer.correct_transcript = AsyncMock(return_value=mock_subtitle_data)
        
        # Тестируем команду
        with patch('tempfile.NamedTemporaryFile'), patch('builtins.open'), patch('os.unlink'):
            await handlers.corrected_subtitles_command(update, context)
        
        # Проверяем, что были вызваны нужные методы
        handlers.youtube_processor.extract_raw_subtitles.assert_called_once()
        handlers.summarizer.correct_transcript.assert_called_once()
        update.message.reply_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_corrected_subtitles_command_no_url(self):
        """Тест команды без URL"""
        update = Mock()
        context = Mock()
        
        update.effective_user.id = 12345
        update.message.text = "/corrected_subtitles"
        update.message.reply_text = AsyncMock()
        
        handlers = BotHandlers(Mock(), Mock())
        handlers._is_authorized_user = Mock(return_value=True)
        
        await handlers.corrected_subtitles_command(update, context)
        
        # Должно быть отправлено сообщение с инструкцией
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "usage" in call_args[0][0].lower() or "использование" in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_corrected_subtitles_command_unauthorized(self):
        """Тест команды для неавторизованного пользователя"""
        update = Mock()
        context = Mock()
        
        update.effective_user.id = 99999  # Неавторизованный пользователь
        update.message.text = "/corrected_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        update.message.reply_text = AsyncMock()
        
        handlers = BotHandlers(Mock(), Mock())
        handlers._is_authorized_user = Mock(return_value=False)
        
        await handlers.corrected_subtitles_command(update, context)
        
        # Должно быть отправлено сообщение о запрете доступа
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "access_denied" in str(call_args) or "доступ" in call_args[0][0].lower() 