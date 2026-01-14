from typing import List
from app.models.raffle import RaffleEntry


class TikTokAPI:
    """Placeholder for TikTok API implementation."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize TikTok API client (placeholder).
        
        Args:
            api_key: TikTok API key (not used yet)
        """
        self.api_key = api_key
    
    def get_user_entries(
        self,
        video_url: str,
        max_entries_per_user: int = 5
    ) -> List[RaffleEntry]:
        """
        Fetch comments from TikTok video (not implemented).
        
        Args:
            video_url: TikTok video URL
            max_entries_per_user: Maximum entries per user (default: 5)
            
        Returns:
            List of RaffleEntry objects
            
        Raises:
            NotImplementedError: TikTok support coming soon
        """
        raise NotImplementedError("TikTok support coming soon")
