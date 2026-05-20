"""
Lattice: Conflict-Free Replicated Data Types (CRDTs)

Data structures for building distributed, eventually-consistent systems.
All replicas converge automatically without coordination.

Quick Start:
    >>> from lattice import GCounter, ORSet, PNCounter
    >>> 
    >>> # Counter that can only grow
    >>> views = GCounter("server-1")
    >>> views.increment(100)
    >>> 
    >>> # Counter that can increment and decrement
    >>> score = PNCounter("server-1")
    >>> score.increment(10)
    >>> score.decrement(3)
    >>> 
    >>> # Set with add/remove (add wins on conflict)
    >>> cart = ORSet[str]("device-1")
    >>> cart.add("milk")
    >>> cart.remove("milk")
    >>> cart.add("bread")

Merging replicas:
    >>> node_a = GCounter("node-a")
    >>> node_b = GCounter("node-b")
    >>> 
    >>> node_a.increment(5)
    >>> node_b.increment(3)
    >>> 
    >>> node_a.merge(node_b)
    >>> print(node_a.value)  # 8

Available CRDTs:
    Counters: GCounter, PNCounter
    Registers: LWWRegister, MVRegister
    Sets: GSet, TwoPSet, ORSet, LWWSet
    Maps: ORMap
"""

from .lattice import (
    # Timestamps
    HLCTimestamp,
    
    # Base
    CRDT,
    DeltaCRDT,
    
    # Counters
    GCounter,
    PNCounter,
    
    # Registers
    LWWRegister,
    MVRegister,
    
    # Sets
    GSet,
    TwoPSet,
    ORSet,
    LWWSet,
    
    # Maps
    ORMap,
    
    # Utilities
    merge_all,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Timestamps
    'HLCTimestamp',
    
    # Base
    'CRDT',
    'DeltaCRDT',
    
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
