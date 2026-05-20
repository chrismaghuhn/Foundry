"""
MALO: Merkle Append-Only Log

A cryptographically verifiable append-only log using Merkle trees.
Provides tamper-evidence for audit logs, event streams, and compliance records.

Key Features:
- Inclusion proofs: Prove an entry exists at a specific index
- Consistency proofs: Prove new log extends old log without modification
- Efficient frontier-based storage: O(log n) space for tree state
- Batch operations: Amortized O(1) per entry for bulk appends

Architecture:
    The log maintains a "frontier" — the minimal set of nodes needed to
    compute the next root. For an append-only Merkle tree, this is the
    rightmost node at each level where the subtree is complete.
    
    Example frontier for log with 5 entries:
    
              [root]
             /      \\
          [A]        [B]      <- B is in frontier (incomplete right subtree)
         /   \\      /
       [0,1] [2,3] [4]        <- [0,1], [2,3] are complete, [4] is in frontier
    
    Frontier = [hash(4), hash(2,3), hash(A)]  (3 nodes for 5 entries)

Tree Construction:
    We use a "perfect" binary Merkle tree where:
    - Leaves are at the bottom
    - Internal nodes are hash(left || right)
    - If right child is missing, we hash(left || left) [RFC 6962 style]
    
    This ensures the tree is always complete and deterministic.

Proof Types:
    1. Inclusion Proof: Path from leaf to root
       - Verifier can recompute root and compare
       - O(log n) hashes in proof
    
    2. Consistency Proof: Proves tree(n) is prefix of tree(m)
       - Uses nodes from both old and new tree
       - O(log n) hashes in proof
       - Critical for "append-only" guarantee

Thread Safety:
    - Appends are serialized via asyncio.Lock
    - Reads (proofs, verification) are lock-free
    - Root access is atomic (single assignment)

References:
    - RFC 6962: Certificate Transparency
    - RFC 9162: Certificate Transparency Version 2.0
    - Crosby & Wallach: "Efficient Data Structures for Tamper-Evident Logging"

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Generic, TypeVar, Callable, Iterator
from functools import cached_property
import struct
import time

logger = logging.getLogger(__name__)


# =============================================================================
# Core Types
# =============================================================================

# Domain separator for leaf vs internal nodes (prevents second preimage attacks)
LEAF_PREFIX = b'\x00'
NODE_PREFIX = b'\x01'


def hash_leaf(data: bytes) -> bytes:
    """
    Hash a leaf node with domain separation.
    
    Using a prefix prevents attacks where an attacker crafts data
    that hashes to the same value as an internal node.
    """
    return hashlib.sha256(LEAF_PREFIX + data).digest()


def hash_nodes(left: bytes, right: bytes) -> bytes:
    """
    Hash two child nodes into parent.
    
    Uses domain separation prefix to distinguish from leaf hashes.
    """
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


@dataclass(frozen=True, slots=True)
class MerkleRoot:
    """
    Immutable Merkle root with metadata.
    
    The root alone is sufficient to verify any inclusion proof.
    The size is needed for consistency proofs.
    """
    hash: bytes
    size: int  # Number of entries when this root was computed
    timestamp: float = field(default_factory=time.time)
    
    def hex(self) -> str:
        """Root hash as hex string."""
        return self.hash.hex()
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MerkleRoot):
            return NotImplemented
        return self.hash == other.hash and self.size == other.size
    
    def __repr__(self) -> str:
        return f"MerkleRoot({self.hex()[:16]}..., size={self.size})"


@dataclass(frozen=True, slots=True)
class InclusionProof:
    """
    Proof that an entry exists at a specific index in the log.
    
    The proof is a list of sibling hashes from leaf to root.
    Each entry includes:
    - hash: The sibling hash
    - is_left: Whether the sibling is on the left
    
    Verification:
    1. Start with hash of the entry
    2. For each sibling in proof:
       - If sibling is_left: hash = hash_nodes(sibling, hash)
       - Else: hash = hash_nodes(hash, sibling)
    3. Final hash should equal the root
    """
    index: int
    entry_hash: bytes
    siblings: tuple[tuple[bytes, bool], ...]  # (hash, is_left) pairs
    root: MerkleRoot
    
    def to_dict(self) -> dict:
        """Serialize for JSON transport."""
        return {
            "index": self.index,
            "entry_hash": self.entry_hash.hex(),
            "siblings": [(h.hex(), is_left) for h, is_left in self.siblings],
            "root_hash": self.root.hex(),
            "root_size": self.root.size,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'InclusionProof':
        """Deserialize from JSON."""
        return cls(
            index=data["index"],
            entry_hash=bytes.fromhex(data["entry_hash"]),
            siblings=tuple(
                (bytes.fromhex(h), is_left) 
                for h, is_left in data["siblings"]
            ),
            root=MerkleRoot(
                hash=bytes.fromhex(data["root_hash"]),
                size=data["root_size"]
            )
        )


@dataclass(frozen=True, slots=True)
class ConsistencyProof:
    """
    Proof that a newer tree is an extension of an older tree.
    
    This proves that:
    1. All entries in the old tree exist unchanged in the new tree
    2. The old tree is a prefix of the new tree
    3. No entries were modified, deleted, or reordered
    
    The proof contains nodes needed to:
    1. Reconstruct the old root from shared subtrees
    2. Show those subtrees exist in the new tree
    """
    old_size: int
    new_size: int
    old_root: MerkleRoot
    new_root: MerkleRoot
    proof_nodes: tuple[bytes, ...]
    
    def to_dict(self) -> dict:
        """Serialize for JSON transport."""
        return {
            "old_size": self.old_size,
            "new_size": self.new_size,
            "old_root_hash": self.old_root.hex(),
            "new_root_hash": self.new_root.hex(),
            "proof_nodes": [h.hex() for h in self.proof_nodes],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConsistencyProof':
        """Deserialize from JSON."""
        return cls(
            old_size=data["old_size"],
            new_size=data["new_size"],
            old_root=MerkleRoot(
                hash=bytes.fromhex(data["old_root_hash"]),
                size=data["old_size"]
            ),
            new_root=MerkleRoot(
                hash=bytes.fromhex(data["new_root_hash"]),
                size=data["new_size"]
            ),
            proof_nodes=tuple(bytes.fromhex(h) for h in data["proof_nodes"])
        )


# =============================================================================
# Tree Mathematics
# =============================================================================

def tree_size(n: int) -> int:
    """
    Compute the number of nodes in a perfect Merkle tree with n leaves.
    
    For n leaves, we have:
    - n leaf nodes
    - n-1 internal nodes (for n > 0)
    - Total: 2n - 1 nodes
    """
    if n == 0:
        return 0
    return 2 * n - 1


def tree_height(n: int) -> int:
    """
    Compute the height of a Merkle tree with n leaves.
    
    Height is ceil(log2(n)) for n > 0.
    A single leaf has height 0.
    """
    if n <= 1:
        return 0
    return (n - 1).bit_length()


def is_power_of_two(n: int) -> bool:
    """Check if n is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def largest_power_of_two_less_than(n: int) -> int:
    """
    Find largest k such that 2^k < n.
    
    This is used to split trees optimally.
    For n=5: returns 4 (split into 4 + 1)
    For n=7: returns 4 (split into 4 + 3)
    """
    if n <= 1:
        return 0
    k = 1
    while k * 2 < n:
        k *= 2
    return k


