#!/usr/bin/env python3
"""
Arc Usage Examples

Demonstrates real-world usage of the Adaptive Replacement Cache.
"""

import asyncio
import time
import random
from arc import ArcCache, ArcCacheSync, arc_cache, CacheStats


async def example_basic_cache():
    """
    Example 1: Basic Cache Operations
    """
    print("=" * 60)
    print("Example 1: Basic Cache Operations")
    print("=" * 60)
    
    cache: ArcCache[str, int] = ArcCache(capacity=100)
    
    # Simple put and get
    await cache.put("answer", 42)
    await cache.put("year", 2024)
    
    print(f"\nStored values:")
    print(f"  answer = {await cache.get('answer')}")
    print(f"  year = {await cache.get('year')}")
    print(f"  missing = {await cache.get('missing')}")
    
    # Check stats
    print(f"\nCache stats:")
    print(f"  Size: {cache.size}/{cache.capacity}")
    print(f"  Hits: {cache.stats.hits}")
    print(f"  Misses: {cache.stats.misses}")
    print()


async def example_get_or_fetch():
    """
    Example 2: Automatic Fetching on Miss
    """
    print("=" * 60)
    print("Example 2: Get or Fetch Pattern")
    print("=" * 60)
    
    cache: ArcCache[str, dict] = ArcCache(capacity=100)
    
    # Simulated database
    database = {
        "user:1": {"name": "Alice", "email": "alice@example.com"},
        "user:2": {"name": "Bob", "email": "bob@example.com"},
        "user:3": {"name": "Charlie", "email": "charlie@example.com"},
    }
    
    async def fetch_user(user_id: str) -> dict:
        """Simulate database fetch with delay."""
        print(f"  [DB] Fetching {user_id}...")
        await asyncio.sleep(0.1)  # Simulate latency
        return database.get(user_id, {"error": "not found"})
    
    print("\nFirst fetch (cache miss):")
    user = await cache.get_or_fetch("user:1", fetch_user)
    print(f"  Result: {user}")
    
    print("\nSecond fetch (cache hit):")
    user = await cache.get_or_fetch("user:1", fetch_user)
    print(f"  Result: {user}")
    
    print(f"\nStats: {cache.stats.hits} hits, {cache.stats.misses} misses")
    print()


async def example_arc_vs_lru():
    """
    Example 3: ARC vs LRU - Scan Resistance
    """
    print("=" * 60)
    print("Example 3: ARC Scan Resistance")
    print("=" * 60)
    
    cache: ArcCache[int, str] = ArcCache(capacity=10)
    
    # Create a "working set" of frequently accessed items
    print("\nBuilding working set (items 0-4, accessed twice each):")
    for i in range(5):
        await cache.put(i, f"working_{i}")
        await cache.get(i)  # Access twice to promote to T2
    
    print(f"  Working set in cache: {await cache.keys()}")
    
    # Simulate a "scan" - sequential access to many different items
    print("\nSimulating scan (items 100-119, accessed once each):")
    for i in range(100, 120):
        await cache.put(i, f"scan_{i}")
    
    # Check how much of working set survived
    working_set_hits = 0
    for i in range(5):
        if await cache.get(i) is not None:
            working_set_hits += 1
    
    print(f"\nWorking set items surviving: {working_set_hits}/5")
    print(f"ARC parameter p (T1 target size): {cache.p:.1f}")
    print("(With LRU, entire working set would be evicted)")
    print()


async def example_adaptive_behavior():
    """
    Example 4: ARC's Adaptive Parameter
    """
    print("=" * 60)
    print("Example 4: Adaptive Behavior")
    print("=" * 60)
    
    cache: ArcCache[int, int] = ArcCache(capacity=10)
    
    # Phase 1: Recency-heavy workload
    print("\nPhase 1: Recency-heavy (many unique items)")
    for i in range(50):
        await cache.put(i, i)
    
    print(f"  p = {cache.p:.2f} (target T1 size)")
    
    # Phase 2: Frequency-heavy workload
    print("\nPhase 2: Frequency-heavy (same items repeatedly)")
    for _ in range(100):
        key = random.randint(0, 9)
        await cache.put(key, key)
        await cache.get(key)
    
    print(f"  p = {cache.p:.2f} (should adapt based on ghost hits)")
    
    state = await cache.debug_state()
    print(f"\nInternal state:")
    print(f"  T1 (recent): {state['t1_size']} items")
    print(f"  T2 (frequent): {state['t2_size']} items")
    print(f"  B1 (ghost recent): {state['b1_size']} items")
    print(f"  B2 (ghost frequent): {state['b2_size']} items")
    print()


