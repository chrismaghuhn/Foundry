"""Tests for sentinel."""

import asyncio
import pytest
import time
from sentinel import (
    RateLimiter,
    RateLimitConfig,
    RateLimitResponse,
    LimitResult,
    Algorithm,
    InMemoryBackend,
    MultiTierLimiter,
    RateLimitExceeded,
    create_limiter,
    per_second,
    per_minute,
)


# =============================================================================
# Backend Tests
# =============================================================================

class TestInMemoryBackend:
    """Test in-memory backend operations."""
    
    @pytest.mark.asyncio
    async def test_get_set(self):
        """Basic get/set operations."""
        backend = InMemoryBackend()
        
        await backend.set("key1", {"count": 5}, ttl_seconds=60)
        result = await backend.get("key1")
        
        assert result == {"count": 5}
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Get returns None for missing keys."""
        backend = InMemoryBackend()
        result = await backend.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        """Keys expire after TTL."""
        backend = InMemoryBackend()
        
        await backend.set("key1", {"x": 1}, ttl_seconds=0.1)
        
        # Should exist immediately
        assert await backend.get("key1") is not None
        
        # Should expire
        await asyncio.sleep(0.15)
        assert await backend.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_increment(self):
        """Atomic increment operations."""
        backend = InMemoryBackend()
        
        await backend.set("key1", {"count": 10}, ttl_seconds=60)
        
        new_val = await backend.increment("key1", "count", 5)
        assert new_val == 15
        
        result = await backend.get("key1")
        assert result["count"] == 15
    
    @pytest.mark.asyncio
    async def test_get_and_set_atomic(self):
        """Atomic get-and-set operations."""
        backend = InMemoryBackend()
        
        await backend.set("key1", {"value": 100}, ttl_seconds=60)
        
        def double_it(current):
            if current is None:
                return {"value": 0}
            return {"value": current["value"] * 2}
        
        result = await backend.get_and_set("key1", double_it, ttl_seconds=60)
        assert result["value"] == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Concurrent operations are thread-safe."""
        backend = InMemoryBackend()
        await backend.set("counter", {"n": 0}, ttl_seconds=60)
        
        async def increment():
            for _ in range(100):
                await backend.increment("counter", "n", 1)
        
        # Run 10 concurrent incrementers
        await asyncio.gather(*[increment() for _ in range(10)])
        
        result = await backend.get("counter")
        assert result["n"] == 1000  # 10 * 100


# =============================================================================
# Token Bucket Algorithm Tests
# =============================================================================

