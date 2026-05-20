"""
Styx: Cryptographically Secure Async Secret Sharing

A production-grade implementation of Shamir's Secret Sharing Scheme.

Quick Start:
    >>> from styx import Styx, SecretSharer
    >>> sharer = SecretSharer()
    >>> shares = sharer.split(b"my secret", n=5, k=3)
    >>> recovered = sharer.reconstruct(shares[:3])
    >>> assert recovered == b"my secret"

For distributed collection:
    >>> import asyncio
    >>> async with Styx() as styx:
    ...     shares = styx.split(secret, n=5, k=3)
    ...     await styx.distribute(shares, peers)
    ...     result = await styx.collect(peers, threshold=3)
    ...     secret = styx.reconstruct(result.shares)
"""

from .styx import (
    # Core classes
    GF256,
    Share,
    SecretSharer,
    
    # Distributed collection
    ShareCollector,
    ShareTransport,
    InMemoryTransport,
    Peer,
    PeerState,
    CollectionResult,
    
    # High-level API
    Styx,
    
    # Exceptions
    StyxError,
    IntegrityError,
    InsufficientSharesError,
    DuplicateShareError,
    
    # Utilities
    generate_hmac_key,
    shares_to_hex,
    shares_from_hex,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core
    'GF256',
    'Share', 
    'SecretSharer',
    
    # Distributed
    'ShareCollector',
    'ShareTransport',
    'InMemoryTransport',
    'Peer',
    'PeerState',
    'CollectionResult',
    
    # High-level
    'Styx',
    
    # Exceptions
    'StyxError',
    'IntegrityError',
    'InsufficientSharesError',
    'DuplicateShareError',
    
    # Utils
    'generate_hmac_key',
    'shares_to_hex',
    'shares_from_hex',
]
