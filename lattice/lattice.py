"""
Lattice: Conflict-Free Replicated Data Types (CRDTs)

A library for building distributed, eventually-consistent data structures
that automatically resolve conflicts without coordination.

Mathematical Foundation:
    CRDTs are based on semilattice theory. A semilattice (S, ⊔) is a set S
    with a binary operation ⊔ (join/merge) that is:
    
    - Commutative: a ⊔ b = b ⊔ a
    - Associative: (a ⊔ b) ⊔ c = a ⊔ (b ⊔ c)
    - Idempotent: a ⊔ a = a
    
    These properties guarantee that replicas converge regardless of:
    - Message ordering
    - Message duplication
    - Network partitions
    
    The join operation computes the Least Upper Bound (LUB) of two states.

Included CRDTs:
    Counters:
        - GCounter: Grow-only counter (increment only)
        - PNCounter: Positive-Negative counter (increment and decrement)
    
    Registers:
        - LWWRegister: Last-Writer-Wins register (timestamp-based)
        - MVRegister: Multi-Value register (preserves concurrent writes)
    
    Sets:
        - GSet: Grow-only set (add only)
        - TwoPSet: Two-Phase set (add and remove, but remove is permanent)
        - ORSet: Observed-Remove set (add and remove with proper semantics)
        - LWWSet: Last-Writer-Wins set (timestamp-based add/remove)
    
    Maps:
        - ORMap: Observed-Remove map (keys can be added/removed)

Delta-State CRDTs:
    For network efficiency, each CRDT supports delta-state operations.
    Instead of sending full state, replicas exchange only the changes
    (deltas) since the last sync. Deltas are themselves CRDTs and can
    be merged.

Usage Pattern:
    1. Create a CRDT instance with a unique replica ID
    2. Perform local operations (increment, add, set, etc.)
    3. Periodically merge with other replicas
    4. Read the current value

Example:
    >>> from lattice import GCounter, PNCounter, ORSet
    >>> 
    >>> # Each replica has a unique ID
    >>> counter_a = GCounter("replica-a")
    >>> counter_b = GCounter("replica-b")
    >>> 
    >>> # Local operations
    >>> counter_a.increment(5)
    >>> counter_b.increment(3)
    >>> 
    >>> # Merge states (in any order)
    >>> counter_a.merge(counter_b)
    >>> counter_b.merge(counter_a)
    >>> 
    >>> # Both replicas converge to same value
    >>> assert counter_a.value == counter_b.value == 8

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import time
import uuid
import json
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Generic, TypeVar, Callable, Iterator, 
    Mapping, Set, FrozenSet, Optional, Union
)
from functools import reduce
from copy import deepcopy
import threading


# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# =============================================================================
# Base Classes
# =============================================================================

class CRDT(ABC, Generic[T]):
    """
    Abstract base class for all CRDTs.
    
    Every CRDT must implement:
    - value: Current state as a plain Python type
    - merge(): Combine with another replica
    - clone(): Create an independent copy
    - to_dict() / from_dict(): Serialization
    
    The merge operation must satisfy semilattice properties:
    - Commutative: a.merge(b) ≡ b.merge(a)
    - Associative: a.merge(b).merge(c) ≡ a.merge(b.merge(c))
    - Idempotent: a.merge(a) ≡ a
    """
    
    @property
    @abstractmethod
    def value(self) -> T:
        """Get the current value as a plain Python type."""
        ...
    
    @abstractmethod
    def merge(self, other: 'CRDT[T]') -> 'CRDT[T]':
        """
        Merge another replica's state into this one.
        
        Returns self for method chaining.
        The merge operation computes the Least Upper Bound (LUB).
        """
        ...
    
    @abstractmethod
    def clone(self) -> 'CRDT[T]':
        """Create an independent copy of this CRDT."""
        ...
    
    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        ...
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> 'CRDT[T]':
        """Deserialize from a dictionary."""
        ...


class DeltaCRDT(CRDT[T], ABC):
    """
    CRDT that supports delta-state synchronization.
    
    Delta-state CRDTs track changes since the last sync and allow
    sending only the delta (change) rather than the full state.
    This dramatically reduces network bandwidth for large states.
    
    The delta is itself a CRDT that can be merged.
    """
    
    @abstractmethod
    def delta(self) -> 'DeltaCRDT[T]':
        """
        Get the delta (changes) since last delta_reset().
        
        Returns a new CRDT containing only the changes.
        """
        ...
    
    @abstractmethod
    def delta_reset(self) -> None:
        """
        Reset the delta tracker.
        
        Call this after successfully sending a delta to a replica.
        """
        ...
    
    def apply_delta(self, delta: 'DeltaCRDT[T]') -> 'DeltaCRDT[T]':
        """
        Apply a delta received from another replica.
        
        This is equivalent to merge() but semantically indicates
        we're applying a delta rather than full state.
        """
        return self.merge(delta)


# =============================================================================
# Timestamps
# =============================================================================

@dataclass(frozen=True, order=True)
class HLCTimestamp:
    """
    Hybrid Logical Clock timestamp for LWW types.
    
    Combines physical time with a logical counter to ensure:
    1. Timestamps are always increasing locally
    2. Timestamps are close to wall-clock time
    3. Total ordering exists (using node_id as tiebreaker)
    """
    physical: int  # Milliseconds since epoch
    logical: int   # Logical counter for same-millisecond events
    node_id: str   # Tiebreaker for concurrent events
    
    @classmethod
    def now(cls, node_id: str, last: Optional['HLCTimestamp'] = None) -> 'HLCTimestamp':
        """
        Generate a new timestamp guaranteed to be greater than `last`.
        """
        physical = int(time.time() * 1000)
        
        if last is None:
            return cls(physical, 0, node_id)
        
        if physical > last.physical:
            return cls(physical, 0, node_id)
        else:
            # Physical time hasn't advanced, increment logical
            return cls(last.physical, last.logical + 1, node_id)
    
    @classmethod
    def receive(cls, node_id: str, local: 'HLCTimestamp', remote: 'HLCTimestamp') -> 'HLCTimestamp':
        """
        Generate timestamp when receiving a message with `remote` timestamp.
        """
        physical = int(time.time() * 1000)
        max_physical = max(physical, local.physical, remote.physical)
        
        if max_physical == physical and physical > local.physical and physical > remote.physical:
            return cls(physical, 0, node_id)
        elif max_physical == local.physical and local.physical == remote.physical:
            return cls(max_physical, max(local.logical, remote.logical) + 1, node_id)
        elif max_physical == local.physical:
            return cls(max_physical, local.logical + 1, node_id)
        else:
            return cls(max_physical, remote.logical + 1, node_id)
    
    def to_dict(self) -> dict:
        return {"physical": self.physical, "logical": self.logical, "node_id": self.node_id}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HLCTimestamp':
        return cls(data["physical"], data["logical"], data["node_id"])


# =============================================================================
# Counters
# =============================================================================

class GCounter(DeltaCRDT[int]):
    """
    Grow-only Counter.
    
    Each replica maintains its own count. The total value is the sum
    of all replica counts. Only increment is supported.
    
    State: {replica_id: count}
    
    Merge: Take max of each replica's count
        merged[r] = max(self[r], other[r])
    
    This works because counts only increase, so max is the LUB.
    
    Example:
        >>> a = GCounter("node-a")
        >>> b = GCounter("node-b")
        >>> a.increment(5)
        >>> b.increment(3)
        >>> a.merge(b)
        >>> a.value
        8
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._counts: dict[str, int] = {replica_id: 0}
        self._delta_counts: dict[str, int] = {}
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> int:
        """Total count across all replicas."""
        return sum(self._counts.values())
    
    def increment(self, amount: int = 1) -> 'GCounter':
        """
        Increment the counter.
        
        Only positive amounts are allowed (grow-only).
        """
        if amount < 0:
            raise ValueError("GCounter only supports positive increments")
        
        self._counts[self._replica_id] = self._counts.get(self._replica_id, 0) + amount
        self._delta_counts[self._replica_id] = self._counts[self._replica_id]
        
        return self
    
    def merge(self, other: 'GCounter') -> 'GCounter':
        """Merge by taking max of each replica's count."""
        for replica_id, count in other._counts.items():
            self._counts[replica_id] = max(self._counts.get(replica_id, 0), count)
        return self
    
    def delta(self) -> 'GCounter':
        """Get delta containing only local changes."""
        d = GCounter(self._replica_id)
        d._counts = dict(self._delta_counts)
        return d
    
    def delta_reset(self) -> None:
        """Clear the delta tracker."""
        self._delta_counts.clear()
    
    def clone(self) -> 'GCounter':
        c = GCounter(self._replica_id)
        c._counts = dict(self._counts)
        c._delta_counts = dict(self._delta_counts)
        return c
    
    def to_dict(self) -> dict:
        return {
            "type": "GCounter",
            "replica_id": self._replica_id,
            "counts": self._counts
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GCounter':
        c = cls(data["replica_id"])
        c._counts = dict(data["counts"])
        return c
    
    def __repr__(self) -> str:
        return f"GCounter({self.value}, replicas={len(self._counts)})"


class PNCounter(DeltaCRDT[int]):
    """
    Positive-Negative Counter.
    
    Supports both increment and decrement by maintaining two GCounters:
    - P (positive): tracks increments
    - N (negative): tracks decrements
    
    Value = P.value - N.value
    
    This decomposition allows both operations while maintaining
    CRDT properties. Each operation only affects one GCounter.
    
    Example:
        >>> c = PNCounter("node-a")
        >>> c.increment(10)
        >>> c.decrement(3)
        >>> c.value
        7
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._p = GCounter(replica_id)  # Positive counts
        self._n = GCounter(replica_id)  # Negative counts
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> int:
        """Net count (increments - decrements)."""
        return self._p.value - self._n.value
    
    def increment(self, amount: int = 1) -> 'PNCounter':
        """Increment the counter."""
        if amount < 0:
            return self.decrement(-amount)
        self._p.increment(amount)
        return self
    
    def decrement(self, amount: int = 1) -> 'PNCounter':
        """Decrement the counter."""
        if amount < 0:
            return self.increment(-amount)
        self._n.increment(amount)
        return self
    
    def merge(self, other: 'PNCounter') -> 'PNCounter':
        """Merge both P and N counters."""
        self._p.merge(other._p)
        self._n.merge(other._n)
        return self
    
    def delta(self) -> 'PNCounter':
        d = PNCounter(self._replica_id)
        d._p = self._p.delta()
        d._n = self._n.delta()
        return d
    
    def delta_reset(self) -> None:
        self._p.delta_reset()
        self._n.delta_reset()
    
    def clone(self) -> 'PNCounter':
        c = PNCounter(self._replica_id)
        c._p = self._p.clone()
        c._n = self._n.clone()
        return c
    
    def to_dict(self) -> dict:
        return {
            "type": "PNCounter",
            "replica_id": self._replica_id,
            "p": self._p.to_dict(),
            "n": self._n.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PNCounter':
        c = cls(data["replica_id"])
        c._p = GCounter.from_dict(data["p"])
        c._n = GCounter.from_dict(data["n"])
        return c
    
    def __repr__(self) -> str:
        return f"PNCounter({self.value})"


# =============================================================================
# Registers
# =============================================================================

class LWWRegister(DeltaCRDT[Optional[T]], Generic[T]):
    """
    Last-Writer-Wins Register.
    
    Stores a single value. Concurrent writes are resolved by timestamp:
    the write with the highest timestamp wins.
    
    This provides strong eventual consistency but may lose updates
    if two replicas write concurrently. Use MVRegister if you need
    to preserve all concurrent writes.
    
    The timestamp uses HLC to handle clock skew gracefully.
    
    Example:
        >>> a = LWWRegister[str]("node-a")
        >>> b = LWWRegister[str]("node-b")
        >>> a.set("hello")
        >>> b.set("world")
        >>> a.merge(b)
        >>> # Value depends on which had higher timestamp
    """
    
    def __init__(self, replica_id: str, initial: Optional[T] = None):
        self._replica_id = replica_id
        self._value: Optional[T] = initial
        self._timestamp: Optional[HLCTimestamp] = None
        
        if initial is not None:
            self._timestamp = HLCTimestamp.now(replica_id)
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> Optional[T]:
        """Current value of the register."""
        return self._value
    
    @property
    def timestamp(self) -> Optional[HLCTimestamp]:
        """Timestamp of the current value."""
        return self._timestamp
    
    def set(self, value: T) -> 'LWWRegister[T]':
        """
        Set the register's value.
        
        Automatically generates a timestamp higher than the current one.
        """
        self._value = value
        self._timestamp = HLCTimestamp.now(self._replica_id, self._timestamp)
        return self
    
    def merge(self, other: 'LWWRegister[T]') -> 'LWWRegister[T]':
        """
        Merge by keeping the value with the higher timestamp.
        
        If timestamps are equal (extremely rare), use node_id as tiebreaker.
        """
        if other._timestamp is None:
            return self
        
        if self._timestamp is None or other._timestamp > self._timestamp:
            self._value = other._value
            self._timestamp = other._timestamp
        
        return self
    
    def delta(self) -> 'LWWRegister[T]':
        """The delta is the full state (register is small)."""
        return self.clone()
    
    def delta_reset(self) -> None:
        """No-op for registers (always send full state)."""
        pass
    
    def clone(self) -> 'LWWRegister[T]':
        r = LWWRegister[T](self._replica_id)
        r._value = deepcopy(self._value)
        r._timestamp = self._timestamp
        return r
    
    def to_dict(self) -> dict:
        return {
            "type": "LWWRegister",
            "replica_id": self._replica_id,
            "value": self._value,
            "timestamp": self._timestamp.to_dict() if self._timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LWWRegister':
        r = cls(data["replica_id"])
        r._value = data["value"]
        r._timestamp = HLCTimestamp.from_dict(data["timestamp"]) if data["timestamp"] else None
        return r
    
    def __repr__(self) -> str:
        return f"LWWRegister({self._value!r})"


class MVRegister(DeltaCRDT[FrozenSet[T]], Generic[T]):
    """
    Multi-Value Register.
    
    Unlike LWWRegister, this preserves ALL concurrent writes.
    Reading returns a set of values representing concurrent versions.
    The application must resolve the conflict (or present choices to user).
    
    State: {(value, vector_clock)} pairs
    
    On write: Replace all pairs with new (value, incremented_clock)
    On merge: Keep pairs that aren't dominated by others
    
    A pair (v1, vc1) dominates (v2, vc2) if vc1 > vc2 (causally after).
    
    Example:
        >>> a = MVRegister[str]("node-a")
        >>> b = MVRegister[str]("node-b")
        >>> a.set("hello")
        >>> b.set("world")  # Concurrent with a's write
        >>> a.merge(b)
        >>> a.value  # frozenset({"hello", "world"})
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        # Each entry: (value, {replica_id: counter})
        self._entries: list[tuple[T, dict[str, int]]] = []
        self._clock: dict[str, int] = {}
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> FrozenSet[T]:
        """
        Set of all concurrent values.
        
        If only one value, there's no conflict.
        If multiple values, they represent concurrent writes.
        """
        return frozenset(v for v, _ in self._entries)
    
    @property
    def is_conflicted(self) -> bool:
        """True if there are multiple concurrent values."""
        return len(self._entries) > 1
    
    def set(self, value: T) -> 'MVRegister[T]':
        """
        Set the register, replacing all previous values.
        
        This causally follows all previously observed values.
        """
        # Increment our clock
        self._clock[self._replica_id] = self._clock.get(self._replica_id, 0) + 1
        
        # Replace all entries with new one
        self._entries = [(value, dict(self._clock))]
        
        return self
    
    def merge(self, other: 'MVRegister[T]') -> 'MVRegister[T]':
        """
        Merge by keeping non-dominated entries.
        
        An entry is dominated if another entry's clock is >= in all components.
        """
        # Combine clocks (take max)
        for replica_id, counter in other._clock.items():
            self._clock[replica_id] = max(self._clock.get(replica_id, 0), counter)
        
        # Combine entries
        all_entries = self._entries + other._entries
        
        # Remove dominated entries
        kept = []
        for value, clock in all_entries:
            dominated = False
            for other_value, other_clock in all_entries:
                if clock is other_clock:
                    continue
                if self._dominates(other_clock, clock):
                    dominated = True
                    break
            if not dominated:
                # Deduplicate identical entries
                if not any(self._clock_equal(clock, k) and value == v for v, k in kept):
                    kept.append((value, clock))
        
        self._entries = kept
        return self
    
    def _dominates(self, a: dict[str, int], b: dict[str, int]) -> bool:
        """Check if clock a strictly dominates clock b."""
        all_keys = set(a.keys()) | set(b.keys())
        all_geq = all(a.get(k, 0) >= b.get(k, 0) for k in all_keys)
        any_gt = any(a.get(k, 0) > b.get(k, 0) for k in all_keys)
        return all_geq and any_gt
    
    def _clock_equal(self, a: dict[str, int], b: dict[str, int]) -> bool:
        """Check if two clocks are equal."""
        all_keys = set(a.keys()) | set(b.keys())
        return all(a.get(k, 0) == b.get(k, 0) for k in all_keys)
    
    def delta(self) -> 'MVRegister[T]':
        return self.clone()
    
    def delta_reset(self) -> None:
        pass
    
    def clone(self) -> 'MVRegister[T]':
        r = MVRegister[T](self._replica_id)
        r._entries = [(deepcopy(v), dict(c)) for v, c in self._entries]
        r._clock = dict(self._clock)
        return r
    
    def to_dict(self) -> dict:
        return {
            "type": "MVRegister",
            "replica_id": self._replica_id,
            "entries": [(v, c) for v, c in self._entries],
            "clock": self._clock
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MVRegister':
        r = cls(data["replica_id"])
        r._entries = [(v, c) for v, c in data["entries"]]
        r._clock = dict(data["clock"])
        return r
    
    def __repr__(self) -> str:
        if len(self._entries) == 0:
            return "MVRegister(∅)"
        elif len(self._entries) == 1:
            return f"MVRegister({self._entries[0][0]!r})"
        else:
            return f"MVRegister(conflict: {self.value})"


# =============================================================================
# Sets
# =============================================================================

class GSet(DeltaCRDT[FrozenSet[T]], Generic[T]):
    """
    Grow-only Set.
    
    Elements can only be added, never removed.
    Merge is set union.
    
    Simple but useful for:
    - Collecting votes (can't unvote)
    - Recording events
    - Building other CRDTs
    
    Example:
        >>> a = GSet[str]("node-a")
        >>> b = GSet[str]("node-b")
        >>> a.add("x")
        >>> b.add("y")
        >>> a.merge(b)
        >>> a.value  # frozenset({"x", "y"})
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._elements: set[T] = set()
        self._delta_elements: set[T] = set()
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> FrozenSet[T]:
        """Immutable view of the set."""
        return frozenset(self._elements)
    
    def add(self, element: T) -> 'GSet[T]':
        """Add an element to the set."""
        if element not in self._elements:
            self._elements.add(element)
            self._delta_elements.add(element)
        return self
    
    def __contains__(self, element: T) -> bool:
        return element in self._elements
    
    def __len__(self) -> int:
        return len(self._elements)
    
    def __iter__(self) -> Iterator[T]:
        return iter(self._elements)
    
    def merge(self, other: 'GSet[T]') -> 'GSet[T]':
        """Merge is set union."""
        self._elements |= other._elements
        return self
    
    def delta(self) -> 'GSet[T]':
        d = GSet[T](self._replica_id)
        d._elements = set(self._delta_elements)
        return d
    
    def delta_reset(self) -> None:
        self._delta_elements.clear()
    
    def clone(self) -> 'GSet[T]':
        g = GSet[T](self._replica_id)
        g._elements = set(self._elements)
        g._delta_elements = set(self._delta_elements)
        return g
    
    def to_dict(self) -> dict:
        return {
            "type": "GSet",
            "replica_id": self._replica_id,
            "elements": list(self._elements)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GSet':
        g = cls(data["replica_id"])
        g._elements = set(data["elements"])
        return g
    
    def __repr__(self) -> str:
        return f"GSet({self._elements})"


class TwoPSet(DeltaCRDT[FrozenSet[T]], Generic[T]):
    """
    Two-Phase Set.
    
    Supports both add and remove, but with a restriction:
    once removed, an element can NEVER be re-added.
    
    State: (add_set, remove_set) - both GSets
    Value: add_set - remove_set
    
    Use when:
    - Removal is rare and permanent
    - You need simple semantics
    
    Don't use when:
    - Elements might be re-added after removal (use ORSet)
    
    Example:
        >>> s = TwoPSet[str]("node-a")
        >>> s.add("x").add("y")
        >>> s.remove("x")
        >>> s.value  # frozenset({"y"})
        >>> s.add("x")  # No effect! x was removed
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._added: set[T] = set()
        self._removed: set[T] = set()
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> FrozenSet[T]:
        """Elements that have been added but not removed."""
        return frozenset(self._added - self._removed)
    
    def add(self, element: T) -> 'TwoPSet[T]':
        """
        Add an element.
        
        Has no effect if element was previously removed.
        """
        self._added.add(element)
        return self
    
    def remove(self, element: T) -> 'TwoPSet[T]':
        """
        Remove an element permanently.
        
        Once removed, the element can never be re-added.
        """
        if element in self._added:
            self._removed.add(element)
        return self
    
    def __contains__(self, element: T) -> bool:
        return element in self._added and element not in self._removed
    
    def __len__(self) -> int:
        return len(self.value)
    
    def merge(self, other: 'TwoPSet[T]') -> 'TwoPSet[T]':
        """Merge both add and remove sets."""
        self._added |= other._added
        self._removed |= other._removed
        return self
    
    def delta(self) -> 'TwoPSet[T]':
        return self.clone()
    
    def delta_reset(self) -> None:
        pass
    
    def clone(self) -> 'TwoPSet[T]':
        s = TwoPSet[T](self._replica_id)
        s._added = set(self._added)
        s._removed = set(self._removed)
        return s
    
    def to_dict(self) -> dict:
        return {
            "type": "TwoPSet",
            "replica_id": self._replica_id,
            "added": list(self._added),
            "removed": list(self._removed)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TwoPSet':
        s = cls(data["replica_id"])
        s._added = set(data["added"])
        s._removed = set(data["removed"])
        return s
    
    def __repr__(self) -> str:
        return f"TwoPSet({self.value})"


class ORSet(DeltaCRDT[FrozenSet[T]], Generic[T]):
    """
    Observed-Remove Set (Add-Wins semantics).
    
    The most powerful set CRDT. Supports:
    - Add: Always succeeds
    - Remove: Removes only currently observed instances
    - Re-add after remove: Works correctly
    
    Implementation:
    Each add creates a unique tag (replica_id + counter).
    The set contains (element, tag) pairs.
    Remove removes all tags for an element that we've seen.
    A concurrent add creates a new tag that survives the remove.
    
    This is "add-wins": concurrent add and remove results in element present.
    
    Trade-off:
    - More complex than TwoPSet
    - Requires garbage collection of removed tags (not implemented here)
    - More space due to tag storage
    
    Example:
        >>> a = ORSet[str]("node-a")
        >>> b = ORSet[str]("node-b")
        >>> a.add("x")
        >>> b.merge(a)  # b sees "x"
        >>> 
        >>> # Concurrent operations:
        >>> a.remove("x")  # a removes x
        >>> b.add("x")     # b re-adds x (new tag)
        >>> 
        >>> a.merge(b)
        >>> "x" in a  # True! b's add survives a's remove
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._counter = 0
        # Map: element -> set of tags (each tag is unique identifier)
        self._entries: dict[T, set[str]] = {}
        self._delta_entries: dict[T, set[str]] = {}
        self._delta_removed: dict[T, set[str]] = {}
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> FrozenSet[T]:
        """Elements currently in the set."""
        return frozenset(e for e, tags in self._entries.items() if tags)
    
    def _generate_tag(self) -> str:
        """Generate a unique tag for this replica."""
        self._counter += 1
        return f"{self._replica_id}:{self._counter}"
    
    def add(self, element: T) -> 'ORSet[T]':
        """
        Add an element with a new unique tag.
        
        If element exists, adds another tag (harmless).
        If element was removed, the new tag makes it present again.
        """
        tag = self._generate_tag()
        
        if element not in self._entries:
            self._entries[element] = set()
        self._entries[element].add(tag)
        
        # Track delta
        if element not in self._delta_entries:
            self._delta_entries[element] = set()
        self._delta_entries[element].add(tag)
        
        return self
    
    def remove(self, element: T) -> 'ORSet[T]':
        """
        Remove all observed tags for an element.
        
        Only removes tags we currently see. Concurrent adds
        create new tags that won't be affected.
        """
        if element in self._entries:
            removed_tags = self._entries[element].copy()
            self._entries[element].clear()
            
            # Track removed tags in delta
            if element not in self._delta_removed:
                self._delta_removed[element] = set()
            self._delta_removed[element] |= removed_tags
        
        return self
    
    def __contains__(self, element: T) -> bool:
        return element in self._entries and bool(self._entries[element])
    
    def __len__(self) -> int:
        return sum(1 for tags in self._entries.values() if tags)
    
    def __iter__(self) -> Iterator[T]:
        return iter(self.value)
    
    def merge(self, other: 'ORSet[T]') -> 'ORSet[T]':
        """
        Merge by computing the set of surviving tags.
        
        A tag survives if:
        - It exists in either replica AND
        - It wasn't removed by the other replica
        
        This gives add-wins semantics: a concurrent add creates
        a tag the remover doesn't know about, so it survives.
        """
        # Process other's entries
        for element, other_tags in other._entries.items():
            if element not in self._entries:
                self._entries[element] = set()
            
            # Add tags we don't have
            self._entries[element] |= other_tags
        
        # Process other's delta removals (if available)
        for element, removed_tags in other._delta_removed.items():
            if element in self._entries:
                self._entries[element] -= removed_tags
        
        # Clean up empty entries
        self._entries = {e: tags for e, tags in self._entries.items() if tags}
        
        return self
    
    def delta(self) -> 'ORSet[T]':
        """Get delta with added and removed tags."""
        d = ORSet[T](self._replica_id)
        d._entries = {e: set(tags) for e, tags in self._delta_entries.items()}
        d._delta_removed = {e: set(tags) for e, tags in self._delta_removed.items()}
        return d
    
    def delta_reset(self) -> None:
        self._delta_entries.clear()
        self._delta_removed.clear()
    
    def clone(self) -> 'ORSet[T]':
        s = ORSet[T](self._replica_id)
        s._counter = self._counter
        s._entries = {e: set(tags) for e, tags in self._entries.items()}
        s._delta_entries = {e: set(tags) for e, tags in self._delta_entries.items()}
        s._delta_removed = {e: set(tags) for e, tags in self._delta_removed.items()}
        return s
    
    def to_dict(self) -> dict:
        return {
            "type": "ORSet",
            "replica_id": self._replica_id,
            "counter": self._counter,
            "entries": {str(e): list(tags) for e, tags in self._entries.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ORSet':
        s = cls(data["replica_id"])
        s._counter = data["counter"]
        s._entries = {e: set(tags) for e, tags in data["entries"].items()}
        return s
    
    def __repr__(self) -> str:
        return f"ORSet({self.value})"


class LWWSet(DeltaCRDT[FrozenSet[T]], Generic[T]):
    """
    Last-Writer-Wins Set.
    
    Each element has an add-timestamp and remove-timestamp.
    Element is present if add-timestamp > remove-timestamp.
    
    Simpler than ORSet but provides different semantics:
    - Concurrent add and remove: higher timestamp wins
    - Unlike ORSet which is add-wins
    
    Useful when you want timestamp-based resolution and
    can tolerate the "later remove wins" behavior.
    
    Example:
        >>> s = LWWSet[str]("node-a")
        >>> s.add("x")
        >>> s.remove("x")
        >>> "x" in s  # False (remove was later)
    """
    
    def __init__(self, replica_id: str):
        self._replica_id = replica_id
        self._adds: dict[T, HLCTimestamp] = {}
        self._removes: dict[T, HLCTimestamp] = {}
        self._last_ts: Optional[HLCTimestamp] = None
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> FrozenSet[T]:
        """Elements where add_timestamp > remove_timestamp."""
        result = set()
        for element, add_ts in self._adds.items():
            remove_ts = self._removes.get(element)
            if remove_ts is None or add_ts > remove_ts:
                result.add(element)
        return frozenset(result)
    
    def _next_timestamp(self) -> HLCTimestamp:
        self._last_ts = HLCTimestamp.now(self._replica_id, self._last_ts)
        return self._last_ts
    
    def add(self, element: T) -> 'LWWSet[T]':
        """Add element with current timestamp."""
        ts = self._next_timestamp()
        existing = self._adds.get(element)
        if existing is None or ts > existing:
            self._adds[element] = ts
        return self
    
    def remove(self, element: T) -> 'LWWSet[T]':
        """Remove element with current timestamp."""
        ts = self._next_timestamp()
        existing = self._removes.get(element)
        if existing is None or ts > existing:
            self._removes[element] = ts
        return self
    
    def __contains__(self, element: T) -> bool:
        if element not in self._adds:
            return False
        add_ts = self._adds[element]
        remove_ts = self._removes.get(element)
        return remove_ts is None or add_ts > remove_ts
    
    def __len__(self) -> int:
        return len(self.value)
    
    def merge(self, other: 'LWWSet[T]') -> 'LWWSet[T]':
        """Merge by keeping max timestamp for each element."""
        for element, ts in other._adds.items():
            existing = self._adds.get(element)
            if existing is None or ts > existing:
                self._adds[element] = ts
        
        for element, ts in other._removes.items():
            existing = self._removes.get(element)
            if existing is None or ts > existing:
                self._removes[element] = ts
        
        # Update our timestamp if needed
        if other._last_ts and (self._last_ts is None or other._last_ts > self._last_ts):
            self._last_ts = other._last_ts
        
        return self
    
    def delta(self) -> 'LWWSet[T]':
        return self.clone()
    
    def delta_reset(self) -> None:
        pass
    
    def clone(self) -> 'LWWSet[T]':
        s = LWWSet[T](self._replica_id)
        s._adds = dict(self._adds)
        s._removes = dict(self._removes)
        s._last_ts = self._last_ts
        return s
    
    def to_dict(self) -> dict:
        return {
            "type": "LWWSet",
            "replica_id": self._replica_id,
            "adds": {str(e): ts.to_dict() for e, ts in self._adds.items()},
            "removes": {str(e): ts.to_dict() for e, ts in self._removes.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LWWSet':
        s = cls(data["replica_id"])
        s._adds = {e: HLCTimestamp.from_dict(ts) for e, ts in data["adds"].items()}
        s._removes = {e: HLCTimestamp.from_dict(ts) for e, ts in data["removes"].items()}
        return s
    
    def __repr__(self) -> str:
        return f"LWWSet({self.value})"


# =============================================================================
# Maps
# =============================================================================

class ORMap(DeltaCRDT[Mapping[K, V]], Generic[K, V]):
    """
    Observed-Remove Map.
    
    A map where:
    - Keys can be added and removed (ORSet semantics)
    - Values are themselves CRDTs that merge
    
    When the same key is added concurrently with different values,
    the values are merged (not one-wins).
    
    The value_factory creates new CRDT instances for keys.
    
    Example:
        >>> # Map of user_id -> counter
        >>> def counter_factory():
        ...     return PNCounter("shared")
        >>> 
        >>> m = ORMap[str, PNCounter]("node-a", counter_factory)
        >>> m["alice"].increment(5)
        >>> m["bob"].increment(3)
    """
    
    def __init__(self, replica_id: str, value_factory: Callable[[], CRDT[V]]):
        self._replica_id = replica_id
        self._value_factory = value_factory
        self._keys = ORSet[K](replica_id)
        self._values: dict[K, CRDT[V]] = {}
    
    @property
    def replica_id(self) -> str:
        return self._replica_id
    
    @property
    def value(self) -> Mapping[K, V]:
        """Current map as a plain dict."""
        return {k: self._values[k].value for k in self._keys if k in self._values}
    
    def __getitem__(self, key: K) -> CRDT[V]:
        """
        Get or create the value for a key.
        
        Automatically adds the key if not present.
        """
        if key not in self._keys:
            self._keys.add(key)
        
        if key not in self._values:
            self._values[key] = self._value_factory()
        
        return self._values[key]
    
    def __setitem__(self, key: K, value: CRDT[V]) -> None:
        """Set the CRDT value for a key."""
        if key not in self._keys:
            self._keys.add(key)
        self._values[key] = value
    
    def __delitem__(self, key: K) -> None:
        """Remove a key (ORSet remove semantics)."""
        self._keys.remove(key)
        # Note: we keep the value for merge purposes
        # A concurrent update to the value will re-add the key
    
    def __contains__(self, key: K) -> bool:
        return key in self._keys
    
    def __len__(self) -> int:
        return len(self._keys)
    
    def keys(self) -> FrozenSet[K]:
        """Active keys."""
        return self._keys.value
    
    def merge(self, other: 'ORMap[K, V]') -> 'ORMap[K, V]':
        """
        Merge keys (ORSet merge) and values (CRDT merge).
        """
        self._keys.merge(other._keys)
        
        # Merge values for all keys that exist in either
        all_keys = set(self._values.keys()) | set(other._values.keys())
        for key in all_keys:
            if key in self._values and key in other._values:
                self._values[key].merge(other._values[key])
            elif key in other._values:
                self._values[key] = other._values[key].clone()
        
        return self
    
    def delta(self) -> 'ORMap[K, V]':
        d = ORMap[K, V](self._replica_id, self._value_factory)
        d._keys = self._keys.delta()
        d._values = {k: v.clone() for k, v in self._values.items()}
        return d
    
    def delta_reset(self) -> None:
        self._keys.delta_reset()
    
    def clone(self) -> 'ORMap[K, V]':
        m = ORMap[K, V](self._replica_id, self._value_factory)
        m._keys = self._keys.clone()
        m._values = {k: v.clone() for k, v in self._values.items()}
        return m
    
    def to_dict(self) -> dict:
        return {
            "type": "ORMap",
            "replica_id": self._replica_id,
            "keys": self._keys.to_dict(),
            "values": {str(k): v.to_dict() for k, v in self._values.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict, value_factory: Callable[[], CRDT]) -> 'ORMap':
        m = cls(data["replica_id"], value_factory)
        m._keys = ORSet.from_dict(data["keys"])
        # Values need type-specific deserialization
        return m
    
    def __repr__(self) -> str:
        return f"ORMap({dict(self.value)})"


# =============================================================================
# Utilities
# =============================================================================

def merge_all(*crdts: CRDT[T]) -> CRDT[T]:
    """
    Merge multiple CRDTs into one.
    
    Returns a new CRDT containing the merged state.
    The original CRDTs are not modified.
    """
    if not crdts:
        raise ValueError("At least one CRDT required")
    
    result = crdts[0].clone()
    for crdt in crdts[1:]:
        result.merge(crdt)
    
    return result


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base classes
    'CRDT',
    'DeltaCRDT',
    
    # Timestamp
    'HLCTimestamp',
    
    # Counters
    'GCounter',
    'PNCounter',
    
    # Registers
    'LWWRegister',
    'MVRegister',
    
    # Sets
    'GSet',
    'TwoPSet',
    'ORSet',
    'LWWSet',
    
    # Maps
    'ORMap',
    
    # Utilities
    'merge_all',
]
