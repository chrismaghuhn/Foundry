"""
Chrono: Distributed Logical Clock Library

Implements multiple clock algorithms for distributed systems:
- Lamport Timestamps: Simple scalar logical clocks
- Vector Clocks: Full causality tracking (detects concurrent events)
- Hybrid Logical Clocks (HLC): Physical time + logical for bounded metadata

Background:
    In distributed systems, wall clock time is unreliable due to clock drift,
    NTP adjustments, and leap seconds. Logical clocks provide causal ordering
    guarantees regardless of physical time synchronization.

Key Concepts:
    - Happens-Before (→): Event A happens-before B if A could have caused B
    - Concurrent (||): Events are concurrent if neither happened-before the other
    - Causality: If A → B, then clock(A) < clock(B)

Clock Comparison:
    | Type     | Size    | Concurrent Detection | Physical Time |
    |----------|---------|---------------------|---------------|
    | Lamport  | O(1)    | No                  | No            |
    | Vector   | O(n)    | Yes                 | No            |
    | HLC      | O(1)    | No                  | Yes (bounded) |

Thread Safety:
    All clock implementations use asyncio.Lock for thread-safe updates.
    For high-throughput scenarios, consider per-thread clocks with periodic sync.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import time
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Generic, TypeVar, Protocol
from functools import total_ordering
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# Core Types
# =============================================================================

class Ordering(Enum):
    """Result of comparing two clock timestamps."""
    BEFORE = auto()      # A happened before B
    AFTER = auto()       # A happened after B
    EQUAL = auto()       # A and B are the same event
    CONCURRENT = auto()  # A and B are causally independent


T = TypeVar('T', bound='Timestamp')


class Timestamp(Protocol):
    """Protocol for all timestamp types."""
    
    def compare(self, other: 'Timestamp') -> Ordering:
        """Compare this timestamp with another."""
        ...
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for network transmission."""
        ...
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Timestamp':
        """Deserialize from bytes."""
        ...


# =============================================================================
# Lamport Timestamps
# =============================================================================

@total_ordering
@dataclass(frozen=True, slots=True)
class LamportTimestamp:
    """
    Lamport Logical Clock Timestamp
    
    The simplest logical clock. A single counter that increments on:
    1. Local events
    2. Sending messages
    3. Receiving messages (max of local and received + 1)
    
    Properties:
    - If A → B, then L(A) < L(B)  (causality implies ordering)
    - If L(A) < L(B), A might or might not have caused B (not bidirectional!)
    - Cannot detect concurrent events
    
    Use when: You need total ordering and don't care about concurrency detection.
    """
    counter: int
    node_id: str = ""  # Tiebreaker for total ordering
    
    def __lt__(self, other: 'LamportTimestamp') -> bool:
        if self.counter != other.counter:
            return self.counter < other.counter
        return self.node_id < other.node_id
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LamportTimestamp):
            return NotImplemented
        return self.counter == other.counter and self.node_id == other.node_id
    
    def compare(self, other: 'LamportTimestamp') -> Ordering:
        """Compare timestamps. Note: cannot detect true concurrency."""
        if self == other:
            return Ordering.EQUAL
        elif self < other:
            return Ordering.BEFORE
        else:
            return Ordering.AFTER
    
    def to_bytes(self) -> bytes:
        """Serialize: 8-byte counter + node_id string."""
        counter_bytes = self.counter.to_bytes(8, 'big')
        node_bytes = self.node_id.encode('utf-8')
        return counter_bytes + len(node_bytes).to_bytes(2, 'big') + node_bytes
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LamportTimestamp':
        counter = int.from_bytes(data[:8], 'big')
        node_len = int.from_bytes(data[8:10], 'big')
        node_id = data[10:10+node_len].decode('utf-8')
        return cls(counter=counter, node_id=node_id)
    
    def __repr__(self) -> str:
        return f"L({self.counter}@{self.node_id})"


