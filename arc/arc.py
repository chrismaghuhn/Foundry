"""
Arc: Adaptive Replacement Cache

A self-tuning cache that automatically balances recency and frequency based on
observed access patterns. Implements the ARC algorithm from IBM Research.

Why ARC over LRU?
    LRU suffers from "scan pollution" — a sequential scan evicts your entire
    working set. LRU also can't distinguish between items accessed once vs
    items accessed repeatedly.
    
    ARC maintains two LRU lists:
    - T1: Items seen once recently (recency)
    - T2: Items seen at least twice (frequency)
    
    Plus two "ghost" lists that track recently evicted keys:
    - B1: Keys recently evicted from T1
    - B2: Keys recently evicted from T2
    
    The key insight is adaptive sizing. ARC maintains a target size `p` for T1.
    When we get a "ghost hit" in B1 (meaning we evicted something too soon from T1),
    we increase p to favor recency. Ghost hits in B2 decrease p to favor frequency.

Algorithm Reference:
    Megiddo & Modha, "ARC: A Self-Tuning, Low Overhead Replacement Cache"
    USENIX FAST 2003

Complexity:
    - All operations: O(1) amortized
    - Space: O(2c) keys + O(c) values where c is capacity

Thread Safety:
    - All public methods are protected by an async RWLock
    - Read operations (get without fetch) use read lock
    - Write operations (put, eviction) use write lock

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Hashable,
    Iterator,
    TypeVar,
    Optional,
)

# Type variables
K = TypeVar('K', bound=Hashable)
V = TypeVar('V')


# =============================================================================
# Async RWLock Implementation
# =============================================================================

class RWLock:
    """
    Async Read-Write Lock.
    
    This implementation uses a simple asyncio.Lock for both reads and writes.
    In practice, for a cache with mostly writes (get causes promotion = write),
    a simple lock is sufficient and avoids complexity.
    
    A more sophisticated implementation would allow concurrent reads,
    but the correctness-first approach is simpler.
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    class _LockContext:
        def __init__(self, lock: asyncio.Lock):
            self._lock = lock
        
        async def __aenter__(self):
            await self._lock.acquire()
            return self
        
        async def __aexit__(self, *args):
            self._lock.release()
    
    def read(self) -> _LockContext:
        """Acquire read lock (same as write in this implementation)."""
        return self._LockContext(self._lock)
    
    def write(self) -> _LockContext:
        """Acquire write lock."""
        return self._LockContext(self._lock)


# =============================================================================
# LRU List Implementation
# =============================================================================

class LRUList(Generic[K, V]):
    """
    Doubly-linked LRU list with O(1) operations.
    
    Uses OrderedDict internally for simplicity while maintaining O(1) guarantees.
    Supports both full entries (key → value) and ghost entries (key only).
    
    Operations:
    - add_mru(key, value): Add to most-recently-used end
    - remove(key): Remove and return value
    - pop_lru(): Remove and return least-recently-used
    - move_to_mru(key): Move existing key to MRU position
    - contains(key): Check membership
    - peek_lru(): View LRU without removing
    """
    
    def __init__(self):
        self._data: OrderedDict[K, V | None] = OrderedDict()
    
    def __len__(self) -> int:
        return len(self._data)
    
    def __contains__(self, key: K) -> bool:
        return key in self._data
    
    def __iter__(self) -> Iterator[K]:
        return iter(self._data)
    
    def add_mru(self, key: K, value: V | None = None) -> None:
        """Add item at MRU position (end of list)."""
        if key in self._data:
            del self._data[key]
        self._data[key] = value
    
    def remove(self, key: K) -> V | None:
        """Remove and return item. Returns None if not found."""
        return self._data.pop(key, None)
    
    def pop_lru(self) -> tuple[K, V | None] | None:
        """Remove and return LRU item (first in list)."""
        if not self._data:
            return None
        key, value = next(iter(self._data.items()))
        del self._data[key]
        return key, value
    
    def peek_lru(self) -> tuple[K, V | None] | None:
        """View LRU item without removing."""
        if not self._data:
            return None
        key = next(iter(self._data))
        return key, self._data[key]
    
    def move_to_mru(self, key: K) -> bool:
        """Move existing key to MRU position. Returns False if not found."""
        if key not in self._data:
            return False
        self._data.move_to_end(key)
        return True
    
    def get(self, key: K) -> V | None:
        """Get value without moving position."""
        return self._data.get(key)
    
    def clear(self) -> None:
        """Remove all items."""
        self._data.clear()


# =============================================================================
# Cache Entry
# =============================================================================

@dataclass
class CacheEntry(Generic[V]):
    """
    Metadata for a cached value.
    
    Tracks access statistics for potential future extensions
    (e.g., TTL, access counting for metrics).
    """
    value: V
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 1
    
    def touch(self) -> None:
        """Update access timestamp and count."""
        self.last_accessed = time.time()
        self.access_count += 1


