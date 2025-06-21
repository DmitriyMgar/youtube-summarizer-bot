"""
Data models for user activity analytics
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class UserActivity:
    """Основная модель активности пользователя"""
    timestamp: datetime
    user_id: int
    username: str
    first_name: str
    last_name: Optional[str]
    chat_id: int
    command: str
    message_text: str
    video_url: Optional[str] = None
    video_id: Optional[str] = None
    output_format: Optional[str] = None
    processing_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class CommandStats:
    """Статистика по командам"""
    command: str
    total_uses: int
    unique_users: int
    success_rate: float
    avg_processing_time: Optional[float] = None


@dataclass
class VideoProcessingEvent:
    """События обработки видео"""
    timestamp: datetime
    user_id: int
    video_id: str
    video_url: str
    title: str
    duration: int
    output_format: str
    processing_time: float
    success: bool
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None 