"""
Localization messages for YouTube SummaryBot
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
📝 **{bot_name}** v{bot_version}

Привет, {first_name}! 👋

Я помогу вам создавать конспекты видео с YouTube с помощью ИИ. 

**Как пользоваться:**
1️⃣ Просто отправьте мне ссылку на YouTube
2️⃣ Выберите операцию из предложенных кнопок
3️⃣ Выберите формат документа
4️⃣ Получите готовый конспект!

**Что я умею:**
📋 Создавать конспекты и изложения видео
📝 Извлекать чистые субтитры
✨ Исправлять и переводить субтитры

**Основные команды:**
/start - Показать это приветственное сообщение
/help - Получить подробную справку
/status - Проверить статус обработки
/formats - Посмотреть доступные форматы

**Поддерживаемые форматы:** {supported_formats}

Просто отправьте мне ссылку на YouTube, чтобы начать! 🚀
        """,
        
        "help_text": """
📝 <b>{bot_name} - Справочное руководство</b>

<b>Как использовать:</b>
1. Отправьте мне любую ссылку на YouTube
2. Выберите операцию из интерактивного меню:
   • 📋 <b>Создать конспект</b> - полный анализ видео с помощью ИИ
   • 📝 <b>Чистые субтитры</b> - извлечение субтитров без обработки
   • ✨ <b>Исправленные субтитры</b> - перевод и коррекция субтитров
3. Выберите формат документа (TXT, DOCX, PDF)
4. Дождитесь обработки (1-5 минут)
5. Скачайте готовый конспект или субтитры

<b>Поддерживаемые ссылки:</b>
• youtube.com/watch?v=VIDEO_ID
• youtu.be/VIDEO_ID
• m.youtube.com/watch?v=VIDEO_ID

<b>Команды:</b>
• <code>/start</code> - Показать приветственное сообщение
• <code>/help</code> - Показать это руководство
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
        "formats_specify": "Формат выбирается в интерактивном меню после отправки ссылки на YouTube.",
        
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
        "error_no_url": "❌ Пожалуйста, отправьте ссылку на YouTube.\n\nПросто отправьте ссылку в виде сообщения, и я проведу вас через интерактивное меню.",
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
        "processing_ai_correction": "🤖 Исправляю текст, пунктуацию и ошибки преобразования аудио в текст...",
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
            "status": "Проверить статус обработки",
            "formats": "Посмотреть доступные форматы вывода",
            "cancel": "Отменить текущий запрос на обработку"
        },
        
        # Новые сообщения для /raw_subtitles
        "raw_subtitles_usage": "📝 **Использование команды:**\n`/raw_subtitles <YouTube URL> [format:формат]`\n\n**Примеры:**\n`/raw_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n`/raw_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ format:docx`\n\n**Доступные форматы:** txt, docx, pdf",
        "raw_subtitles_processing": "⏳ Извлекаю субтитры из видео...",
        "raw_subtitles_not_found": "❌ **Субтитры недоступны**\n\nДля этого видео нет субтитров. Попробуйте создать изложение видео с помощью интерактивного меню.",
        "raw_subtitles_error": "❌ **Ошибка извлечения субтитров**\n\n{error}\n\nПопробуйте позже или используйте другое видео.",
        "raw_subtitles_file_error": "❌ **Ошибка создания файла**\n\nНе удалось создать файл с субтитрами. Попробуйте снова.",
        
        # Новые сообщения для /corrected_subtitles
        "corrected_subtitles_usage": "✨ **Использование команды:**\n`/corrected_subtitles <YouTube URL> [format:формат]`\n\n**Примеры:**\n`/corrected_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n`/corrected_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ format:pdf`\n\n**Доступные форматы:** txt, docx, pdf\n*Команда извлекает субтитры и улучшает их читаемость с помощью ИИ*",
        "corrected_subtitles_processing": "⏳ Извлекаю субтитры и улучшаю их с помощью ИИ...\n\n*Это может занять 1-2 минуты*",
        "corrected_subtitles_error": "❌ **Ошибка обработки субтитров**\n\n{error}\n\nПопробуйте позже или используйте другое видео.",
        "corrected_subtitles_file_error": "❌ **Ошибка создания файла**\n\nНе удалось создать файл с исправленными субтитрами. Попробуйте снова.",
        
        "video_unavailable": "❌ **Видео недоступно**\n\nВидео может быть приватным, удаленным или недоступным в вашем регионе.",
        
        # Subscription messages
        "subscription_required": """
