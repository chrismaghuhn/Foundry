#!/usr/bin/env python3
"""
Sentinel Usage Examples

Demonstrates real-world scenarios for the Sentinel rate limiting library.
"""

import asyncio
import time
from sentinel import (
    RateLimiter,
    RateLimitConfig,
    Algorithm,
    MultiTierLimiter,
    RateLimitExceeded,
    create_limiter,
    per_second,
    per_minute,
)


async def example_basic_rate_limiting():
    """
    Example 1: Basic Rate Limiting
    
    Simple API rate limiting with token bucket algorithm.
    """
    print("=" * 60)
    print("Example 1: Basic Rate Limiting")
    print("=" * 60)
    
    # 5 requests per second
    limiter = per_second(5)
    
    print("\nSending 10 requests with limit of 5/second:")
    
    for i in range(10):
        response = await limiter.check("user:123")
        
        status = "✓ Allowed" if response.allowed else "✗ Denied"
        print(f"  Request {i+1}: {status} (remaining: {response.remaining})")
        
        if response.denied:
            print(f"    Retry after: {response.retry_after:.2f}s")
    
    print("✓ Basic rate limiting works!\n")


async def example_algorithm_comparison():
    """
    Example 2: Algorithm Comparison
    
    Compare behavior of different algorithms.
    """
    print("=" * 60)
    print("Example 2: Algorithm Comparison")
    print("=" * 60)
    
    algorithms = [
        ("Token Bucket", Algorithm.TOKEN_BUCKET),
        ("Sliding Window", Algorithm.SLIDING_WINDOW),
        ("Fixed Window", Algorithm.FIXED_WINDOW),
        ("Leaky Bucket", Algorithm.LEAKY_BUCKET),
    ]
    
    for name, algo in algorithms:
        limiter = create_limiter(5, 1.0, algorithm=algo)
        
        # Rapid burst of 8 requests
        allowed = 0
        for _ in range(8):
            if (await limiter.check(f"test-{name}")).allowed:
                allowed += 1
        
        print(f"\n{name}:")
        print(f"  Allowed {allowed}/8 rapid requests (limit: 5/sec)")
        
        # Wait a bit and try again
        await asyncio.sleep(0.3)
        
        response = await limiter.check(f"test-{name}")
        print(f"  After 0.3s wait: {'Allowed' if response.allowed else 'Denied'}")
    
    print("\n✓ Algorithm comparison complete!\n")


async def example_decorator_usage():
    """
    Example 3: Decorator-Based Rate Limiting
    
    Protect functions with decorators.
    """
    print("=" * 60)
    print("Example 3: Decorator-Based Rate Limiting")
    print("=" * 60)
    
    limiter = create_limiter(3, 1.0)
    
    @limiter.limit(key_func=lambda user_id: f"api:{user_id}")
    async def call_api(user_id: int) -> dict:
        """Simulated API call."""
        return {"user": user_id, "data": "success"}
    
    print("\nCalling API as user 1:")
    for i in range(5):
        try:
            result = await call_api(1)
            print(f"  Call {i+1}: {result}")
        except RateLimitExceeded as e:
            print(f"  Call {i+1}: ✗ Rate limited! Retry in {e.response.retry_after:.2f}s")
    
    print("\nCalling API as user 2 (separate quota):")
    for i in range(3):
        result = await call_api(2)
        print(f"  Call {i+1}: {result}")
    
    print("✓ Decorator rate limiting works!\n")


async def example_context_manager():
    """
    Example 4: Context Manager Usage
    
    Use context manager for fine-grained control.
    """
    print("=" * 60)
    print("Example 4: Context Manager Usage")
    print("=" * 60)
    
    limiter = create_limiter(3, 1.0)
    
    print("\nProcessing requests with context manager:")
    
    for i in range(5):
        async with limiter(f"user:456") as response:
            if response.allowed:
                print(f"  Request {i+1}: ✓ Processing... (remaining: {response.remaining})")
                await asyncio.sleep(0.05)  # Simulate work
            else:
                print(f"  Request {i+1}: ✗ Skipped (retry in {response.retry_after:.2f}s)")
    
    print("✓ Context manager works!\n")


async def example_multi_tier_limiting():
    """
    Example 5: Multi-Tier Rate Limiting
    
    Apply multiple limits simultaneously.
    """
    print("=" * 60)
    print("Example 5: Multi-Tier Rate Limiting")
    print("=" * 60)
    
    # Three tiers:
    # - 3 requests per second (burst protection)
    # - 10 requests per 10 seconds (short-term limit)
    # - 100 requests per minute (sustained limit)
    
    tiers = MultiTierLimiter([
        per_second(3),
        create_limiter(10, 10.0),
        per_minute(100),
    ])
    
    print("\nSending requests with 3-tier limiting:")
    print("  Tier 1: 3/second")
    print("  Tier 2: 10/10 seconds")
    print("  Tier 3: 100/minute")
    
    # Simulate bursty traffic
    total_allowed = 0
    total_denied = 0
    
    for batch in range(3):
        print(f"\n  Batch {batch + 1} (5 rapid requests):")
        for i in range(5):
            response = await tiers.check("user:789")
            if response.allowed:
                total_allowed += 1
                print(f"    Request {i+1}: ✓")
            else:
                total_denied += 1
                print(f"    Request {i+1}: ✗ (limited)")
        
        if batch < 2:
            print("    [Waiting 0.5s...]")
            await asyncio.sleep(0.5)
    
    print(f"\n  Total: {total_allowed} allowed, {total_denied} denied")
    print("✓ Multi-tier limiting works!\n")