# =============================================================================
# Frontier-Based Merkle Tree
# =============================================================================

class MerkleLog:
    """
    Append-only Merkle log with efficient frontier-based storage.
    
    Instead of storing the entire tree, we maintain:
    1. All leaf hashes (for proof generation)
    2. The "frontier" - nodes needed to compute next root
    3. Historical roots (for consistency proofs)
    
    The frontier represents partially-complete subtrees.
    When we append, we may complete subtrees and collapse the frontier.
    
    Example evolution:
    
    n=1: frontier = [h0]
    n=2: frontier = [hash(h0,h1)]  # Subtree complete, collapsed
    n=3: frontier = [h2, hash(h0,h1)]
    n=4: frontier = [hash(hash(h0,h1), hash(h2,h3))]
    n=5: frontier = [h4, hash(hash(h0,h1), hash(h2,h3))]
    
    The frontier has at most ceil(log2(n)) entries.
    """
    
    def __init__(self):
        self._leaves: list[bytes] = []  # All leaf hashes
        self._frontier: list[bytes] = []  # Current frontier
        self._roots: list[MerkleRoot] = []  # Historical roots
        self._lock = asyncio.Lock()
    
    @property
    def size(self) -> int:
        """Number of entries in the log."""
        return len(self._leaves)
    
    @property
    def root(self) -> MerkleRoot | None:
        """Current Merkle root, or None if empty."""
        return self._roots[-1] if self._roots else None
    
    def get_root_at_size(self, size: int) -> MerkleRoot | None:
        """Get historical root when log had `size` entries."""
        if size == 0 or size > len(self._roots):
            return None
        return self._roots[size - 1]
    
    async def append(self, entry: bytes) -> MerkleRoot:
        """
        Append an entry to the log.
        
        Returns the new root after appending.
        Thread-safe via async lock.
        """
        async with self._lock:
            return self._append_internal(entry)
    
    async def append_batch(self, entries: list[bytes]) -> MerkleRoot:
        """
        Append multiple entries atomically.
        
        More efficient than individual appends due to lock amortization.
        """
        async with self._lock:
            for entry in entries:
                self._append_internal(entry)
            return self._roots[-1] if self._roots else None
    
    def _append_internal(self, entry: bytes) -> MerkleRoot:
        """
        Internal append without locking.
        
        Algorithm:
        1. Hash the new entry as a leaf
        2. Add to frontier
        3. While we can merge (have two nodes at same level):
           - Pop two nodes, hash together, push result
        4. Compute root from frontier
        """
        leaf_hash = hash_leaf(entry)
        self._leaves.append(leaf_hash)
        
        # Add new leaf to frontier
        self._frontier.append(leaf_hash)
        
        # Collapse complete subtrees
        # After adding leaf i, we can merge if (i+1) has trailing zeros in binary
        # This corresponds to completing a power-of-2 subtree
        index = len(self._leaves)  # 1-indexed
        
        while index > 0 and index % 2 == 0:
            # Merge the last two frontier nodes
            right = self._frontier.pop()
            left = self._frontier.pop()
            merged = hash_nodes(left, right)
            self._frontier.append(merged)
            index //= 2
        
        # Compute current root from frontier
        root_hash = self._compute_root_from_frontier()
        root = MerkleRoot(hash=root_hash, size=len(self._leaves))
        self._roots.append(root)
        
        return root
    
    def _compute_root_from_frontier(self) -> bytes:
        """
        Compute root by hashing frontier right-to-left.
        
        The frontier contains incomplete subtrees from smallest (rightmost)
        to largest (leftmost). We combine them right-to-left.
        
        For frontier [a, b, c] where c is smallest:
        - First: hash(b, c)
        - Then: hash(a, hash(b, c))
        """
        if not self._frontier:
            return b'\x00' * 32  # Empty tree sentinel
        
        if len(self._frontier) == 1:
            return self._frontier[0]
        
        # Combine right-to-left
        result = self._frontier[-1]
        for i in range(len(self._frontier) - 2, -1, -1):
            result = hash_nodes(self._frontier[i], result)
        
        return result
    
    def get_inclusion_proof(self, index: int) -> InclusionProof:
        """
        Generate proof that entry at `index` is in the log.
        
        The proof is the path from the leaf to the root,
        including all sibling hashes needed to recompute the root.
        
        We compute sibling hashes by reconstructing parts of the tree
        from the stored leaf hashes.
        """
        if index < 0 or index >= len(self._leaves):
            raise IndexError(f"Index {index} out of range [0, {len(self._leaves)})")
        
        n = len(self._leaves)
        siblings = []
        
        # Walk up the tree from the leaf
        # At each level, compute the sibling hash
        current_idx = index
        current_size = n
        
        while current_size > 1:
            # Determine sibling index
            if current_idx % 2 == 0:
                # We're on the left, sibling is on right
                sibling_idx = current_idx + 1
                is_left = False
            else:
                # We're on the right, sibling is on left
                sibling_idx = current_idx - 1
                is_left = True
            
            # Compute sibling hash
            if sibling_idx < current_size:
                # Compute hash of subtree rooted at sibling
                # Find the range of leaves this subtree covers
                subtree_size = self._subtree_size_at_level(current_size, n)
                start_leaf = sibling_idx * subtree_size
                end_leaf = min(start_leaf + subtree_size, n)
                
                sibling_hash = self._merkle_tree_hash(start_leaf, end_leaf - start_leaf)
            else:
                # No sibling (odd node), duplicate self
                subtree_size = self._subtree_size_at_level(current_size, n)
                start_leaf = current_idx * subtree_size
                end_leaf = min(start_leaf + subtree_size, n)
                sibling_hash = self._merkle_tree_hash(start_leaf, end_leaf - start_leaf)
                is_left = True
            
            siblings.append((sibling_hash, is_left))
            
            # Move up
            current_idx //= 2
            current_size = (current_size + 1) // 2
        
        return InclusionProof(
            index=index,
            entry_hash=self._leaves[index],
            siblings=tuple(siblings),
            root=self.root
        )
    
    def _subtree_size_at_level(self, level_size: int, total_leaves: int) -> int:
        """
        Compute how many leaves each node at a given level covers.
        
        For a tree with n leaves:
        - Level 0 (leaves): each node covers 1 leaf
        - Level 1: each node covers 2 leaves
        - Level k: each node covers 2^k leaves
        """
        # Calculate the level number from bottom
        # At leaf level, level_size = total_leaves, subtree_size = 1
        subtree_size = 1
        size = total_leaves
        while size > level_size:
            subtree_size *= 2
            size = (size + 1) // 2
        return subtree_size
    
    def get_consistency_proof(self, old_size: int, new_size: int = None) -> ConsistencyProof:
        """
        Generate proof that tree at `new_size` extends tree at `old_size`.
        
        This proves that:
        1. All entries 0..old_size-1 are unchanged
        2. Entries old_size..new_size-1 were only appended
        
        The proof uses the "subproof" algorithm from RFC 6962.
        
        Algorithm:
        - Find shared complete subtrees between old and new tree
        - Return nodes needed to verify old root can be computed from new tree
        """
        if new_size is None:
            new_size = len(self._leaves)
        
        if old_size <= 0 or old_size > new_size or new_size > len(self._leaves):
            raise ValueError(f"Invalid sizes: old={old_size}, new={new_size}, current={len(self._leaves)}")
        
        if old_size == new_size:
            # Trivial case - same tree
            old_root = self.get_root_at_size(old_size)
            return ConsistencyProof(
                old_size=old_size,
                new_size=new_size,
                old_root=old_root,
                new_root=old_root,
                proof_nodes=()
            )
        
        # Generate subproof nodes
        proof_nodes = []
        self._subproof(old_size, new_size, True, proof_nodes)
        
        return ConsistencyProof(
            old_size=old_size,
            new_size=new_size,
            old_root=self.get_root_at_size(old_size),
            new_root=self.get_root_at_size(new_size),
            proof_nodes=tuple(proof_nodes)
        )
    
    def _subproof(self, m: int, n: int, is_right: bool, proof: list[bytes]) -> bytes:
        """
        Generate consistency subproof recursively.
        
        Based on RFC 6962 algorithm:
        - m: old tree size
        - n: new tree size (of this subtree)
        - is_right: whether this subtree is on the right of the path
        
        Returns the hash of the subtree with n leaves.
        """
        if m == n:
            # Subtree unchanged, return its root
            if is_right:
                # Need to include in proof since it's not on path to old root
                root = self._merkle_tree_hash(0, n)
                proof.append(root)
            return self._merkle_tree_hash(0, n)
        
        if m == 0:
            # Old tree doesn't cover this subtree
            return self._merkle_tree_hash(0, n)
        
        # Split the tree
        k = largest_power_of_two_less_than(n)
        
        if m <= k:
            # Old tree is entirely in left subtree
            left = self._subproof(m, k, False, proof)
            right = self._merkle_tree_hash(k, n - k)
            proof.append(right)
            return hash_nodes(left, right)
        else:
            # Old tree spans both subtrees
            left = self._merkle_tree_hash(0, k)
            proof.append(left)
            right = self._subproof(m - k, n - k, True, proof)
            return hash_nodes(left, right)
    
    def _merkle_tree_hash(self, start: int, count: int) -> bytes:
        """
        Compute Merkle root for a range of leaves.
        
        start: starting leaf index
        count: number of leaves in subtree
        """
        if count == 0:
            return b'\x00' * 32
        
        if count == 1:
            return self._leaves[start]
        
        k = largest_power_of_two_less_than(count)
        left = self._merkle_tree_hash(start, k)
        right = self._merkle_tree_hash(start + k, count - k)
        return hash_nodes(left, right)


