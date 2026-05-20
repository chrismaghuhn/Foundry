"""
Arc: Adaptive Replacement Cache

A self-tuning cache that automatically balances recency and frequency
based on observed access patterns. Drop-in replacement for LRU with
better hit rates and scan resistance.

Quick Start:
    >>> from arc import ArcCache
    >>> import asyncio
    >>> 
    >>> async def main():
    ...     cache = ArcCache[str, bytes](capacity=1000)
    ...     await cache.put("key", b"value")
    ...     value = await cache.get("key")
    ...     print(f"Hit rate: {cache.stats.hit_rate:.1%}")
    >>> 
    >>> asyncio.run(main())

For synchronous usage:
    >>> from arc import ArcCacheSync
    >>> 
    >>> cache = ArcCacheSync[str, int](capacity=100)
    >>> cache.put("answer", 42)
    >>> print(cache.get("answer"))

As a decorator:
    >>> from arc import arc_cache
    >>> 
    >>> @arc_cache(capacity=1000)
    >>> async def fetch_user(user_id: int) -> dict:
    ...     return await db.get_user(user_id)
"""

from .arc import (
    # Main classes
    ArcCache,
    ArcCacheSync,
    
    # Decorator
    arc_cache,
    
    # Types
    CacheEntry,
    CacheStats,
    
    # Utilities
    RWLock,
    LRUList,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    'ArcCache',
    'ArcCacheSync',
    'arc_cache',
    'CacheEntry',
    'CacheStats',
    'RWLock',
    'LRUList',
]
