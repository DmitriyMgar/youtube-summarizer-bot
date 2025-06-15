"""
Utility functions for YouTube URL validation and video ID extraction
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


def is_valid_youtube_url(url: str) -> bool:
    """
    Validate if a given URL is a valid YouTube video URL.
    
    Supports:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID  
    - m.youtube.com/watch?v=VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    """
    if not url or not isinstance(url, str):
        return False
    
    # YouTube URL patterns
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url.strip()):
            return True
    
    return False


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various YouTube URL formats.
    
    Returns:
        str: Video ID if found, None otherwise
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Add protocol if missing for proper parsing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Try different extraction methods
    video_id = None
    
    # Method 1: Standard youtube.com/watch URLs
    if 'youtube.com/watch' in url:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'v' in query_params:
            video_id = query_params['v'][0]
    
    # Method 2: youtu.be short URLs
    elif 'youtu.be/' in url:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            video_id = path_parts[0]
    
    # Method 3: Embed URLs
    elif 'youtube.com/embed/' in url:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'embed':
            video_id = path_parts[1]
    
    # Method 4: youtube.com/v/ URLs
    elif 'youtube.com/v/' in url:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'v':
            video_id = path_parts[1]
    
    # Method 5: Regex fallback for any YouTube URL
    if not video_id:
        patterns = [
            r'(?:v=|/)([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
    
    # Validate video ID format
    if video_id and is_valid_video_id(video_id):
        return video_id
    
    return None


def is_valid_video_id(video_id: str) -> bool:
    """
    Validate YouTube video ID format.
    
    YouTube video IDs are exactly 11 characters long and contain
    alphanumeric characters, hyphens, and underscores.
    """
    if not video_id or not isinstance(video_id, str):
        return False
    
    # YouTube video ID pattern: exactly 11 characters, alphanumeric + _ and -
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    return bool(re.match(pattern, video_id))


def normalize_youtube_url(url: str) -> Optional[str]:
    """
    Normalize YouTube URL to standard format: https://www.youtube.com/watch?v=VIDEO_ID
    
    Returns:
        str: Normalized URL if valid, None otherwise
    """
    video_id = extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return None


def get_youtube_thumbnail_url(video_id: str, quality: str = 'maxresdefault') -> str:
    """
    Generate YouTube thumbnail URL for a given video ID.
    
    Args:
        video_id: YouTube video ID
        quality: Thumbnail quality ('maxresdefault', 'hqdefault', 'mqdefault', 'default')
    
    Returns:
        str: Thumbnail URL
    """
    if not is_valid_video_id(video_id):
        raise ValueError("Invalid video ID")
    
    valid_qualities = ['maxresdefault', 'hqdefault', 'mqdefault', 'default']
    if quality not in valid_qualities:
        quality = 'maxresdefault'
    
    return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system usage.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    if not filename:
        return "unknown"
    
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove extra whitespace and limit length
    sanitized = ' '.join(sanitized.split())[:100]
    
    # Ensure it's not empty
    if not sanitized.strip():
        sanitized = "unknown"
    
    return sanitized.strip() 