# =============================================================================
# Verification (Stateless)
# =============================================================================

class MerkleVerifier:
    """
    Stateless verifier for Merkle proofs.
    
    Can verify proofs without access to the log itself.
    This is what auditors and clients use.
    """
    
    @staticmethod
    def verify_inclusion(
        entry: bytes,
        proof: InclusionProof
    ) -> bool:
        """
        Verify that an entry is included in the log.
        
        Args:
            entry: The original entry data (not hash)
            proof: The inclusion proof from the log
        
        Returns:
            True if proof is valid, False otherwise
        """
        # Hash the entry
        current = hash_leaf(entry)
        
        # Check it matches the proof's entry hash
        if current != proof.entry_hash:
            return False
        
        # Walk up the tree using siblings
        for sibling_hash, is_left in proof.siblings:
            if is_left:
                current = hash_nodes(sibling_hash, current)
            else:
                current = hash_nodes(current, sibling_hash)
        
        # Compare with expected root
        return current == proof.root.hash
    
    @staticmethod
    def verify_consistency(proof: ConsistencyProof) -> bool:
        """
        Verify that a newer tree is an extension of an older tree.
        
        This proves append-only property: no entries were modified or deleted.
        
        Algorithm from RFC 6962:
        1. Start with proof nodes
        2. Compute both old and new roots
        3. Verify they match expected values
        """
        if proof.old_size > proof.new_size:
            return False
        
        if proof.old_size == proof.new_size:
            return proof.old_root.hash == proof.new_root.hash
        
        if proof.old_size == 0:
            return True  # Empty tree is prefix of any tree
        
        # Use the subproof verification algorithm
        return MerkleVerifier._verify_consistency_proof(
            proof.old_size,
            proof.new_size,
            proof.old_root.hash,
            proof.new_root.hash,
            list(proof.proof_nodes)
        )
    
    @staticmethod
    def _verify_consistency_proof(
        old_size: int,
        new_size: int,
        old_root: bytes,
        new_root: bytes,
        proof: list[bytes]
    ) -> bool:
        """
        Internal consistency verification.
        
        Based on RFC 6962 algorithm.
        """
        if old_size == new_size:
            return old_root == new_root and len(proof) == 0
        
        if old_size == 0:
            return True
        
        # Shift proof nodes as we consume them
        proof_idx = [0]
        
        def next_proof() -> bytes:
            if proof_idx[0] >= len(proof):
                raise ValueError("Proof too short")
            node = proof[proof_idx[0]]
            proof_idx[0] += 1
            return node
        
        try:
            # Find the split point
            # This is complex - we need to verify both paths simultaneously
            old_hash, new_hash = MerkleVerifier._verify_subproof(
                old_size, new_size, next_proof, True
            )
            
            return old_hash == old_root and new_hash == new_root
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def _verify_subproof(
        m: int, 
        n: int, 
        next_proof: Callable[[], bytes],
        is_right: bool
    ) -> tuple[bytes, bytes]:
        """
        Verify subproof recursively.
        
        Returns (old_tree_hash, new_tree_hash) for the subtree.
        """
        if m == n:
            if is_right:
                node = next_proof()
                return node, node
            else:
                # Need to reconstruct from children
                raise ValueError("Cannot verify without node")
        
        if m == 0:
            # This subtree is entirely new
            raise ValueError("Invalid subproof structure")
        
        k = largest_power_of_two_less_than(n)
        
        if m <= k:
            # Old tree entirely in left subtree
            left_old, left_new = MerkleVerifier._verify_subproof(m, k, next_proof, False)
            right_new = next_proof()
            
            old_hash = left_old
            new_hash = hash_nodes(left_new, right_new)
            
            # Adjust old hash if m < k
            if m < k:
                # Need more nodes for old hash
                pass  # Already handled by recursion
            
            return old_hash, new_hash
        else:
            # Old tree spans both subtrees
            left_node = next_proof()
            right_old, right_new = MerkleVerifier._verify_subproof(m - k, n - k, next_proof, True)
            
            old_hash = hash_nodes(left_node, right_old)
            new_hash = hash_nodes(left_node, right_new)
            
            return old_hash, new_hash


