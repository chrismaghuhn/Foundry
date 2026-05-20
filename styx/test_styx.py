"""Tests for styx."""

import asyncio
import pytest
import secrets
from styx import (
    GF256,
    Share,
    SecretSharer,
    ShareCollector,
    InMemoryTransport,
    Peer,
    PeerState,
    Styx,
    IntegrityError,
    InsufficientSharesError,
    DuplicateShareError,
    generate_hmac_key,
    shares_to_hex,
    shares_from_hex,
)


# =============================================================================
# GF(2^8) Arithmetic Tests
# =============================================================================

class TestGF256:
    """Test Galois Field arithmetic."""
    
    def test_addition_is_xor(self):
        """Addition in GF(2^8) is XOR."""
        assert GF256.add(0, 0) == 0
        assert GF256.add(255, 0) == 255
        assert GF256.add(0b10101010, 0b01010101) == 0b11111111
        assert GF256.add(100, 100) == 0  # a + a = 0
    
    def test_subtraction_equals_addition(self):
        """Subtraction is identical to addition in characteristic 2."""
        for _ in range(100):
            a, b = secrets.randbelow(256), secrets.randbelow(256)
            assert GF256.sub(a, b) == GF256.add(a, b)
    
    def test_multiplication_identity(self):
        """1 is multiplicative identity."""
        for a in range(256):
            assert GF256.mul(a, 1) == a
            assert GF256.mul(1, a) == a
    
    def test_multiplication_by_zero(self):
        """Anything times zero is zero."""
        for a in range(256):
            assert GF256.mul(a, 0) == 0
            assert GF256.mul(0, a) == 0
    
    def test_multiplication_commutativity(self):
        """a * b = b * a"""
        for _ in range(100):
            a, b = secrets.randbelow(256), secrets.randbelow(256)
            assert GF256.mul(a, b) == GF256.mul(b, a)
    
    def test_multiplication_associativity(self):
        """(a * b) * c = a * (b * c)"""
        for _ in range(50):
            a = secrets.randbelow(256)
            b = secrets.randbelow(256)
            c = secrets.randbelow(256)
            assert GF256.mul(GF256.mul(a, b), c) == GF256.mul(a, GF256.mul(b, c))
    
    def test_distributivity(self):
        """a * (b + c) = a*b + a*c"""
        for _ in range(50):
            a = secrets.randbelow(256)
            b = secrets.randbelow(256)
            c = secrets.randbelow(256)
            lhs = GF256.mul(a, GF256.add(b, c))
            rhs = GF256.add(GF256.mul(a, b), GF256.mul(a, c))
            assert lhs == rhs
    
    def test_division_inverse(self):
        """a / b * b = a for b != 0"""
        for _ in range(100):
            a = secrets.randbelow(256)
            b = secrets.randbelow(255) + 1  # b != 0
            assert GF256.mul(GF256.div(a, b), b) == a
    
    def test_division_by_zero_raises(self):
        """Division by zero should raise."""
        with pytest.raises(ZeroDivisionError):
            GF256.div(100, 0)
    
    def test_multiplicative_inverse(self):
        """a * a^(-1) = 1"""
        for a in range(1, 256):  # Skip 0
            inv = GF256.inverse(a)
            assert GF256.mul(a, inv) == 1
    
    def test_inverse_of_zero_raises(self):
        """Zero has no inverse."""
        with pytest.raises(ZeroDivisionError):
            GF256.inverse(0)
    
    def test_exponentiation(self):
        """a^n computed correctly."""
        # Known values
        assert GF256.pow(2, 0) == 1
        assert GF256.pow(2, 1) == 2
        assert GF256.pow(2, 8) == GF256._gf_mult_slow(128, 2)  # 2^8 with reduction
        
        # Verify against repeated multiplication
        for _ in range(20):
            base = secrets.randbelow(255) + 1
            exp = secrets.randbelow(10)
            
            expected = 1
            for _ in range(exp):
                expected = GF256.mul(expected, base)
            
            assert GF256.pow(base, exp) == expected


# =============================================================================
# Share Tests
# =============================================================================

