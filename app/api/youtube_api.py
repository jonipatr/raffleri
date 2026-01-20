import os
import re
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
    CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
    PLAYLISTS_URL = "https://www.googleapis.com/youtube/v3/playlists"
    PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
    
    def __init__(self, api_key: str, podcast_playlist_id: Optional[str] = None):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API v3 key
        """
        self.api_key = api_key
        self.podcast_playlist_id = podcast_playlist_id
        self.debug_messages = os.getenv("DEBUG_YOUTUBE_MESSAGES") == "1"

    def resolve_channel_id_from_url(self, channel_url: str) -> Optional[str]:
        """
        Resolve a channel URL to a channel ID.
        Supports /channel/ URLs directly and @handle URLs via channels.list(forHandle).
        """
        channel_id = extract_channel_id(channel_url)
        if channel_id:
            return channel_id
        handle_match = re.search(r'@([a-zA-Z0-9_-]+)', channel_url or "")
        if handle_match:
            handle = handle_match.group(1)
            return self._resolve_channel_handle(handle)
        return None

    def get_video_live_metadata(self, video_id: str) -> Dict[str, Optional[str]]:
        """
        Fetch combined snippet + liveStreamingDetails to validate cached stream.
        Returns: {live_broadcast_content, channel_id, active_live_chat_id}
        """
        params = {
            'part': 'snippet,liveStreamingDetails',
            'id': video_id,
            'key': self.api_key
        }
        response = requests.get(self.VIDEOS_URL, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get('items', [])
        if not items:
            return {"live_broadcast_content": None, "channel_id": None, "active_live_chat_id": None}
        item = items[0]
        snippet = item.get("snippet", {}) or {}
        live_details = item.get("liveStreamingDetails", {}) or {}
        return {
            "live_broadcast_content": snippet.get("liveBroadcastContent"),
            "channel_id": snippet.get("channelId"),
            "active_live_chat_id": live_details.get("activeLiveChatId")
        }
    
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

    def check_live_chat_active(self, live_chat_id: str) -> bool:
        """
        Check if a liveChatId is still active by attempting a minimal fetch.
        """
        params = {
            'liveChatId': live_chat_id,
            'part': 'snippet,authorDetails',
            'maxResults': 1,
            'key': self.api_key
        }
        try:
            response = requests.get(self.LIVECHAT_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError:
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error = error_data['error']
                    error_code = error.get('code', response.status_code)
                    error_reason = error.get('errors', [{}])[0].get('reason', '') if error.get('errors') else ''
                    if error_code == 403 and error_reason in ['liveChatEnded', 'liveChatDisabled']:
                        return False
            except ValueError:
                return False
            return False
        except requests.exceptions.RequestException:
            return False
        
        if 'error' in data:
            return False
        return True

    def fetch_live_chat_page(
        self,
        live_chat_id: str,
        page_token: Optional[str] = None,
        max_results: int = 200
    ) -> Tuple[List[Dict], Optional[str], int]:
        params = {
            'liveChatId': live_chat_id,
            'part': 'snippet,authorDetails',
            'maxResults': min(max(1, max_results), 200),
            'key': self.api_key
        }
        if page_token:
            params['pageToken'] = page_token

        response = requests.get(self.LIVECHAT_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = data.get('items', [])
        next_page_token = data.get('nextPageToken')
        polling_interval_ms = data.get('pollingIntervalMillis', 1000)

        messages: List[Dict] = []
        for item in items:
            if self.debug_messages:
                print("TEMP: Live chat message JSON:", item)
            snippet = item.get('snippet', {})
            author_details = item.get('authorDetails', {})

            message_type = snippet.get('type', '')
            if message_type not in ['textMessageEvent', 'superChatEvent', 'superStickerEvent']:
                continue

            messages.append({
                'message_id': item.get('id'),
                'username': author_details.get('displayName', 'Unknown'),
                'comment_text': snippet.get('displayMessage', ''),
                'published_at': snippet.get('publishedAt')
            })

        if not self.debug_messages:
            print(f"TEMP: fetched {len(messages)} live chat messages")

        return messages, next_page_token, polling_interval_ms
    
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
        max_pages = 50  # 50 pages × 200 maxResults = 10,000 messages max
        
        # Use for loop instead of while - max 5 pages (10,000 messages)
        try:
            for page_count in range(1, max_pages + 1):
                params = {
                    'liveChatId': live_chat_id,
                    'part': 'snippet,authorDetails',
                    'maxResults': 200,  # liveChatMessages.list max
                    'key': self.api_key
                }
                
                if page_token:
                    params['pageToken'] = page_token
                
                try:
                    # LIVECHAT_URL = "https://www.googleapis.com/youtube/v3/liveChat/messages"
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
                next_page_token = data.get('nextPageToken')
                
                messages_before = len(messages)
                for item in items:
                    if self.debug_messages:
                        print("TEMP: Live chat message JSON:", item)
                    snippet = item.get('snippet', {})
                    author_details = item.get('authorDetails', {})
                    
                    # Get message type - only process text messages
                    message_type = snippet.get('type', '')
                    if message_type not in ['textMessageEvent', 'superChatEvent', 'superStickerEvent']:
                        continue
                    
                    # Get comment text
                    display_message = snippet.get('displayMessage', '')
                    
                    # Get author information
                    username = author_details.get('displayName', 'Unknown')
                    
                    message = {
                        'message_id': item.get('id'),
                        'username': username,
                        'comment_text': display_message
                    }
                    messages.append(message)
                
                messages_after = len(messages)
                messages_added = messages_after - messages_before
                
                # Stop early if we got 0 messages (no more available)
                if messages_added == 0 and len(messages) > 0:
                    break
                
                # Stop early if we've reached max_messages
                if len(messages) >= max_messages:
                    break
                
                # Get nextPageToken for next iteration (if not on last page)
                if page_count < max_pages:
                    page_token = next_page_token
                    if not page_token:
                        break
                    
                    # Respect polling interval to avoid rate limits
                    polling_interval_ms = data.get('pollingIntervalMillis', 1000)  # Default 1 second
                    polling_interval_sec = max(0.5, polling_interval_ms / 1000.0)
                    sleep_time = min(polling_interval_sec, 2.0)  # Cap at 2 seconds max
                    time.sleep(sleep_time)
        finally:
            pass

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
        video_id = extract_video_id(video_url)
        
        # Step 1: Check if video is live
        try:
            is_live = self.check_if_live(video_id)
        except requests.exceptions.RequestException as e:
            raise e
        
        if not is_live:
            raise ValueError(
                "This video is not currently live. Only active live streams are supported."
            )
        
        # Step 2: Get liveChatId
        try:
            live_chat_id = self.get_live_chat_id(video_id)
        except requests.exceptions.RequestException as e:
            raise e
        
        if not live_chat_id:
            raise ValueError(
                "Could not find live chat ID. Live chat may not be enabled for this stream."
            )
        
        # Step 3: Fetch live chat messages
        try:
            messages, total_results = self.get_live_chat_messages(live_chat_id, max_entries_per_user)
        except (ValueError, requests.exceptions.RequestException) as e:
            raise e
        
        if not messages:
            raise ValueError("No live chat messages found for this stream.")
        
        # Store total comment count before processing
        total_comments = len(messages)
        
        # Step 4: Count messages per user and store comment texts
        user_data: Dict[str, Dict] = {}
        
        for message in messages:
            username = message['username']
            comment_text = message['comment_text']
            
            key = f"user_{username}"
            
            if key not in user_data:
                user_data[key] = {
                    'user_id': None,
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
                # Store comments for this user (keyed by username)
                lookup_key = user_info['username']
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
        # Use channels.list with forHandle to resolve handle directly
        params = {
            'part': 'id',
            'forHandle': handle,
            'key': self.api_key
        }
        
        try:
            response = requests.get(self.CHANNELS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data or 'items' not in data or not data['items']:
                return None
            
            # Get channel ID from search result
            channel = data['items'][0]
            channel_id = channel.get('id')
            return channel_id
        except requests.exceptions.RequestException:
            return None

    def get_channel_stats(self, channel_url: Optional[str] = None, channel_id: Optional[str] = None) -> Dict:
        """
        Fetch basic channel statistics and metadata.
        
        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channelname)
            channel_id: YouTube channel ID (alternative to channel_url)
            
        Returns:
            Dictionary with title and statistics (subscriber_count, video_count, view_count)
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
        
        params = {
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': self.api_key
        }
        
        try:
            response = requests.get(self.CHANNELS_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to fetch channel statistics: {str(e)}"
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
            return {}
        
        item = items[0]
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        
        def to_int(value: Optional[str]) -> Optional[int]:
            try:
                return int(value) if value is not None else None
            except (ValueError, TypeError):
                return None
        
        podcast_items = []
        if self.podcast_playlist_id:
            podcast_items = self._get_playlist_items(self.podcast_playlist_id, max_items=200)

        return {
            'title': snippet.get('title'),
            'subscriber_count': to_int(stats.get('subscriberCount')),
            'video_count': to_int(stats.get('videoCount')),
            'podcast_count': len(podcast_items),
            'podcasts': podcast_items
        }

    def _get_podcast_playlist_items(self, channel_id: str, max_items: int = 200) -> List[Dict]:
        """
        Collect podcast episodes from playlists whose titles include "podcast".
        
        Args:
            channel_id: YouTube channel ID
            max_items: Maximum podcast items to return
            
        Returns:
            List of podcast items (title + video_url)
        """
        items: List[Dict] = []
        seen_video_ids = set()
        page_token = None

        while True:
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'maxResults': 50,
                'key': self.api_key
            }
            if page_token:
                params['pageToken'] = page_token

            try:
                response = requests.get(self.PLAYLISTS_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException:
                return items

            if 'error' in data:
                return items

            playlist_items = data.get('items', [])
            for playlist in playlist_items:
                title = playlist.get('snippet', {}).get('title', '')
                playlist_id = playlist.get('id')
                if not playlist_id:
                    continue
                if 'podcast' in title.casefold():
                    self._collect_playlist_videos(
                        playlist_id,
                        items,
                        seen_video_ids,
                        max_items=max_items
                    )
                    if len(items) >= max_items:
                        return items

            page_token = data.get('nextPageToken')
            if not page_token:
                break

        return items

    def _get_playlist_items(self, playlist_id: str, max_items: int = 200) -> List[Dict]:
        """
        Collect items from a specific playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            max_items: Maximum playlist items to return
            
        Returns:
            List of playlist items (title + video_url)
        """
        items: List[Dict] = []
        seen_video_ids = set()
        self._collect_playlist_videos(
            playlist_id,
            items,
            seen_video_ids,
            max_items=max_items
        )
        return items

    def _collect_playlist_videos(
        self,
        playlist_id: str,
        items: List[Dict],
        seen_video_ids: set,
        max_items: int
    ) -> None:
        """Append playlist videos into items list (deduped by videoId)."""
        page_token = None

        while len(items) < max_items:
            params = {
                'part': 'snippet,contentDetails',
                'playlistId': playlist_id,
                'maxResults': 50,
                'key': self.api_key
            }
            if page_token:
                params['pageToken'] = page_token

            try:
                response = requests.get(self.PLAYLIST_ITEMS_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException:
                return

            if 'error' in data:
                return

            playlist_items = data.get('items', [])
            for item in playlist_items:
                content = item.get('contentDetails', {})
                video_id = content.get('videoId')
                if not video_id or video_id in seen_video_ids:
                    continue
                snippet = item.get('snippet', {})
                title = snippet.get('title', 'Untitled')
                items.append({
                    'title': title,
                    'video_url': f"https://www.youtube.com/watch?v={video_id}"
                })
                seen_video_ids.add(video_id)
                if len(items) >= max_items:
                    return

            page_token = data.get('nextPageToken')
            if not page_token:
                break
    
    def get_active_live_streams(self, channel_url: Optional[str] = None, channel_id: Optional[str] = None) -> List[Dict]:
        """
        Get all active live streams for a channel.
        
        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channelname)
            channel_id: YouTube channel ID (alternative to channel_url)
            
        Returns:
            List of dictionaries with video_id, video_url, live_chat_id, and title for each active stream
            
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
        
        # Search for active live streams (get up to 50 to handle multiple streams)
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'eventType': 'live',
            'type': 'video',
            'maxResults': 50,  # Get all active streams
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
            return []
        
        # Process all live streams
        streams = []
        for video in items:
            video_id = video.get('id', {}).get('videoId')
            if not video_id:
                continue
            
            # Get video title from snippet
            snippet = video.get('snippet', {})
            title = snippet.get('title', 'Untitled Stream')
            
            # Get live chat ID for this video
            try:
                live_chat_id = self.get_live_chat_id(video_id)
            except requests.exceptions.RequestException:
                live_chat_id = None
            
            streams.append({
                'video_id': video_id,
                'video_url': f"https://www.youtube.com/watch?v={video_id}",
                'live_chat_id': live_chat_id,
                'title': title
            })
        
        return streams
    
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
        
        # Use get_active_live_streams and return first one
        streams = self.get_active_live_streams(channel_url=channel_url, channel_id=channel_id)
        if not streams:
            return None
        
        # Return first stream (without title for backward compatibility)
        first_stream = streams[0]
        return {
            'video_id': first_stream['video_id'],
            'video_url': first_stream['video_url'],
            'live_chat_id': first_stream['live_chat_id']
        }