# =============================================================================
# Cache Statistics
# =============================================================================

@dataclass
class CacheStats:
    """
    Cache performance statistics.
    
    Useful for monitoring and tuning.
    """
    hits: int = 0
    misses: int = 0
    ghost_hits_b1: int = 0  # Would have been in T1
    ghost_hits_b2: int = 0  # Would have been in T2
    evictions: int = 0
    
    @property
    def total_requests(self) -> int:
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate
    
    def to_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "ghost_hits_b1": self.ghost_hits_b1,
            "ghost_hits_b2": self.ghost_hits_b2,
            "evictions": self.evictions,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate,
        }


# =============================================================================
# ARC Cache Implementation
# =============================================================================

class ArcCache(Generic[K, V]):
    """
    Adaptive Replacement Cache with self-tuning eviction policy.
    
    ARC automatically balances between:
    - Recency: Items accessed recently (even if only once)
    - Frequency: Items accessed multiple times
    
    The balance is controlled by parameter `p`, which adapts based on
    workload. Ghost hits in B1 increase p (more recency), ghost hits
    in B2 decrease p (more frequency).
    
    Usage:
        cache = ArcCache[str, bytes](capacity=1000)
        
        # Simple get/put
        await cache.put("key", b"value")
        value = await cache.get("key")
        
        # Get with automatic fetch on miss
        async def fetch_from_db(key: str) -> bytes:
            return await db.get(key)
        
        value = await cache.get_or_fetch("key", fetch_from_db)
        
        # Statistics
        stats = cache.stats
        print(f"Hit rate: {stats.hit_rate:.2%}")
    
    Parameters:
        capacity: Maximum number of items to cache
    
    Implementation Notes:
        The cache maintains four lists:
        - T1: Recently accessed items (seen once)
        - T2: Frequently accessed items (seen 2+ times)
        - B1: Ghost list of keys recently evicted from T1
        - B2: Ghost list of keys recently evicted from T2
        
        Invariants:
        - |T1| + |T2| ≤ capacity (real items)
        - |T1| + |B1| ≤ capacity (recency history)
        - |T2| + |B2| ≤ capacity (frequency history)
        - |T1| + |T2| + |B1| + |B2| ≤ 2 * capacity (total)
    """
    
    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")
        
        self._capacity = capacity
        
        # Target size for T1 (adaptive parameter)
        self._p: float = 0.0
        
        # Real cache lists (store actual values)
        self._t1: LRUList[K, CacheEntry[V]] = LRUList()  # Recent, seen once
        self._t2: LRUList[K, CacheEntry[V]] = LRUList()  # Frequent, seen 2+
        
        # Ghost lists (store only keys, for adaptation)
        self._b1: LRUList[K, None] = LRUList()  # Recently evicted from T1
        self._b2: LRUList[K, None] = LRUList()  # Recently evicted from T2
        
        # Statistics
        self._stats = CacheStats()
        
        # Concurrency control
        self._lock = RWLock()
    
    @property
    def capacity(self) -> int:
        """Maximum number of cached items."""
        return self._capacity
    
    @property
    def size(self) -> int:
        """Current number of cached items."""
        return len(self._t1) + len(self._t2)
    
    @property
    def stats(self) -> CacheStats:
        """Cache statistics (hits, misses, hit rate, etc.)."""
        return self._stats
    
    @property
    def p(self) -> float:
        """
        Current target size for T1 (recency list).
        
        Higher p means more space for recently-accessed items.
        Lower p means more space for frequently-accessed items.
        """
        return self._p
    
    async def get(self, key: K) -> V | None:
        """
        Get value from cache.
        
        Returns None if key not in cache (doesn't fetch).
        """
        async with self._lock.write():  # Need write for promotion
            return self._get_internal(key)
    
    def _get_internal(self, key: K) -> V | None:
        """Internal get without locking. Handles cache hit logic."""
        
        # Case 1: Hit in T1 (recent) - promote to T2 (frequent)
        if key in self._t1:
            entry = self._t1.remove(key)
            entry.touch()
            self._t2.add_mru(key, entry)
            self._stats.hits += 1
            return entry.value
        
        # Case 2: Hit in T2 (frequent) - move to MRU of T2
        if key in self._t2:
            entry = self._t2.get(key)
            entry.touch()
            self._t2.move_to_mru(key)
            self._stats.hits += 1
            return entry.value
        
        # Case 3: Miss
        self._stats.misses += 1
        return None
    
    async def put(self, key: K, value: V) -> None:
        """
        Put value into cache.
        
        If key exists, updates the value and promotes if in T1.
        If key is new, adds to T1 (may trigger eviction).
        """
        async with self._lock.write():
            self._put_internal(key, value)
    
    def _put_internal(self, key: K, value: V) -> None:
        """Internal put without locking."""
        
        # Case 1: Key already in T1
        if key in self._t1:
            entry = self._t1.remove(key)
            entry.value = value
            entry.touch()
            self._t2.add_mru(key, entry)
            return
        
        # Case 2: Key already in T2
        if key in self._t2:
            entry = self._t2.get(key)
            entry.value = value
            entry.touch()
            self._t2.move_to_mru(key)
            return
        
        # Case 3: Key in B1 (ghost hit - was evicted from T1 too soon)
        if key in self._b1:
            self._stats.ghost_hits_b1 += 1
            
            # Adapt: increase p to give more space to T1
            delta = max(1.0, len(self._b2) / max(1, len(self._b1)))
            self._p = min(self._p + delta, float(self._capacity))
            
            # Remove from B1
            self._b1.remove(key)
            
            # Make room and insert to T2 (it's been accessed twice now)
            self._replace(key, in_b2=False)
            self._t2.add_mru(key, CacheEntry(value))
            return
        
        # Case 4: Key in B2 (ghost hit - was evicted from T2 too soon)
        if key in self._b2:
            self._stats.ghost_hits_b2 += 1
            
            # Adapt: decrease p to give more space to T2
            delta = max(1.0, len(self._b1) / max(1, len(self._b2)))
            self._p = max(self._p - delta, 0.0)
            
            # Remove from B2
            self._b2.remove(key)
            
            # Make room and insert to T2
            self._replace(key, in_b2=True)
            self._t2.add_mru(key, CacheEntry(value))
            return
        
        # Case 5: Complete miss (not in cache or ghost lists)
        
        # First, make room if needed
        total_t1_b1 = len(self._t1) + len(self._b1)
        total_t2_b2 = len(self._t2) + len(self._b2)
        total_size = total_t1_b1 + total_t2_b2
        
        if total_t1_b1 == self._capacity:
            # T1 + B1 is full
            if len(self._t1) < self._capacity:
                # There's room in T1, just remove oldest ghost from B1
                self._b1.pop_lru()
            else:
                # T1 is full, evict LRU from T1 to B1 first
                # (handled by _replace below)
                pass
        elif total_size >= 2 * self._capacity:
            # Total history is full, remove from B2
            if len(self._b2) > 0:
                self._b2.pop_lru()
            else:
                self._b1.pop_lru()
        
        # Now make room in actual cache
        self._replace(key, in_b2=False)
        
        # Insert to T1 (first access)
        self._t1.add_mru(key, CacheEntry(value))
    
    def _replace(self, key: K, in_b2: bool) -> None:
        """
        Make room for a new item by evicting if necessary.
        
        Args:
            key: The key about to be inserted (for decision making)
            in_b2: Whether the triggering event was a B2 ghost hit
        """
        t1_size = len(self._t1)
        t2_size = len(self._t2)
        
        if t1_size + t2_size < self._capacity:
            # No eviction needed
            return
        
        # Decide whether to evict from T1 or T2
        # Evict from T1 if:
        # - T1 is larger than target p, OR
        # - T1 is at target p but key is in B2 (favor T2)
        if t1_size > 0 and (t1_size > self._p or (t1_size == int(self._p) and in_b2)):
            # Evict LRU from T1 → B1
            evicted = self._t1.pop_lru()
            if evicted:
                evicted_key, _ = evicted
                self._b1.add_mru(evicted_key, None)
                self._stats.evictions += 1
        else:
            # Evict LRU from T2 → B2
            if t2_size > 0:
                evicted = self._t2.pop_lru()
                if evicted:
                    evicted_key, _ = evicted
                    self._b2.add_mru(evicted_key, None)
                    self._stats.evictions += 1
    
    async def get_or_fetch(
        self,
        key: K,
        fetch: Callable[[K], Awaitable[V]],
    ) -> V:
        """
        Get value from cache, fetching on miss.
        
        This is the primary interface for most use cases. On cache miss,
        calls the fetch function to load the value, caches it, and returns.
        
        Args:
            key: Cache key
            fetch: Async function to fetch value on miss
        
        Returns:
            Cached or freshly fetched value
        
        Raises:
            Exception from fetch function on failure (value not cached)
        """
        # Try cache first
        async with self._lock.write():
            value = self._get_internal(key)
            if value is not None:
                return value
        
        # Fetch outside the lock to allow concurrent fetches
        # This is a deliberate design choice: we allow multiple
        # concurrent fetches for the same key. The last one wins.
        # Alternative would be to use a per-key lock, but that adds
        # complexity and memory overhead.
        value = await fetch(key)
        
        # Cache the result
        async with self._lock.write():
            self._put_internal(key, value)
        
        return value
    
    async def remove(self, key: K) -> V | None:
        """
        Remove key from cache.
        
        Returns the value if it was cached, None otherwise.
        Also removes from ghost lists if present.
        """
        async with self._lock.write():
            # Check T1
            if key in self._t1:
                entry = self._t1.remove(key)
                return entry.value if entry else None
            
            # Check T2
            if key in self._t2:
                entry = self._t2.remove(key)
                return entry.value if entry else None
            
            # Remove from ghosts too
            self._b1.remove(key)
            self._b2.remove(key)
            
            return None
    
    async def clear(self) -> None:
        """Clear all cached items and reset statistics."""
        async with self._lock.write():
            self._t1.clear()
            self._t2.clear()
            self._b1.clear()
            self._b2.clear()
            self._p = 0.0
            self._stats = CacheStats()
    
    async def contains(self, key: K) -> bool:
        """Check if key is in cache (without affecting LRU order)."""
        async with self._lock.read():
            return key in self._t1 or key in self._t2
    
    async def keys(self) -> list[K]:
        """Get all cached keys."""
        async with self._lock.read():
            return list(self._t1) + list(self._t2)
    
    async def debug_state(self) -> dict:
        """
        Get internal state for debugging.
        
        Returns sizes of all lists and current p value.
        """
        async with self._lock.read():
            return {
                "capacity": self._capacity,
                "p": self._p,
                "t1_size": len(self._t1),
                "t2_size": len(self._t2),
                "b1_size": len(self._b1),
                "b2_size": len(self._b2),
                "total_cached": len(self._t1) + len(self._t2),
            }


