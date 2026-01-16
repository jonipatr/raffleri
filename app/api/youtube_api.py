import requests
import time
from typing import List, Optional, Dict, Tuple
from app.models.raffle import RaffleEntry
from app.utils.youtube import extract_video_id, extract_channel_id


class YouTubeAPI:
    """Handles YouTube Data API v3 interactions for fetching live chat messages from active streams."""
    
    VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
    LIVECHAT_URL = "https://www.googleapis.com/youtube/v3/liveChat/messages"
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    
    def __init__(self, api_key: str):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API v3 key
        """
        self.api_key = api_key
    
    def check_if_live(self, video_id: str) -> bool:
        """
        Check if a video is currently live.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if video is live, False otherwise
            
        Raises:
            requests.RequestException: If API request fails
        """
        params = {
            'part': 'snippet',
            'id': video_id,
            'key': self.api_key
        }
        
        try:
            response = requests.get(self.VIDEOS_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to check if video is live: {str(e)}"
            )
        
        if 'error' in data:
            error = data['error']
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', 'Unknown')
            raise requests.exceptions.RequestException(
                f"YouTube API error ({error_code}): {error_msg}"
            )
        
        items = data.get('items', [])
        if not items:
            return False
        
        snippet = items[0].get('snippet', {})
        live_broadcast_content = snippet.get('liveBroadcastContent', 'none')
        
        return live_broadcast_content == 'live'
    
    def get_live_chat_id(self, video_id: str) -> Optional[str]:
        """
        Get activeLiveChatId from video's liveStreamingDetails.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            liveChatId if available, None otherwise
            
        Raises:
            requests.RequestException: If API request fails
        """
        params = {
            'part': 'liveStreamingDetails',
            'id': video_id,
            'key': self.api_key
        }
        
        try:
            response = requests.get(self.VIDEOS_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to get video details: {str(e)}"
            )
        
        if 'error' in data:
            error = data['error']
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', 'Unknown')
            raise requests.exceptions.RequestException(
                f"YouTube API error ({error_code}): {error_msg}"
            )
        
        items = data.get('items', [])
        if not items:
            return None
        
        video = items[0]
        live_streaming_details = video.get('liveStreamingDetails', {})
        live_chat_id = live_streaming_details.get('activeLiveChatId')
        
        return live_chat_id
    
    def get_live_chat_messages(
        self,
        live_chat_id: str,
        max_entries_per_user: int = 5,
        max_messages: int = 10000
    ) -> Tuple[List[Dict], Optional[int]]:
        """
        Fetch live chat messages from a live chat.
        
        Args:
            live_chat_id: Live chat ID
            max_entries_per_user: Maximum entries per user (default: 5)
            max_messages: Maximum number of messages to fetch (default: 10000)
            
        Returns:
            Tuple of (List of message dictionaries with user info and comment text, 
                     Optional total results count from API - may not reflect all messages)
            
        Raises:
            ValueError: If total_results exceeds max_messages
            requests.RequestException: If API request fails
        """
        messages = []
        page_token = None
        total_results = None  # Will be set from first response
        max_pages = 5  # 5 pages × 2000 maxResults = 10,000 messages max
        
        print(f"[DEBUG] Starting to fetch messages from liveChatId: {live_chat_id}")
        
        # Use for loop instead of while - max 5 pages (10,000 messages)
        for page_count in range(1, max_pages + 1):
            print(f"[DEBUG] Fetching page {page_count}...")
            params = {
                'liveChatId': live_chat_id,
                'part': 'snippet,authorDetails',
                'maxResults': 2000,  # Maximum allowed by API to minimize requests
                'key': self.api_key
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            try:
                response = requests.get(self.LIVECHAT_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.HTTPError as e:
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error = error_data['error']
                        error_msg = error.get('message', 'Unknown error')
                        error_code = error.get('code', response.status_code)
                        error_reason = error.get('errors', [{}])[0].get('reason', '') if error.get('errors') else ''
                        
                        if error_code == 403:
                            if error_reason == 'liveChatEnded':
                                raise ValueError(
                                    "The live chat has ended. This video is no longer live."
                                )
                            elif error_reason == 'liveChatDisabled':
                                raise ValueError(
                                    "Live chat is not enabled for this broadcast."
                                )
                            elif 'too soon' in error_msg.lower() or 'refresh' in error_msg.lower():
                                # Rate limit error - wait and retry
                                polling_interval = data.get('pollingIntervalMillis', 5000) / 1000.0  # Convert to seconds
                                raise requests.exceptions.RequestException(
                                    f"Rate limit: {error_msg}. Please wait {polling_interval:.1f} seconds before retrying."
                                )
                        
                        raise requests.exceptions.RequestException(
                            f"YouTube API error ({error_code}): {error_msg}"
                        )
                except ValueError:
                    raise requests.exceptions.RequestException(
                        f"YouTube API request failed: {response.status_code} {response.reason}"
                    )
            except requests.exceptions.RequestException as e:
                raise requests.exceptions.RequestException(
                    f"YouTube API request failed: {str(e)}"
                )
            
            if 'error' in data:
                error = data['error']
                error_msg = error.get('message', 'Unknown error')
                error_code = error.get('code', 'Unknown')
                raise requests.exceptions.RequestException(
                    f"YouTube API error ({error_code}): {error_msg}"
                )
            
            # Get total results count from first response (if available)
            # Note: This may not reflect ALL messages ever sent, only those currently retrievable
            if total_results is None:
                page_info = data.get('pageInfo', {})
                total_results = page_info.get('totalResults')
                
                # Check if total results exceeds maximum allowed
                if total_results and total_results > max_messages:
                    raise ValueError(
                        f"This live stream has {total_results:,} messages, which exceeds the maximum "
                        f"of {max_messages:,} messages allowed. Please try with a stream that has fewer messages."
                    )
            
            # Process messages
            items = data.get('items', [])
            print(f"[DEBUG] Page {page_count}: Got {len(items)} items from API")
            
            messages_before = len(messages)
            for item in items:
                snippet = item.get('snippet', {})
                author_details = item.get('authorDetails', {})
                
                # Get message type - only process text messages
                message_type = snippet.get('type', '')
                if message_type not in ['textMessageEvent', 'superChatEvent', 'superStickerEvent']:
                    continue
                
                # Get comment text
                display_message = snippet.get('displayMessage', '')
                
                # Get author information
                user_id = author_details.get('channelId')
                username = author_details.get('displayName', 'Unknown')
                
                messages.append({
                    'user_id': user_id,
                    'username': username,
                    'comment_text': display_message
                })
            
            messages_after = len(messages)
            messages_added = messages_after - messages_before
            
            print(f"[DEBUG] Total messages collected so far: {len(messages)}, added this page: {messages_added}")
            
            # Stop early if we got 0 messages (no more available)
            if messages_added == 0 and len(messages) > 0:
                print("[DEBUG] Got 0 new messages - all available messages fetched, stopping early")
                break
            
            # Stop early if we've reached max_messages
            if len(messages) >= max_messages:
                print(f"[DEBUG] Reached max_messages limit ({max_messages}), stopping")
                break
            
            # Get nextPageToken for next iteration (if not on last page)
            if page_count < max_pages:
                page_token = data.get('nextPageToken')
                if not page_token:
                    print("[DEBUG] No nextPageToken, finished fetching")
                    break
                
                # Respect polling interval to avoid rate limits
                polling_interval_ms = data.get('pollingIntervalMillis', 1000)  # Default 1 second
                polling_interval_sec = max(0.5, polling_interval_ms / 1000.0)
                sleep_time = min(polling_interval_sec, 2.0)  # Cap at 2 seconds max
                print(f"[DEBUG] Waiting {sleep_time:.2f} seconds before next request...")
                time.sleep(sleep_time)
        
        print(f"[DEBUG] Finished fetching. Total messages: {len(messages)}, Total pages: {page_count}")
        return messages, total_results
    
    def get_user_entries(
        self,
        video_url: str,
        max_entries_per_user: int = 5
    ) -> Tuple[List[RaffleEntry], Dict[str, List[str]], int]:
        """
        Fetch live chat messages from YouTube video and create raffle entries.
        
        Args:
            video_url: YouTube video URL (must be an active live stream)
            max_entries_per_user: Maximum entries per user (default: 5)
            
        Returns:
            Tuple of (List of RaffleEntry objects, Dict mapping user keys to their comments, total_comments count)
            
        Raises:
            ValueError: If video URL is invalid, not live, or has no live chat
            requests.RequestException: If API request fails
        """
        print(f"[DEBUG] Starting get_user_entries for URL: {video_url}")
        video_id = extract_video_id(video_url)
        print(f"[DEBUG] Extracted video ID: {video_id}")
        
        # Step 1: Check if video is live
        print("[DEBUG] Step 1: Checking if video is live...")
        try:
            is_live = self.check_if_live(video_id)
            print(f"[DEBUG] Video is live: {is_live}")
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Error checking if live: {e}")
            raise e
        
        if not is_live:
            raise ValueError(
                "This video is not currently live. Only active live streams are supported."
            )
        
        # Step 2: Get liveChatId
        print("[DEBUG] Step 2: Getting liveChatId...")
        try:
            live_chat_id = self.get_live_chat_id(video_id)
            print(f"[DEBUG] Live chat ID: {live_chat_id}")
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Error getting liveChatId: {e}")
            raise e
        
        if not live_chat_id:
            raise ValueError(
                "Could not find live chat ID. Live chat may not be enabled for this stream."
            )
        
        # Step 3: Fetch live chat messages
        print("[DEBUG] Step 3: Fetching live chat messages...")
        try:
            messages, total_results = self.get_live_chat_messages(live_chat_id, max_entries_per_user)
            print(f"[DEBUG] Fetched {len(messages)} messages, total_results: {total_results}")
        except (ValueError, requests.exceptions.RequestException) as e:
            print(f"[DEBUG] Error fetching messages: {e}")
            raise e
        
        if not messages:
            raise ValueError("No live chat messages found for this stream.")
        
        # Store total comment count before processing
        total_comments = len(messages)
        
        # Step 4: Count messages per user and store comment texts
        user_data: Dict[str, Dict] = {}
        
        for message in messages:
            user_id = message['user_id']
            username = message['username']
            comment_text = message['comment_text']
            
            # Use user_id as key, fallback to username if no user_id
            key = user_id if user_id else f"user_{username}"
            
            if key not in user_data:
                user_data[key] = {
                    'user_id': user_id,
                    'username': username,
                    'count': 0,
                    'comments': []  # Store all comments for this user
                }
            
            # Increment count and store comment (up to max_entries_per_user)
            if user_data[key]['count'] < max_entries_per_user:
                user_data[key]['count'] += 1
                user_data[key]['comments'].append(comment_text)
        
        # Step 5: Convert to RaffleEntry objects
        entries = []
        user_comments_map: Dict[str, List[str]] = {}
        
        for key, user_info in user_data.items():
            if user_info['count'] > 0:
                entries.append(RaffleEntry(
                    platform='youtube',
                    user_id=user_info['user_id'],
                    username=user_info['username'],
                    entries=user_info['count'],
                    comment_text=None  # Will be set when winner is picked
                ))
                # Store comments for this user (keyed by user_id or username)
                lookup_key = user_info['user_id'] if user_info['user_id'] else user_info['username']
                user_comments_map[lookup_key] = user_info['comments']
        
        return entries, user_comments_map, total_comments
    
    def _resolve_channel_handle(self, handle: str) -> Optional[str]:
        """
        Resolve a channel handle (@channelname) to channel ID using YouTube API.
        
        Args:
            handle: Channel handle without @ (e.g., "channelname")
            
        Returns:
            Channel ID if found, None otherwise
        """
        # Use search.list to find channel by handle
        params = {
            'part': 'snippet',
            'q': handle,
            'type': 'channel',
            'maxResults': 1,
            'key': self.api_key
        }
        
        try:
            response = requests.get(self.SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data or 'items' not in data or not data['items']:
                return None
            
            # Get channel ID from search result
            channel = data['items'][0]
            channel_id = channel.get('id', {}).get('channelId')
            return channel_id
        except requests.exceptions.RequestException:
            return None
    
    def get_active_live_stream(self, channel_url: Optional[str] = None, channel_id: Optional[str] = None) -> Optional[Dict]:
        """
        Check if a channel has an active live stream.
        
        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channelname)
            channel_id: YouTube channel ID (alternative to channel_url)
            
        Returns:
            Dictionary with video_id, video_url, and live_chat_id if found, None otherwise
            
        Raises:
            ValueError: If neither channel_url nor channel_id is provided
            requests.RequestException: If API request fails
        """
        if not channel_url and not channel_id:
            raise ValueError("Either channel_url or channel_id must be provided")
        
        # Extract channel_id from URL if needed
        if channel_url and not channel_id:
            channel_id = extract_channel_id(channel_url)
            
            # If extraction failed, try to resolve @channelname handle
            if not channel_id:
                import re
                handle_match = re.search(r'@([a-zA-Z0-9_-]+)', channel_url)
                if handle_match:
                    handle = handle_match.group(1)
                    channel_id = self._resolve_channel_handle(handle)
            
            if not channel_id:
                raise ValueError("Could not extract or resolve channel ID from URL")
        
        # Search for active live streams
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'eventType': 'live',
            'type': 'video',
            'maxResults': 1,
            'key': self.api_key
        }
        
        try:
            response = requests.get(self.SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to search for live streams: {str(e)}"
            )
        
        if 'error' in data:
            error = data['error']
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', 'Unknown')
            raise requests.exceptions.RequestException(
                f"YouTube API error ({error_code}): {error_msg}"
            )
        
        items = data.get('items', [])
        if not items:
            return None
        
        # Get the first live stream
        video = items[0]
        video_id = video.get('id', {}).get('videoId')
        
        if not video_id:
            return None
        
        # Get live chat ID for this video
        try:
            live_chat_id = self.get_live_chat_id(video_id)
        except requests.exceptions.RequestException:
            live_chat_id = None
        
        return {
            'video_id': video_id,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'live_chat_id': live_chat_id
        }
