"""
Sentinel: Async-Native Rate Limiting Library

A production-grade rate limiter supporting multiple algorithms:
- Token Bucket: Smooth rate limiting with burst capacity
- Sliding Window: Precise request counting over time windows
- Leaky Bucket: Constant output rate regardless of input bursts
- Fixed Window: Simple time-based counters (fastest)

Architecture:
    1. RateLimiter is the main interface, algorithm-agnostic
    2. Algorithms implement the LimitAlgorithm protocol
    3. Backends (Memory/Redis) handle state persistence
    4. Decorators and context managers provide easy integration

Key Design Decisions:
    - All operations are async for non-blocking I/O
    - Algorithms are stateless; state lives in backends
    - Keys support hierarchical namespacing (user:123:api:posts)
    - Backpressure returns wait time, not just reject/accept

Thread Safety:
    Memory backend uses asyncio.Lock per key for fine-grained locking.
    Redis backend relies on atomic Lua scripts.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    TypeVar,
    ParamSpec,
    Protocol,
)
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')


# =============================================================================
# Core Types
# =============================================================================

class LimitResult(Enum):
    """Result of a rate limit check."""
    ALLOWED = auto()      # Request allowed
    DENIED = auto()       # Request denied (limit exceeded)
    THROTTLED = auto()    # Request should wait (backpressure)


@dataclass(frozen=True, slots=True)
class RateLimitResponse:
    """
    Complete response from a rate limit check.
    
    Provides all information needed for:
    - Making allow/deny decisions
    - Setting retry-after headers
    - Monitoring and alerting
    """
    result: LimitResult
    key: str
    limit: int                    # Max requests allowed
    remaining: int                # Requests remaining in window
    reset_at: float              # Unix timestamp when limit resets
    retry_after: float | None    # Seconds to wait (if denied/throttled)
    
    @property
    def allowed(self) -> bool:
        return self.result == LimitResult.ALLOWED
    
    @property
    def denied(self) -> bool:
        return self.result == LimitResult.DENIED
    
    def __bool__(self) -> bool:
        """Allow using response in boolean context."""
        return self.allowed


@dataclass
class RateLimitConfig:
    """
    Configuration for a rate limit rule.
    
    Examples:
        # 100 requests per minute
        RateLimitConfig(limit=100, window_seconds=60)
        
        # 10 requests per second with burst of 20
        RateLimitConfig(limit=10, window_seconds=1, burst=20)
    """
    limit: int                    # Max requests in window
    window_seconds: float         # Time window duration
    burst: int | None = None      # Burst capacity (token bucket only)
    
    def __post_init__(self):
        if self.limit <= 0:
            raise ValueError("Limit must be positive")
        if self.window_seconds <= 0:
            raise ValueError("Window must be positive")
        if self.burst is not None and self.burst < self.limit:
            raise ValueError("Burst must be >= limit")


# =============================================================================
# Backend Protocol
# =============================================================================

class RateLimitBackend(Protocol):
    """
    Protocol for rate limit state storage.
    
    Implement this to add Redis, Memcached, or other backends.
    All operations must be atomic to prevent race conditions.
    """
    
    async def get(self, key: str) -> dict[str, Any] | None:
        """Get state for a key. Returns None if not found."""
        ...
    
    async def set(self, key: str, state: dict[str, Any], ttl_seconds: float) -> None:
        """Set state for a key with TTL."""
        ...
    
    async def increment(self, key: str, field: str, amount: float = 1) -> float:
        """Atomically increment a field. Returns new value."""
        ...
    
    async def get_and_set(
        self, 
        key: str, 
        updater: Callable[[dict[str, Any] | None], dict[str, Any]],
        ttl_seconds: float
    ) -> dict[str, Any]:
        """Atomically get current state, apply updater, and set new state."""
        ...


class InMemoryBackend:
    """
    Thread-safe in-memory backend with automatic expiration.
    
    Uses per-key locks for fine-grained concurrency.
    Suitable for single-process applications.
    """
    
    def __init__(self):
        self._data: dict[str, tuple[dict[str, Any], float]] = {}  # key -> (state, expiry)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()
    
    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create lock for a key."""
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]
    
    async def get(self, key: str) -> dict[str, Any] | None:
        lock = await self._get_lock(key)
        async with lock:
            if key not in self._data:
                return None
            
            state, expiry = self._data[key]
            if time.time() > expiry:
                del self._data[key]
                return None
            
            return state.copy()
    
    async def set(self, key: str, state: dict[str, Any], ttl_seconds: float) -> None:
        lock = await self._get_lock(key)
        async with lock:
            expiry = time.time() + ttl_seconds
            self._data[key] = (state.copy(), expiry)
    
    async def increment(self, key: str, field: str, amount: float = 1) -> float:
        lock = await self._get_lock(key)
        async with lock:
            if key not in self._data:
                return amount
            
            state, expiry = self._data[key]
            if time.time() > expiry:
                del self._data[key]
                return amount
            
            current = state.get(field, 0)
            new_value = current + amount
            state[field] = new_value
            self._data[key] = (state, expiry)
            return new_value
    
    async def get_and_set(
        self,
        key: str,
        updater: Callable[[dict[str, Any] | None], dict[str, Any]],
        ttl_seconds: float
    ) -> dict[str, Any]:
        lock = await self._get_lock(key)
        async with lock:
            # Get current state
            current = None
            if key in self._data:
                state, expiry = self._data[key]
                if time.time() <= expiry:
                    current = state
            
            # Apply update
            new_state = updater(current)
            
            # Store new state
            expiry = time.time() + ttl_seconds
            self._data[key] = (new_state.copy(), expiry)
            
            return new_state
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        async with self._global_lock:
            now = time.time()
            expired = [k for k, (_, exp) in self._data.items() if now > exp]
            for key in expired:
                del self._data[key]
                self._locks.pop(key, None)
            return len(expired)