🔒 **Доступ ограничен**

Этот бот доступен только подписчикам канала @{channel_username}.

Чтобы получить доступ:
1. Подпишитесь на канал: t.me/{channel_username}
2. Вернитесь и снова используйте бота

После подписки доступ будет предоставлен автоматически! ✨
        """,
        
        "subscription_check_failed": """
⚠️ **Не удалось проверить подписку**

Произошла временная ошибка при проверке вашей подписки на канал. 
Попробуйте снова через несколько минут.

Если ошибка повторяется, обратитесь к администратору.
        """,
        
        # Interactive dialog messages
        "video_detected": "🎥 **Видео обнаружено!**\n\n📹 {title}\n\nЧто вы хотите сделать с этим видео?",
        "operation_selected": "✅ **{operation}** выбрано\n\n📋 **Выберите формат вывода:**",
        "processing_started": "⏳ **Обработка началась...**\n\n🎬 **Видео:** {title}\n📋 **Операция:** {operation}\n📄 **Формат:** {format}\n\n*Это может занять 1-3 минуты. Вы получите уведомление, когда будет готово.*",
        "processing_complete": "✅ **Обработка завершена!**\n\nВаш {operation} в формате {format} готов для скачивания.",
        "session_expired": "❌ Сессия истекла. Пожалуйста, отправьте ссылку YouTube снова.",
        "operation_cancelled": "❌ Операция отменена.",
        "invalid_youtube_url": "❌ Недействительная ссылка YouTube. Пожалуйста, отправьте действительную ссылку на видео YouTube.",
        "processing_cancelled": "❌ Обработка отменена пользователем.",
        
        # Button labels
        "btn_summarize": "📄 Резюме",
        "btn_raw_subtitles": "📝 Субтитры", 
        "btn_corrected_subtitles": "✨ Исправленные",
        "btn_format_txt": "📄 TXT",
        "btn_format_docx": "📑 DOCX",
        "btn_format_pdf": "📕 PDF",
        "btn_back": "⬅️ Назад",
        "btn_cancel": "❌ Отмена",
        "btn_cancel_processing": "❌ Отменить обработку",
        
        # Operation display names
        "operation_summarize": "Создание резюме",
        "operation_raw_subtitles": "Извлечение субтитров",
        "operation_corrected_subtitles": "Исправление субтитров",
        
        # Additional interactive messages
        "please_wait": "⏳ Пожалуйста, подождите...",
        "video_processing": "🔄 Обрабатываю видео...",
        "processing_video_started": "🔄 **Обработка началась!** Извлекаю содержимое видео...",
        "ai_processing": "🤖 ИИ обрабатывает контент...",
        "document_creating": "📄 Создаю документ...",
        "sending_result": "📤 Отправляю результат...",
        
        # Error messages for interactive flow
        "error_video_too_long": "❌ **Видео слишком длинное**\n\nМаксимальная длина: {max_duration} минут\nДлина вашего видео: {video_duration} минут",
        "video_duration_exceeded": """
⏱️ **Опс! Видео получилось длинноватым**

Ваше видео длится **{video_minutes} минут**, а максимально допустимая длительность — **{max_minutes} минут**.

💡 **Что можно сделать:**
• Найти более короткую версию видео
• Разделить длинное видео на части
• Попробовать извлечь только субтитры командой /raw_subtitles

