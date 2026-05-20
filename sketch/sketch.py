"""
Sketch: Probabilistic Data Structures

Space-efficient data structures with mathematically proven error bounds.
Trade memory for accuracy with quantifiable guarantees.

Mathematical Foundations:

    Bloom Filter:
        A bit array of m bits with k hash functions.
        False positive rate: (1 - e^(-kn/m))^k
        Optimal k = (m/n) × ln(2)
        
    HyperLogLog:
        Uses the observation that in a stream of random numbers,
        the maximum number of leading zeros in binary representation
        approximates log₂(cardinality).
        
        Standard error: 1.04 / √m where m = 2^p registers
        
    Count-Min Sketch:
        A 2D array of counters. Each item hashes to one counter per row.
        Query returns minimum across rows (overestimates, never underestimates).
        
        With width w and depth d:
        - Error ≤ εN with probability ≥ 1-δ
        - where w = ⌈e/ε⌉ and d = ⌈ln(1/δ)⌉
        
    Cuckoo Filter:
        Stores fingerprints in a cuckoo hash table.
        Supports deletion (unlike Bloom).
        Better space efficiency at low false positive rates.

All structures support:
    - Serialization for persistence
    - Merging for distributed aggregation
    - Error estimation methods

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import hashlib
import math
import struct
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Generic, TypeVar, Iterator, Optional, 
    Union, List, Tuple, Callable
)
from functools import cached_property
import random


# =============================================================================
# Hash Functions
# =============================================================================

def _hash128(data: bytes, seed: int = 0) -> Tuple[int, int]:
    """
    Generate two 64-bit hashes from input data.
    
    Uses MD5 for simplicity (128 bits = two 64-bit values).
    In production, consider xxhash or murmurhash for speed.
    """
    h = hashlib.md5(data + seed.to_bytes(8, 'little')).digest()
    h1 = int.from_bytes(h[:8], 'little')
    h2 = int.from_bytes(h[8:], 'little')
    return h1, h2


def _hash_family(data: bytes, k: int, m: int) -> Iterator[int]:
    """
    Generate k hash values in range [0, m) using double hashing.
    
    This technique generates k hashes from just 2 hash computations:
        h_i(x) = (h1(x) + i × h2(x)) mod m
    
    Kirsch & Mitzenmacher (2006) proved this is as good as k independent
    hash functions for Bloom filters.
    """
    h1, h2 = _hash128(data)
    
    # Ensure h2 is odd (coprime with m if m is power of 2)
    h2 = h2 | 1
    
    for i in range(k):
        yield (h1 + i * h2) % m


def _fingerprint(data: bytes, bits: int) -> int:
    """
    Generate a fingerprint of specified bit length.
    
    Used by Cuckoo Filter for compact storage.
    """
    h = _hash128(data)[0]
    # Never return 0 (reserved for empty bucket)
    fp = (h % ((1 << bits) - 1)) + 1
    return fp


# =============================================================================
# Bit Array Utilities
# =============================================================================

class BitArray:
    """
    Compact bit array implementation.
    
    Stores bits in a bytearray for memory efficiency.
    Supports atomic-style operations for thread safety considerations.
    """
    
    def __init__(self, size: int):
        if size < 1:
            raise ValueError("Size must be at least 1")
        self._size = size
        self._bytes = bytearray((size + 7) // 8)
    
    @property
    def size(self) -> int:
        """Number of bits in the array."""
        return self._size
    
    def __len__(self) -> int:
        return self._size
    
    def __getitem__(self, index: int) -> bool:
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of range [0, {self._size})")
        byte_idx = index // 8
        bit_idx = index % 8
        return bool(self._bytes[byte_idx] & (1 << bit_idx))
    
    def __setitem__(self, index: int, value: bool) -> None:
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of range [0, {self._size})")
        byte_idx = index // 8
        bit_idx = index % 8
        if value:
            self._bytes[byte_idx] |= (1 << bit_idx)
        else:
            self._bytes[byte_idx] &= ~(1 << bit_idx)
    
    def set(self, index: int) -> bool:
        """Set bit to 1, return previous value."""
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of range [0, {self._size})")
        byte_idx = index // 8
        bit_idx = index % 8
        mask = 1 << bit_idx
        was_set = bool(self._bytes[byte_idx] & mask)
        self._bytes[byte_idx] |= mask
        return was_set
    
    def clear(self, index: int) -> bool:
        """Set bit to 0, return previous value."""
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of range [0, {self._size})")
        byte_idx = index // 8
        bit_idx = index % 8
        mask = 1 << bit_idx
        was_set = bool(self._bytes[byte_idx] & mask)
        self._bytes[byte_idx] &= ~mask
        return was_set
    
    def count_ones(self) -> int:
        """Count number of bits set to 1."""
        return sum(bin(b).count('1') for b in self._bytes)
    
    def merge_or(self, other: 'BitArray') -> None:
        """Bitwise OR with another array (union)."""
        if self._size != other._size:
            raise ValueError("Cannot merge arrays of different sizes")
        for i in range(len(self._bytes)):
            self._bytes[i] |= other._bytes[i]
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return bytes(self._bytes)
    
    @classmethod
    def from_bytes(cls, data: bytes, size: int) -> 'BitArray':
        """Deserialize from bytes."""
        arr = cls(size)
        arr._bytes = bytearray(data)
        return arr


# =============================================================================
# Bloom Filter
# =============================================================================

class BloomFilter:
    """
    Classic Bloom Filter for membership testing.
    
    A Bloom filter is a space-efficient probabilistic data structure that
    tests whether an element is a member of a set. False positives are
    possible, but false negatives are not.
    
    Space Complexity: O(n) bits where n is expected number of elements
    False Positive Rate: Configurable (typically 1-10%)
    
    Parameters:
        expected_items: Expected number of items to insert
        false_positive_rate: Desired false positive rate (0 < fpr < 1)
    
    Mathematical Properties:
        - Optimal number of hash functions: k = (m/n) × ln(2)
        - False positive rate: (1 - e^(-kn/m))^k
        - Bits per element for 1% FPR: ~9.6 bits
    
    Example:
        >>> bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
        >>> bf.add(b"hello")
        >>> b"hello" in bf  # True
        >>> b"world" in bf  # Probably False (1% chance of False Positive)
    
    Thread Safety:
        Add operations are safe for concurrent use (bits can only go 0→1).
        Contains operations are safe.
        Merge operations should be externally synchronized.
    """
    
    def __init__(
        self,
        expected_items: int,
        false_positive_rate: float = 0.01,
        *,
        _bits: Optional[BitArray] = None,
        _num_bits: Optional[int] = None,
        _num_hashes: Optional[int] = None,
        _count: int = 0,
    ):
        if expected_items < 1:
            raise ValueError("expected_items must be at least 1")
        if not 0 < false_positive_rate < 1:
            raise ValueError("false_positive_rate must be between 0 and 1")
        
        self._expected_items = expected_items
        self._fpr = false_positive_rate
        
        if _bits is not None:
            # Deserialization path
            self._bits = _bits
            self._num_bits = _num_bits
            self._num_hashes = _num_hashes
            self._count = _count
        else:
            # Calculate optimal parameters
            # m = -n × ln(p) / (ln(2))²
            n = expected_items
            p = false_positive_rate
            
            m = int(math.ceil(-n * math.log(p) / (math.log(2) ** 2)))
            self._num_bits = max(m, 64)  # Minimum 64 bits
            
            # k = (m/n) × ln(2)
            k = int(round((self._num_bits / n) * math.log(2)))
            self._num_hashes = max(k, 1)  # At least 1 hash
            
            self._bits = BitArray(self._num_bits)
            self._count = 0
    
    @property
    def expected_items(self) -> int:
        """Expected number of items the filter was sized for."""
        return self._expected_items
    
    @property
    def false_positive_rate(self) -> float:
        """Configured false positive rate."""
        return self._fpr
    
    @property
    def num_bits(self) -> int:
        """Number of bits in the filter."""
        return self._num_bits
    
    @property
    def num_hashes(self) -> int:
        """Number of hash functions."""
        return self._num_hashes
    
    @property
    def count(self) -> int:
        """Approximate number of items added (may overcount on duplicates)."""
        return self._count
    
    @property
    def size_bytes(self) -> int:
        """Memory used by the bit array."""
        return (self._num_bits + 7) // 8
    
    def estimated_fpr(self) -> float:
        """
        Estimate current false positive rate based on fill ratio.
        
        More accurate than the configured rate when actual inserts differ
        from expected.
        """
        # Count actual bits set
        bits_set = self._bits.count_ones()
        
        # Estimate FPR: (bits_set / m)^k
        fill_ratio = bits_set / self._num_bits
        return fill_ratio ** self._num_hashes
    
    def _hash_indices(self, item: bytes) -> Iterator[int]:
        """Generate hash indices for an item."""
        return _hash_family(item, self._num_hashes, self._num_bits)
    
    def add(self, item: Union[bytes, str]) -> bool:
        """
        Add an item to the filter.
        
        Returns True if item was probably new (at least one bit was set).
        Returns False if item was probably already present.
        
        Note: This is a probabilistic indicator, not a guarantee.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        any_new = False
        for idx in self._hash_indices(item):
            if not self._bits.set(idx):
                any_new = True
        
        if any_new:
            self._count += 1
        
        return any_new
    
    def __contains__(self, item: Union[bytes, str]) -> bool:
        """
        Test if an item might be in the filter.
        
        Returns True if item might be present (with false positive probability).
        Returns False if item is definitely not present.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        return all(self._bits[idx] for idx in self._hash_indices(item))
    
    def contains(self, item: Union[bytes, str]) -> bool:
        """Alias for __contains__."""
        return item in self
    
    def merge(self, other: 'BloomFilter') -> 'BloomFilter':
        """
        Merge another Bloom filter into this one.
        
        Both filters must have the same parameters (bits and hashes).
        After merge, this filter contains the union of both sets.
        
        Returns self for method chaining.
        """
        if self._num_bits != other._num_bits:
            raise ValueError(f"Cannot merge: different bit counts ({self._num_bits} vs {other._num_bits})")
        if self._num_hashes != other._num_hashes:
            raise ValueError(f"Cannot merge: different hash counts ({self._num_hashes} vs {other._num_hashes})")
        
        self._bits.merge_or(other._bits)
        self._count += other._count  # Approximate
        
        return self
    
    def union(self, other: 'BloomFilter') -> 'BloomFilter':
        """Create a new filter containing the union of both."""
        result = self.copy()
        result.merge(other)
        return result
    
    def copy(self) -> 'BloomFilter':
        """Create a copy of this filter."""
        return BloomFilter(
            self._expected_items,
            self._fpr,
            _bits=BitArray.from_bytes(self._bits.to_bytes(), self._num_bits),
            _num_bits=self._num_bits,
            _num_hashes=self._num_hashes,
            _count=self._count,
        )
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        import base64
        return {
            "type": "BloomFilter",
            "expected_items": self._expected_items,
            "fpr": self._fpr,
            "num_bits": self._num_bits,
            "num_hashes": self._num_hashes,
            "count": self._count,
            "bits": base64.b64encode(self._bits.to_bytes()).decode('ascii'),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BloomFilter':
        """Deserialize from dictionary."""
        import base64
        bits_data = base64.b64decode(data["bits"])
        bits = BitArray.from_bytes(bits_data, data["num_bits"])
        return cls(
            data["expected_items"],
            data["fpr"],
            _bits=bits,
            _num_bits=data["num_bits"],
            _num_hashes=data["num_hashes"],
            _count=data["count"],
        )
    
    def __repr__(self) -> str:
        return (f"BloomFilter(items≈{self._count}, bits={self._num_bits}, "
                f"hashes={self._num_hashes}, fpr={self.estimated_fpr():.4f})")


# =============================================================================
# Counting Bloom Filter
# =============================================================================

class CountingBloomFilter:
    """
    Counting Bloom Filter with deletion support.
    
    Instead of bits, uses counters. This allows items to be removed,
    at the cost of more memory (typically 4 bits per counter).
    
    Parameters:
        expected_items: Expected number of items
        false_positive_rate: Desired false positive rate
        counter_bits: Bits per counter (default 4, max count = 15)
    
    Trade-offs vs Standard Bloom:
        - Pro: Supports deletion
        - Con: 4× more memory (4 bits vs 1 bit per position)
        - Con: Counter overflow possible (saturates at max)
    
    Example:
        >>> cbf = CountingBloomFilter(expected_items=1000)
        >>> cbf.add(b"hello")
        >>> cbf.remove(b"hello")
        >>> b"hello" in cbf  # False
    """
    
    def __init__(
        self,
        expected_items: int,
        false_positive_rate: float = 0.01,
        counter_bits: int = 4,
        *,
        _counters: Optional[bytearray] = None,
        _num_counters: Optional[int] = None,
        _num_hashes: Optional[int] = None,
        _count: int = 0,
    ):
        if expected_items < 1:
            raise ValueError("expected_items must be at least 1")
        if not 0 < false_positive_rate < 1:
            raise ValueError("false_positive_rate must be between 0 and 1")
        if counter_bits < 2 or counter_bits > 16:
            raise ValueError("counter_bits must be between 2 and 16")
        
        self._expected_items = expected_items
        self._fpr = false_positive_rate
        self._counter_bits = counter_bits
        self._max_count = (1 << counter_bits) - 1
        
        if _counters is not None:
            self._counters = _counters
            self._num_counters = _num_counters
            self._num_hashes = _num_hashes
            self._count = _count
        else:
            # Same sizing as Bloom filter
            n = expected_items
            p = false_positive_rate
            
            m = int(math.ceil(-n * math.log(p) / (math.log(2) ** 2)))
            self._num_counters = max(m, 64)
            
            k = int(round((self._num_counters / n) * math.log(2)))
            self._num_hashes = max(k, 1)
            
            # For simplicity, use 1 byte per counter (wasteful but simple)
            # In production, pack counters for memory efficiency
            self._counters = bytearray(self._num_counters)
            self._count = 0
    
    @property
    def count(self) -> int:
        """Approximate number of items in the filter."""
        return self._count
    
    def _hash_indices(self, item: bytes) -> Iterator[int]:
        return _hash_family(item, self._num_hashes, self._num_counters)
    
    def add(self, item: Union[bytes, str]) -> bool:
        """
        Add an item to the filter.
        
        Increments all counters (saturating at max).
        Returns True if item appears to be new.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        any_zero = False
        for idx in self._hash_indices(item):
            if self._counters[idx] == 0:
                any_zero = True
            if self._counters[idx] < self._max_count:
                self._counters[idx] += 1
        
        if any_zero:
            self._count += 1
        
        return any_zero
    
    def remove(self, item: Union[bytes, str]) -> bool:
        """
        Remove an item from the filter.
        
        Decrements all counters (stopping at 0).
        Returns True if item appeared to be present.
        
        Warning: Removing an item that was never added can cause
        false negatives for other items.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        # First check if present
        if item not in self:
            return False
        
        for idx in self._hash_indices(item):
            if self._counters[idx] > 0:
                self._counters[idx] -= 1
        
        self._count = max(0, self._count - 1)
        return True
    
    def __contains__(self, item: Union[bytes, str]) -> bool:
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        return all(self._counters[idx] > 0 for idx in self._hash_indices(item))
    
    def to_dict(self) -> dict:
        import base64
        return {
            "type": "CountingBloomFilter",
            "expected_items": self._expected_items,
            "fpr": self._fpr,
            "counter_bits": self._counter_bits,
            "num_counters": self._num_counters,
            "num_hashes": self._num_hashes,
            "count": self._count,
            "counters": base64.b64encode(bytes(self._counters)).decode('ascii'),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CountingBloomFilter':
        import base64
        counters = bytearray(base64.b64decode(data["counters"]))
        return cls(
            data["expected_items"],
            data["fpr"],
            data["counter_bits"],
            _counters=counters,
            _num_counters=data["num_counters"],
            _num_hashes=data["num_hashes"],
            _count=data["count"],
        )
    
    def __repr__(self) -> str:
        return f"CountingBloomFilter(items≈{self._count}, counters={self._num_counters})"


# =============================================================================
# Cuckoo Filter
# =============================================================================

class CuckooFilter:
    """
    Cuckoo Filter for membership testing with deletion.
    
    Uses cuckoo hashing with fingerprints instead of full items.
    Better space efficiency than Counting Bloom at low FPRs.
    
    Parameters:
        capacity: Maximum number of items
        fingerprint_bits: Bits per fingerprint (determines FPR)
        bucket_size: Items per bucket (default 4)
    
    Properties:
        - Supports deletion (unlike Bloom)
        - Lower FPR than Bloom at same space (at low FPRs)
        - Can fill to ~95% capacity
        - Lookup: O(1), 2 memory accesses
    
    False Positive Rate:
        FPR ≈ 2 × bucket_size / 2^fingerprint_bits
        
        With 8-bit fingerprints and bucket_size=4:
        FPR ≈ 8/256 ≈ 3%
    
    Example:
        >>> cf = CuckooFilter(capacity=1000, fingerprint_bits=12)
        >>> cf.add(b"hello")
        >>> b"hello" in cf  # True
        >>> cf.remove(b"hello")
        >>> b"hello" in cf  # False
    """
    
    MAX_KICKS = 500  # Maximum relocations before declaring full
    
    def __init__(
        self,
        capacity: int,
        fingerprint_bits: int = 8,
        bucket_size: int = 4,
        *,
        _buckets: Optional[List[List[int]]] = None,
        _count: int = 0,
    ):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if fingerprint_bits < 4 or fingerprint_bits > 32:
            raise ValueError("fingerprint_bits must be between 4 and 32")
        if bucket_size < 1 or bucket_size > 8:
            raise ValueError("bucket_size must be between 1 and 8")
        
        self._capacity = capacity
        self._fingerprint_bits = fingerprint_bits
        self._bucket_size = bucket_size
        
        # Number of buckets (round up to power of 2 for efficient modulo)
        num_buckets = 1
        while num_buckets * bucket_size < capacity:
            num_buckets *= 2
        self._num_buckets = num_buckets
        
        if _buckets is not None:
            self._buckets = _buckets
            self._count = _count
        else:
            # Each bucket is a list of fingerprints (0 = empty)
            self._buckets: List[List[int]] = [
                [0] * bucket_size for _ in range(num_buckets)
            ]
            self._count = 0
    
    @property
    def capacity(self) -> int:
        """Maximum capacity."""
        return self._num_buckets * self._bucket_size
    
    @property
    def count(self) -> int:
        """Number of items in the filter."""
        return self._count
    
    @property
    def load_factor(self) -> float:
        """Fraction of capacity used."""
        return self._count / self.capacity
    
    def estimated_fpr(self) -> float:
        """Estimated false positive rate."""
        return 2 * self._bucket_size / (1 << self._fingerprint_bits)
    
    def _bucket_indices(self, item: bytes) -> Tuple[int, int, int]:
        """
        Get the two bucket indices and fingerprint for an item.
        
        Uses partial-key cuckoo hashing:
            i1 = hash(item)
            i2 = i1 ⊕ hash(fingerprint)
        
        This allows computing the alternate index from just the fingerprint,
        which is essential for the relocation process.
        """
        h1, _ = _hash128(item)
        i1 = h1 % self._num_buckets
        fp = _fingerprint(item, self._fingerprint_bits)
        
        # XOR with hash of fingerprint
        fp_hash = _hash128(fp.to_bytes(4, 'little'))[0]
        i2 = (i1 ^ fp_hash) % self._num_buckets
        
        return i1, i2, fp
    
    def _alternate_index(self, index: int, fingerprint: int) -> int:
        """Compute alternate bucket index from current index and fingerprint."""
        fp_hash = _hash128(fingerprint.to_bytes(4, 'little'))[0]
        return (index ^ fp_hash) % self._num_buckets
    
    def add(self, item: Union[bytes, str]) -> bool:
        """
        Add an item to the filter.
        
        Returns True if successful.
        Returns False if filter is too full (item not added).
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        i1, i2, fp = self._bucket_indices(item)
        
        # Try to insert in bucket 1
        bucket1 = self._buckets[i1]
        for j in range(self._bucket_size):
            if bucket1[j] == 0:
                bucket1[j] = fp
                self._count += 1
                return True
        
        # Try to insert in bucket 2
        bucket2 = self._buckets[i2]
        for j in range(self._bucket_size):
            if bucket2[j] == 0:
                bucket2[j] = fp
                self._count += 1
                return True
        
        # Both full, need to relocate
        # Randomly pick one of the two buckets
        current_index = random.choice([i1, i2])
        current_fp = fp
        
        for _ in range(self.MAX_KICKS):
            # Pick random entry in bucket
            j = random.randrange(self._bucket_size)
            bucket = self._buckets[current_index]
            
            # Swap fingerprints
            current_fp, bucket[j] = bucket[j], current_fp
            
            # Find alternate location for kicked fingerprint
            current_index = self._alternate_index(current_index, current_fp)
            bucket = self._buckets[current_index]
            
            # Try to insert
            for k in range(self._bucket_size):
                if bucket[k] == 0:
                    bucket[k] = current_fp
                    self._count += 1
                    return True
        
        # Failed after MAX_KICKS
        return False
    
    def __contains__(self, item: Union[bytes, str]) -> bool:
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        i1, i2, fp = self._bucket_indices(item)
        
        return fp in self._buckets[i1] or fp in self._buckets[i2]
    
    def remove(self, item: Union[bytes, str]) -> bool:
        """
        Remove an item from the filter.
        
        Returns True if item was found and removed.
        Returns False if item was not found.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        i1, i2, fp = self._bucket_indices(item)
        
        # Check bucket 1
        bucket1 = self._buckets[i1]
        for j in range(self._bucket_size):
            if bucket1[j] == fp:
                bucket1[j] = 0
                self._count -= 1
                return True
        
        # Check bucket 2
        bucket2 = self._buckets[i2]
        for j in range(self._bucket_size):
            if bucket2[j] == fp:
                bucket2[j] = 0
                self._count -= 1
                return True
        
        return False
    
    def to_dict(self) -> dict:
        return {
            "type": "CuckooFilter",
            "capacity": self._capacity,
            "fingerprint_bits": self._fingerprint_bits,
            "bucket_size": self._bucket_size,
            "num_buckets": self._num_buckets,
            "count": self._count,
            "buckets": self._buckets,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CuckooFilter':
        cf = cls(
            data["capacity"],
            data["fingerprint_bits"],
            data["bucket_size"],
            _buckets=data["buckets"],
            _count=data["count"],
        )
        cf._num_buckets = data["num_buckets"]
        return cf
    
    def __repr__(self) -> str:
        return (f"CuckooFilter(count={self._count}, capacity={self.capacity}, "
                f"load={self.load_factor:.1%}, fpr≈{self.estimated_fpr():.4f})")


# =============================================================================
# HyperLogLog
# =============================================================================

class HyperLogLog:
    """
    HyperLogLog for cardinality estimation.
    
    Estimates the number of distinct elements in a stream using
    O(log log n) space. Based on the observation that the maximum
    number of leading zeros in hashed values approximates log₂(n).
    
    Parameters:
        precision: Number of bits for register index (4-18)
                  More precision = more accuracy, more memory
                  Registers = 2^precision
    
    Error Rate:
        Standard error ≈ 1.04 / √m where m = 2^precision
        
        precision=10 (1024 registers): ~3.25% error
        precision=14 (16384 registers): ~0.81% error
        precision=16 (65536 registers): ~0.41% error
    
    Memory:
        6 bits per register × 2^precision registers
        precision=14 uses ~12KB
    
    Example:
        >>> hll = HyperLogLog(precision=14)
        >>> for i in range(1000000):
        ...     hll.add(f"user_{i}".encode())
        >>> hll.count()  # ~1000000 ± 0.81%
    
    Merge:
        Two HyperLogLog sketches can be merged by taking the max
        of corresponding registers. This is exact (no additional error).
    """
    
    # Bias correction constants (alpha_m)
    ALPHA = {
        4: 0.673,
        5: 0.697,
        6: 0.709,
    }
    
    def __init__(
        self,
        precision: int = 14,
        *,
        _registers: Optional[bytearray] = None,
    ):
        if precision < 4 or precision > 18:
            raise ValueError("precision must be between 4 and 18")
        
        self._precision = precision
        self._num_registers = 1 << precision
        self._register_mask = self._num_registers - 1
        
        if _registers is not None:
            self._registers = _registers
        else:
            self._registers = bytearray(self._num_registers)
    
    @property
    def precision(self) -> int:
        """Number of bits for register indexing."""
        return self._precision
    
    @property
    def num_registers(self) -> int:
        """Number of registers (2^precision)."""
        return self._num_registers
    
    @property
    def standard_error(self) -> float:
        """Expected relative standard error."""
        return 1.04 / math.sqrt(self._num_registers)
    
    @property
    def size_bytes(self) -> int:
        """Memory used by registers."""
        return self._num_registers
    
    def _alpha(self) -> float:
        """Bias correction factor."""
        if self._precision in self.ALPHA:
            return self.ALPHA[self._precision]
        # For larger m, alpha ≈ 0.7213 / (1 + 1.079/m)
        return 0.7213 / (1 + 1.079 / self._num_registers)
    
    def _leading_zeros(self, value: int, max_bits: int) -> int:
        """Count leading zeros in the binary representation."""
        if value == 0:
            return max_bits
        
        count = 0
        mask = 1 << (max_bits - 1)
        while (value & mask) == 0 and count < max_bits:
            count += 1
            mask >>= 1
        
        return count
    
    def add(self, item: Union[bytes, str]) -> None:
        """
        Add an item to the sketch.
        
        Hashes the item, uses first p bits as register index,
        and remaining bits to count leading zeros.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        h, _ = _hash128(item)
        
        # First p bits → register index
        index = h & self._register_mask
        
        # Remaining bits → count leading zeros
        w = h >> self._precision
        # Add 1 because we're looking at position, not count
        rho = self._leading_zeros(w, 64 - self._precision) + 1
        
        # Update register with max
        if rho > self._registers[index]:
            self._registers[index] = rho
    
    def count(self) -> int:
        """
        Estimate the cardinality (number of distinct items).
        
        Uses the HyperLogLog algorithm with small/large range corrections.
        """
        m = self._num_registers
        alpha = self._alpha()
        
        # Raw harmonic mean estimate
        # E = alpha × m² / sum(2^(-register[i]))
        indicator_sum = sum(2.0 ** (-r) for r in self._registers)
        estimate = alpha * m * m / indicator_sum
        
        # Small range correction (linear counting)
        if estimate <= 2.5 * m:
            # Count registers with value 0
            zeros = sum(1 for r in self._registers if r == 0)
            if zeros > 0:
                # Use linear counting
                estimate = m * math.log(m / zeros)
        
        # Large range correction
        elif estimate > (1 << 32) / 30:
            estimate = -(1 << 32) * math.log(1 - estimate / (1 << 32))
        
        return int(estimate)
    
    def merge(self, other: 'HyperLogLog') -> 'HyperLogLog':
        """
        Merge another HyperLogLog into this one.
        
        The result estimates the cardinality of the union.
        Both sketches must have the same precision.
        
        Returns self for method chaining.
        """
        if self._precision != other._precision:
            raise ValueError(f"Cannot merge: different precisions ({self._precision} vs {other._precision})")
        
        for i in range(self._num_registers):
            if other._registers[i] > self._registers[i]:
                self._registers[i] = other._registers[i]
        
        return self
    
    def union(self, other: 'HyperLogLog') -> 'HyperLogLog':
        """Create a new sketch containing the union."""
        result = self.copy()
        result.merge(other)
        return result
    
    def copy(self) -> 'HyperLogLog':
        """Create a copy of this sketch."""
        return HyperLogLog(
            self._precision,
            _registers=bytearray(self._registers),
        )
    
    def to_dict(self) -> dict:
        import base64
        return {
            "type": "HyperLogLog",
            "precision": self._precision,
            "registers": base64.b64encode(bytes(self._registers)).decode('ascii'),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HyperLogLog':
        import base64
        registers = bytearray(base64.b64decode(data["registers"]))
        return cls(data["precision"], _registers=registers)
    
    def __repr__(self) -> str:
        return (f"HyperLogLog(count≈{self.count()}, precision={self._precision}, "
                f"error≈{self.standard_error:.2%})")


# =============================================================================
# Count-Min Sketch
# =============================================================================

class CountMinSketch:
    """
    Count-Min Sketch for frequency estimation.
    
    Estimates the frequency of items in a stream. Always overestimates
    (never underestimates) the true count.
    
    Parameters:
        width: Number of counters per row
        depth: Number of rows (hash functions)
    
    Or use from_error():
        epsilon: Maximum overestimate as fraction of total count
        delta: Probability of exceeding epsilon
    
    Guarantees:
        Estimated count is in [true_count, true_count + εN]
        with probability at least 1 - δ
        where N is total number of items added
    
    Example:
        >>> cms = CountMinSketch.from_error(epsilon=0.001, delta=0.01)
        >>> for word in document:
        ...     cms.add(word.encode())
        >>> cms.count(b"the")  # Approximately correct frequency
    
    Merge:
        Two sketches with same dimensions can be merged by adding
        corresponding counters. Useful for distributed counting.
    """
    
    def __init__(
        self,
        width: int,
        depth: int,
        *,
        _counters: Optional[List[List[int]]] = None,
        _total: int = 0,
    ):
        if width < 1 or depth < 1:
            raise ValueError("width and depth must be at least 1")
        
        self._width = width
        self._depth = depth
        self._total = _total
        
        if _counters is not None:
            self._counters = _counters
        else:
            self._counters = [[0] * width for _ in range(depth)]
    
    @classmethod
    def from_error(cls, epsilon: float, delta: float) -> 'CountMinSketch':
        """
        Create a sketch with specified error bounds.
        
        Parameters:
            epsilon: Maximum overestimate as fraction of total count
            delta: Probability of exceeding epsilon
        
        The sketch will satisfy:
            count(x) ≤ true_count(x) + εN
            with probability ≥ 1 - δ
        """
        if not 0 < epsilon < 1:
            raise ValueError("epsilon must be between 0 and 1")
        if not 0 < delta < 1:
            raise ValueError("delta must be between 0 and 1")
        
        # width = ceil(e / epsilon)
        width = int(math.ceil(math.e / epsilon))
        # depth = ceil(ln(1/delta))
        depth = int(math.ceil(math.log(1 / delta)))
        
        return cls(width, depth)
    
    @property
    def width(self) -> int:
        """Number of counters per row."""
        return self._width
    
    @property
    def depth(self) -> int:
        """Number of rows."""
        return self._depth
    
    @property
    def total(self) -> int:
        """Total number of items added."""
        return self._total
    
    @property
    def size_bytes(self) -> int:
        """Approximate memory usage (assuming 8 bytes per counter)."""
        return self._width * self._depth * 8
    
    def _hash_indices(self, item: bytes) -> List[int]:
        """Get one index per row for an item."""
        return list(_hash_family(item, self._depth, self._width))
    
    def add(self, item: Union[bytes, str], count: int = 1) -> None:
        """
        Add an item to the sketch.
        
        Parameters:
            item: The item to add
            count: Number of times to add (can be negative for deletion,
                   but may cause underestimates)
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        for row, col in enumerate(self._hash_indices(item)):
            self._counters[row][col] += count
        
        self._total += count
    
    def count(self, item: Union[bytes, str]) -> int:
        """
        Estimate the count of an item.
        
        Returns the minimum count across all rows, which is
        an overestimate of the true count.
        """
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        indices = self._hash_indices(item)
        return min(self._counters[row][col] for row, col in enumerate(indices))
    
    def point_query(self, item: Union[bytes, str]) -> int:
        """Alias for count()."""
        return self.count(item)
    
    def inner_product(self, other: 'CountMinSketch') -> int:
        """
        Estimate the inner product of two frequency vectors.
        
        Useful for computing similarity between two streams.
        """
        if self._width != other._width or self._depth != other._depth:
            raise ValueError("Sketches must have same dimensions")
        
        # Minimum over rows of sum of products
        estimates = []
        for row in range(self._depth):
            product_sum = sum(
                self._counters[row][col] * other._counters[row][col]
                for col in range(self._width)
            )
            estimates.append(product_sum)
        
        return min(estimates)
    
    def merge(self, other: 'CountMinSketch') -> 'CountMinSketch':
        """
        Merge another sketch into this one.
        
        The result estimates frequencies in the combined stream.
        Both sketches must have the same dimensions.
        
        Returns self for method chaining.
        """
        if self._width != other._width or self._depth != other._depth:
            raise ValueError("Cannot merge: different dimensions")
        
        for row in range(self._depth):
            for col in range(self._width):
                self._counters[row][col] += other._counters[row][col]
        
        self._total += other._total
        
        return self
    
    def copy(self) -> 'CountMinSketch':
        """Create a copy of this sketch."""
        return CountMinSketch(
            self._width,
            self._depth,
            _counters=[row[:] for row in self._counters],
            _total=self._total,
        )
    
    def to_dict(self) -> dict:
        return {
            "type": "CountMinSketch",
            "width": self._width,
            "depth": self._depth,
            "total": self._total,
            "counters": self._counters,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CountMinSketch':
        return cls(
            data["width"],
            data["depth"],
            _counters=data["counters"],
            _total=data["total"],
        )
    
    def __repr__(self) -> str:
        return f"CountMinSketch(width={self._width}, depth={self._depth}, total={self._total})"


# =============================================================================
# Top-K (Heavy Hitters) using Count-Min Sketch
# =============================================================================

class TopK:
    """
    Track the K most frequent items in a stream.
    
    Uses a Count-Min Sketch for frequency estimation combined
    with a min-heap to track the top items.
    
    Parameters:
        k: Number of top items to track
        epsilon: Error bound for Count-Min Sketch
        delta: Probability bound for Count-Min Sketch
    
    Example:
        >>> topk = TopK(k=10, epsilon=0.0001)
        >>> for word in huge_text_file:
        ...     topk.add(word.encode())
        >>> topk.get_top()  # Returns [(b"the", 50000), (b"and", 30000), ...]
    """
    
    def __init__(
        self,
        k: int,
        epsilon: float = 0.001,
        delta: float = 0.01,
    ):
        if k < 1:
            raise ValueError("k must be at least 1")
        
        self._k = k
        self._sketch = CountMinSketch.from_error(epsilon, delta)
        
        # Min-heap of (count, item) tuples
        # We use negative counts for max-heap behavior with heapq
        import heapq
        self._heap: List[Tuple[int, bytes]] = []
        self._items: dict[bytes, int] = {}  # item -> count in heap
    
    @property
    def k(self) -> int:
        """Number of top items to track."""
        return self._k
    
    def add(self, item: Union[bytes, str], count: int = 1) -> None:
        """Add an item to the stream."""
        if isinstance(item, str):
            item = item.encode('utf-8')
        
        import heapq
        
        self._sketch.add(item, count)
        estimated_count = self._sketch.count(item)
        
        if item in self._items:
            # Item already in top-k, update its count
            # (Lazy update - we'll fix heap when needed)
            self._items[item] = estimated_count
        elif len(self._heap) < self._k:
            # Room in heap, add directly
            heapq.heappush(self._heap, (estimated_count, item))
            self._items[item] = estimated_count
        elif estimated_count > self._heap[0][0]:
            # Better than current minimum, replace
            _, old_item = heapq.heapreplace(self._heap, (estimated_count, item))
            del self._items[old_item]
            self._items[item] = estimated_count
    
    def get_top(self) -> List[Tuple[bytes, int]]:
        """
        Get the top K items with their estimated counts.
        
        Returns list of (item, count) tuples, sorted by count descending.
        """
        # Rebuild heap with current counts (lazy updates may have changed things)
        import heapq
        
        self._heap = [
            (self._sketch.count(item), item) 
            for item in self._items
        ]
        heapq.heapify(self._heap)
        
        # Sort by count descending
        result = sorted(
            [(item, count) for count, item in self._heap],
            key=lambda x: x[1],
            reverse=True,
        )
        
        return result
    
    def __repr__(self) -> str:
        return f"TopK(k={self._k}, tracking={len(self._items)} items)"


# =============================================================================
# Utility Functions
# =============================================================================

def optimal_bloom_params(n: int, fpr: float) -> Tuple[int, int]:
    """
    Calculate optimal Bloom filter parameters.
    
    Parameters:
        n: Expected number of items
        fpr: Desired false positive rate
    
    Returns:
        (num_bits, num_hashes)
    """
    # m = -n × ln(p) / (ln(2))²
    m = int(math.ceil(-n * math.log(fpr) / (math.log(2) ** 2)))
    
    # k = (m/n) × ln(2)
    k = int(round((m / n) * math.log(2)))
    
    return m, max(k, 1)


def bloom_fpr(m: int, k: int, n: int) -> float:
    """
    Calculate Bloom filter false positive rate.
    
    Parameters:
        m: Number of bits
        k: Number of hash functions
        n: Number of items
    
    Returns:
        False positive rate
    """
    # (1 - e^(-kn/m))^k
    return (1 - math.exp(-k * n / m)) ** k


def hyperloglog_error(precision: int) -> float:
    """
    Calculate expected standard error for HyperLogLog.
    
    Parameters:
        precision: Number of bits for register index
    
    Returns:
        Standard error (relative)
    """
    return 1.04 / math.sqrt(1 << precision)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Membership testing
    'BloomFilter',
    'CountingBloomFilter',
    'CuckooFilter',
    
    # Cardinality estimation
    'HyperLogLog',
    
    # Frequency estimation
    'CountMinSketch',
    'TopK',
    
    # Utilities
    'BitArray',
    'optimal_bloom_params',
    'bloom_fpr',
    'hyperloglog_error',
]