class TestTokenBucket:
    """Test token bucket algorithm."""
    
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Requests within limit are allowed."""
        limiter = create_limiter(10, 1.0, algorithm=Algorithm.TOKEN_BUCKET)
        
        for i in range(10):
            response = await limiter.check("user1")
            assert response.allowed, f"Request {i+1} should be allowed"
    
    @pytest.mark.asyncio
    async def test_denies_over_limit(self):
        """Requests over limit are denied."""
        limiter = create_limiter(5, 1.0, algorithm=Algorithm.TOKEN_BUCKET)
        
        # Use up all tokens
        for _ in range(5):
            await limiter.check("user1")
        
        # Next request should be denied
        response = await limiter.check("user1")
        assert response.denied
        assert response.retry_after is not None
        assert response.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_tokens_refill(self):
        """Tokens refill over time."""
        limiter = create_limiter(10, 1.0, algorithm=Algorithm.TOKEN_BUCKET)
        
        # Use all tokens
        for _ in range(10):
            await limiter.check("user1")
        
        # Should be denied
        assert not (await limiter.check("user1")).allowed
        
        # Wait for refill (1 token per 0.1s for 10/second)
        await asyncio.sleep(0.15)
        
        # Should have refilled
        assert (await limiter.check("user1")).allowed
    
    @pytest.mark.asyncio
    async def test_burst_capacity(self):
        """Burst allows exceeding normal rate temporarily."""
        limiter = create_limiter(
            10, 1.0, 
            algorithm=Algorithm.TOKEN_BUCKET,
            burst=20  # Can burst to 20
        )
        
        # Should allow 20 rapid requests
        allowed = 0
        for _ in range(25):
            if (await limiter.check("user1")).allowed:
                allowed += 1
        
        assert allowed == 20


# =============================================================================
# Sliding Window Algorithm Tests
# =============================================================================

class TestSlidingWindow:
    """Test sliding window algorithm."""
    
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Requests within limit are allowed."""
        limiter = create_limiter(5, 1.0, algorithm=Algorithm.SLIDING_WINDOW)
        
        for i in range(5):
            response = await limiter.check("user1")
            assert response.allowed, f"Request {i+1} should be allowed"
    
    @pytest.mark.asyncio
    async def test_denies_over_limit(self):
        """Requests over limit are denied."""
        limiter = create_limiter(5, 1.0, algorithm=Algorithm.SLIDING_WINDOW)
        
        for _ in range(5):
            await limiter.check("user1")
        
        response = await limiter.check("user1")
        assert response.denied
    
    @pytest.mark.asyncio
    async def test_window_slides(self):
        """Old requests expire from the window."""
        limiter = create_limiter(5, 0.5, algorithm=Algorithm.SLIDING_WINDOW)
        
        # Use all quota
        for _ in range(5):
            await limiter.check("user1")
        
        assert not (await limiter.check("user1")).allowed
        
        # Wait for window to slide
        await asyncio.sleep(0.6)
        
        # Should be allowed again
        assert (await limiter.check("user1")).allowed


# =============================================================================
# Fixed Window Algorithm Tests
# =============================================================================

