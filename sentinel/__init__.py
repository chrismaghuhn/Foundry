"""
Sentinel: Async-Native Rate Limiting Library

Multiple algorithms, pluggable backends, easy integration.

Quick Start:
    >>> from sentinel import per_second, RateLimitExceeded
    >>> 
    >>> limiter = per_second(10)  # 10 requests per second
    >>> 
    >>> @limiter.limit(key_func=lambda user_id: f"user:{user_id}")
    >>> async def api_call(user_id: int):
    ...     return {"status": "ok"}
    >>> 
    >>> # Or check manually:
    >>> response = await limiter.check("user:123")
    >>> if response.allowed:
    ...     print(f"Remaining: {response.remaining}")
"""

from .sentinel import (
    # Core
    RateLimiter,
    RateLimitConfig,
    RateLimitResponse,
    LimitResult,
    
    # Algorithms
    Algorithm,
    LimitAlgorithm,
    TokenBucketAlgorithm,
    SlidingWindowAlgorithm,
    FixedWindowAlgorithm,
    LeakyBucketAlgorithm,
    
    # Backends
    RateLimitBackend,
    InMemoryBackend,
    
    # Multi-tier
    MultiTierLimiter,
    
    # Exceptions
    SentinelError,
    RateLimitExceeded,
    
    # Convenience
    create_limiter,
    per_second,
    per_minute,
    per_hour,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

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
