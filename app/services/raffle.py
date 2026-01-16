import random
from typing import List, Dict, Optional
from app.models.raffle import RaffleEntry


def build_weighted_pool(entries: List[RaffleEntry]) -> List[RaffleEntry]:
    """
    Build a weighted pool where each entry appears based on entry count.
    
    Args:
        entries: List of RaffleEntry objects
        
    Returns:
        List of RaffleEntry objects where each entry appears 'entries' times
    """
    pool = []
    for entry in entries:
        pool.extend([entry] * entry.entries)
    return pool


def pick_winner(
    entries: List[RaffleEntry],
    user_comments_map: Optional[Dict[str, List[str]]] = None
) -> RaffleEntry:
    """
    Pick one winner from the weighted raffle pool and assign a winning comment.
    
    Args:
        entries: List of RaffleEntry objects
        user_comments_map: Optional dict mapping user_id/username to list of their comments
        
    Returns:
        Single RaffleEntry winner with comment_text set
        
    Raises:
        ValueError: If entries list is empty
    """
    if not entries:
        raise ValueError("Cannot pick winner from empty entries list")
    
    pool = build_weighted_pool(entries)
    winner = random.choice(pool)
    
    # Set winning comment text if available
    if user_comments_map:
        lookup_key = winner.user_id if winner.user_id else winner.username
        if lookup_key in user_comments_map:
            comments = user_comments_map[lookup_key]
            if comments:
                # Pick a random comment from this user's comments
                winner.comment_text = random.choice(comments)
    
    return winner