# =============================================================================
# Synchronous Wrapper
# =============================================================================

class ArcCacheSync(Generic[K, V]):
    """
    Synchronous wrapper for ArcCache.
    
    For use in non-async contexts. All operations are blocking.
    
    Usage:
        cache = ArcCacheSync[str, int](capacity=100)
        cache.put("key", 42)
        value = cache.get("key")
    """
    
    def __init__(self, capacity: int):
        self._cache = ArcCache[K, V](capacity)
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _run(self, coro):
        loop = self._get_loop()
        return loop.run_until_complete(coro)
    
    @property
    def capacity(self) -> int:
        return self._cache.capacity
    
    @property
    def size(self) -> int:
        return self._cache.size
    
    @property
    def stats(self) -> CacheStats:
        return self._cache.stats
    
    @property
    def p(self) -> float:
        return self._cache.p
    
    def get(self, key: K) -> V | None:
        return self._run(self._cache.get(key))
    
    def put(self, key: K, value: V) -> None:
        self._run(self._cache.put(key, value))
    
    def remove(self, key: K) -> V | None:
        return self._run(self._cache.remove(key))
    
    def clear(self) -> None:
        self._run(self._cache.clear())
    
    def contains(self, key: K) -> bool:
        return self._run(self._cache.contains(key))
    
    def keys(self) -> list[K]:
        return self._run(self._cache.keys())
    
    def debug_state(self) -> dict:
        return self._run(self._cache.debug_state())


