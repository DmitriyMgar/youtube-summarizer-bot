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
    bot_name: str = Field('YouTube Summarizer Bot', env='BOT_NAME')
    bot_version: str = Field('1.0.0', env='BOT_VERSION')
    debug: bool = Field(False, env='DEBUG')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    
    # Processing Configuration
    max_video_duration: int = Field(3600, env='MAX_VIDEO_DURATION')  # 1 hour
    max_queue_size: int = Field(100, env='MAX_QUEUE_SIZE')
    processing_timeout: int = Field(300, env='PROCESSING_TIMEOUT')  # 5 minutes
    
    # Document Generation
    supported_formats: List[str] = Field(['txt', 'docx', 'pdf'], env='SUPPORTED_FORMATS')
    default_format: str = Field('txt', env='DEFAULT_FORMAT')
    
    # Redis Configuration
    redis_host: str = Field('localhost', env='REDIS_HOST')
    redis_port: int = Field(6379, env='REDIS_PORT')
    redis_db: int = Field(0, env='REDIS_DB')
    redis_password: Optional[str] = Field(None, env='REDIS_PASSWORD')
    
    # Security Settings
    allowed_users: List[int] = Field([], env='ALLOWED_USERS')
    rate_limit_messages: int = Field(10, env='RATE_LIMIT_MESSAGES')
    rate_limit_window: int = Field(60, env='RATE_LIMIT_WINDOW')
    
    # FFmpeg Configuration
    ffmpeg_binary_path: str = Field('ffmpeg', env='FFMPEG_BINARY_PATH')

    @field_validator('supported_formats', mode='before')
    @classmethod
    def parse_supported_formats(cls, v):
        if isinstance(v, str):
            if not v.strip():  # Handle empty string
                return ['txt', 'docx', 'pdf']  # Default formats
            return [fmt.strip() for fmt in v.split(',')]
        return v if v else ['txt', 'docx', 'pdf']  # Default formats
    
    @field_validator('allowed_users', mode='before')
    @classmethod
    def parse_allowed_users(cls, v):
        if isinstance(v, str) and v:
            return [int(user_id.strip()) for user_id in v.split(',') if user_id.strip()]
        return v if v else []
    
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
        if hasattr(info, 'data') and 'supported_formats' in info.data and v not in info.data['supported_formats']:
            raise ValueError(f'Default format must be one of: {info.data["supported_formats"]}')
        return v

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings 