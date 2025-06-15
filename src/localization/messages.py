"""
Localization messages for YouTube Summarizer Bot
Russian translation support
"""

from typing import Dict, Any

# Current language setting (default: Russian)
_current_language = "ru"

# Message templates in Russian
MESSAGES = {
    "ru": {
        # Welcome and help messages
        "welcome_message": """
🎥 **{bot_name}** v{bot_version}

Привет, {first_name}! 👋

Я могу помочь вам создать краткие изложения видео с YouTube с помощью ИИ. Просто отправьте мне ссылку на YouTube, и я:

🔍 Извлеку субтитры и ключевые кадры
🤖 Создам краткое изложение с помощью ИИ  
📄 Создам загружаемый документ

**Команды:**
/start - Показать это приветственное сообщение
/help - Получить подробную справку
/summarize <ссылка YouTube> - Создать изложение видео
/status - Проверить статус обработки
/formats - Посмотреть доступные форматы

**Поддерживаемые форматы:** {supported_formats}

Просто отправьте мне ссылку на YouTube, чтобы начать! 🚀
        """,
        
        "help_text": """
📖 <b>{bot_name} - Справочное руководство</b>

<b>Как использовать:</b>
1. Отправьте мне любую ссылку на YouTube
2. Выберите предпочитаемый формат вывода
3. Дождитесь обработки ИИ (1-5 минут)
4. Скачайте документ с изложением

<b>Поддерживаемые ссылки:</b>
• youtube.com/watch?v=VIDEO_ID
• youtu.be/VIDEO_ID
• m.youtube.com/watch?v=VIDEO_ID

<b>Команды:</b>
• <code>/summarize [ссылка]</code> - Обработать определенное видео
• <code>/status</code> - Проверить текущую очередь обработки
• <code>/formats</code> - Посмотреть доступные форматы документов
• <code>/cancel</code> - Отменить текущий запрос

<b>Ограничения:</b>
• Максимальная длина видео: {max_duration} минут
• Ограничение скорости: {rate_limit_messages} запросов в {rate_limit_window} секунд

<b>Конфиденциальность:</b>
• Видео обрабатываются временно и не сохраняются
• Извлекаются только субтитры и ключевые кадры
• Ваши данные не передаются третьим лицам

Нужна дополнительная помощь? Обратитесь к администратору бота.
        """,
        
        # Format messages
        "formats_title": "📄 **Доступные форматы вывода**",
        "formats_supported": "**Поддерживаемые форматы:**",
        "formats_default": "**Формат по умолчанию:** {default_format}",
        "formats_specify": "Вы можете указать формат при запросе: `/summarize [ссылка] format:[формат]`",
        
        "format_descriptions": {
            'txt': '📝 Простой текст (.txt) - Простой, читаемый формат',
            'docx': '📄 Документ Word (.docx) - Богатое форматирование с заголовками',
            'pdf': '📕 PDF документ (.pdf) - Профессиональный форматированный вывод'
        },
        
        # Status messages
        "status_processing": """
⏳ **Статус обработки**

**Ваш запрос:**
• ID видео: `{video_id}`
• Статус: {status}
• Позиция в очереди: {position}
• Ориентировочное время: {estimated_time} минут

Пожалуйста, дождитесь завершения обработки...
        """,
        
        "status_no_requests": """
✅ **Нет активных запросов**

У вас нет видео, которые в данный момент обрабатываются.
Отправьте мне ссылку на YouTube, чтобы начать новое изложение!
        """,
        
        # Error messages
        "error_no_url": "❌ Пожалуйста, укажите ссылку на YouTube.\n\nИспользование: `/summarize [ссылка на YouTube]`",
        "error_unsupported_format": "❌ Неподдерживаемый формат: {format}\n\nДоступные форматы: {available_formats}",
        "error_invalid_url": "❌ Это не похоже на действительную ссылку YouTube.\n\nПожалуйста, отправьте действительную ссылку YouTube или используйте /help для получения дополнительной информации.",
        "error_unauthorized": "❌ Извините, у вас нет права использовать этого бота.",
        "error_rate_limit": "❌ Превышено ограничение скорости. Пожалуйста, подождите {rate_limit_window} секунд между запросами.",
        "error_extract_video_id": "❌ Не удалось извлечь ID видео из ссылки. Пожалуйста, проверьте ссылку и попробуйте снова.",
        "error_queue_full": "❌ Очередь обработки заполнена. Пожалуйста, попробуйте позже.",
        "error_general": "❌ Произошла ошибка при постановке в очередь вашего запроса. Пожалуйста, попробуйте позже.",
        
        # Success messages
        "success_queued": """✅ **Видео поставлено в очередь для обработки!**

📹 ID видео: `{video_id}`
📄 Формат вывода: {output_format}
⏱️ Ориентировочное время обработки: 2-5 минут

Я отправлю вам документ с изложением, когда он будет готов! 🚀""",
        
        "success_cancelled": "✅ Ваш запрос на обработку был отменен.",
        "error_no_cancel": "❌ Активный запрос на обработку для отмены не найден.",
        
        # Processing updates
        "processing_ai_summary": "🤖 Создание краткого изложения с помощью ИИ...",
        "processing_document": "📄 Создание документа...",
        
        # Completion message
        "completion_message": """
✅ **Изложение готово!**

📹 **Видео**: {title}
⏱️ **Длительность**: {duration}
🤖 **Модель ИИ**: {ai_model}
📊 **Использовано токенов**: {tokens_used}

**Краткое изложение**:
{executive_summary}...

📁 Документ прикреплен ниже!
        """,
        
        # Error messages for processing
        "processing_failed": """
❌ **Обработка не удалась**

Произошла ошибка при обработке вашего видео:
{error_message}

Пожалуйста, попробуйте снова или обратитесь в службу поддержки, если проблема не исчезнет.
        """,
        
        "document_send_failed": "Документ был создан, но не удалось отправить.",
        
        # Bot commands descriptions
        "commands": {
            "start": "Запустить бота и увидеть приветственное сообщение",
            "help": "Получить подробную справку и инструкции по использованию",
            "summarize": "Создать изложение видео YouTube",
            "status": "Проверить статус обработки",
            "formats": "Посмотреть доступные форматы вывода",
            "cancel": "Отменить текущий запрос на обработку"
        }
    },
    
    # English messages (fallback)
    "en": {
        "welcome_message": """
🎥 **{bot_name}** v{bot_version}

Hello {first_name}! 👋

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

**Supported formats:** {supported_formats}

Just send me a YouTube URL to get started! 🚀
        """,
        # ... (keeping original English messages as fallback)
    }
}


def set_language(language_code: str) -> None:
    """Set the current language."""
    global _current_language
    if language_code in MESSAGES:
        _current_language = language_code
    else:
        _current_language = "ru"  # Default to Russian


def get_messages() -> Dict[str, Any]:
    """Get messages for the current language."""
    return MESSAGES.get(_current_language, MESSAGES["ru"])


def get_message(key: str, **kwargs) -> str:
    """Get a specific message with formatting."""
    messages = get_messages()
    
    # Navigate nested keys (e.g., "format_descriptions.txt")
    keys = key.split('.')
    message = messages
    for k in keys:
        if isinstance(message, dict) and k in message:
            message = message[k]
        else:
            return f"Missing message: {key}"
    
    # Format the message if it's a string
    if isinstance(message, str) and kwargs:
        try:
            return message.format(**kwargs)
        except KeyError as e:
            return f"Missing parameter {e} for message: {key}"
    
    return message if isinstance(message, str) else str(message) 