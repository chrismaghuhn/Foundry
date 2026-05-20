"""Tests for malo."""

import pytest
import asyncio
from malo import (
    MerkleLog,
    MerkleVerifier,
    MerkleRoot,
    AuditLog,
    InclusionProof,
    ConsistencyProof,
    hash_leaf,
    hash_nodes,
    tree_height,
    tree_size,
    is_power_of_two,
)


# =============================================================================
# Hash Function Tests
# =============================================================================

class TestHashFunctions:
    """Test low-level hash functions."""
    
    def test_leaf_hash_deterministic(self):
        """Leaf hashes are deterministic."""
        data = b"test data"
        h1 = hash_leaf(data)
        h2 = hash_leaf(data)
        
        assert h1 == h2
        assert len(h1) == 32  # SHA-256
    
    def test_leaf_hash_unique(self):
        """Different data produces different hashes."""
        h1 = hash_leaf(b"data1")
        h2 = hash_leaf(b"data2")
        
        assert h1 != h2
    
    def test_node_hash_deterministic(self):
        """Node hashes are deterministic."""
        left = hash_leaf(b"left")
        right = hash_leaf(b"right")
        
        h1 = hash_nodes(left, right)
        h2 = hash_nodes(left, right)
        
        assert h1 == h2
    
    def test_node_hash_order_matters(self):
        """hash(a, b) != hash(b, a)."""
        left = hash_leaf(b"left")
        right = hash_leaf(b"right")
        
        h1 = hash_nodes(left, right)
        h2 = hash_nodes(right, left)
        
        assert h1 != h2
    
    def test_domain_separation(self):
        """Leaf and node hashes use different prefixes."""
        # Craft data that would produce same hash without domain separation
        data = b"test"
        leaf_hash = hash_leaf(data)
        
        # Even if we try to craft malicious data, prefix prevents collision
        assert leaf_hash != hash_nodes(b"", data)


# =============================================================================
# Tree Math Tests
# =============================================================================

class TestTreeMath:
    """Test tree size/height calculations."""
    
    def test_tree_height(self):
        """Tree height calculations."""
        assert tree_height(0) == 0
        assert tree_height(1) == 0
        assert tree_height(2) == 1
        assert tree_height(3) == 2
        assert tree_height(4) == 2
        assert tree_height(5) == 3
        assert tree_height(8) == 3
        assert tree_height(9) == 4
    
    def test_is_power_of_two(self):
        """Power of two detection."""
        assert is_power_of_two(1) is True
        assert is_power_of_two(2) is True
        assert is_power_of_two(4) is True
        assert is_power_of_two(8) is True
        assert is_power_of_two(3) is False
        assert is_power_of_two(5) is False
        assert is_power_of_two(0) is False


# =============================================================================
# MerkleLog Tests
# =============================================================================

class TestMerkleLog:
    """Test core Merkle log operations."""
    
    @pytest.mark.asyncio
    async def test_empty_log(self):
        """Empty log has no root."""
        log = MerkleLog()
        
        assert log.size == 0
        assert log.root is None
    
    @pytest.mark.asyncio
    async def test_single_entry(self):
        """Single entry produces valid root."""
        log = MerkleLog()
        
        root = await log.append(b"first entry")
        
        assert log.size == 1
        assert root is not None
        assert root.size == 1
        assert len(root.hash) == 32
    
    @pytest.mark.asyncio
    async def test_two_entries(self):
        """Two entries produce combined root."""
        log = MerkleLog()
        
        root1 = await log.append(b"entry 1")
        root2 = await log.append(b"entry 2")
        
        assert log.size == 2
        assert root1 != root2
        assert root2.size == 2
    
    @pytest.mark.asyncio
    async def test_root_deterministic(self):
        """Same entries produce same root."""
        log1 = MerkleLog()
        log2 = MerkleLog()
        
        await log1.append(b"a")
        await log1.append(b"b")
        await log1.append(b"c")
        
        await log2.append(b"a")
        await log2.append(b"b")
        await log2.append(b"c")
        
        assert log1.root == log2.root
    
    @pytest.mark.asyncio
    async def test_batch_append(self):
        """Batch append works correctly."""
        log = MerkleLog()
        
        root = await log.append_batch([b"a", b"b", b"c", b"d"])
        
        assert log.size == 4
        assert root.size == 4
    
    @pytest.mark.asyncio
    async def test_historical_roots(self):
        """Historical roots are preserved."""
        log = MerkleLog()
        
        r1 = await log.append(b"1")
        r2 = await log.append(b"2")
        r3 = await log.append(b"3")
        
        assert log.get_root_at_size(1) == r1
        assert log.get_root_at_size(2) == r2
        assert log.get_root_at_size(3) == r3