# =============================================================================
# Rate Limiting Algorithms
# =============================================================================

class LimitAlgorithm(ABC):
    """
    Base class for rate limiting algorithms.
    
    Each algorithm implements different trade-offs:
    - Token Bucket: Allows bursts, smooth average rate
    - Sliding Window: Precise counting, more memory
    - Leaky Bucket: Constant output, queue-based
    - Fixed Window: Simple, but boundary spikes possible
    """
    
    @abstractmethod
    async def check(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend,
        cost: int = 1
    ) -> RateLimitResponse:
        """
        Check if request is allowed and update state.
        
        Args:
            key: Unique identifier for this limit (e.g., "user:123")
            config: Rate limit configuration
            backend: State storage backend
            cost: Cost of this request (default 1)
        
        Returns:
            RateLimitResponse with result and metadata
        """
        ...
    
    @abstractmethod
    async def peek(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend
    ) -> RateLimitResponse:
        """
        Check current state without consuming quota.
        
        Useful for displaying remaining quota to users.
        """
        ...


class TokenBucketAlgorithm(LimitAlgorithm):
    """
    Token Bucket Algorithm
    
    How it works:
    1. Bucket holds tokens up to a maximum (burst capacity)
    2. Tokens are added at a constant rate (limit / window)
    3. Each request consumes tokens
    4. Request denied if not enough tokens
    
    Properties:
    - Allows short bursts up to bucket capacity
    - Smooth average rate over time
    - Memory efficient (just two numbers: tokens + timestamp)
    
    Best for: APIs that should allow occasional bursts but maintain
    average rate limits over time.
    """
    
    async def check(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend,
        cost: int = 1
    ) -> RateLimitResponse:
        now = time.time()
        capacity = config.burst or config.limit
        refill_rate = config.limit / config.window_seconds  # tokens per second
        
        # First, get current state to calculate available tokens
        current_state = await backend.get(key)
        
        if current_state is None:
            available_tokens = capacity
        else:
            elapsed = now - current_state.get("last_update", now)
            current_tokens = current_state.get("tokens", capacity)
            available_tokens = min(capacity, current_tokens + elapsed * refill_rate)
        
        if available_tokens >= cost:
            # Allowed - consume tokens
            new_tokens = available_tokens - cost
            await backend.set(key, {"tokens": new_tokens, "last_update": now}, config.window_seconds * 2)
            
            remaining = int(new_tokens)
            reset_at = now + (capacity - new_tokens) / refill_rate
            
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=None
            )
        else:
            # Denied - calculate wait time
            deficit = cost - available_tokens
            retry_after = deficit / refill_rate
            
            return RateLimitResponse(
                result=LimitResult.DENIED,
                key=key,
                limit=config.limit,
                remaining=0,
                reset_at=now + retry_after,
                retry_after=retry_after
            )
    
    async def peek(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend
    ) -> RateLimitResponse:
        now = time.time()
        capacity = config.burst or config.limit
        refill_rate = config.limit / config.window_seconds
        
        state = await backend.get(key)
        
        if state is None:
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=capacity,
                reset_at=now,
                retry_after=None
            )
        
        elapsed = now - state.get("last_update", now)
        tokens = min(capacity, state.get("tokens", capacity) + elapsed * refill_rate)
        
        remaining = int(max(0, tokens))
        reset_at = now + (capacity - tokens) / refill_rate if tokens < capacity else now
        
        return RateLimitResponse(
            result=LimitResult.ALLOWED if tokens >= 1 else LimitResult.DENIED,
            key=key,
            limit=config.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=None if tokens >= 1 else (1 - tokens) / refill_rate
        )