async def example_decorator():
    """
    Example 5: Function Caching with Decorator
    """
    print("=" * 60)
    print("Example 5: @arc_cache Decorator")
    print("=" * 60)
    
    call_count = 0
    
    @arc_cache(capacity=100)
    async def expensive_computation(x: int, y: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)  # Simulate expensive work
        return x * y + x + y
    
    print("\nCalling expensive_computation(3, 4) three times:")
    
    start = time.time()
    result1 = await expensive_computation(3, 4)
    time1 = time.time() - start
    print(f"  Call 1: {result1} ({time1*1000:.1f}ms)")
    
    start = time.time()
    result2 = await expensive_computation(3, 4)
    time2 = time.time() - start
    print(f"  Call 2: {result2} ({time2*1000:.1f}ms) [cached]")
    
    start = time.time()
    result3 = await expensive_computation(3, 4)
    time3 = time.time() - start
    print(f"  Call 3: {result3} ({time3*1000:.1f}ms) [cached]")
    
    print(f"\nActual function calls: {call_count}")
    print(f"Cache stats: {expensive_computation.cache_stats().hit_rate:.0%} hit rate")
    print()


def example_sync_cache():
    """
    Example 6: Synchronous Cache Usage
    """
    print("=" * 60)
    print("Example 6: Synchronous Cache")
    print("=" * 60)
    
    cache: ArcCacheSync[str, float] = ArcCacheSync(capacity=50)
    
    # Cache some computed values
    print("\nCaching computed values:")
    for i in range(10):
        key = f"sqrt_{i}"
        value = i ** 0.5
        cache.put(key, value)
        print(f"  {key} = {value:.4f}")
    
    print(f"\nRetrieving cached values:")
    print(f"  sqrt_4 = {cache.get('sqrt_4')}")
    print(f"  sqrt_9 = {cache.get('sqrt_9')}")
    
    print(f"\nCache size: {cache.size}")
    print()


async def example_statistics():
    """
    Example 7: Detailed Statistics
    """
    print("=" * 60)
    print("Example 7: Cache Statistics")
    print("=" * 60)
    
    cache: ArcCache[int, int] = ArcCache(capacity=20)
    
    # Generate mixed workload
    print("\nGenerating mixed workload...")
    
    # Some items accessed frequently
    for _ in range(50):
        key = random.randint(0, 5)
        await cache.put(key, key)
        await cache.get(key)
    
    # Some items accessed once (scan)
    for i in range(100, 150):
        await cache.put(i, i)
    
    # Access some cached items
    for _ in range(30):
        await cache.get(random.randint(0, 5))
    
    # Access some missing items
    for i in range(200, 220):
        await cache.get(i)
    
    stats = cache.stats
    print(f"\nStatistics:")
    print(f"  Total requests: {stats.total_requests}")
    print(f"  Hits: {stats.hits}")
    print(f"  Misses: {stats.misses}")
    print(f"  Hit rate: {stats.hit_rate:.1%}")
    print(f"  Evictions: {stats.evictions}")
    print(f"  Ghost hits (B1): {stats.ghost_hits_b1}")
    print(f"  Ghost hits (B2): {stats.ghost_hits_b2}")
    
    print(f"\nAs dictionary: {stats.to_dict()}")
    print()


async def example_concurrent_access():
    """
    Example 8: Concurrent Access
    """
    print("=" * 60)
    print("Example 8: Concurrent Access")
    print("=" * 60)
    
    cache: ArcCache[str, int] = ArcCache(capacity=100)
    
    async def writer(worker_id: int, count: int):
        for i in range(count):
            key = f"worker_{worker_id}_item_{i}"
            await cache.put(key, worker_id * 1000 + i)
            await asyncio.sleep(0.001)
    
    async def reader(worker_id: int, count: int):
        hits = 0
        for i in range(count):
            key = f"worker_{worker_id % 3}_item_{i % 10}"
            if await cache.get(key) is not None:
                hits += 1
            await asyncio.sleep(0.001)
        return hits
    
    print("\nRunning 3 writers and 3 readers concurrently...")
    
    start = time.time()
    results = await asyncio.gather(
        writer(0, 50),
        writer(1, 50),
        writer(2, 50),
        reader(0, 50),
        reader(1, 50),
        reader(2, 50),
    )
    elapsed = time.time() - start
    
    print(f"\nCompleted in {elapsed*1000:.1f}ms")
    print(f"Reader hits: {sum(results[3:])}")
    print(f"Final cache size: {cache.size}")
    print(f"Hit rate: {cache.stats.hit_rate:.1%}")
    print()


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  ARC - ADAPTIVE REPLACEMENT CACHE EXAMPLES")
    print("=" * 60 + "\n")
    
    await example_basic_cache()
    await example_get_or_fetch()
    await example_arc_vs_lru()
    await example_adaptive_behavior()
    await example_decorator()
    example_sync_cache()
    await example_statistics()
    await example_concurrent_access()
    
    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
