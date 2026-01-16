import re
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://youtube.com/embed/VIDEO_ID
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID string
        
    Raises:
        ValueError: If video ID cannot be extracted from URL
    """
    # Pattern for youtu.be URLs
    youtu_be_pattern = r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(youtu_be_pattern, url)
    if match:
        return match.group(1)
    
    # Pattern for embed URLs
    embed_pattern = r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    match = re.search(embed_pattern, url)
    if match:
        return match.group(1)
    
    # Parse standard watch URLs
    parsed = urlparse(url)
    if parsed.hostname and 'youtube.com' in parsed.hostname:
        query_params = parse_qs(parsed.query)
        if 'v' in query_params:
            video_id = query_params['v'][0]
            if len(video_id) == 11:  # YouTube video IDs are 11 characters
                return video_id
    
    raise ValueError(f"Could not extract video ID from URL: {url}")


def extract_channel_id(url: str) -> str | None:
    """
    Extract YouTube channel ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/channel/CHANNEL_ID (returns channel ID directly)
    - https://www.youtube.com/@channelname (returns None, needs API resolution)
    - https://www.youtube.com/c/channelname (returns None, needs API resolution)
    - https://www.youtube.com/user/username (returns None, needs API resolution)
    
    Args:
        url: YouTube channel URL
        
    Returns:
        Channel ID string if /channel/ format, None otherwise (needs API resolution)
    """
    # Pattern for /channel/CHANNEL_ID
    channel_pattern = r'(?:youtube\.com/channel/)([a-zA-Z0-9_-]+)'
    match = re.search(channel_pattern, url)
    if match:
        return match.group(1)
    
    # For @channelname, c/channelname, or user/username formats,
    # return None - these need to be resolved via YouTube API
    return None


def is_channel_url(url: str) -> bool:
    """
    Check if a URL is a YouTube channel URL.
    
    Supports:
    - https://www.youtube.com/@channelname
    - https://www.youtube.com/channel/CHANNEL_ID
    - https://www.youtube.com/c/channelname
    - https://www.youtube.com/user/username
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a channel URL, False otherwise
    """
    if not url or 'youtube.com' not in url:
        return False
    
    # Check for channel URL patterns
    channel_patterns = [
        r'youtube\.com/channel/',
        r'youtube\.com/@',
        r'youtube\.com/c/',
        r'youtube\.com/user/',
    ]
    
    for pattern in channel_patterns:
        if re.search(pattern, url):
            return True
    
    return False
