"""
YouTube Video Summarizer Bot - Configuration Settings
Using Pydantic for configuration management and validation
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field('', env='TELEGRAM_BOT_TOKEN')
    
    # OpenAI Configuration  
    openai_api_key: str = Field('', env='OPENAI_API_KEY')
    openai_model: str = Field('gpt-4o', env='OPENAI_MODEL')
    openai_max_tokens: int = Field(4000, env='OPENAI_MAX_TOKENS')
    
    # YouTube Configuration
    youtube_api_key: Optional[str] = Field(None, env='YOUTUBE_API_KEY')
    
    # Application Settings
    bot_name: str = Field('YouTube SummaryBot', env='BOT_NAME')
    bot_version: str = Field('1.0.0', env='BOT_VERSION')
    debug: bool = Field(False, env='DEBUG')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    
    # Processing Configuration
    max_video_duration: int = Field(3600, env='MAX_VIDEO_DURATION')  # 1 hour
    max_queue_size: int = Field(100, env='MAX_QUEUE_SIZE')
    processing_timeout: int = Field(300, env='PROCESSING_TIMEOUT')  # 5 minutes
    
    # Document Generation
    supported_formats: str = Field(default='txt,docx,pdf', env='SUPPORTED_FORMATS')
    default_format: str = Field('txt', env='DEFAULT_FORMAT')
    
    # Redis Configuration
    redis_host: str = Field('localhost', env='REDIS_HOST')
    redis_port: int = Field(6379, env='REDIS_PORT')
    redis_db: int = Field(0, env='REDIS_DB')
    redis_password: Optional[str] = Field(None, env='REDIS_PASSWORD')
    
    # Security Settings
    allowed_users: str = Field(default='', env='ALLOWED_USERS')
    rate_limit_messages: int = Field(10, env='RATE_LIMIT_MESSAGES')
    rate_limit_window: int = Field(60, env='RATE_LIMIT_WINDOW')
    
    # FFmpeg Configuration
    ffmpeg_binary_path: str = Field('ffmpeg', env='FFMPEG_BINARY_PATH')
    
    # Video Frame Extraction
    extract_video_frames: bool = Field(False, env='EXTRACT_VIDEO_FRAMES')
    max_frames_count: int = Field(3, env='MAX_FRAMES_COUNT')
    
    # Language Configuration
    language: str = Field('ru', env='LANGUAGE')
    
    # Channel Subscription Settings
    required_channel_username: str = Field('logloss_notes', env='REQUIRED_CHANNEL_USERNAME')
    subscription_check_enabled: bool = Field(True, env='SUBSCRIPTION_CHECK_ENABLED')
    subscription_cache_ttl: int = Field(300, env='SUBSCRIPTION_CACHE_TTL')  # 5 minutes

    @property
    def supported_formats_list(self) -> List[str]:
        """Get supported formats as a list."""
        if not self.supported_formats.strip():
            return ['txt', 'docx', 'pdf']
        return [fmt.strip() for fmt in self.supported_formats.split(',')]
    
    @property
    def allowed_users_list(self) -> List[int]:
        """Get allowed users as a list."""
        if not self.allowed_users.strip():
            return []
        return [int(user_id.strip()) for user_id in self.allowed_users.split(',') if user_id.strip()]
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()
    
    @field_validator('default_format')
    @classmethod
    def validate_default_format(cls, v, info):
        if hasattr(info, 'data') and 'supported_formats' in info.data:
            supported_formats = [fmt.strip() for fmt in info.data['supported_formats'].split(',')]
            if v not in supported_formats:
                raise ValueError(f'Default format must be one of: {supported_formats}')
        return v
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        allowed_languages = ['ru', 'en']
        if v.lower() not in allowed_languages:
            raise ValueError(f'Language must be one of: {allowed_languages}')
        return v.lower()

    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        'env_nested_delimiter': '__',
        'extra': 'ignore'
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings 