"""
AUDIT: The Selective Verification Game

Demonstration / reference implementation — not for production deployment.

THE LIE PLAYERS BELIEVE:
"If I play honestly, the system will reward me."

THE MECHANIC: AUDIT SCARCITY
- Players make CLAIMS backed by cryptographic COMMITMENTS
- Claims can be LIES
- Limited AUDIT TOKENS mean only some claims get verified
- Unverified lies SUCCEED

Usage:
    from audit import AuditGame, PlayerStrategy
    
    game = AuditGame(
        player_configs=[
            ("Alice", PlayerStrategy.HONEST),
            ("Bob", PlayerStrategy.STRATEGIC),
        ],
        rounds=5
    )
    game.play_game()
    print(game.get_log())

Author: chrismaghuhn
License: MIT
"""

from .audit import (
    AuditGame,
    Player,
    PlayerStrategy,
    Action,
    Commitment,
)

__version__ = "1.0.0"
__all__ = ['AuditGame', 'Player', 'PlayerStrategy', 'Action', 'Commitment']