class TestFixedWindow:
    """Test fixed window algorithm."""
    
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Requests within limit are allowed."""
        limiter = create_limiter(5, 1.0, algorithm=Algorithm.FIXED_WINDOW)
        
        for i in range(5):
            response = await limiter.check("user1")
            assert response.allowed
    
    @pytest.mark.asyncio
    async def test_denies_over_limit(self):
        """Requests over limit are denied."""
        limiter = create_limiter(5, 1.0, algorithm=Algorithm.FIXED_WINDOW)
        
        for _ in range(5):
            await limiter.check("user1")
        
        response = await limiter.check("user1")
        assert response.denied
    
    @pytest.mark.asyncio
    async def test_window_resets(self):
        """Counter resets when window changes."""
        limiter = create_limiter(5, 0.5, algorithm=Algorithm.FIXED_WINDOW)
        
        for _ in range(5):
            await limiter.check("user1")
        
        assert not (await limiter.check("user1")).allowed
        
        # Wait for next window
        await asyncio.sleep(0.6)
        
        # New window, new quota
        assert (await limiter.check("user1")).allowed


# =============================================================================
# Leaky Bucket Algorithm Tests
# =============================================================================

class TestLeakyBucket:
    """Test leaky bucket algorithm."""
    
    @pytest.mark.asyncio
    async def test_allows_within_capacity(self):
        """Requests within bucket capacity are allowed."""
        limiter = create_limiter(10, 1.0, algorithm=Algorithm.LEAKY_BUCKET)
        
        for i in range(10):
            response = await limiter.check("user1")
            assert response.allowed, f"Request {i+1} should be allowed"
    
    @pytest.mark.asyncio
    async def test_denies_overflow(self):
        """Requests that overflow bucket are denied."""
        limiter = create_limiter(5, 1.0, algorithm=Algorithm.LEAKY_BUCKET)
        
        for _ in range(5):
            await limiter.check("user1")
        
        response = await limiter.check("user1")
        assert response.denied
    
    @pytest.mark.asyncio
    async def test_bucket_leaks(self):
        """Water leaks out over time."""
        limiter = create_limiter(10, 1.0, algorithm=Algorithm.LEAKY_BUCKET)
        
        # Fill bucket
        for _ in range(10):
            await limiter.check("user1")
        
        assert not (await limiter.check("user1")).allowed
        
        # Wait for some water to leak
        await asyncio.sleep(0.2)
        
        # Should have capacity again
        assert (await limiter.check("user1")).allowed


# =============================================================================
# Rate Limiter Interface Tests
# =============================================================================

class TestRateLimiter:
    """Test rate limiter main interface."""
    
    @pytest.mark.asyncio
    async def test_is_allowed_helper(self):
        """is_allowed returns boolean."""
        limiter = create_limiter(2, 1.0)
        
        assert await limiter.is_allowed("user1") is True
        assert await limiter.is_allowed("user1") is True
        assert await limiter.is_allowed("user1") is False
    
    @pytest.mark.asyncio
    async def test_peek_does_not_consume(self):
        """Peek checks quota without consuming."""
        limiter = create_limiter(5, 1.0)
        
        # Peek multiple times
        for _ in range(10):
            response = await limiter.peek("user1")
            assert response.remaining == 5
        
        # Now actually use one
        await limiter.check("user1")
        
        response = await limiter.peek("user1")
        assert response.remaining == 4
    
    @pytest.mark.asyncio
    async def test_different_keys_independent(self):
        """Different keys have independent limits."""
        limiter = create_limiter(2, 1.0)
        
        # Use user1's quota
        await limiter.check("user1")
        await limiter.check("user1")
        assert not (await limiter.check("user1")).allowed
        
        # user2 should have full quota
        assert (await limiter.check("user2")).allowed
        assert (await limiter.check("user2")).allowed
        assert not (await limiter.check("user2")).allowed
    
    @pytest.mark.asyncio
    async def test_cost_parameter(self):
        """Cost parameter consumes multiple units."""
        limiter = create_limiter(10, 1.0)
        
        # Consume 5 at once
        response = await limiter.check("user1", cost=5)
        assert response.allowed
        assert response.remaining == 5
        
        # Consume 5 more
        response = await limiter.check("user1", cost=5)
        assert response.allowed
        
        # No more quota
        response = await limiter.check("user1", cost=1)
        assert response.denied
    
    @pytest.mark.asyncio
    async def test_wait_and_check(self):
        """Wait and check blocks until allowed."""
        limiter = create_limiter(2, 0.5)
        
        # Use quota
        await limiter.check("user1")
        await limiter.check("user1")
        
        # Should wait and then succeed
        start = time.time()
        response = await limiter.wait_and_check("user1", max_wait=2.0)
        elapsed = time.time() - start
        
        assert response.allowed
        assert elapsed >= 0.1  # Should have waited
    
    @pytest.mark.asyncio
    async def test_response_metadata(self):
        """Response contains useful metadata."""
        limiter = create_limiter(10, 60.0)
        
        response = await limiter.check("user1")
        
        assert response.limit == 10
        assert response.remaining == 9
        assert response.reset_at > time.time()
        assert response.key == "sentinel:user1"


# =============================================================================
# Decorator Tests
# =============================================================================

class TestDecorator:
    """Test rate limit decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_allows(self):
        """Decorated function executes when allowed."""
        limiter = create_limiter(5, 1.0)
        
        @limiter.limit()
        async def my_func() -> str:
            return "success"
        
        result = await my_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_raises_when_exceeded(self):
        """Decorator raises RateLimitExceeded when over limit."""
        limiter = create_limiter(2, 1.0)
        
        @limiter.limit()
        async def my_func() -> str:
            return "success"
        
        await my_func()
        await my_func()
        
        with pytest.raises(RateLimitExceeded) as exc:
            await my_func()
        
        assert exc.value.response.denied
    
    @pytest.mark.asyncio
    async def test_decorator_custom_key(self):
        """Decorator uses custom key function."""
        limiter = create_limiter(2, 1.0)
        
        @limiter.limit(key_func=lambda user_id: f"user:{user_id}")
        async def my_func(user_id: int) -> str:
            return f"hello {user_id}"
        
        # Each user has own limit
        await my_func(1)
        await my_func(1)
        
        # User 1 exceeded
        with pytest.raises(RateLimitExceeded):
            await my_func(1)
        
        # User 2 still has quota
        result = await my_func(2)
        assert result == "hello 2"


