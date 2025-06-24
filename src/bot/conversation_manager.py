"""
YouTube Video Summarizer Bot - Conversation Management System
Manages user dialog states and session storage for interactive interface
"""

import json
import logging
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Union
import redis.asyncio as redis
from datetime import datetime, timedelta

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationState(Enum):
    """Enumeration of conversation states."""
    IDLE = "idle"
    AWAITING_OPERATION = "awaiting_operation"
    AWAITING_FORMAT = "awaiting_format"
    PROCESSING = "processing"


@dataclass
class UserSession:
    """User session data structure."""
    user_id: int
    state: ConversationState
    youtube_url: str
    selected_operation: Optional[str] = None
    selected_format: Optional[str] = None
    video_title: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.context is None:
            self.context = {}


class ConversationManager:
    """Manages user conversation sessions and dialog flow."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize conversation manager with Redis client."""
        self.redis = redis_client
        self.session_timeout = 1800  # 30 minutes
        self.key_prefix = "conversation"
        self._fallback_storage = {}  # In-memory fallback if Redis unavailable
        
        if not self.redis:
            self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True
            )
            logger.info("Redis connection initialized for conversation manager")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis connection: {e}. Using in-memory fallback.")
            self.redis = None
    
    def _get_session_key(self, user_id: int) -> str:
        """Generate Redis key for user session."""
        return f"{self.key_prefix}:{user_id}"
    
    async def get_user_session(self, user_id: int) -> Optional[UserSession]:
        """Retrieve user session from storage."""
        try:
            if self.redis:
                session_data = await self.redis.get(self._get_session_key(user_id))
                if session_data:
                    data = json.loads(session_data)
                    # Convert state string back to enum
                    data['state'] = ConversationState(data['state'])
                    # Convert timestamps
                    if data.get('created_at'):
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                    if data.get('updated_at'):
                        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                    return UserSession(**data)
            else:
                # Fallback to in-memory storage
                session_data = self._fallback_storage.get(user_id)
                if session_data:
                    return session_data
                    
        except Exception as e:
            logger.error(f"Error retrieving session for user {user_id}: {e}")
        
        return None
    
    async def save_user_session(self, session: UserSession) -> bool:
        """Save user session to storage."""
        try:
            session.updated_at = datetime.now()
            
            if self.redis:
                # Prepare data for JSON serialization
                session_dict = asdict(session)
                session_dict['state'] = session.state.value
                session_dict['created_at'] = session.created_at.isoformat() if session.created_at else None
                session_dict['updated_at'] = session.updated_at.isoformat() if session.updated_at else None
                
                session_data = json.dumps(session_dict)
                await self.redis.setex(
                    self._get_session_key(session.user_id),
                    self.session_timeout,
                    session_data
                )
            else:
                # Fallback to in-memory storage
                self._fallback_storage[session.user_id] = session
            
            logger.debug(f"Session saved for user {session.user_id}, state: {session.state.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving session for user {session.user_id}: {e}")
            return False
    
    async def clear_user_session(self, user_id: int) -> bool:
        """Remove user session from storage."""
        try:
            if self.redis:
                await self.redis.delete(self._get_session_key(user_id))
            else:
                self._fallback_storage.pop(user_id, None)
            
            logger.debug(f"Session cleared for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session for user {user_id}: {e}")
            return False
    
    async def update_session_state(self, user_id: int, state: ConversationState) -> bool:
        """Update only the state of user session."""
        session = await self.get_user_session(user_id)
        if session:
            session.state = state
            return await self.save_user_session(session)
        return False
    
    async def set_user_url(self, user_id: int, url: str, video_title: Optional[str] = None) -> bool:
        """Set YouTube URL for user session."""
        session = await self.get_user_session(user_id)
        if not session:
            session = UserSession(
                user_id=user_id,
                state=ConversationState.AWAITING_OPERATION,
                youtube_url=url,
                video_title=video_title
            )
        else:
            session.youtube_url = url
            session.video_title = video_title
            session.state = ConversationState.AWAITING_OPERATION
            # Reset selections for new URL
            session.selected_operation = None
            session.selected_format = None
        
        return await self.save_user_session(session)
    
    async def set_user_operation(self, user_id: int, operation: str) -> bool:
        """Set selected operation for user session."""
        session = await self.get_user_session(user_id)
        if session:
            session.selected_operation = operation
            session.state = ConversationState.AWAITING_FORMAT
            return await self.save_user_session(session)
        return False
    
    async def set_user_format(self, user_id: int, format_type: str) -> bool:
        """Set selected format for user session."""
        session = await self.get_user_session(user_id)
        if session:
            session.selected_format = format_type
            session.state = ConversationState.PROCESSING
            return await self.save_user_session(session)
        return False
    
    async def update_session_context(self, user_id: int, key: str, value: Any) -> bool:
        """Update specific context value in user session."""
        session = await self.get_user_session(user_id)
        if session:
            if not session.context:
                session.context = {}
            session.context[key] = value
            return await self.save_user_session(session)
        return False
    
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        try:
            if self.redis:
                keys = await self.redis.keys(f"{self.key_prefix}:*")
                return len(keys)
            else:
                return len(self._fallback_storage)
        except Exception as e:
            logger.error(f"Error getting active sessions count: {e}")
            return 0
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (mainly for fallback storage)."""
        if not self.redis:
            # Clean up expired sessions in fallback storage
            current_time = datetime.now()
            expired_users = []
            
            for user_id, session in self._fallback_storage.items():
                if session.updated_at and (current_time - session.updated_at).seconds > self.session_timeout:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self._fallback_storage[user_id]
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired sessions from fallback storage")
            
            return len(expired_users)
        
        return 0
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        try:
            if self.redis:
                keys = await self.redis.keys(f"{self.key_prefix}:*")
                total_sessions = len(keys)
                
                # Get state distribution
                states = {}
                for key in keys[:50]:  # Limit to avoid performance issues
                    try:
                        session_data = await self.redis.get(key)
                        if session_data:
                            data = json.loads(session_data)
                            state = data.get('state', 'unknown')
                            states[state] = states.get(state, 0) + 1
                    except Exception:
                        continue
                
                return {
                    'total_sessions': total_sessions,
                    'state_distribution': states,
                    'storage_type': 'redis'
                }
            else:
                states = {}
                for session in self._fallback_storage.values():
                    state = session.state.value
                    states[state] = states.get(state, 0) + 1
                
                return {
                    'total_sessions': len(self._fallback_storage),
                    'state_distribution': states,
                    'storage_type': 'memory'
                }
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {'error': str(e)} 