from pydantic import BaseModel, Field
from typing import Optional


class RaffleEntry(BaseModel):
    """Represents a user's entry in the raffle pool."""
    platform: str
    user_id: Optional[str] = None
    username: str
    entries: int = Field(ge=1, le=5, description="Number of entries (1-5)")


class RaffleRequest(BaseModel):
    """Request model for raffle endpoint."""
    video_url: str
    winners: int = Field(default=1, ge=1, description="Number of winners (defaults to 1)")


class RaffleResponse(BaseModel):
    """Response model for raffle endpoint."""
    winner: RaffleEntry
    total_entries: int
    total_participants: int
    platform: str
