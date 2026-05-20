"""
LEDGER: Mutual Reputation Protocol

Demonstration / reference implementation — not for production deployment.

A protocol where reputation is MUTUAL. You cannot judge without being judged.
You cannot see their review until you've committed yours.

"You cannot judge without being judged."

Usage:
    from ledger import Identity, LedgerProtocol, ReviewContent, Rating
    
    # Create identities
    manager = Identity("Sarah Chen")
    employee = Identity("Alex Kim")
    
    # Initialize protocol
    protocol = LedgerProtocol()
    
    # Initiate mutual review
    review = protocol.initiate(manager, employee, "Employment 2022-2024")
    
    # Both commit their reviews (sealed, not visible)
    protocol.commit_review(review.review_id, manager, manager_review_content)
    protocol.commit_review(review.review_id, employee, employee_review_content)
    
    # Reveal simultaneously
    revealed = protocol.reveal(review.review_id)
    
    # Both reviews are now visible and permanently linked

Author: chrismaghuhn
License: MIT
"""

from .ledger import (
    Identity,
    Rating,
    ReviewContent,
    ReviewStatus,
    SealedReview,
    MutualReview,
    LedgerProtocol,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    'Identity',
    'Rating',
    'ReviewContent',
    'ReviewStatus',
    'SealedReview',
    'MutualReview',
    'LedgerProtocol',
]