class TestShare:
    """Test Share data structure."""
    
    def test_share_creation(self):
        """Basic share creation."""
        share = Share(
            index=1,
            data=b"test data",
            hmac=b"0" * 32,
            threshold=3,
            total=5
        )
        assert share.index == 1
        assert share.data == b"test data"
        assert share.threshold == 3
        assert share.total == 5
    
    def test_share_index_validation(self):
        """Index must be in [1, 255]."""
        with pytest.raises(ValueError):
            Share(index=0, data=b"x", hmac=b"0" * 32, threshold=2, total=3)
        
        with pytest.raises(ValueError):
            Share(index=256, data=b"x", hmac=b"0" * 32, threshold=2, total=3)
    
    def test_share_data_validation(self):
        """Data cannot be empty."""
        with pytest.raises(ValueError):
            Share(index=1, data=b"", hmac=b"0" * 32, threshold=2, total=3)
    
    def test_share_hmac_validation(self):
        """HMAC must be 32 bytes."""
        with pytest.raises(ValueError):
            Share(index=1, data=b"x", hmac=b"short", threshold=2, total=3)
    
    def test_share_serialization_roundtrip(self):
        """Shares serialize and deserialize correctly."""
        original = Share(
            index=42,
            data=b"secret share data here",
            hmac=secrets.token_bytes(32),
            threshold=3,
            total=7
        )
        
        serialized = original.to_bytes()
        restored = Share.from_bytes(serialized)
        
        assert restored.index == original.index
        assert restored.data == original.data
        assert restored.hmac == original.hmac
        assert restored.threshold == original.threshold
        assert restored.total == original.total
    
    def test_share_immutability(self):
        """Shares are frozen (immutable)."""
        share = Share(index=1, data=b"x", hmac=b"0" * 32, threshold=2, total=3)
        
        with pytest.raises(AttributeError):
            share.index = 2


# =============================================================================
# Secret Sharing Tests
# =============================================================================

class TestSecretSharer:
    """Test core secret sharing functionality."""
    
    @pytest.fixture
    def sharer(self):
        return SecretSharer(hmac_key=b"test-key-for-reproducibility!!"[:32].ljust(32, b'!'))
    
    def test_split_and_reconstruct_minimal(self, sharer):
        """Basic 2-of-3 split and reconstruct."""
        secret = b"hello"
        shares = sharer.split(secret, n=3, k=2)
        
        assert len(shares) == 3
        
        # Any 2 shares should work
        assert sharer.reconstruct(shares[:2]) == secret
        assert sharer.reconstruct(shares[1:]) == secret
        assert sharer.reconstruct([shares[0], shares[2]]) == secret
    
    def test_split_and_reconstruct_exact_threshold(self, sharer):
        """Reconstruct with exactly k shares."""
        secret = b"test secret 123"
        shares = sharer.split(secret, n=10, k=5)
        
        assert sharer.reconstruct(shares[:5]) == secret
    
    def test_split_and_reconstruct_more_than_threshold(self, sharer):
        """Extra shares don't break reconstruction."""
        secret = b"another secret"
        shares = sharer.split(secret, n=7, k=3)
        
        # All shares work
        assert sharer.reconstruct(shares) == secret
        
        # Any 3+ shares work
        assert sharer.reconstruct(shares[:3]) == secret
        assert sharer.reconstruct(shares[2:5]) == secret
        assert sharer.reconstruct(shares[4:]) == secret
    
    def test_insufficient_shares_raises(self, sharer):
        """Fewer than k shares should raise."""
        secret = b"secret"
        shares = sharer.split(secret, n=5, k=3)
        
        with pytest.raises(InsufficientSharesError):
            sharer.reconstruct(shares[:2])  # Only 2, need 3
    
    def test_large_secret(self, sharer):
        """Handle secrets of significant size."""
        secret = secrets.token_bytes(10000)  # 10KB
        shares = sharer.split(secret, n=5, k=3)
        
        reconstructed = sharer.reconstruct(shares[:3])
        assert reconstructed == secret
    
    def test_all_byte_values(self, sharer):
        """Correctly handle all possible byte values."""
        secret = bytes(range(256))
        shares = sharer.split(secret, n=5, k=3)
        
        assert sharer.reconstruct(shares[:3]) == secret
    
    def test_single_byte_secret(self, sharer):
        """Handle single-byte secrets."""
        for byte_val in [0, 1, 127, 128, 255]:
            secret = bytes([byte_val])
            shares = sharer.split(secret, n=5, k=3)
            assert sharer.reconstruct(shares[:3]) == secret
    
    def test_hmac_verification(self, sharer):
        """Tampered shares are detected."""
        secret = b"sensitive data"
        shares = sharer.split(secret, n=5, k=3)
        
        # Tamper with the first share's data
        tampered = Share(
            index=shares[0].index,
            data=b"x" * len(shares[0].data),  # Wrong data
            hmac=shares[0].hmac,  # Original HMAC won't match
            threshold=shares[0].threshold,
            total=shares[0].total
        )
        
        with pytest.raises(IntegrityError):
            sharer.reconstruct([tampered, shares[1], shares[2]])
    
    def test_hmac_verification_disabled(self, sharer):
        """Can skip HMAC verification if desired."""
        secret = b"test"
        shares = sharer.split(secret, n=3, k=2)
        
        # Create share with wrong HMAC
        bad_share = Share(
            index=shares[0].index,
            data=shares[0].data,
            hmac=b"x" * 32,  # Wrong HMAC
            threshold=shares[0].threshold,
            total=shares[0].total
        )
        
        # With verification disabled, reconstruction works
        # (but is insecure - don't do this in production!)
        result = sharer.reconstruct([bad_share, shares[1]], verify_hmac=False)
        assert result == secret
    
    def test_duplicate_shares_detected(self, sharer):
        """Duplicate share indices raise error."""
        secret = b"test"
        shares = sharer.split(secret, n=5, k=3)
        
        # Duplicate the same share
        with pytest.raises(DuplicateShareError):
            sharer.reconstruct([shares[0], shares[0], shares[1]])
    
    def test_parameter_validation(self, sharer):
        """Invalid parameters raise ValueError."""
        with pytest.raises(ValueError):
            sharer.split(b"", n=5, k=3)  # Empty secret
        
        with pytest.raises(ValueError):
            sharer.split(b"x", n=1, k=1)  # k < 2
        
        with pytest.raises(ValueError):
            sharer.split(b"x", n=5, k=6)  # k > n
        
        with pytest.raises(ValueError):
            sharer.split(b"x", n=256, k=3)  # n > 255
    
    def test_different_hmac_keys(self):
        """Different HMAC keys produce different HMACs."""
        secret = b"test secret"
        
        sharer1 = SecretSharer(hmac_key=b"key1" + b"\x00" * 28)
        sharer2 = SecretSharer(hmac_key=b"key2" + b"\x00" * 28)
        
        shares1 = sharer1.split(secret, n=3, k=2)
        shares2 = sharer2.split(secret, n=3, k=2)
        
        # HMACs should differ
        assert shares1[0].hmac != shares2[0].hmac
        
        # Cross-verification fails
        with pytest.raises(IntegrityError):
            sharer1.reconstruct(shares2[:2])
    
    def test_reproducibility_with_same_data(self, sharer):
        """Same secret produces same share data (different HMACs due to random coeffs)."""
        # Note: Shares will have DIFFERENT data each time due to random polynomial
        # This test verifies that reconstruction always works
        secret = b"deterministic test"
        
        for _ in range(10):
            shares = sharer.split(secret, n=5, k=3)
            assert sharer.reconstruct(shares[:3]) == secret


