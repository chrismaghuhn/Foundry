"""
Shamir: Secret Sharing Scheme

Split secrets into N shares where any K can reconstruct it,
but K-1 shares reveal absolutely nothing.

Information-theoretically secure - invented by Adi Shamir in 1979.

Quick Start:
    >>> from shamir import split, combine
    >>> 
    >>> # Split secret into 5 shares, need 3 to reconstruct
    >>> secret = b"my secret key"
    >>> shares = split(secret, n=5, k=3)
    >>> 
    >>> # Any 3 shares can reconstruct
    >>> recovered = combine(shares[:3])
    >>> assert recovered == secret
    >>> 
    >>> # 2 shares reveal NOTHING about the secret!

The Math:
    - Secret encoded as constant term of random polynomial
    - Shares are evaluations at different x values
    - K points uniquely determine a degree K-1 polynomial
    - K-1 points are consistent with ALL possible secrets
"""

from .shamir import (
    # Core functions
    split,
    combine,
    verify_shares,
    
    # Data structures
    Share,
    
    # Utilities
    split_string,
    combine_string,
    share_to_hex,
    share_from_hex,
    
    # GF(256) for advanced users
    GF256,
    
    # Visualization
    visualize_polynomial,
    visualize_split,
    visualize_reconstruction,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core
    'split', 'combine', 'verify_shares',
    
    # Data structures
    'Share',
    
    # Utilities
    'split_string', 'combine_string',
    'share_to_hex', 'share_from_hex',
    
    # GF(256)
    'GF256',
    
    # Visualization
    'visualize_polynomial', 'visualize_split', 'visualize_reconstruction',
]
