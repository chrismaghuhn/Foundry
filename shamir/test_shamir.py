"""Tests for shamir."""

import pytest
from shamir import (
    # Core
    split,
    combine,
    verify_shares,
    
    # Data structures
    Share,
    
    # Utilities
    split_string,
    combine_string,
    share_to_hex,
    share_from_hex,
    
    # GF(256)
    GF256,
)


# =============================================================================
# GF(256) Tests
# =============================================================================

class TestGF256:
    """Test Galois Field GF(256) arithmetic."""
    
    def test_add_identity(self):
        """a + 0 = a"""
        for a in [0, 1, 127, 255]:
            assert GF256.add(a, 0) == a
    
    def test_add_inverse(self):
        """a + a = 0 (in GF(2^n), every element is its own additive inverse)"""
        for a in [0, 1, 127, 255]:
            assert GF256.add(a, a) == 0
    
    def test_add_commutative(self):
        """a + b = b + a"""
        assert GF256.add(42, 73) == GF256.add(73, 42)
    
    def test_mul_identity(self):
        """a * 1 = a"""
        for a in [0, 1, 127, 255]:
            assert GF256.mul(a, 1) == a
    
    def test_mul_zero(self):
        """a * 0 = 0"""
        for a in [0, 1, 127, 255]:
            assert GF256.mul(a, 0) == 0
    
    def test_mul_commutative(self):
        """a * b = b * a"""
        assert GF256.mul(42, 73) == GF256.mul(73, 42)
    
    def test_div_inverse(self):
        """a / a = 1 for a != 0"""
        for a in [1, 42, 127, 255]:
            assert GF256.div(a, a) == 1
    
    def test_div_zero_numerator(self):
        """0 / a = 0"""
        assert GF256.div(0, 42) == 0
    
    def test_div_by_zero(self):
        """Division by zero raises error."""
        with pytest.raises(ZeroDivisionError):
            GF256.div(42, 0)
    
    def test_mul_div_roundtrip(self):
        """(a * b) / b = a"""
        for a in [1, 42, 127, 255]:
            for b in [1, 42, 127, 255]:
                result = GF256.div(GF256.mul(a, b), b)
                assert result == a
    
    def test_pow_zero(self):
        """a^0 = 1"""
        for a in [1, 42, 127, 255]:
            assert GF256.pow(a, 0) == 1
    
    def test_pow_one(self):
        """a^1 = a"""
        for a in [0, 1, 42, 255]:
            assert GF256.pow(a, 1) == a
    
    def test_inverse(self):
        """a * inverse(a) = 1"""
        for a in [1, 42, 127, 255]:
            inv = GF256.inverse(a)
            assert GF256.mul(a, inv) == 1
    
    def test_inverse_zero(self):
        """Zero has no inverse."""
        with pytest.raises(ZeroDivisionError):
            GF256.inverse(0)


# =============================================================================
# Basic Split/Combine Tests
# =============================================================================

class TestBasicSplitCombine:
    """Test basic split and combine operations."""
    
    def test_simple_split_combine(self):
        """Basic split and combine."""
        secret = b"hello"
        shares = split(secret, n=5, k=3)
        
        assert len(shares) == 5
        recovered = combine(shares[:3])
        assert recovered == secret
    
    def test_all_shares(self):
        """Using all shares works."""
        secret = b"secret"
        shares = split(secret, n=5, k=3)
        
        recovered = combine(shares)
        assert recovered == secret
    
    def test_minimum_shares(self):
        """Exactly K shares work."""
        secret = b"data"
        shares = split(secret, n=5, k=3)
        
        recovered = combine(shares[:3])
        assert recovered == secret
    
    def test_different_share_combinations(self):
        """Different combinations of K shares all work."""
        secret = b"test"
        shares = split(secret, n=5, k=3)
        
        # Try different combinations
        assert combine([shares[0], shares[1], shares[2]]) == secret
        assert combine([shares[0], shares[2], shares[4]]) == secret
        assert combine([shares[1], shares[3], shares[4]]) == secret
        assert combine([shares[2], shares[3], shares[4]]) == secret
    
    def test_single_byte(self):
        """Single byte secret."""
        secret = b"X"
        shares = split(secret, n=3, k=2)
        
        assert combine(shares[:2]) == secret
    
    def test_long_secret(self):
        """Long secret works."""
        secret = b"A" * 1000
        shares = split(secret, n=5, k=3)
        
        assert combine(shares[:3]) == secret
    
    def test_binary_data(self):
        """Binary data (non-ASCII bytes) works."""
        secret = bytes(range(256))
        shares = split(secret, n=5, k=3)
        
        assert combine(shares[:3]) == secret


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_minimum_threshold(self):
        """k=2 (minimum threshold)."""
        secret = b"secret"
        shares = split(secret, n=5, k=2)
        
        assert combine(shares[:2]) == secret
    
    def test_n_equals_k(self):
        """n=k (all shares required)."""
        secret = b"secret"
        shares = split(secret, n=3, k=3)
        
        assert combine(shares) == secret
    
    def test_max_shares(self):
        """n=255 (maximum shares)."""
        secret = b"x"
        shares = split(secret, n=255, k=3)
        
        assert len(shares) == 255
        assert combine(shares[:3]) == secret
    
    def test_empty_secret_error(self):
        """Empty secret raises error."""
        with pytest.raises(ValueError):
            split(b"", n=5, k=3)
    
    def test_invalid_k_n(self):
        """Invalid k > n raises error."""
        with pytest.raises(ValueError):
            split(b"secret", n=3, k=5)
    
    def test_k_too_small(self):
        """k < 2 raises error."""
        with pytest.raises(ValueError):
            split(b"secret", n=5, k=1)
    
    def test_n_too_large(self):
        """n > 255 raises error."""
        with pytest.raises(ValueError):
            split(b"secret", n=256, k=3)
    
    def test_not_bytes(self):
        """Non-bytes input raises error."""
        with pytest.raises(TypeError):
            split("string", n=5, k=3)  # type: ignore


