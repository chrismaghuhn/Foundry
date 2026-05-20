"""
Chrono: Distributed Logical Clock Library

Implement proper causality tracking in distributed systems.

Quick Start:
    >>> from chrono import LamportClock, VectorClock, HybridLogicalClock
    >>> 
    >>> # Simple ordering
    >>> clock = LamportClock("node-1")
    >>> ts1 = await clock.tick()
    >>> ts2 = await clock.send()
    >>> 
    >>> # Concurrency detection
    >>> vclock = VectorClock("node-1")
    >>> ts = await vclock.tick()
    >>> if ts.concurrent_with(other_ts):
    ...     print("Conflict detected!")
    >>> 
    >>> # Physical time + logical ordering
    >>> hlc = HybridLogicalClock("node-1")
    >>> ts = await hlc.tick()
    >>> print(ts.to_datetime_str())
"""

from .chrono import (
    # Core types
    Ordering,
    Timestamp,
    
    # Lamport
    LamportTimestamp,
    LamportClock,
    
    # Vector
    VectorTimestamp,
    VectorClock,
    
    # HLC
    HLCTimestamp,
    HybridLogicalClock,
    
    # Utilities
    Event,
    EventLog,
    Message,
    ClockType,
    create_clock,
    
    # Causal broadcast
    CausalBroadcaster,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core
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
    
    # Broadcast
    'CausalBroadcaster',
]