# =============================================================================
# Context Manager Tests
# =============================================================================

class TestContextManager:
    """Test rate limit context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Context manager provides response."""
        limiter = create_limiter(5, 1.0)
        
        async with limiter("user1") as response:
            assert response.allowed
            assert response.remaining == 4
    
    @pytest.mark.asyncio
    async def test_context_manager_denied(self):
        """Context manager works when denied."""
        limiter = create_limiter(1, 1.0)
        
        # Use up quota
        await limiter.check("user1")
        
        async with limiter("user1") as response:
            assert response.denied
            # Can check and handle denial inside context


# =============================================================================
# Multi-Tier Limiter Tests
# =============================================================================

class TestMultiTierLimiter:
    """Test multi-tier rate limiting."""
    
    @pytest.mark.asyncio
    async def test_all_tiers_must_allow(self):
        """Request only allowed if all tiers allow."""
        # 5/second AND 10/minute
        per_sec = create_limiter(5, 1.0)
        per_min = create_limiter(10, 60.0)
        
        multi = MultiTierLimiter([per_sec, per_min])
        
        # First 5 should pass (within per-second limit)
        for i in range(5):
            response = await multi.check("user1")
            assert response.allowed, f"Request {i+1} should be allowed"
        
        # 6th should fail (per-second exceeded)
        response = await multi.check("user1")
        assert response.denied
    
    @pytest.mark.asyncio
    async def test_returns_most_restrictive(self):
        """Returns the most restrictive denial."""
        # Both have same limit but different windows
        fast = create_limiter(5, 1.0)    # Resets quickly
        slow = create_limiter(5, 60.0)   # Resets slowly
        
        multi = MultiTierLimiter([fast, slow])
        
        # Exhaust both
        for _ in range(5):
            await multi.check("user1")
        
        response = await multi.check("user1")
        assert response.denied


# =============================================================================
# Convenience Constructor Tests
# =============================================================================

class TestConvenienceConstructors:
    """Test convenience constructor functions."""
    
    @pytest.mark.asyncio
    async def test_per_second(self):
        """per_second creates correct limiter."""
        limiter = per_second(10)
        
        # 10 allowed
        for _ in range(10):
            assert (await limiter.check("key")).allowed
        
        # 11th denied
        assert not (await limiter.check("key")).allowed
    
    @pytest.mark.asyncio
    async def test_per_minute(self):
        """per_minute creates correct limiter."""
        limiter = per_minute(100)
        
        response = await limiter.peek("key")
        assert response.limit == 100


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_config_limit(self):
        """Rejects non-positive limit."""
        with pytest.raises(ValueError):
            RateLimitConfig(limit=0, window_seconds=60)
        
        with pytest.raises(ValueError):
            RateLimitConfig(limit=-1, window_seconds=60)
    
    def test_invalid_config_window(self):
        """Rejects non-positive window."""
        with pytest.raises(ValueError):
            RateLimitConfig(limit=10, window_seconds=0)
    
    def test_invalid_burst(self):
        """Rejects burst smaller than limit."""
        with pytest.raises(ValueError):
            RateLimitConfig(limit=10, window_seconds=60, burst=5)
    
    @pytest.mark.asyncio
    async def test_rapid_concurrent_requests(self):
        """Handles rapid concurrent requests correctly."""
        limiter = create_limiter(100, 1.0)
        
        async def make_request():
            return await limiter.check("user1")
        
        # Fire 150 concurrent requests
        results = await asyncio.gather(*[make_request() for _ in range(150)])
        
        allowed = sum(1 for r in results if r.allowed)
        denied = sum(1 for r in results if r.denied)
        
        assert allowed == 100
        assert denied == 50
    
    @pytest.mark.asyncio
    async def test_response_bool_conversion(self):
        """Response can be used in boolean context."""
        limiter = create_limiter(1, 1.0)
        
        response = await limiter.check("user1")
        assert bool(response) is True
        
        response = await limiter.check("user1")
        assert bool(response) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