async def example_wait_for_quota():
    """
    Example 6: Wait for Quota
    
    Block until quota is available (for background jobs).
    """
    print("=" * 60)
    print("Example 6: Wait for Quota")
    print("=" * 60)
    
    limiter = create_limiter(2, 1.0)
    
    print("\nBackground job processing with waiting:")
    
    async def process_job(job_id: int):
        start = time.time()
        response = await limiter.wait_and_check("jobs", max_wait=5.0)
        waited = time.time() - start
        
        if response.allowed:
            print(f"  Job {job_id}: Started after {waited:.2f}s wait")
            await asyncio.sleep(0.1)  # Simulate work
            return True
        else:
            print(f"  Job {job_id}: Timeout after {waited:.2f}s")
            return False
    
    # Launch 5 jobs concurrently (only 2/sec allowed)
    print("\n  Launching 5 concurrent jobs (limit: 2/sec):")
    start = time.time()
    results = await asyncio.gather(*[process_job(i+1) for i in range(5)])
    total = time.time() - start
    
    print(f"\n  All jobs completed in {total:.2f}s")
    print(f"  Successful: {sum(results)}/{len(results)}")
    print("✓ Wait for quota works!\n")


async def example_api_headers():
    """
    Example 7: HTTP API Headers
    
    Extract rate limit info for HTTP headers.
    """
    print("=" * 60)
    print("Example 7: HTTP API Headers")
    print("=" * 60)
    
    limiter = per_minute(100)
    
    print("\nSimulating API response headers:")
    
    for i in range(3):
        response = await limiter.check("api-client")
        
        # Standard rate limit headers
        headers = {
            "X-RateLimit-Limit": str(response.limit),
            "X-RateLimit-Remaining": str(response.remaining),
            "X-RateLimit-Reset": str(int(response.reset_at)),
        }
        
        if response.denied:
            headers["Retry-After"] = str(int(response.retry_after) + 1)
        
        print(f"\n  Request {i+1}:")
        for header, value in headers.items():
            print(f"    {header}: {value}")
    
    print("\n✓ Headers generated correctly!\n")


async def example_burst_handling():
    """
    Example 8: Burst Handling
    
    Token bucket with burst capacity.
    """
    print("=" * 60)
    print("Example 8: Burst Handling")
    print("=" * 60)
    
    # 10/sec sustained, but allow bursts up to 30
    limiter = create_limiter(
        10, 1.0,
        algorithm=Algorithm.TOKEN_BUCKET,
        burst=30
    )
    
    print("\nToken bucket with burst=30, sustained=10/sec:")
    
    # Rapid burst
    print("\n  Phase 1: Rapid burst of 35 requests")
    allowed = 0
    for _ in range(35):
        if (await limiter.check("burst-test")).allowed:
            allowed += 1
    print(f"  Allowed: {allowed}/35")
    
    # Wait for refill
    print("\n  Phase 2: Waiting 1 second for refill...")
    await asyncio.sleep(1.0)
    
    # Check how many tokens refilled
    response = await limiter.peek("burst-test")
    print(f"  Tokens refilled: ~{response.remaining}")
    
    # More requests
    print("\n  Phase 3: 15 more requests")
    allowed = 0
    for _ in range(15):
        if (await limiter.check("burst-test")).allowed:
            allowed += 1
    print(f"  Allowed: {allowed}/15")
    
    print("✓ Burst handling works!\n")


async def example_per_endpoint_limiting():
    """
    Example 9: Per-Endpoint Rate Limiting
    
    Different limits for different API endpoints.
    """
    print("=" * 60)
    print("Example 9: Per-Endpoint Rate Limiting")
    print("=" * 60)
    
    # Different limits per endpoint
    limiters = {
        "/api/search": create_limiter(10, 1.0),   # 10/sec (fast)
        "/api/write": create_limiter(5, 1.0),     # 5/sec (slower)
        "/api/admin": create_limiter(2, 1.0),     # 2/sec (restricted)
    }
    
    print("\nEndpoint-specific rate limits:")
    for endpoint, limiter in limiters.items():
        print(f"  {endpoint}: {limiter.config.limit}/sec")
    
    print("\nSimulating requests:")
    
    async def call_endpoint(endpoint: str, user_id: str):
        limiter = limiters[endpoint]
        response = await limiter.check(f"{endpoint}:{user_id}")
        return response.allowed
    
    for endpoint in limiters:
        allowed = 0
        for _ in range(12):
            if await call_endpoint(endpoint, "user1"):
                allowed += 1
        print(f"  {endpoint}: {allowed}/12 requests allowed")
    
    print("✓ Per-endpoint limiting works!\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  SENTINEL RATE LIMITING LIBRARY - EXAMPLES")
    print("=" * 60 + "\n")
    
    await example_basic_rate_limiting()
    await example_algorithm_comparison()
    await example_decorator_usage()
    await example_context_manager()
    await example_multi_tier_limiting()
    await example_wait_for_quota()
    await example_api_headers()
    await example_burst_handling()
    await example_per_endpoint_limiting()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
