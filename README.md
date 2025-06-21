# YouTube Video Summarizer Bot

An AI-powered Telegram bot that summarizes YouTube videos using OpenAI's GPT models. The bot extracts video transcripts, processes them with AI, and generates downloadable documents in multiple formats.

## Features

🎥 **YouTube Video Processing**
- Supports all YouTube URL formats (youtube.com, youtu.be, m.youtube.com)
- Extracts video metadata, transcripts, and key frames
- Handles both manual and auto-generated subtitles

🤖 **AI-Powered Summarization**
- Uses OpenAI GPT models for intelligent content analysis
- Generates structured summaries with key points and takeaways
- Includes timestamp references for important segments

📄 **Multiple Output Formats**
- Plain text (.txt) - Simple, readable format
- Word Document (.docx) - Rich formatting with tables and styling
- PDF Document (.pdf) - Professional formatted output

⚡ **Async Processing**
- Queue-based processing system with Redis backend
- Real-time status updates during processing
- Rate limiting and user management

🔒 **Security & Reliability**
- Environment-based configuration
- Comprehensive error handling and logging
- User authorization and rate limiting

🌐 **Localization**
- Russian language support (default)
- English language fallback
- Configurable via environment variable

🖼️ **Video Frame Extraction**
- Optional screenshot analysis (disabled by default to save time/tokens)

📋 **Subtitle Processing**
- Automatic and manual subtitle extraction with AI correction

📄 **Document Generation**
- Professional formatting with timestamps and structure

🔄 **Rate Limiting & Security**
- User restrictions and request throttling

📺 **Channel Subscription Control**
- Restrict bot access to channel subscribers only
- Configurable channel verification
- Redis-based caching for optimal performance
- Whitelist system for verified users

## Prerequisites

- Python 3.11 or higher
- FFmpeg (for video frame extraction)
- Redis (for queue management, optional - falls back to in-memory)
- Telegram Bot Token
- OpenAI API Key

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd youtube-summarizer-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Required Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional Configuration
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4000
BOT_NAME=YouTube Summarizer Bot
DEBUG=False
LOG_LEVEL=INFO

# Processing Limits
MAX_VIDEO_DURATION=3600
MAX_QUEUE_SIZE=100
PROCESSING_TIMEOUT=300

# Document Settings
SUPPORTED_FORMATS=txt,docx,pdf
DEFAULT_FORMAT=txt

# Redis Configuration (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Security Settings
ALLOWED_USERS=  # Comma-separated user IDs (leave empty for all users)
RATE_LIMIT_MESSAGES=10
RATE_LIMIT_WINDOW=60

# FFmpeg Configuration
FFMPEG_BINARY_PATH=ffmpeg

# Video Frame Extraction (скриншоты)
EXTRACT_VIDEO_FRAMES=false  # true для включения извлечения кадров (займет больше времени и токенов)
MAX_FRAMES_COUNT=3          # количество извлекаемых кадров из видео

# Language Configuration
LANGUAGE=ru

# Channel Subscription Control
SUBSCRIPTION_CHECK_ENABLED=true           # Enable/disable subscription verification
REQUIRED_CHANNEL_USERNAME=logloss_notes   # Channel username (without @)
SUBSCRIPTION_CACHE_TTL=300                # Cache duration for subscription checks (seconds)
```

### 3. Get Required API Keys

**Telegram Bot Token:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the provided token

**OpenAI API Key:**
1. Visit [OpenAI API](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

## Usage

### Starting the Bot

```bash
# From the project root
cd src
python main.py
```

### Bot Commands

- `/start` - Welcome message and bot introduction
- `/help` - Detailed usage instructions
- `/summarize <URL>` - Summarize a specific video
- `/status` - Check processing queue status
- `/formats` - View available output formats
- `/cancel` - Cancel current processing request

### Using the Bot

1. **Subscribe to required channel** - Must be subscribed to [@logloss_notes](https://t.me/logloss_notes) (if enabled)
2. **Send a YouTube URL** - Just paste any YouTube link
3. **Choose format** (optional) - Use `/summarize <URL> format:pdf`
4. **Wait for processing** - Typically 2-5 minutes
5. **Download document** - Receive formatted summary

### Channel Subscription Feature

When enabled (`SUBSCRIPTION_CHECK_ENABLED=true`), the bot requires users to be subscribed to a specific Telegram channel before processing requests:

- **Required Channel**: Configurable via `REQUIRED_CHANNEL_USERNAME`
- **Verification**: Bot checks subscription status using Telegram API
- **Caching**: Subscription status cached for 5 minutes, verified users whitelisted for 24 hours
- **Error Handling**: Bot allows access if API check fails to ensure availability
- **Management**: Use `check_whitelist.py` script to view/manage whitelisted users

## Architecture

```
youtube-summarizer-bot/
├── src/
│   ├── main.py              # Application entry point
│   ├── bot/                 # Telegram bot handlers
│   ├── youtube/             # Video processing
│   ├── ai/                  # OpenAI integration
│   ├── documents/           # Document generation
│   ├── queue/               # Async queue management
│   └── utils/               # Utilities and helpers
├── config/                  # Configuration management
├── tests/                   # Test files
├── docs/                    # Documentation
└── requirements.txt         # Dependencies
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Adding New Features

1. **Document Formats**: Extend `DocumentGenerator` class
2. **AI Models**: Modify `VideoSummarizer` configuration
3. **Bot Commands**: Add handlers in `bot/handlers.py`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | GPT model to use | `gpt-4o` |
| `MAX_VIDEO_DURATION` | Max video length (seconds) | `3600` |
| `SUPPORTED_FORMATS` | Output formats | `txt,docx,pdf` |
| `REDIS_HOST` | Redis server host | `localhost` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LANGUAGE` | Bot interface language | `ru` |
| `EXTRACT_VIDEO_FRAMES` | Enable video frame extraction | `false` |
| `MAX_FRAMES_COUNT` | Number of frames to extract | `3` |
| `SUBSCRIPTION_CHECK_ENABLED` | Enable channel subscription verification | `true` |
| `REQUIRED_CHANNEL_USERNAME` | Required channel username (without @) | `logloss_notes` |
| `SUBSCRIPTION_CACHE_TTL` | Subscription check cache duration (seconds) | `300` |

### Processing Limits

- **Video Duration**: Maximum 1 hour (configurable)
- **Queue Size**: Maximum 100 concurrent requests
- **Rate Limiting**: 10 requests per minute per user
- **File Cleanup**: Temporary files deleted after 24 hours

## Troubleshooting

### Common Issues

**Bot not responding:**
- Check Telegram bot token
- Verify network connectivity
- Check logs for errors

**Video processing fails:**
- Ensure FFmpeg is installed and accessible
- Check video URL validity
- Verify video has available transcripts

**AI summarization fails:**
- Verify OpenAI API key and credits
- Check API rate limits
- Ensure model availability

**Subscription check fails:**
- Ensure bot is administrator of the required channel
- Check `REQUIRED_CHANNEL_USERNAME` configuration
- Verify Redis connection for caching
- Review bot permissions in channel settings

**Document generation fails:**
- Check disk space for temporary files
- Verify document library dependencies
- Check file permissions

### Logs

Logs are output to stdout in JSON format. Key log sources:
- `main` - Application lifecycle
- `bot.handlers` - Telegram interactions
- `youtube.processor` - Video processing
- `ai.summarizer` - AI operations
- `queue.manager` - Queue operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Create an issue with reproduction steps

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video processing
- [OpenAI](https://openai.com/) - AI summarization
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - Transcript extraction 