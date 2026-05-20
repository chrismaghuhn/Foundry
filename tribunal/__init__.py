"""
TRIBUNAL: The Performance Review Game

Demonstration / reference implementation — not for production deployment.

"This game makes players feel the helplessness of being judged
 by rules they cannot see, verify, or enforce."

Usage:
    from tribunal import TribunalGame, TaskDifficulty, ManagerBehavior
    
    game = TribunalGame(
        worker_ids=["Alice", "Bob", "Carol"],
        manager_behavior=ManagerBehavior.FAVORITES,
        favorites=["Bob"]
    )
    
    # Play rounds
    views = game.play_round({
        "Alice": TaskDifficulty.HARD,
        "Bob": TaskDifficulty.EASY,
        "Carol": TaskDifficulty.MEDIUM,
    })
    
    # Each worker sees only their own rating
    print(views["Alice"])
    
    # At game end, reveal the truth
    print(game.reveal_truth())

Author: chrismaghuhn
License: MIT
"""

from .tribunal import (
    TribunalGame,
    TaskDifficulty,
    Rating,
    ManagerBehavior,
)

__version__ = "1.0.0"
__all__ = ['TribunalGame', 'TaskDifficulty', 'Rating', 'ManagerBehavior']