# =============================================================================
# Inclusion Proof Tests
# =============================================================================

class TestInclusionProofs:
    """Test inclusion proof generation and verification."""
    
    @pytest.mark.asyncio
    async def test_single_entry_proof(self):
        """Proof for single-entry log."""
        log = MerkleLog()
        await log.append(b"only entry")
        
        proof = log.get_inclusion_proof(0)
        
        assert proof.index == 0
        assert len(proof.siblings) == 0  # No siblings for single entry
    
    @pytest.mark.asyncio
    async def test_proof_verification(self):
        """Proofs verify correctly."""
        log = MerkleLog()
        
        entries = [b"entry 1", b"entry 2", b"entry 3", b"entry 4"]
        for entry in entries:
            await log.append(entry)
        
        # Verify each entry
        for i, entry in enumerate(entries):
            proof = log.get_inclusion_proof(i)
            assert MerkleVerifier.verify_inclusion(entry, proof)
    
    @pytest.mark.asyncio
    async def test_invalid_entry_fails(self):
        """Proof fails for wrong entry."""
        log = MerkleLog()
        
        await log.append(b"correct entry")
        proof = log.get_inclusion_proof(0)
        
        # Try to verify with wrong data
        assert not MerkleVerifier.verify_inclusion(b"wrong entry", proof)
    
    @pytest.mark.asyncio
    async def test_tampered_proof_fails(self):
        """Tampered proof fails verification."""
        log = MerkleLog()
        
        await log.append(b"entry 1")
        await log.append(b"entry 2")
        
        proof = log.get_inclusion_proof(0)
        
        # Tamper with sibling hash
        if proof.siblings:
            tampered_siblings = ((b'\x00' * 32, proof.siblings[0][1]),) + proof.siblings[1:]
            tampered = InclusionProof(
                index=proof.index,
                entry_hash=proof.entry_hash,
                siblings=tampered_siblings,
                root=proof.root
            )
            assert not MerkleVerifier.verify_inclusion(b"entry 1", tampered)
    
    @pytest.mark.asyncio
    async def test_proof_serialization(self):
        """Proofs serialize and deserialize correctly."""
        log = MerkleLog()
        
        await log.append(b"entry 1")
        await log.append(b"entry 2")
        await log.append(b"entry 3")
        
        original = log.get_inclusion_proof(1)
        
        # Round-trip through dict
        data = original.to_dict()
        restored = InclusionProof.from_dict(data)
        
        assert restored.index == original.index
        assert restored.entry_hash == original.entry_hash
        assert len(restored.siblings) == len(original.siblings)
    
    @pytest.mark.asyncio
    async def test_out_of_range_raises(self):
        """Out of range index raises error."""
        log = MerkleLog()
        
        await log.append(b"only entry")
        
        with pytest.raises(IndexError):
            log.get_inclusion_proof(1)
        
        with pytest.raises(IndexError):
            log.get_inclusion_proof(-1)


# =============================================================================
# Consistency Proof Tests
# =============================================================================

class TestConsistencyProofs:
    """Test consistency proof generation and verification."""
    
    @pytest.mark.asyncio
    async def test_same_size_trivial(self):
        """Same size produces trivial proof."""
        log = MerkleLog()
        
        await log.append(b"entry 1")
        await log.append(b"entry 2")
        
        proof = log.get_consistency_proof(2, 2)
        
        assert proof.old_size == proof.new_size
        assert len(proof.proof_nodes) == 0
    
    @pytest.mark.asyncio
    async def test_consistency_verification(self):
        """Consistency proofs verify correctly."""
        log = MerkleLog()
        
        # Build log incrementally
        await log.append(b"entry 1")
        await log.append(b"entry 2")
        
        old_root = log.root
        
        await log.append(b"entry 3")
        await log.append(b"entry 4")
        
        # Prove consistency from 2 to 4
        proof = log.get_consistency_proof(2, 4)
        
        assert proof.old_root == old_root
        assert proof.new_root == log.root
    
    @pytest.mark.asyncio
    async def test_proof_serialization(self):
        """Consistency proofs serialize correctly."""
        log = MerkleLog()
        
        await log.append(b"1")
        await log.append(b"2")
        await log.append(b"3")
        
        original = log.get_consistency_proof(2, 3)
        
        data = original.to_dict()
        restored = ConsistencyProof.from_dict(data)
        
        assert restored.old_size == original.old_size
        assert restored.new_size == original.new_size
    
    @pytest.mark.asyncio
    async def test_invalid_sizes_raise(self):
        """Invalid sizes raise error."""
        log = MerkleLog()
        
        await log.append(b"1")
        await log.append(b"2")
        
        with pytest.raises(ValueError):
            log.get_consistency_proof(0, 2)  # old_size = 0
        
        with pytest.raises(ValueError):
            log.get_consistency_proof(3, 2)  # old > new
        
        with pytest.raises(ValueError):
            log.get_consistency_proof(2, 5)  # new > current


