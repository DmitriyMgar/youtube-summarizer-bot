"""
Queue Manager - Handle async video processing requests
Uses Redis for queue management and rate limiting
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import redis.asyncio as redis

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ProcessingRequest:
    """Data structure for processing requests."""
    user_id: int
    video_id: str
    video_url: str
    output_format: str
    chat_id: int
    status: str = 'queued'
    timestamp: float = None
    estimated_completion: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.estimated_completion is None:
            # Estimate 3 minutes processing time
            self.estimated_completion = self.timestamp + 180


class QueueManager:
    """Manage video processing queue using Redis."""
    
    def __init__(self):
        self.redis_client = None
        self.queue_key = "yt_summarizer:queue"
        self.processing_key = "yt_summarizer:processing"
        self.rate_limit_key = "yt_summarizer:rate_limit"
        self.user_requests_key = "yt_summarizer:user_requests"
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            # Create Redis connection with proper configuration
            redis_url = f"redis://"
            if settings.redis_password:
                redis_url += f":{settings.redis_password}@"
            redis_url += f"{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to in-memory storage for development
            logger.warning("Using in-memory fallback for queue management")
            self.redis_client = None
    
    async def add_request(
        self, 
        user_id: int, 
        video_id: str, 
        video_url: str, 
        output_format: str, 
        chat_id: int
    ) -> bool:
        """Add a new processing request to the queue."""
        try:
            # Check if user already has a pending request
            existing_request = await self.get_user_status(user_id)
            if existing_request and existing_request['status'] in ['queued', 'processing']:
                logger.warning(f"User {user_id} already has a pending request")
                return False
            
            # Create processing request
            request = ProcessingRequest(
                user_id=user_id,
                video_id=video_id,
                video_url=video_url,
                output_format=output_format,
                chat_id=chat_id
            )
            
            if self.redis_client:
                # Add to Redis queue
                request_data = json.dumps(asdict(request))
                await self.redis_client.lpush(self.queue_key, request_data)
                
                # Track user request
                await self.redis_client.hset(
                    self.user_requests_key, 
                    str(user_id), 
                    request_data
                )
                
                # Set expiration for user request tracking (24 hours)
                await self.redis_client.expire(self.user_requests_key, 86400)
                
            else:
                # Fallback in-memory storage
                if not hasattr(self, '_memory_queue'):
                    self._memory_queue = []
                    self._memory_user_requests = {}
                
                self._memory_queue.insert(0, request)
                self._memory_user_requests[str(user_id)] = request
            
            logger.info(f"Added processing request for user {user_id}, video {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding request to queue: {e}")
            return False
    
    async def get_next_request(self) -> Optional[ProcessingRequest]:
        """Get the next request from the queue for processing."""
        try:
            if self.redis_client:
                # Get from Redis queue
                request_data = await self.redis_client.brpop(self.queue_key, timeout=1)
                if request_data:
                    _, request_json = request_data
                    request_dict = json.loads(request_json)
                    request = ProcessingRequest(**request_dict)
                    
                    # Move to processing set
                    request.status = 'processing'
                    await self.redis_client.hset(
                        self.processing_key,
                        str(request.user_id),
                        json.dumps(asdict(request))
                    )
                    
                    return request
            else:
                # Fallback in-memory storage
                if hasattr(self, '_memory_queue') and self._memory_queue:
                    request = self._memory_queue.pop()
                    request.status = 'processing'
                    return request
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next request: {e}")
            return None
    
    async def complete_request(self, user_id: int, success: bool = True) -> bool:
        """Mark a request as completed and clean up."""
        try:
            if self.redis_client:
                # Remove from processing and user requests
                await self.redis_client.hdel(self.processing_key, str(user_id))
                await self.redis_client.hdel(self.user_requests_key, str(user_id))
            else:
                # Fallback in-memory storage
                if hasattr(self, '_memory_user_requests'):
                    self._memory_user_requests.pop(str(user_id), None)
            
            logger.info(f"Completed request for user {user_id}, success: {success}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing request: {e}")
            return False
    
    async def cancel_user_request(self, user_id: int) -> bool:
        """Cancel a user's pending request."""
        try:
            if self.redis_client:
                # Check if user has a request
                user_request = await self.redis_client.hget(self.user_requests_key, str(user_id))
                if not user_request:
                    return False
                
                request_data = json.loads(user_request)
                
                # Remove from appropriate location
                if request_data['status'] == 'queued':
                    # Remove from queue (this is more complex with Redis lists)
                    # For simplicity, we'll mark as cancelled
                    request_data['status'] = 'cancelled'
                    await self.redis_client.hset(
                        self.user_requests_key,
                        str(user_id),
                        json.dumps(request_data)
                    )
                elif request_data['status'] == 'processing':
                    # Remove from processing
                    await self.redis_client.hdel(self.processing_key, str(user_id))
                
                # Clean up user request after a delay
                await asyncio.sleep(1)
                await self.redis_client.hdel(self.user_requests_key, str(user_id))
                
            else:
                # Fallback in-memory storage
                if hasattr(self, '_memory_user_requests'):
                    request = self._memory_user_requests.get(str(user_id))
                    if request and request.status in ['queued', 'processing']:
                        if hasattr(self, '_memory_queue') and request in self._memory_queue:
                            self._memory_queue.remove(request)
                        self._memory_user_requests.pop(str(user_id), None)
                        return True
                
                return False
            
            logger.info(f"Cancelled request for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling request: {e}")
            return False
    
    async def get_user_status(self, user_id: int) -> Optional[Dict]:
        """Get status of user's current request."""
        try:
            if self.redis_client:
                # Check user requests
                user_request = await self.redis_client.hget(self.user_requests_key, str(user_id))
                if user_request:
                    request_data = json.loads(user_request)
                    
                    # Calculate position in queue if queued
                    position = 0
                    if request_data['status'] == 'queued':
                        queue_length = await self.redis_client.llen(self.queue_key)
                        position = max(1, queue_length // 2)  # Rough estimate
                    
                    # Calculate estimated time
                    estimated_time = max(0, (request_data['estimated_completion'] - time.time()) / 60)
                    
                    return {
                        'video_id': request_data['video_id'],
                        'status': request_data['status'],
                        'position': position,
                        'estimated_time': round(estimated_time, 1)
                    }
            else:
                # Fallback in-memory storage
                if hasattr(self, '_memory_user_requests'):
                    request = self._memory_user_requests.get(str(user_id))
                    if request:
                        estimated_time = max(0, (request.estimated_completion - time.time()) / 60)
                        position = 0
                        if hasattr(self, '_memory_queue') and request in self._memory_queue:
                            position = self._memory_queue.index(request) + 1
                        
                        return {
                            'video_id': request.video_id,
                            'status': request.status,
                            'position': position,
                            'estimated_time': round(estimated_time, 1)
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user status: {e}")
            return None
    
    async def get_queue_size(self) -> int:
        """Get current queue size."""
        try:
            if self.redis_client:
                return await self.redis_client.llen(self.queue_key)
            else:
                return len(getattr(self, '_memory_queue', []))
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        try:
            current_time = time.time()
            
            if self.redis_client:
                # Use Redis for rate limiting
                key = f"{self.rate_limit_key}:{user_id}"
                
                # Get current request count in time window
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, current_time - settings.rate_limit_window)
                pipe.zcard(key)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.expire(key, settings.rate_limit_window)
                
                results = await pipe.execute()
                request_count = results[1]
                
                return request_count < settings.rate_limit_messages
            else:
                # Fallback in-memory rate limiting
                if not hasattr(self, '_memory_rate_limits'):
                    self._memory_rate_limits = {}
                
                user_requests = self._memory_rate_limits.get(user_id, [])
                
                # Clean old requests
                cutoff_time = current_time - settings.rate_limit_window
                user_requests = [req_time for req_time in user_requests if req_time > cutoff_time]
                
                # Check if under limit
                if len(user_requests) < settings.rate_limit_messages:
                    user_requests.append(current_time)
                    self._memory_rate_limits[user_id] = user_requests
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error to avoid blocking users
    
    async def get_queue_stats(self) -> Dict:
        """Get overall queue statistics."""
        try:
            if self.redis_client:
                queue_size = await self.redis_client.llen(self.queue_key)
                processing_count = await self.redis_client.hlen(self.processing_key)
                active_users = await self.redis_client.hlen(self.user_requests_key)
            else:
                queue_size = len(getattr(self, '_memory_queue', []))
                processing_count = len([
                    req for req in getattr(self, '_memory_user_requests', {}).values()
                    if getattr(req, 'status', None) == 'processing'
                ])
                active_users = len(getattr(self, '_memory_user_requests', {}))
            
            return {
                'queue_size': queue_size,
                'processing_count': processing_count,
                'active_users': active_users,
                'total_capacity': settings.max_queue_size
            }
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {'queue_size': 0, 'processing_count': 0, 'active_users': 0}
    
    async def cleanup_expired_requests(self):
        """Clean up expired or stale requests."""
        try:
            current_time = time.time()
            cleanup_cutoff = current_time - 3600  # 1 hour timeout
            
            if self.redis_client:
                # Get all user requests
                all_requests = await self.redis_client.hgetall(self.user_requests_key)
                
                for user_id, request_json in all_requests.items():
                    try:
                        request_data = json.loads(request_json)
                        if request_data['timestamp'] < cleanup_cutoff:
                            await self.redis_client.hdel(self.user_requests_key, user_id)
                            await self.redis_client.hdel(self.processing_key, user_id)
                            logger.info(f"Cleaned up expired request for user {user_id}")
                    except Exception as e:
                        logger.error(f"Error cleaning up request for user {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close() 