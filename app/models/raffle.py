from pydantic import BaseModel, Field
from typing import Optional, List


class RaffleEntry(BaseModel):
    """Represents a user's entry in the raffle pool."""
    platform: str
    user_id: Optional[str] = None
    username: str
    entries: int = Field(ge=1, le=5, description="Number of entries (1-5)")
    comment_text: Optional[str] = None  # The winning comment text (if available)


class RaffleRequest(BaseModel):
    """Request model for raffle endpoint."""
    video_url: str
    winners: int = Field(default=1, ge=1, description="Number of winners (defaults to 1)")


class RaffleResponse(BaseModel):
    """Response model for raffle endpoint."""
    winner: RaffleEntry
    total_comments: int  # Actual number of comments/messages fetched
    total_participants: int
    platform: str


class ChannelRequest(BaseModel):
    """Request model for channel endpoint."""
    channel_url: Optional[str] = None
    channel_id: Optional[str] = None


class ChannelResponse(BaseModel):
    """Response model for channel endpoint."""
    is_live: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    live_chat_id: Optional[str] = None


class StreamInfo(BaseModel):
    """Information about a single live stream."""
    video_id: str
    video_url: str
    live_chat_id: Optional[str] = None
    title: str


class ChannelStats(BaseModel):
    """Basic channel statistics and metadata."""
    title: Optional[str] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None
    podcast_count: Optional[int] = None
    podcasts: Optional[List["PodcastItem"]] = None


class PodcastItem(BaseModel):
    """Represents a podcast episode/item."""
    title: str
    video_url: str


class ChannelStreamsResponse(BaseModel):
    """Response model for channel streams endpoint."""
    streams: list[StreamInfo]
    channel: Optional[ChannelStats] = None