# =============================================================================
# Async Collection Tests
# =============================================================================

class TestShareCollector:
    """Test async distributed share collection."""
    
    @pytest.fixture
    def setup(self):
        """Create sharer, transport, and collector."""
        transport = InMemoryTransport(latency_ms=10)
        sharer = SecretSharer(hmac_key=b"test-key-32-bytes-long-here!!!!!")
        collector = ShareCollector(transport, sharer)
        return sharer, transport, collector
    
    @pytest.mark.asyncio
    async def test_distribute_and_collect(self, setup):
        """Basic distribute and collect cycle."""
        sharer, transport, collector = setup
        
        secret = b"distributed secret"
        shares = sharer.split(secret, n=5, k=3)
        
        peers = [
            Peer(peer_id=f"peer-{i}", address="127.0.0.1", port=8000 + i)
            for i in range(5)
        ]
        
        # Distribute shares
        results = await collector.distribute(shares, peers)
        assert all(results.values())
        
        # Collect back
        collection = await collector.collect(peers, threshold=3)
        
        assert collection.success
        assert len(collection.shares) >= 3
        
        # Reconstruct
        reconstructed = sharer.reconstruct(collection.shares)
        assert reconstructed == secret
    
    @pytest.mark.asyncio
    async def test_collect_with_failures(self, setup):
        """Collection succeeds even with some peer failures."""
        sharer, transport, collector = setup
        
        secret = b"resilient secret"
        shares = sharer.split(secret, n=5, k=3)
        
        peers = [
            Peer(peer_id=f"peer-{i}", address="127.0.0.1", port=8000 + i)
            for i in range(5)
        ]
        
        # Only distribute to 3 peers (simulating 2 unavailable)
        await collector.distribute(shares[:3], peers[:3])
        
        # Collection should still succeed with 3 available
        collection = await collector.collect(peers, threshold=3, timeout_per_peer=0.1)
        
        assert collection.success
        assert len(collection.shares) == 3
    
    @pytest.mark.asyncio
    async def test_collect_insufficient(self, setup):
        """Collection fails when not enough shares available."""
        sharer, transport, collector = setup
        
        secret = b"test"
        shares = sharer.split(secret, n=5, k=3)
        
        peers = [
            Peer(peer_id=f"peer-{i}", address="127.0.0.1", port=8000 + i)
            for i in range(5)
        ]
        
        # Only distribute to 2 peers
        await collector.distribute(shares[:2], peers[:2])
        
        # Collection should fail (need 3, only 2 available)
        collection = await collector.collect(peers, threshold=3, timeout_per_peer=0.1)
        
        assert not collection.success
        assert len(collection.shares) == 2


# =============================================================================
# High-Level API Tests
# =============================================================================

class TestStyxAPI:
    """Test high-level Styx API."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Styx works as async context manager."""
        async with Styx() as styx:
            shares = styx.split(b"test", n=3, k=2)
            assert len(shares) == 3
            
            reconstructed = styx.reconstruct(shares[:2])
            assert reconstructed == b"test"
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Complete split -> distribute -> collect -> reconstruct."""
        async with Styx() as styx:
            secret = b"full workflow test"
            
            peers = [
                Peer(peer_id=f"node-{i}", address="localhost", port=9000 + i)
                for i in range(5)
            ]
            
            # Split
            shares = styx.split(secret, n=5, k=3)
            
            # Distribute
            results = await styx.distribute(shares, peers)
            assert all(results.values())
            
            # Collect
            collection = await styx.collect(peers, threshold=3)
            assert collection.success
            
            # Reconstruct
            recovered = styx.reconstruct(collection.shares)
            assert recovered == secret


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilities:
    """Test utility functions."""
    
    def test_generate_hmac_key(self):
        """Generated keys are 32 bytes and random."""
        key1 = generate_hmac_key()
        key2 = generate_hmac_key()
        
        assert len(key1) == 32
        assert len(key2) == 32
        assert key1 != key2
    
    def test_shares_hex_roundtrip(self):
        """Shares convert to hex and back."""
        sharer = SecretSharer(hmac_key=b"test-key-32-bytes-exactly-here!!")
        shares = sharer.split(b"test secret", n=5, k=3)
        
        hex_strings = shares_to_hex(shares)
        restored = shares_from_hex(hex_strings)
        
        assert len(restored) == len(shares)
        for original, restored_share in zip(shares, restored):
            assert restored_share.index == original.index
            assert restored_share.data == original.data
            assert restored_share.hmac == original.hmac


# =============================================================================
# Property-Based Testing (Simplified)
# =============================================================================

class TestProperties:
    """Property-based tests for stronger guarantees."""
    
    def test_reconstruction_any_k_subset(self):
        """Any k shares from n reconstruct correctly."""
        from itertools import combinations
        
        sharer = SecretSharer(hmac_key=b"property-test-key-32-bytes-long!")
        secret = b"property test secret"
        
        shares = sharer.split(secret, n=6, k=3)
        
        # Try all possible 3-combinations
        for subset in combinations(shares, 3):
            reconstructed = sharer.reconstruct(list(subset))
            assert reconstructed == secret, f"Failed with indices {[s.index for s in subset]}"
    
    def test_k_minus_one_reveals_nothing(self):
        """k-1 shares should not help guess the secret."""
        # This is a statistical test - with k-1 shares, any secret is equally likely
        # We verify that different secrets produce the same partial share patterns
        
        sharer = SecretSharer(hmac_key=b"security-test-key-32-bytes-long!")
        
        # For k=2, a single share reveals nothing
        # All single-byte secrets 0-255 could produce any share value at index 1
        possible_y_values = set()
        
        for secret_byte in range(256):
            shares = sharer.split(bytes([secret_byte]), n=3, k=2)
            possible_y_values.add(shares[0].data[0])
        
        # Should cover many values (not all due to random polynomial, but many)
        # With k=2, a random linear polynomial f(x) = a + bx where a,b are random
        # covers about 63% of values (1 - 1/e) statistically
        assert len(possible_y_values) > 100  # At least 100 distinct values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
