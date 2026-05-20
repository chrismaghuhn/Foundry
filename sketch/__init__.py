"""
Sketch: Probabilistic Data Structures

Space-efficient data structures with mathematically proven error bounds.

Quick Start:
    >>> from sketch import BloomFilter, HyperLogLog, CountMinSketch
    >>> 
    >>> # Check membership with 1% false positive rate
    >>> seen = BloomFilter(expected_items=10000, false_positive_rate=0.01)
    >>> seen.add(b"hello")
    >>> b"hello" in seen  # True
    >>> 
    >>> # Count unique items with ~1% error
    >>> counter = HyperLogLog(precision=14)
    >>> for user_id in stream:
    ...     counter.add(user_id)
    >>> counter.count()  # Approximate cardinality
    >>> 
    >>> # Track frequencies with bounded error
    >>> freq = CountMinSketch.from_error(epsilon=0.001, delta=0.01)
    >>> freq.add(b"word", count=5)
    >>> freq.count(b"word")  # ≥ 5 (never underestimates)

Available Structures:
    BloomFilter: Membership testing (no false negatives)
    CountingBloomFilter: Membership with deletion support
    CuckooFilter: Better space efficiency at low FPRs
    HyperLogLog: Cardinality estimation
    CountMinSketch: Frequency estimation
    TopK: Heavy hitter tracking

All structures support:
    - Serialization (to_dict/from_dict)
    - Merging for distributed aggregation
    - Configurable error bounds
"""

from .sketch import (
    # Membership testing
    BloomFilter,
    CountingBloomFilter,
    CuckooFilter,
    
    # Cardinality estimation
    HyperLogLog,
    
    # Frequency estimation
    CountMinSketch,
    TopK,
    
    # Utilities
    BitArray,
    optimal_bloom_params,
    bloom_fpr,
    hyperloglog_error,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Membership
    'BloomFilter',
    'CountingBloomFilter', 
    'CuckooFilter',
    
    # Cardinality
    'HyperLogLog',
    
    # Frequency
    'CountMinSketch',
    'TopK',
    
    # Utilities
    'BitArray',
    'optimal_bloom_params',
    'bloom_fpr',
    'hyperloglog_error',
]
