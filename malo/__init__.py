"""
MALO: Merkle Append-Only Log

Tamper-evident logging using Merkle trees with inclusion and consistency proofs.

Quick Start:
    >>> from malo import AuditLog
    >>> import asyncio
    >>> 
    >>> async def main():
    ...     log = AuditLog()
    ...     entry = await log.append(b"Event data")
    ...     proof = log.get_proof(entry.index)
    ...     assert AuditLog.verify(b"Event data", proof)
    >>> 
    >>> asyncio.run(main())

For auditors verifying proofs offline:
    >>> from malo import MerkleVerifier, InclusionProof
    >>> 
    >>> proof_data = {...}  # Received from server
    >>> proof = InclusionProof.from_dict(proof_data)
    >>> is_valid = MerkleVerifier.verify_inclusion(b"Original data", proof)

Key Concepts:
    - MerkleLog: Low-level append-only log with frontier optimization
    - AuditLog: High-level API for audit logging
    - InclusionProof: Proves an entry exists at specific index
    - ConsistencyProof: Proves new log extends old log (append-only property)
"""

from .malo import (
    # Core functions
    hash_leaf,
    hash_nodes,
    
    # Types
    MerkleRoot,
    InclusionProof,
    ConsistencyProof,
    LogEntry,
    
    # Core classes
    MerkleLog,
    MerkleVerifier,
    AuditLog,
    
    # Storage interface
    LogStorage,
    InMemoryStorage,
    
    # Utilities
    tree_height,
    tree_size,
    is_power_of_two,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Functions
    'hash_leaf',
    'hash_nodes',
    
    # Types
    'MerkleRoot',
    'InclusionProof', 
    'ConsistencyProof',
    'LogEntry',
    
    # Core
    'MerkleLog',
    'MerkleVerifier',
    'AuditLog',
    
    # Storage
    'LogStorage',
    'InMemoryStorage',
    
    # Utilities
    'tree_height',
    'tree_size', 
    'is_power_of_two',
]