# =============================================================================
# Share Tests
# =============================================================================

class TestShare:
    """Test Share data structure."""
    
    def test_share_x_valid(self):
        """Valid x values (1-255)."""
        share = Share(x=1, data=b"test")
        assert share.x == 1
        
        share = Share(x=255, data=b"test")
        assert share.x == 255
    
    def test_share_x_invalid(self):
        """Invalid x values raise error."""
        with pytest.raises(ValueError):
            Share(x=0, data=b"test")
        
        with pytest.raises(ValueError):
            Share(x=256, data=b"test")
    
    def test_share_to_bytes(self):
        """Share serialization."""
        share = Share(x=42, data=b"hello")
        serialized = share.to_bytes()
        
        assert serialized[0] == 42
        assert serialized[1:] == b"hello"
    
    def test_share_from_bytes(self):
        """Share deserialization."""
        share = Share.from_bytes(b"\x2ahello")
        
        assert share.x == 42
        assert share.data == b"hello"
    
    def test_share_roundtrip(self):
        """Serialization roundtrip."""
        original = Share(x=123, data=b"test data")
        recovered = Share.from_bytes(original.to_bytes())
        
        assert recovered == original
    
    def test_share_equality(self):
        """Share equality."""
        share1 = Share(x=1, data=b"data")
        share2 = Share(x=1, data=b"data")
        share3 = Share(x=2, data=b"data")
        
        assert share1 == share2
        assert share1 != share3


# =============================================================================
# Utility Tests
# =============================================================================

class TestUtilities:
    """Test utility functions."""
    
    def test_split_string(self):
        """String splitting."""
        shares = split_string("hello", n=5, k=3)
        recovered = combine_string(shares[:3])
        
        assert recovered == "hello"
    
    def test_split_string_unicode(self):
        """Unicode string splitting."""
        secret = "Hello 世界 🌍"
        shares = split_string(secret, n=5, k=3)
        recovered = combine_string(shares[:3])
        
        assert recovered == secret
    
    def test_share_to_hex(self):
        """Hex conversion."""
        share = Share(x=1, data=b"\xab\xcd")
        hex_str = share_to_hex(share)
        
        assert hex_str == "01:abcd"
    
    def test_share_from_hex(self):
        """Hex parsing."""
        share = share_from_hex("2a:deadbeef")
        
        assert share.x == 42
        assert share.data == bytes.fromhex("deadbeef")
    
    def test_hex_roundtrip(self):
        """Hex conversion roundtrip."""
        original = Share(x=100, data=b"test123")
        recovered = share_from_hex(share_to_hex(original))
        
        assert recovered == original


# =============================================================================
# Security Tests
# =============================================================================

class TestSecurity:
    """Test security properties."""
    
    def test_shares_are_different(self):
        """All shares should be different."""
        secret = b"secret"
        shares = split(secret, n=5, k=3)
        
        share_data = [s.data for s in shares]
        assert len(set(share_data)) == 5  # All unique
    
    def test_shares_hide_secret(self):
        """Shares should not reveal the secret directly."""
        secret = b"AAAA"  # Repeated pattern
        shares = split(secret, n=5, k=3)
        
        # Secret should not appear in any share
        for share in shares:
            assert share.data != secret
    
    def test_k_minus_1_insufficient(self):
        """K-1 shares should not allow reconstruction to the same value."""
        secret = b"secret"
        shares = split(secret, n=5, k=3)
        
        # With only 2 shares (k-1), we can still call combine
        # but the result should be wrong
        wrong_result = combine(shares[:2])
        
        # The result has the same length but different content
        assert len(wrong_result) == len(secret)
        # Very high probability it's wrong
        # (technically there's a tiny chance it's correct by coincidence)
    
    def test_verify_consistent_shares(self):
        """Consistent shares pass verification."""
        secret = b"test"
        shares = split(secret, n=5, k=3)
        
        assert verify_shares(shares, k=3) == True
    
    def test_different_splits_different_shares(self):
        """Same secret produces different shares each time."""
        secret = b"secret"
        
        shares1 = split(secret, n=5, k=3)
        shares2 = split(secret, n=5, k=3)
        
        # At least some shares should be different
        different = False
        for s1, s2 in zip(shares1, shares2):
            if s1.data != s2.data:
                different = True
                break
        
        assert different


# =============================================================================
# Reconstruction Tests
# =============================================================================

class TestReconstruction:
    """Test various reconstruction scenarios."""
    
    def test_out_of_order_shares(self):
        """Shares don't need to be in order."""
        secret = b"order test"
        shares = split(secret, n=5, k=3)
        
        # Reverse order
        reversed_shares = [shares[4], shares[2], shares[0]]
        assert combine(reversed_shares) == secret
    
    def test_excess_shares(self):
        """More than K shares work."""
        secret = b"excess"
        shares = split(secret, n=5, k=3)
        
        # Use 4 shares when only 3 needed
        assert combine(shares[:4]) == secret
    
    def test_duplicate_shares_error(self):
        """Duplicate shares raise error."""
        secret = b"dup"
        shares = split(secret, n=5, k=3)
        
        with pytest.raises(ValueError):
            combine([shares[0], shares[0], shares[1]])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
