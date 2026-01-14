import random
from typing import List
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


def pick_winner(entries: List[RaffleEntry]) -> RaffleEntry:
    """
    Pick one winner from the weighted raffle pool.
    
    Args:
        entries: List of RaffleEntry objects
        
    Returns:
        Single RaffleEntry winner
        
    Raises:
        ValueError: If entries list is empty
    """
    if not entries:
        raise ValueError("Cannot pick winner from empty entries list")
    
    pool = build_weighted_pool(entries)
    winner = random.choice(pool)
    return winner