# =============================================================================
# Function Decorator
# =============================================================================

def arc_cache(capacity: int = 128):
    """
    Decorator for caching async function results with ARC policy.
    
    Similar to functools.lru_cache but:
    - Uses ARC instead of LRU (better hit rate)
    - Supports async functions
    - Configurable capacity
    
    Usage:
        @arc_cache(capacity=1000)
        async def fetch_user(user_id: int) -> User:
            return await db.get_user(user_id)
        
        # Access cache stats
        print(fetch_user.cache_stats())
        
        # Clear cache
        await fetch_user.cache_clear()
    
    Note:
        Arguments must be hashable. The cache key is a tuple of all arguments.
    """
    def decorator(func: Callable[..., Awaitable[V]]) -> Callable[..., Awaitable[V]]:
        cache: ArcCache[tuple, V] = ArcCache(capacity)
        
        async def wrapper(*args, **kwargs) -> V:
            # Create cache key from arguments
            key = (args, tuple(sorted(kwargs.items())))
            
            # Try cache
            result = await cache.get(key)
            if result is not None:
                return result
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.put(key, result)
            
            return result
        
        # Attach cache management methods
        wrapper.cache = cache
        wrapper.cache_stats = lambda: cache.stats
        wrapper.cache_clear = cache.clear
        wrapper.cache_size = lambda: cache.size
        
        return wrapper
    
    return decorator


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main classes
    'ArcCache',
    'ArcCacheSync',
    
    # Decorator
    'arc_cache',
    
    # Types
    'CacheEntry',
    'CacheStats',
    
    # Utilities
    'RWLock',
    'LRUList',
]