Если вам часто нужно обрабатывать длинные видео, напишите администратору — возможно, мы сможем увеличить лимит специально для вас! ✨
        """,
        "error_no_subtitles": "❌ **Субтитры недоступны**\n\nДля этого видео нет субтитров. Попробуйте другое видео.",
        "error_processing_failed": "❌ **Ошибка обработки**\n\n{error}\n\nПопробуйте снова или выберите другое видео.",
        "error_timeout": "⏰ **Превышен лимит времени**\n\nОбработка заняла слишком много времени. Попробуйте снова.",
        "error_ai_tokens_exceeded": """
🤖 **Видео слишком длинное для ИИ-обработки**

Ваше видео содержит слишком много текста для обработки ИИ за один раз.

💡 **Что можно сделать:**
• Использовать команду `/raw_subtitles` для получения необработанных субтитров
• Обработать более короткое видео (до 60 минут)
• Попробовать позже, когда лимиты обновятся

*Это ограничение OpenAI, а не бота. Мы работаем над улучшением обработки длинных видео.*
        """,
        "error_ai_rate_limit": "🤖 **Превышен лимит запросов к ИИ**\n\nСлишком много запросов в минуту. Попробуйте через 1-2 минуты.",
        "error_ai_quota": "🤖 **Исчерпан лимит ИИ-токенов**\n\nВременная проблема с ИИ-сервисом. Попробуйте позже или обратитесь к администратору.",
        
        # Success messages for interactive flow
        "url_detected": "🔗 **Ссылка обнаружена**\n\nПроверяю видео...",
        "video_info_extracted": "✅ **Информация о видео получена**\n\n📹 {title}\n⏱️ Длительность: {duration}\n👤 Автор: {author}",

        "subscription_verified": """
✅ **Подписка подтверждена!**

Добро пожаловать! Теперь вы можете использовать все функции бота.
        """,
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
/summarize \\[YouTube URL\\] - Summarize a video
/raw\\_subtitles \\[YouTube URL\\] - Extract subtitles without AI processing
/corrected\\_subtitles \\[YouTube URL\\] - Extract and improve subtitles with AI
/status - Check processing status
/formats - See available output formats

**Supported formats:** {supported_formats}

Just send me a YouTube URL to get started! 🚀
        """,
        
        # English versions for /raw_subtitles
        "raw_subtitles_usage": "📝 **Command usage:**\n`/raw_subtitles <YouTube URL> [format:format]`\n\n**Examples:**\n`/raw_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n`/raw_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ format:docx`\n\n**Available formats:** txt, docx, pdf",
        "raw_subtitles_processing": "⏳ Extracting subtitles from video...",
        "raw_subtitles_not_found": "❌ **Subtitles unavailable**\n\nNo subtitles found for this video. Try using `/summarize` for audio processing.",
        "raw_subtitles_error": "❌ **Subtitle extraction error**\n\n{error}\n\nTry again later or use another video.",
        "raw_subtitles_file_error": "❌ **File creation error**\n\nFailed to create subtitle file. Please try again.",
        
        # English versions for /corrected_subtitles
        "corrected_subtitles_usage": "✨ **Command usage:**\n`/corrected_subtitles <YouTube URL> [format:format]`\n\n**Examples:**\n`/corrected_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n`/corrected_subtitles https://www.youtube.com/watch?v=dQw4w9WgXcQ format:pdf`\n\n**Available formats:** txt, docx, pdf\n*This command extracts subtitles and improves their readability using AI*",
        "corrected_subtitles_processing": "⏳ Extracting subtitles and improving them with AI...\n\n*This may take 1-2 minutes*",
        "corrected_subtitles_error": "❌ **Subtitle processing error**\n\n{error}\n\nTry again later or use another video.",
        "corrected_subtitles_file_error": "❌ **File creation error**\n\nFailed to create corrected subtitle file. Please try again.",
        
        "video_unavailable": "❌ **Video unavailable**\n\nVideo may be private, deleted, or unavailable in your region.",
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