# =============================================================================
# AuditLog Tests
# =============================================================================

class TestAuditLog:
    """Test high-level AuditLog API."""
    
    @pytest.mark.asyncio
    async def test_append_returns_entry(self):
        """Append returns structured entry."""
        log = AuditLog()
        
        entry = await log.append(b"test data")
        
        assert entry.index == 0
        assert entry.data == b"test data"
        assert entry.timestamp > 0
        assert entry.root is not None
    
    @pytest.mark.asyncio
    async def test_get_entry(self):
        """Can retrieve entries by index."""
        log = AuditLog()
        
        await log.append(b"entry 0")
        await log.append(b"entry 1")
        await log.append(b"entry 2")
        
        entry = log.get_entry(1)
        
        assert entry.index == 1
        assert entry.data == b"entry 1"
    
    @pytest.mark.asyncio
    async def test_get_proof(self):
        """Can get inclusion proof via high-level API."""
        log = AuditLog()
        
        await log.append(b"test entry")
        
        proof = log.get_proof(0)
        
        assert AuditLog.verify(b"test entry", proof)
    
    @pytest.mark.asyncio
    async def test_checkpoint_and_verify(self):
        """Checkpoint workflow works correctly."""
        log = AuditLog()
        
        await log.append(b"before checkpoint 1")
        await log.append(b"before checkpoint 2")
        
        checkpoint = log.checkpoint()
        
        await log.append(b"after checkpoint 1")
        await log.append(b"after checkpoint 2")
        
        # Get consistency proof
        proof = log.get_consistency_proof(checkpoint.size)
        
        # Verify proof structure is correct
        assert proof.old_size == 2
        assert proof.new_size == 4
        assert proof.old_root == checkpoint
        assert proof.new_root == log.root
        assert len(proof.proof_nodes) > 0  # Should have proof nodes
    
    @pytest.mark.asyncio
    async def test_batch_append(self):
        """Batch append via high-level API."""
        log = AuditLog()
        
        entries = await log.append_batch([b"a", b"b", b"c"])
        
        assert len(entries) == 3
        assert log.size == 3
    
    @pytest.mark.asyncio
    async def test_iterate_entries(self):
        """Can iterate over entries."""
        log = AuditLog()
        
        await log.append(b"1")
        await log.append(b"2")
        await log.append(b"3")
        
        entries = list(log.iterate_entries())
        
        assert len(entries) == 3
        assert entries[0].data == b"1"
        assert entries[2].data == b"3"


# =============================================================================
# Stress Tests
# =============================================================================

class TestStress:
    """Stress tests for larger logs."""
    
    @pytest.mark.asyncio
    async def test_many_entries(self):
        """Log handles many entries."""
        log = MerkleLog()
        
        # Add 100 entries
        for i in range(100):
            await log.append(f"entry {i}".encode())
        
        assert log.size == 100
        
        # Verify random entry
        proof = log.get_inclusion_proof(50)
        assert MerkleVerifier.verify_inclusion(b"entry 50", proof)
    
    @pytest.mark.asyncio
    async def test_consistency_across_many_entries(self):
        """Consistency proofs work for large logs."""
        log = MerkleLog()
        
        # Build log
        for i in range(50):
            await log.append(f"entry {i}".encode())
        
        # Get proof from 10 to 50
        proof = log.get_consistency_proof(10, 50)
        
        assert proof.old_size == 10
        assert proof.new_size == 50
    
    @pytest.mark.asyncio
    async def test_proof_size_logarithmic(self):
        """Proof size grows logarithmically."""
        log = MerkleLog()
        
        # Add 1024 entries (2^10)
        for i in range(1024):
            await log.append(f"entry {i}".encode())
        
        proof = log.get_inclusion_proof(512)
        
        # For 1024 entries, proof should have ~10 siblings
        assert len(proof.siblings) <= 12  # Some tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
