"""
User activity logger implementation
"""

import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

from .models import UserActivity, CommandStats, VideoProcessingEvent

logger = logging.getLogger(__name__)


class UserActivityLogger:
    """Класс для логирования активности пользователей"""
    
    def __init__(self, db_path: str = "data/analytics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            # Таблица активности пользователей
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    chat_id INTEGER NOT NULL,
                    command TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    video_url TEXT,
                    video_id TEXT,
                    output_format TEXT,
                    processing_time REAL,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_message TEXT
                )
            """)
            
            # Таблица событий обработки видео
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_processing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    video_id TEXT NOT NULL,
                    video_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    duration INTEGER,
                    output_format TEXT NOT NULL,
                    processing_time REAL,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_message TEXT,
                    tokens_used INTEGER
                )
            """)
            
            # Индексы для быстрого поиска
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON user_activity(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_command ON user_activity(command)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_timestamp ON video_processing(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_user_id ON video_processing(user_id)")
            
            conn.commit()
            logger.info(f"Analytics database initialized at {self.db_path}")
    
    def log_user_activity(self, activity: UserActivity):
        """Логирование активности пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = asdict(activity)
                data['timestamp'] = activity.timestamp.isoformat()
                
                conn.execute("""
                    INSERT INTO user_activity (
                        timestamp, user_id, username, first_name, last_name, 
                        chat_id, command, message_text, video_url, video_id,
                        output_format, processing_time, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['timestamp'], data['user_id'], data['username'],
                    data['first_name'], data['last_name'], data['chat_id'],
                    data['command'], data['message_text'], data['video_url'],
                    data['video_id'], data['output_format'], data['processing_time'],
                    data['success'], data['error_message']
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
    
    def log_video_processing(self, event: VideoProcessingEvent):
        """Логирование события обработки видео"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = asdict(event)
                data['timestamp'] = event.timestamp.isoformat()
                
                conn.execute("""
                    INSERT INTO video_processing (
                        timestamp, user_id, video_id, video_url, title,
                        duration, output_format, processing_time, success,
                        error_message, tokens_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['timestamp'], data['user_id'], data['video_id'],
                    data['video_url'], data['title'], data['duration'],
                    data['output_format'], data['processing_time'],
                    data['success'], data['error_message'], data['tokens_used']
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging video processing event: {e}")
    
    def get_command_stats(self, days: int = 30) -> List[CommandStats]:
        """Получение статистики по командам"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                since = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor = conn.execute("""
                    SELECT 
                        command,
                        COUNT(*) as total_uses,
                        COUNT(DISTINCT user_id) as unique_users,
                        CAST(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate,
                        AVG(processing_time) as avg_processing_time
                    FROM user_activity 
                    WHERE timestamp >= ?
                    GROUP BY command
                    ORDER BY total_uses DESC
                """, (since,))
                
                return [
                    CommandStats(
                        command=row[0],
                        total_uses=row[1],
                        unique_users=row[2],
                        success_rate=row[3],
                        avg_processing_time=row[4]
                    )
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error getting command stats: {e}")
            return []
    
    def get_active_users(self, days: int = 30) -> List[Dict]:
        """Получение списка активных пользователей"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                since = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor = conn.execute("""
                    SELECT 
                        user_id,
                        username,
                        first_name,
                        COUNT(*) as activity_count,
                        MAX(timestamp) as last_activity,
                        COUNT(DISTINCT command) as commands_used
                    FROM user_activity 
                    WHERE timestamp >= ?
                    GROUP BY user_id, username, first_name
                    ORDER BY activity_count DESC
                """, (since,))
                
                return [
                    {
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'activity_count': row[3],
                        'last_activity': row[4],
                        'commands_used': row[5]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_popular_videos(self, days: int = 30) -> List[Dict]:
        """Получение популярных видео"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                since = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor = conn.execute("""
                    SELECT 
                        video_id,
                        video_url,
                        title,
                        COUNT(*) as processing_count,
                        AVG(processing_time) as avg_processing_time,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM video_processing 
                    WHERE timestamp >= ? AND success = 1
                    GROUP BY video_id, video_url, title
                    ORDER BY processing_count DESC
                    LIMIT 20
                """, (since,))
                
                return [
                    {
                        'video_id': row[0],
                        'video_url': row[1],
                        'title': row[2],
                        'processing_count': row[3],
                        'avg_processing_time': row[4],
                        'unique_users': row[5]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error getting popular videos: {e}")
            return []
    
    def get_daily_activity(self, days: int = 30) -> List[Dict]:
        """Получение ежедневной активности"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                since = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor = conn.execute("""
                    SELECT 
                        DATE(timestamp) as date,
                        COUNT(*) as total_activities,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(CASE WHEN command = 'summarize' THEN 1 END) as summarize_requests,
                        COUNT(CASE WHEN success = 0 THEN 1 END) as errors
                    FROM user_activity 
                    WHERE timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (since,))
                
                return [
                    {
                        'date': row[0],
                        'total_activities': row[1],
                        'unique_users': row[2],
                        'summarize_requests': row[3],
                        'errors': row[4]
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"Error getting daily activity: {e}")
            return []


# Глобальный экземпляр логгера
_activity_logger = None

def get_activity_logger() -> UserActivityLogger:
    """Получить глобальный экземпляр логгера активности"""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = UserActivityLogger()
    return _activity_logger 