class SlidingWindowAlgorithm(LimitAlgorithm):
    """
    Sliding Window Log Algorithm
    
    How it works:
    1. Store timestamp of each request
    2. Count requests within the sliding window
    3. Remove expired timestamps periodically
    
    Properties:
    - Most accurate counting
    - No boundary issues (unlike fixed window)
    - Higher memory usage (stores all timestamps)
    
    Best for: Strict rate limiting where precision matters more than
    memory efficiency.
    """
    
    async def check(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend,
        cost: int = 1
    ) -> RateLimitResponse:
        now = time.time()
        window_start = now - config.window_seconds
        
        # Get current state
        current_state = await backend.get(key)
        
        if current_state is None:
            timestamps = []
        else:
            # Filter out expired timestamps
            timestamps = [ts for ts in current_state.get("timestamps", []) 
                         if ts > window_start]
        
        count = len(timestamps)
        
        if count + cost <= config.limit:
            # Allowed - add timestamps
            timestamps.extend([now] * cost)
            await backend.set(key, {"timestamps": timestamps}, config.window_seconds * 2)
            
            remaining = config.limit - len(timestamps)
            reset_at = now + config.window_seconds
            
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=None
            )
        else:
            # Denied - calculate when oldest will expire
            if timestamps:
                oldest_in_window = min(timestamps)
                retry_after = oldest_in_window + config.window_seconds - now
            else:
                retry_after = config.window_seconds
            
            return RateLimitResponse(
                result=LimitResult.DENIED,
                key=key,
                limit=config.limit,
                remaining=0,
                reset_at=now + max(0, retry_after),
                retry_after=max(0.01, retry_after)
            )
    
    async def peek(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend
    ) -> RateLimitResponse:
        now = time.time()
        window_start = now - config.window_seconds
        
        state = await backend.get(key)
        
        if state is None:
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=config.limit,
                reset_at=now + config.window_seconds,
                retry_after=None
            )
        
        timestamps = [ts for ts in state.get("timestamps", []) if ts > window_start]
        count = len(timestamps)
        remaining = max(0, config.limit - count)
        
        if count < config.limit:
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=remaining,
                reset_at=now + config.window_seconds,
                retry_after=None
            )
        else:
            oldest = min(timestamps) if timestamps else now
            retry_after = oldest + config.window_seconds - now
            return RateLimitResponse(
                result=LimitResult.DENIED,
                key=key,
                limit=config.limit,
                remaining=0,
                reset_at=now + max(0, retry_after),
                retry_after=max(0, retry_after)
            )


class FixedWindowAlgorithm(LimitAlgorithm):
    """
    Fixed Window Counter Algorithm
    
    How it works:
    1. Divide time into fixed windows (e.g., each minute)
    2. Count requests in current window
    3. Reset counter when window changes
    
    Properties:
    - Simplest and fastest
    - Lowest memory (just one counter)
    - Can allow 2x burst at window boundaries
    
    Best for: High-throughput scenarios where simplicity matters and
    occasional boundary bursts are acceptable.
    """
    
    def _get_window_key(self, key: str, config: RateLimitConfig) -> tuple[str, float]:
        """Get window-specific key and reset timestamp."""
        now = time.time()
        window_id = int(now / config.window_seconds)
        window_key = f"{key}:w:{window_id}"
        reset_at = (window_id + 1) * config.window_seconds
        return window_key, reset_at
    
    async def check(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend,
        cost: int = 1
    ) -> RateLimitResponse:
        window_key, reset_at = self._get_window_key(key, config)
        now = time.time()
        
        # Get current count
        current_state = await backend.get(window_key)
        current_count = current_state.get("count", 0) if current_state else 0
        
        if current_count + cost <= config.limit:
            # Allowed - increment count
            new_count = current_count + cost
            await backend.set(window_key, {"count": new_count}, config.window_seconds * 2)
            
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=config.limit - new_count,
                reset_at=reset_at,
                retry_after=None
            )
        else:
            # Denied
            retry_after = reset_at - now
            return RateLimitResponse(
                result=LimitResult.DENIED,
                key=key,
                limit=config.limit,
                remaining=0,
                reset_at=reset_at,
                retry_after=max(0.01, retry_after)
            )
    
    async def peek(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend
    ) -> RateLimitResponse:
        window_key, reset_at = self._get_window_key(key, config)
        now = time.time()
        
        state = await backend.get(window_key)
        count = state.get("count", 0) if state else 0
        remaining = max(0, config.limit - count)
        
        return RateLimitResponse(
            result=LimitResult.ALLOWED if remaining > 0 else LimitResult.DENIED,
            key=key,
            limit=config.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=None if remaining > 0 else max(0, reset_at - now)
        )


class LeakyBucketAlgorithm(LimitAlgorithm):
    """
    Leaky Bucket Algorithm
    
    How it works:
    1. Requests enter a queue (bucket)
    2. Requests "leak" out at a constant rate
    3. If bucket is full, request is rejected
    
    Properties:
    - Smooths out bursts completely
    - Constant output rate
    - Good for downstream protection
    
    Best for: Protecting downstream services that can't handle bursts,
    ensuring constant request rate.
    """
    
    async def check(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend,
        cost: int = 1
    ) -> RateLimitResponse:
        now = time.time()
        capacity = config.burst or config.limit
        leak_rate = config.limit / config.window_seconds  # requests per second
        
        # Get current state
        current_state = await backend.get(key)
        
        if current_state is None:
            water_level = 0
        else:
            # Calculate water leaked since last update
            elapsed = now - current_state.get("last_leak", now)
            leaked = elapsed * leak_rate
            water_level = max(0, current_state.get("water_level", 0) - leaked)
        
        if water_level + cost <= capacity:
            # Allowed - add water
            new_level = water_level + cost
            await backend.set(key, {"water_level": new_level, "last_leak": now}, config.window_seconds * 2)
            
            remaining = int(capacity - new_level)
            drain_time = new_level / leak_rate if leak_rate > 0 else 0
            
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=remaining,
                reset_at=now + drain_time,
                retry_after=None
            )
        else:
            # Bucket overflow
            overflow = water_level + cost - capacity
            retry_after = overflow / leak_rate
            
            return RateLimitResponse(
                result=LimitResult.DENIED,
                key=key,
                limit=config.limit,
                remaining=0,
                reset_at=now + retry_after,
                retry_after=max(0.01, retry_after)
            )
    
    async def peek(
        self,
        key: str,
        config: RateLimitConfig,
        backend: RateLimitBackend
    ) -> RateLimitResponse:
        now = time.time()
        capacity = config.burst or config.limit
        leak_rate = config.limit / config.window_seconds
        
        state = await backend.get(key)
        
        if state is None:
            return RateLimitResponse(
                result=LimitResult.ALLOWED,
                key=key,
                limit=config.limit,
                remaining=capacity,
                reset_at=now,
                retry_after=None
            )
        
        elapsed = now - state.get("last_leak", now)
        leaked = elapsed * leak_rate
        water_level = max(0, state.get("water_level", 0) - leaked)
        remaining = int(max(0, capacity - water_level))
        
        return RateLimitResponse(
            result=LimitResult.ALLOWED if water_level < capacity else LimitResult.DENIED,
            key=key,
            limit=config.limit,
            remaining=remaining,
            reset_at=now + water_level / leak_rate if water_level > 0 else now,
            retry_after=None if water_level < capacity else (water_level - capacity + 1) / leak_rate
        )


