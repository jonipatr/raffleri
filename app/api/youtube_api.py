import requests
from typing import List
from app.models.raffle import RaffleEntry
from app.utils.youtube import extract_video_id


class YouTubeAPI:
    """Handles YouTube Data API v3 interactions for fetching comments."""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
    
    def __init__(self, api_key: str):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API v3 key
        """
        self.api_key = api_key
    
    def get_user_entries(
        self,
        video_url: str,
        max_entries_per_user: int = 5
    ) -> List[RaffleEntry]:
        """
        Fetch comments from YouTube video and create raffle entries.
        
        Args:
            video_url: YouTube video URL
            max_entries_per_user: Maximum entries per user (default: 5)
            
        Returns:
            List of RaffleEntry objects
            
        Raises:
            ValueError: If video URL is invalid
            requests.RequestException: If API request fails
        """
        video_id = extract_video_id(video_url)
        
        # Dictionary to count comments per user
        user_counts: dict[str, dict] = {}
        
        # Fetch all comments with pagination
        page_token = None
        while True:
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 100,
                'key': self.api_key
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            try:
                response = requests.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                raise requests.exceptions.RequestException(
                    f"YouTube API request failed: {str(e)}"
                )
            
            # Check for API errors in response
            if 'error' in data:
                error_msg = data['error'].get('message', 'Unknown error')
                raise requests.exceptions.RequestException(
                    f"YouTube API error: {error_msg}"
                )
            
            # Process comments
            items = data.get('items', [])
            for item in items:
                snippet = item.get('snippet', {})
                top_level_comment = snippet.get('topLevelComment', {})
                comment_snippet = top_level_comment.get('snippet', {})
                
                # Get author information
                author_channel_id = comment_snippet.get('authorChannelId', {})
                user_id = author_channel_id.get('value') if author_channel_id else None
                username = comment_snippet.get('authorDisplayName', 'Unknown')
                
                # Use user_id as key, fallback to username if no user_id
                key = user_id if user_id else username
                
                if key not in user_counts:
                    user_counts[key] = {
                        'user_id': user_id,
                        'username': username,
                        'count': 0
                    }
                
                # Increment count, but cap at max_entries_per_user
                if user_counts[key]['count'] < max_entries_per_user:
                    user_counts[key]['count'] += 1
            
            # Check for next page
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        
        # Convert to RaffleEntry objects
        entries = []
        for user_data in user_counts.values():
            if user_data['count'] > 0:
                entries.append(RaffleEntry(
                    platform='youtube',
                    user_id=user_data['user_id'],
                    username=user_data['username'],
                    entries=user_data['count']
                ))
        
        return entries