# =============================================================================
# High-Level API
# =============================================================================

@dataclass
class LogEntry:
    """
    A structured log entry with metadata.
    
    The actual stored data is the serialized form.
    """
    index: int
    data: bytes
    timestamp: float
    root: MerkleRoot
    
    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "data": self.data.hex(),
            "timestamp": self.timestamp,
            "root_hash": self.root.hex(),
            "root_size": self.root.size,
        }


class AuditLog:
    """
    High-level audit log built on MerkleLog.
    
    Provides:
    - Append with automatic timestamping
    - Entry retrieval with inclusion proofs
    - Consistency verification between checkpoints
    - Persistence hooks (subclass to implement)
    
    Usage:
        log = AuditLog()
        
        # Append entries
        entry = await log.append(b"user:123 action:login")
        
        # Get proof for auditors
        proof = log.get_proof(entry.index)
        
        # Verify (can be done offline)
        valid = AuditLog.verify(b"user:123 action:login", proof)
        
        # Consistency check
        old_root = log.checkpoint()
        # ... more appends ...
        consistency = log.prove_consistency(old_root.size)
        assert AuditLog.verify_consistency(consistency)
    """
    
    def __init__(self):
        self._merkle = MerkleLog()
        self._entries: list[bytes] = []  # Original entry data
        self._timestamps: list[float] = []
    
    @property
    def size(self) -> int:
        """Number of entries in the log."""
        return self._merkle.size
    
    @property
    def root(self) -> MerkleRoot | None:
        """Current Merkle root."""
        return self._merkle.root
    
    async def append(self, data: bytes) -> LogEntry:
        """
        Append an entry to the audit log.
        
        Returns the entry with its index and inclusion proof.
        """
        timestamp = time.time()
        
        # Store original data
        self._entries.append(data)
        self._timestamps.append(timestamp)
        
        # Append to Merkle log
        root = await self._merkle.append(data)
        
        return LogEntry(
            index=len(self._entries) - 1,
            data=data,
            timestamp=timestamp,
            root=root
        )
    
    async def append_batch(self, entries: list[bytes]) -> list[LogEntry]:
        """Append multiple entries atomically."""
        results = []
        timestamp = time.time()
        
        for data in entries:
            self._entries.append(data)
            self._timestamps.append(timestamp)
        
        await self._merkle.append_batch(entries)
        
        # Build result entries
        base_index = len(self._entries) - len(entries)
        for i, data in enumerate(entries):
            root = self._merkle.get_root_at_size(base_index + i + 1)
            results.append(LogEntry(
                index=base_index + i,
                data=data,
                timestamp=timestamp,
                root=root
            ))
        
        return results
    
    def get_entry(self, index: int) -> LogEntry:
        """Get entry by index."""
        if index < 0 or index >= len(self._entries):
            raise IndexError(f"Index {index} out of range")
        
        return LogEntry(
            index=index,
            data=self._entries[index],
            timestamp=self._timestamps[index],
            root=self._merkle.get_root_at_size(index + 1)
        )
    
    def get_proof(self, index: int) -> InclusionProof:
        """Get inclusion proof for entry at index."""
        return self._merkle.get_inclusion_proof(index)
    
    def get_consistency_proof(self, old_size: int, new_size: int = None) -> ConsistencyProof:
        """Get proof that current log extends log at old_size."""
        return self._merkle.get_consistency_proof(old_size, new_size)
    
    def checkpoint(self) -> MerkleRoot:
        """
        Get current root as a checkpoint.
        
        Store this externally to later verify consistency.
        """
        return self._merkle.root
    
    @staticmethod
    def verify(data: bytes, proof: InclusionProof) -> bool:
        """Verify an entry is in the log (static method for offline use)."""
        return MerkleVerifier.verify_inclusion(data, proof)
    
    @staticmethod
    def verify_consistency(proof: ConsistencyProof) -> bool:
        """Verify append-only property (static method for offline use)."""
        return MerkleVerifier.verify_consistency(proof)
    
    def iterate_entries(self, start: int = 0, end: int = None) -> Iterator[LogEntry]:
        """Iterate over entries in range."""
        if end is None:
            end = len(self._entries)
        
        for i in range(start, min(end, len(self._entries))):
            yield self.get_entry(i)