# =============================================================================
# Algorithm Registry
# =============================================================================

class Algorithm(Enum):
    """Available rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


_ALGORITHMS: dict[Algorithm, type[LimitAlgorithm]] = {
    Algorithm.TOKEN_BUCKET: TokenBucketAlgorithm,
    Algorithm.SLIDING_WINDOW: SlidingWindowAlgorithm,
    Algorithm.FIXED_WINDOW: FixedWindowAlgorithm,
    Algorithm.LEAKY_BUCKET: LeakyBucketAlgorithm,
}


def get_algorithm(algo: Algorithm) -> LimitAlgorithm:
    """Get algorithm instance by enum."""
    return _ALGORITHMS[algo]()


# =============================================================================
# Main Rate Limiter
# =============================================================================

class RateLimiter:
    """
    Main rate limiter interface.
    
    Provides a unified API regardless of algorithm or backend choice.
    
    Usage:
        limiter = RateLimiter(
            config=RateLimitConfig(limit=100, window_seconds=60),
            algorithm=Algorithm.TOKEN_BUCKET
        )
        
        # Check rate limit
        response = await limiter.check("user:123")
        if response.allowed:
            # Process request
            pass
        else:
            # Return 429 with Retry-After header
            return Response(status=429, headers={"Retry-After": str(response.retry_after)})
    """
    
    def __init__(
        self,
        config: RateLimitConfig,
        algorithm: Algorithm = Algorithm.TOKEN_BUCKET,
        backend: RateLimitBackend | None = None,
        key_prefix: str = "sentinel"
    ):
        self.config = config
        self.algorithm = get_algorithm(algorithm)
        self.backend = backend or InMemoryBackend()
        self.key_prefix = key_prefix
    
    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self.key_prefix}:{key}"
    
    async def check(self, key: str, cost: int = 1) -> RateLimitResponse:
        """
        Check if request is allowed and consume quota.
        
        Args:
            key: Unique identifier (e.g., user ID, IP address)
            cost: Cost of this request (default 1)
        
        Returns:
            RateLimitResponse with result and metadata
        """
        full_key = self._make_key(key)
        return await self.algorithm.check(full_key, self.config, self.backend, cost)
    
    async def peek(self, key: str) -> RateLimitResponse:
        """
        Check current quota without consuming.
        
        Useful for showing users their remaining quota.
        """
        full_key = self._make_key(key)
        return await self.algorithm.peek(full_key, self.config, self.backend)
    
    async def is_allowed(self, key: str, cost: int = 1) -> bool:
        """Simple boolean check - is this request allowed?"""
        response = await self.check(key, cost)
        return response.allowed
    
    async def wait_and_check(
        self, 
        key: str, 
        cost: int = 1,
        max_wait: float = 30.0
    ) -> RateLimitResponse:
        """
        Wait until request is allowed (with timeout).
        
        Useful for background jobs that can afford to wait.
        
        Args:
            key: Rate limit key
            cost: Request cost
            max_wait: Maximum seconds to wait
        
        Returns:
            RateLimitResponse (always allowed unless timeout)
        """
        deadline = time.time() + max_wait
        
        while True:
            response = await self.check(key, cost)
            
            if response.allowed:
                return response
            
            if response.retry_after is None or time.time() + response.retry_after > deadline:
                return response  # Would exceed max wait
            
            await asyncio.sleep(min(response.retry_after, deadline - time.time()))
    
    def limit(
        self,
        key_func: Callable[..., str] | None = None,
        cost: int = 1
    ) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
        """
        Decorator to rate limit an async function.
        
        Args:
            key_func: Function to extract key from args (default: use function name)
            cost: Cost per call
        
        Example:
            @limiter.limit(key_func=lambda user_id: f"user:{user_id}")
            async def api_call(user_id: int) -> dict:
                ...
        """
        def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                if key_func:
                    key = key_func(*args, **kwargs)
                else:
                    key = func.__name__
                
                response = await self.check(key, cost)
                
                if not response.allowed:
                    raise RateLimitExceeded(response)
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def __call__(self, key: str) -> "RateLimitContext":
        """
        Context manager for rate limiting.
        
        Example:
            async with limiter("user:123") as response:
                if response.allowed:
                    await do_something()
        """
        return RateLimitContext(self, key)


class RateLimitContext:
    """Async context manager for rate limiting."""
    
    def __init__(self, limiter: RateLimiter, key: str, cost: int = 1):
        self.limiter = limiter
        self.key = key
        self.cost = cost
        self.response: RateLimitResponse | None = None
    
    async def __aenter__(self) -> RateLimitResponse:
        self.response = await self.limiter.check(self.key, self.cost)
        return self.response
    
    async def __aexit__(self, *args) -> None:
        pass


# =============================================================================
# Exceptions
# =============================================================================

class SentinelError(Exception):
    """Base exception for Sentinel errors."""
    pass


class RateLimitExceeded(SentinelError):
    """Raised when rate limit is exceeded (for decorator usage)."""
    
    def __init__(self, response: RateLimitResponse):
        self.response = response
        super().__init__(
            f"Rate limit exceeded for '{response.key}'. "
            f"Retry after {response.retry_after:.1f}s"
        )


# =============================================================================
# Multi-Tier Rate Limiting
# =============================================================================

class MultiTierLimiter:
    """
    Apply multiple rate limits simultaneously.
    
    Useful for implementing tiered limits like:
    - 10 requests per second
    - 100 requests per minute
    - 1000 requests per hour
    
    A request is only allowed if ALL limits allow it.
    """
    
    def __init__(self, limiters: list[RateLimiter]):
        if not limiters:
            raise ValueError("At least one limiter required")
        self.limiters = limiters
    
    async def check(self, key: str, cost: int = 1) -> RateLimitResponse:
        """
        Check all limiters. Request allowed only if ALL allow.
        
        Returns the most restrictive response.
        """
        responses = await asyncio.gather(*[
            limiter.check(key, cost) for limiter in self.limiters
        ])
        
        # Find the most restrictive (denied > allowed, longest retry)
        denied = [r for r in responses if r.denied]
        
        if denied:
            # Return the one with longest retry time
            worst = max(denied, key=lambda r: r.retry_after or 0)
            
            # Rollback the ones that succeeded
            # (Note: this is approximate - some algorithms may not rollback perfectly)
            
            return worst
        
        # All allowed - return the one with lowest remaining
        return min(responses, key=lambda r: r.remaining)
    
    async def peek(self, key: str) -> list[RateLimitResponse]:
        """Peek at all tier statuses."""
        return await asyncio.gather(*[
            limiter.peek(key) for limiter in self.limiters
        ])


# =============================================================================
# Convenience Constructors
# =============================================================================

def create_limiter(
    limit: int,
    window_seconds: float,
    algorithm: Algorithm = Algorithm.TOKEN_BUCKET,
    burst: int | None = None,
    **kwargs
) -> RateLimiter:
    """
    Create a rate limiter with sensible defaults.
    
    Example:
        limiter = create_limiter(100, 60)  # 100 per minute
    """
    config = RateLimitConfig(limit=limit, window_seconds=window_seconds, burst=burst)
    return RateLimiter(config, algorithm, **kwargs)


def per_second(limit: int, **kwargs) -> RateLimiter:
    """Create a per-second rate limiter."""
    return create_limiter(limit, 1.0, **kwargs)


def per_minute(limit: int, **kwargs) -> RateLimiter:
    """Create a per-minute rate limiter."""
    return create_limiter(limit, 60.0, **kwargs)


def per_hour(limit: int, **kwargs) -> RateLimiter:
    """Create a per-hour rate limiter."""
    return create_limiter(limit, 3600.0, **kwargs)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core
    'RateLimiter',
    'RateLimitConfig',
    'RateLimitResponse',
    'LimitResult',
    
    # Algorithms
    'Algorithm',
    'LimitAlgorithm',
    'TokenBucketAlgorithm',
    'SlidingWindowAlgorithm',
    'FixedWindowAlgorithm',
    'LeakyBucketAlgorithm',
    
    # Backends
    'RateLimitBackend',
    'InMemoryBackend',
    
    # Multi-tier
    'MultiTierLimiter',
    
    # Exceptions
    'SentinelError',
    'RateLimitExceeded',
    
    # Convenience
    'create_limiter',
    'per_second',
    'per_minute',
    'per_hour',
]