class LamportClock:
    """
    Lamport Logical Clock
    
    Thread-safe implementation with async support.
    
    Usage:
        clock = LamportClock("node-1")
        ts1 = await clock.tick()        # Local event
        ts2 = await clock.send()        # Sending message
        await clock.receive(remote_ts)  # Receiving message
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._counter = 0
        self._lock = asyncio.Lock()
    
    async def tick(self) -> LamportTimestamp:
        """
        Record a local event.
        
        Increments the counter and returns the new timestamp.
        """
        async with self._lock:
            self._counter += 1
            return LamportTimestamp(self._counter, self.node_id)
    
    async def send(self) -> LamportTimestamp:
        """
        Prepare timestamp for sending a message.
        
        Same as tick() - the sender includes this in the message.
        """
        return await self.tick()
    
    async def receive(self, remote: LamportTimestamp) -> LamportTimestamp:
        """
        Process received timestamp.
        
        Updates local clock to max(local, remote) + 1.
        """
        async with self._lock:
            self._counter = max(self._counter, remote.counter) + 1
            return LamportTimestamp(self._counter, self.node_id)
    
    async def current(self) -> LamportTimestamp:
        """Get current timestamp without incrementing."""
        async with self._lock:
            return LamportTimestamp(self._counter, self.node_id)
    
    def current_sync(self) -> LamportTimestamp:
        """Synchronous version for non-async contexts."""
        return LamportTimestamp(self._counter, self.node_id)


# =============================================================================
# Vector Clocks
# =============================================================================

@dataclass
class VectorTimestamp:
    """
    Vector Clock Timestamp
    
    A vector of counters, one per node in the system. Captures full
    causality information and can detect concurrent events.
    
    Properties:
    - A → B iff V(A) < V(B) (all components ≤, at least one <)
    - A || B iff neither V(A) < V(B) nor V(B) < V(A)
    - Size grows with number of nodes (O(n) metadata)
    
    Use when: You need to detect concurrent events (conflict resolution, CRDTs).
    """
    vector: dict[str, int] = field(default_factory=dict)
    
    def __getitem__(self, node_id: str) -> int:
        return self.vector.get(node_id, 0)
    
    def __setitem__(self, node_id: str, value: int) -> None:
        self.vector[node_id] = value
    
    def increment(self, node_id: str) -> 'VectorTimestamp':
        """Return new timestamp with incremented component."""
        new_vector = self.vector.copy()
        new_vector[node_id] = new_vector.get(node_id, 0) + 1
        return VectorTimestamp(new_vector)
    
    def merge(self, other: 'VectorTimestamp') -> 'VectorTimestamp':
        """
        Merge two vector clocks (component-wise max).
        
        Used when receiving a message to incorporate remote knowledge.
        """
        all_nodes = set(self.vector.keys()) | set(other.vector.keys())
        merged = {
            node: max(self[node], other[node])
            for node in all_nodes
        }
        return VectorTimestamp(merged)
    
    def compare(self, other: 'VectorTimestamp') -> Ordering:
        """
        Compare two vector timestamps.
        
        Returns:
            BEFORE: self happened before other (self < other)
            AFTER: self happened after other (self > other)
            EQUAL: timestamps are identical
            CONCURRENT: neither happened before the other
        """
        all_nodes = set(self.vector.keys()) | set(other.vector.keys())
        
        less_or_equal = True
        greater_or_equal = True
        strictly_less = False
        strictly_greater = False
        
        for node in all_nodes:
            self_val = self[node]
            other_val = other[node]
            
            if self_val < other_val:
                strictly_less = True
                greater_or_equal = False
            elif self_val > other_val:
                strictly_greater = True
                less_or_equal = False
        
        if not strictly_less and not strictly_greater:
            return Ordering.EQUAL
        elif less_or_equal and strictly_less:
            return Ordering.BEFORE
        elif greater_or_equal and strictly_greater:
            return Ordering.AFTER
        else:
            return Ordering.CONCURRENT
    
    def happens_before(self, other: 'VectorTimestamp') -> bool:
        """Check if self happened before other."""
        return self.compare(other) == Ordering.BEFORE
    
    def concurrent_with(self, other: 'VectorTimestamp') -> bool:
        """Check if self is concurrent with other."""
        return self.compare(other) == Ordering.CONCURRENT
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        encoded = json.dumps(self.vector, sort_keys=True).encode('utf-8')
        return len(encoded).to_bytes(4, 'big') + encoded
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'VectorTimestamp':
        length = int.from_bytes(data[:4], 'big')
        vector = json.loads(data[4:4+length].decode('utf-8'))
        return cls(vector)
    
    def __repr__(self) -> str:
        items = ", ".join(f"{k}:{v}" for k, v in sorted(self.vector.items()))
        return f"V({items})"
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.vector.items())))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorTimestamp):
            return NotImplemented
        return self.compare(other) == Ordering.EQUAL


class VectorClock:
    """
    Vector Clock Implementation
    
    Maintains a vector of counters for causality tracking.
    
    Usage:
        clock = VectorClock("node-1")
        ts1 = await clock.tick()         # Local event
        ts2 = await clock.send()         # For outgoing message
        ts3 = await clock.receive(remote) # Process incoming
    """
    
    def __init__(self, node_id: str, initial: VectorTimestamp | None = None):
        self.node_id = node_id
        self._timestamp = initial or VectorTimestamp()
        self._lock = asyncio.Lock()
    
    async def tick(self) -> VectorTimestamp:
        """Record a local event."""
        async with self._lock:
            self._timestamp = self._timestamp.increment(self.node_id)
            return VectorTimestamp(self._timestamp.vector.copy())
    
    async def send(self) -> VectorTimestamp:
        """Prepare timestamp for sending. Same as tick."""
        return await self.tick()
    
    async def receive(self, remote: VectorTimestamp) -> VectorTimestamp:
        """
        Process received timestamp.
        
        Merges remote knowledge and increments local counter.
        """
        async with self._lock:
            self._timestamp = self._timestamp.merge(remote)
            self._timestamp = self._timestamp.increment(self.node_id)
            return VectorTimestamp(self._timestamp.vector.copy())
    
    async def current(self) -> VectorTimestamp:
        """Get current timestamp without incrementing."""
        async with self._lock:
            return VectorTimestamp(self._timestamp.vector.copy())
    
    def current_sync(self) -> VectorTimestamp:
        """Synchronous version."""
        return VectorTimestamp(self._timestamp.vector.copy())


# =============================================================================
# Hybrid Logical Clocks (HLC)
# =============================================================================

@total_ordering
@dataclass(frozen=True, slots=True)
class HLCTimestamp:
    """
    Hybrid Logical Clock Timestamp
    
    Combines physical time with logical counter to get the best of both:
    - Bounded size (O(1) like Lamport)
    - Close to wall clock time (useful for TTL, debugging)
    - Causal ordering guarantees
    
    Structure:
        - physical: Wall clock time in milliseconds
        - logical: Counter for events at same physical time
        - node_id: Tiebreaker for total ordering
    
    Properties:
    - l.physical ≤ real_time + ε (bounded drift from physical time)
    - If A → B, then HLC(A) < HLC(B)
    - Provides total ordering with physical time proximity
    
    Use when: You need Lamport-like simplicity but want timestamps
    that are meaningful in wall-clock terms.
    """
    physical: int  # Milliseconds since epoch
    logical: int   # Logical counter within same physical time
    node_id: str = ""
    
    def __lt__(self, other: 'HLCTimestamp') -> bool:
        if self.physical != other.physical:
            return self.physical < other.physical
        if self.logical != other.logical:
            return self.logical < other.logical
        return self.node_id < other.node_id
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HLCTimestamp):
            return NotImplemented
        return (
            self.physical == other.physical and
            self.logical == other.logical and
            self.node_id == other.node_id
        )
    
    def compare(self, other: 'HLCTimestamp') -> Ordering:
        if self == other:
            return Ordering.EQUAL
        elif self < other:
            return Ordering.BEFORE
        else:
            return Ordering.AFTER
    
    def to_bytes(self) -> bytes:
        """Serialize: 8-byte physical + 4-byte logical + node_id."""
        phys = self.physical.to_bytes(8, 'big')
        log = self.logical.to_bytes(4, 'big')
        node = self.node_id.encode('utf-8')
        return phys + log + len(node).to_bytes(2, 'big') + node
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'HLCTimestamp':
        physical = int.from_bytes(data[:8], 'big')
        logical = int.from_bytes(data[8:12], 'big')
        node_len = int.from_bytes(data[12:14], 'big')
        node_id = data[14:14+node_len].decode('utf-8')
        return cls(physical=physical, logical=logical, node_id=node_id)
    
    def to_datetime_str(self) -> str:
        """Convert to ISO datetime string (approximate)."""
        from datetime import datetime
        dt = datetime.fromtimestamp(self.physical / 1000)
        return f"{dt.isoformat()}.{self.logical:04d}"
    
    def __repr__(self) -> str:
        return f"HLC({self.physical}.{self.logical}@{self.node_id})"


class HybridLogicalClock:
    """
    Hybrid Logical Clock Implementation
    
    The HLC algorithm ensures that:
    1. Timestamps are always monotonically increasing
    2. Physical component stays close to wall clock
    3. Logical component handles events at same physical time
    
    Algorithm (on tick/send):
        l' = max(l.physical, wall_time)
        if l' == l.physical:
            c' = l.logical + 1
        else:
            c' = 0
        l = (l', c')
    
    Algorithm (on receive):
        l' = max(l.physical, m.physical, wall_time)
        if l' == l.physical == m.physical:
            c' = max(l.logical, m.logical) + 1
        elif l' == l.physical:
            c' = l.logical + 1
        elif l' == m.physical:
            c' = m.logical + 1
        else:
            c' = 0
        l = (l', c')
    """
    
    def __init__(
        self, 
        node_id: str,
        max_drift_ms: int = 60000,  # Max allowed drift from wall clock
        time_source: callable = None  # For testing
    ):
        self.node_id = node_id
        self.max_drift_ms = max_drift_ms
        self._time_source = time_source or (lambda: int(time.time() * 1000))
        self._physical = 0
        self._logical = 0
        self._lock = asyncio.Lock()
    
    def _wall_time(self) -> int:
        """Get current wall clock time in milliseconds."""
        return self._time_source()
    
    async def tick(self) -> HLCTimestamp:
        """
        Record a local event.
        
        Updates clock and returns new timestamp.
        """
        async with self._lock:
            wall = self._wall_time()
            
            if wall > self._physical:
                # Wall clock advanced - reset logical
                self._physical = wall
                self._logical = 0
            else:
                # Same or earlier wall time - increment logical
                self._logical += 1
            
            # Check for excessive drift
            if self._physical - wall > self.max_drift_ms:
                logger.warning(
                    f"HLC drift exceeded: {self._physical - wall}ms > {self.max_drift_ms}ms"
                )
            
            return HLCTimestamp(self._physical, self._logical, self.node_id)
    
    async def send(self) -> HLCTimestamp:
        """Prepare timestamp for sending. Same as tick."""
        return await self.tick()
    
    async def receive(self, remote: HLCTimestamp) -> HLCTimestamp:
        """
        Process received timestamp.
        
        Merges with remote timestamp while maintaining monotonicity.
        """
        async with self._lock:
            wall = self._wall_time()
            
            # Take max of all three times
            max_physical = max(self._physical, remote.physical, wall)
            
            if max_physical == self._physical == remote.physical:
                # All same - take max logical + 1
                new_logical = max(self._logical, remote.logical) + 1
            elif max_physical == self._physical:
                # Local physical is max
                new_logical = self._logical + 1
            elif max_physical == remote.physical:
                # Remote physical is max
                new_logical = remote.logical + 1
            else:
                # Wall clock is max - reset logical
                new_logical = 0
            
            self._physical = max_physical
            self._logical = new_logical
            
            # Check for excessive drift
            if self._physical - wall > self.max_drift_ms:
                logger.warning(
                    f"HLC drift exceeded after receive: {self._physical - wall}ms"
                )
            
            return HLCTimestamp(self._physical, self._logical, self.node_id)
    
    async def current(self) -> HLCTimestamp:
        """Get current timestamp without incrementing."""
        async with self._lock:
            return HLCTimestamp(self._physical, self._logical, self.node_id)
    
    def current_sync(self) -> HLCTimestamp:
        """Synchronous version."""
        return HLCTimestamp(self._physical, self._logical, self.node_id)


# =============================================================================
# Event Tracking
# =============================================================================

@dataclass
class Event(Generic[T]):
    """
    An event with an associated timestamp.
    
    Generic over timestamp type for flexibility.
    """
    id: str
    timestamp: T
    node_id: str
    data: Any = None
    
    def happens_before(self, other: 'Event[T]') -> bool:
        """Check if this event happened before another."""
        ordering = self.timestamp.compare(other.timestamp)
        return ordering == Ordering.BEFORE
    
    def concurrent_with(self, other: 'Event[T]') -> bool:
        """Check if events are concurrent (only meaningful for vector clocks)."""
        ordering = self.timestamp.compare(other.timestamp)
        return ordering == Ordering.CONCURRENT


class EventLog(Generic[T]):
    """
    Thread-safe event log with ordering.
    
    Maintains events in causal order when possible.
    """
    
    def __init__(self):
        self._events: list[Event[T]] = []
        self._lock = asyncio.Lock()
    
    async def append(self, event: Event[T]) -> None:
        """Add event to log."""
        async with self._lock:
            self._events.append(event)
    
    async def get_ordered(self) -> list[Event[T]]:
        """Get events sorted by timestamp."""
        async with self._lock:
            return sorted(
                self._events,
                key=lambda e: (
                    getattr(e.timestamp, 'physical', 0) or 
                    getattr(e.timestamp, 'counter', 0) or
                    sum(getattr(e.timestamp, 'vector', {}).values())
                )
            )
    
    async def find_concurrent(self) -> list[tuple[Event[T], Event[T]]]:
        """Find all pairs of concurrent events (for vector clocks)."""
        async with self._lock:
            concurrent_pairs = []
            for i, e1 in enumerate(self._events):
                for e2 in self._events[i+1:]:
                    if e1.timestamp.compare(e2.timestamp) == Ordering.CONCURRENT:
                        concurrent_pairs.append((e1, e2))
            return concurrent_pairs
    
    async def visualize_dag(self) -> str:
        """
        Generate ASCII visualization of event causality.
        
        Returns a string showing the happens-before DAG.
        """
        events = await self.get_ordered()
        if not events:
            return "Empty log"
        
        lines = ["Event Causality Graph:", "=" * 40]
        
        for i, event in enumerate(events):
            lines.append(f"{i+1}. [{event.node_id}] {event.id}: {event.timestamp}")
            
            # Find what this event depends on
            deps = []
            for j, earlier in enumerate(events[:i]):
                ordering = earlier.timestamp.compare(event.timestamp)
                if ordering == Ordering.BEFORE:
                    deps.append(j + 1)
            
            if deps:
                lines.append(f"   └─ depends on: {deps}")
        
        return "\n".join(lines)


# =============================================================================
# Clock Factory
# =============================================================================

class ClockType(Enum):
    """Available clock types."""
    LAMPORT = "lamport"
    VECTOR = "vector"
    HLC = "hlc"


def create_clock(
    clock_type: ClockType,
    node_id: str,
    **kwargs
) -> LamportClock | VectorClock | HybridLogicalClock:
    """
    Factory function to create clocks.
    
    Args:
        clock_type: Type of clock to create
        node_id: Unique identifier for this node
        **kwargs: Additional arguments for specific clock types
    
    Returns:
        Appropriate clock instance
    """
    if clock_type == ClockType.LAMPORT:
        return LamportClock(node_id)
    elif clock_type == ClockType.VECTOR:
        return VectorClock(node_id, **kwargs)
    elif clock_type == ClockType.HLC:
        return HybridLogicalClock(node_id, **kwargs)
    else:
        raise ValueError(f"Unknown clock type: {clock_type}")


# =============================================================================
# Message Wrapper
# =============================================================================

@dataclass
class Message(Generic[T]):
    """
    A message with embedded timestamp for distributed communication.
    
    Use this to wrap messages sent between nodes to automatically
    propagate clock information.
    """
    payload: Any
    timestamp: T
    sender_id: str
    
    def to_bytes(self) -> bytes:
        """Serialize message for network transmission."""
        payload_bytes = json.dumps(self.payload).encode('utf-8')
        ts_bytes = self.timestamp.to_bytes()
        sender_bytes = self.sender_id.encode('utf-8')
        
        return (
            len(payload_bytes).to_bytes(4, 'big') + payload_bytes +
            len(ts_bytes).to_bytes(4, 'big') + ts_bytes +
            len(sender_bytes).to_bytes(2, 'big') + sender_bytes
        )
    
    @classmethod
    def from_bytes(
        cls, 
        data: bytes,
        timestamp_cls: type[T]
    ) -> 'Message[T]':
        """Deserialize message."""
        offset = 0
        
        payload_len = int.from_bytes(data[offset:offset+4], 'big')
        offset += 4
        payload = json.loads(data[offset:offset+payload_len].decode('utf-8'))
        offset += payload_len
        
        ts_len = int.from_bytes(data[offset:offset+4], 'big')
        offset += 4
        timestamp = timestamp_cls.from_bytes(data[offset:offset+ts_len])
        offset += ts_len
        
        sender_len = int.from_bytes(data[offset:offset+2], 'big')
        offset += 2
        sender_id = data[offset:offset+sender_len].decode('utf-8')
        
        return cls(payload=payload, timestamp=timestamp, sender_id=sender_id)


# =============================================================================
# Causal Broadcast (Bonus)
# =============================================================================

class CausalBroadcaster:
    """
    Causal broadcast using vector clocks.
    
    Ensures messages are delivered in causal order:
    - If send(m1) → send(m2), then deliver(m1) → deliver(m2) at all nodes
    
    This is useful for distributed systems that need consistency
    without total ordering.
    """
    
    def __init__(self, node_id: str, peers: list[str]):
        self.node_id = node_id
        self.peers = peers
        self.clock = VectorClock(node_id)
        self._pending: list[Message[VectorTimestamp]] = []
        self._delivered: set[str] = set()
        self._lock = asyncio.Lock()
    
    async def broadcast(self, payload: Any) -> Message[VectorTimestamp]:
        """
        Prepare a message for broadcast.
        
        Returns the message to be sent to all peers.
        """
        ts = await self.clock.send()
        msg_id = hashlib.sha256(
            f"{self.node_id}:{ts}:{payload}".encode()
        ).hexdigest()[:16]
        
        return Message(
            payload={"id": msg_id, "data": payload},
            timestamp=ts,
            sender_id=self.node_id
        )
    
    async def receive(
        self, 
        message: Message[VectorTimestamp]
    ) -> list[Message[VectorTimestamp]]:
        """
        Receive a message and return deliverable messages.
        
        Messages are buffered until all causally preceding messages
        have been delivered.
        
        Returns:
            List of messages ready for delivery (in causal order)
        """
        async with self._lock:
            msg_id = message.payload.get("id", "")
            
            if msg_id in self._delivered:
                return []  # Already delivered
            
            self._pending.append(message)
            
            # Try to deliver pending messages
            deliverable = []
            changed = True
            
            while changed:
                changed = False
                for msg in list(self._pending):
                    if self._can_deliver(msg):
                        self._pending.remove(msg)
                        self._delivered.add(msg.payload.get("id", ""))
                        deliverable.append(msg)
                        # Update our clock
                        await self.clock.receive(msg.timestamp)
                        changed = True
            
            return deliverable
    
    def _can_deliver(self, message: Message[VectorTimestamp]) -> bool:
        """
        Check if message can be delivered.
        
        A message can be delivered when all causally preceding
        messages have been delivered. This is checked by comparing
        the message's vector clock against our current clock.
        """
        our_clock = self.clock.current_sync()
        msg_ts = message.timestamp
        sender = message.sender_id
        
        # For each node in the message timestamp
        for node, count in msg_ts.vector.items():
            if node == sender:
                # Sender's component should be exactly one more than ours
                if count > our_clock[node] + 1:
                    return False  # Missing messages from sender
            else:
                # Other components should be <= ours
                if count > our_clock[node]:
                    return False  # Missing messages from other nodes
        
        return True


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core types
    'Ordering',
    'Timestamp',
    
    # Lamport
    'LamportTimestamp',
    'LamportClock',
    
    # Vector
    'VectorTimestamp',
    'VectorClock',
    
    # HLC
    'HLCTimestamp',
    'HybridLogicalClock',
    
    # Utilities
    'Event',
    'EventLog',
    'Message',
    'ClockType',
    'create_clock',
    
    # Causal broadcast
    'CausalBroadcaster',
]