# =============================================================================
# Persistence Interface
# =============================================================================

class LogStorage(ABC):
    """
    Abstract storage backend for persisting audit logs.
    
    Implementations can store to:
    - Files
    - Databases
    - Distributed storage
    - Append-only message queues
    """
    
    @abstractmethod
    async def store_entry(self, index: int, data: bytes, root: MerkleRoot) -> None:
        """Store a new entry."""
        ...
    
    @abstractmethod
    async def load_entries(self, start: int, count: int) -> list[tuple[bytes, MerkleRoot]]:
        """Load entries from storage."""
        ...
    
    @abstractmethod
    async def get_latest_root(self) -> MerkleRoot | None:
        """Get the most recent root from storage."""
        ...


class InMemoryStorage(LogStorage):
    """Simple in-memory storage for testing."""
    
    def __init__(self):
        self._entries: list[tuple[bytes, MerkleRoot]] = []
    
    async def store_entry(self, index: int, data: bytes, root: MerkleRoot) -> None:
        if index != len(self._entries):
            raise ValueError(f"Expected index {len(self._entries)}, got {index}")
        self._entries.append((data, root))
    
    async def load_entries(self, start: int, count: int) -> list[tuple[bytes, MerkleRoot]]:
        return self._entries[start:start + count]
    
    async def get_latest_root(self) -> MerkleRoot | None:
        if not self._entries:
            return None
        return self._entries[-1][1]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core functions
    'hash_leaf',
    'hash_nodes',
    
    # Types
    'MerkleRoot',
    'InclusionProof',
    'ConsistencyProof',
    'LogEntry',
    
    # Core classes
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
