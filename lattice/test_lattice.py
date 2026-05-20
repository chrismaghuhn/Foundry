"""Tests for lattice."""

import pytest
import time
from lattice import (
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
    HLCTimestamp,
    merge_all,
)


# =============================================================================
# GCounter Tests
# =============================================================================

class TestGCounter:
    """Test grow-only counter."""
    
    def test_initial_value_is_zero(self):
        counter = GCounter("node-a")
        assert counter.value == 0
    
    def test_increment(self):
        counter = GCounter("node-a")
        counter.increment(5)
        assert counter.value == 5
    
    def test_multiple_increments(self):
        counter = GCounter("node-a")
        counter.increment(3)
        counter.increment(2)
        counter.increment(5)
        assert counter.value == 10
    
    def test_negative_increment_raises(self):
        counter = GCounter("node-a")
        with pytest.raises(ValueError):
            counter.increment(-1)
    
    def test_merge_different_nodes(self):
        a = GCounter("node-a")
        b = GCounter("node-b")
        
        a.increment(5)
        b.increment(3)
        
        a.merge(b)
        
        assert a.value == 8
    
    def test_merge_is_commutative(self):
        a = GCounter("node-a")
        b = GCounter("node-b")
        
        a.increment(5)
        b.increment(3)
        
        a_copy = a.clone()
        b_copy = b.clone()
        
        a.merge(b)
        b_copy.merge(a_copy)
        
        assert a.value == b_copy.value
    
    def test_merge_is_idempotent(self):
        a = GCounter("node-a")
        b = GCounter("node-b")
        
        a.increment(5)
        b.increment(3)
        
        a.merge(b)
        value_after_first = a.value
        
        a.merge(b)
        value_after_second = a.value
        
        assert value_after_first == value_after_second
    
    def test_serialization(self):
        counter = GCounter("node-a")
        counter.increment(10)
        
        data = counter.to_dict()
        restored = GCounter.from_dict(data)
        
        assert restored.value == counter.value


# =============================================================================
# PNCounter Tests
# =============================================================================

class TestPNCounter:
    """Test positive-negative counter."""
    
    def test_initial_value_is_zero(self):
        counter = PNCounter("node-a")
        assert counter.value == 0
    
    def test_increment(self):
        counter = PNCounter("node-a")
        counter.increment(5)
        assert counter.value == 5
    
    def test_decrement(self):
        counter = PNCounter("node-a")
        counter.increment(10)
        counter.decrement(3)
        assert counter.value == 7
    
    def test_can_go_negative(self):
        counter = PNCounter("node-a")
        counter.decrement(5)
        assert counter.value == -5
    
    def test_merge_increments_and_decrements(self):
        a = PNCounter("node-a")
        b = PNCounter("node-b")
        
        a.increment(10)
        b.decrement(3)
        
        a.merge(b)
        
        assert a.value == 7
    
    def test_merge_is_commutative(self):
        a = PNCounter("node-a")
        b = PNCounter("node-b")
        
        a.increment(5)
        a.decrement(2)
        b.increment(3)
        b.decrement(1)
        
        a_copy = a.clone()
        b_copy = b.clone()
        
        a.merge(b)
        b_copy.merge(a_copy)
        
        assert a.value == b_copy.value


# =============================================================================
# LWWRegister Tests
# =============================================================================

class TestLWWRegister:
    """Test last-writer-wins register."""
    
    def test_initial_value_is_none(self):
        reg = LWWRegister[str]("node-a")
        assert reg.value is None
    
    def test_set_and_get(self):
        reg = LWWRegister[str]("node-a")
        reg.set("hello")
        assert reg.value == "hello"
    
    def test_later_write_wins(self):
        reg = LWWRegister[str]("node-a")
        reg.set("first")
        time.sleep(0.001)  # Ensure different timestamp
        reg.set("second")
        assert reg.value == "second"
    
    def test_merge_higher_timestamp_wins(self):
        a = LWWRegister[str]("node-a")
        b = LWWRegister[str]("node-b")
        
        a.set("from-a")
        time.sleep(0.001)
        b.set("from-b")
        
        a.merge(b)
        
        assert a.value == "from-b"
    
    def test_merge_lower_timestamp_ignored(self):
        a = LWWRegister[str]("node-a")
        b = LWWRegister[str]("node-b")
        
        b.set("from-b")
        time.sleep(0.001)
        a.set("from-a")
        
        a.merge(b)
        
        assert a.value == "from-a"
    
    def test_serialization(self):
        reg = LWWRegister[str]("node-a")
        reg.set("test value")
        
        data = reg.to_dict()
        restored = LWWRegister.from_dict(data)
        
        assert restored.value == reg.value


# =============================================================================
# MVRegister Tests
# =============================================================================

class TestMVRegister:
    """Test multi-value register."""
    
    def test_initial_value_is_empty(self):
        reg = MVRegister[str]("node-a")
        assert reg.value == frozenset()
    
    def test_set_single_value(self):
        reg = MVRegister[str]("node-a")
        reg.set("hello")
        assert reg.value == frozenset({"hello"})
    
    def test_not_conflicted_after_single_set(self):
        reg = MVRegister[str]("node-a")
        reg.set("hello")
        assert not reg.is_conflicted
    
    def test_concurrent_writes_create_conflict(self):
        a = MVRegister[str]("node-a")
        b = MVRegister[str]("node-b")
        
        a.set("from-a")
        b.set("from-b")
        
        a.merge(b)
        
        assert a.is_conflicted
        assert a.value == frozenset({"from-a", "from-b"})
    
    def test_sequential_writes_no_conflict(self):
        a = MVRegister[str]("node-a")
        b = MVRegister[str]("node-b")
        
        a.set("first")
        b.merge(a)
        b.set("second")  # This dominates "first"
        a.merge(b)
        
        assert not a.is_conflicted
        assert a.value == frozenset({"second"})


# =============================================================================
# GSet Tests
# =============================================================================

class TestGSet:
    """Test grow-only set."""
    
    def test_initial_is_empty(self):
        s = GSet[str]("node-a")
        assert len(s) == 0
    
    def test_add_element(self):
        s = GSet[str]("node-a")
        s.add("x")
        assert "x" in s
    
    def test_add_multiple(self):
        s = GSet[str]("node-a")
        s.add("x")
        s.add("y")
        s.add("z")
        assert s.value == frozenset({"x", "y", "z"})
    
    def test_add_duplicate(self):
        s = GSet[str]("node-a")
        s.add("x")
        s.add("x")
        assert len(s) == 1
    
    def test_merge_is_union(self):
        a = GSet[str]("node-a")
        b = GSet[str]("node-b")
        
        a.add("x")
        a.add("y")
        b.add("y")
        b.add("z")
        
        a.merge(b)
        
        assert a.value == frozenset({"x", "y", "z"})


# =============================================================================
# TwoPSet Tests
# =============================================================================

class TestTwoPSet:
    """Test two-phase set."""
    
    def test_add_and_contains(self):
        s = TwoPSet[str]("node-a")
        s.add("x")
        assert "x" in s
    
    def test_remove(self):
        s = TwoPSet[str]("node-a")
        s.add("x")
        s.remove("x")
        assert "x" not in s
    
    def test_remove_is_permanent(self):
        s = TwoPSet[str]("node-a")
        s.add("x")
        s.remove("x")
        s.add("x")  # Try to re-add
        assert "x" not in s  # Still removed
    
    def test_merge_respects_removes(self):
        a = TwoPSet[str]("node-a")
        b = TwoPSet[str]("node-b")
        
        a.add("x")
        b.merge(a)
        
        a.remove("x")
        b.add("x")  # Try to re-add on b
        
        a.merge(b)
        
        assert "x" not in a  # Remove wins


# =============================================================================
# ORSet Tests
# =============================================================================

class TestORSet:
    """Test observed-remove set."""
    
    def test_add_and_contains(self):
        s = ORSet[str]("node-a")
        s.add("x")
        assert "x" in s
    
    def test_remove(self):
        s = ORSet[str]("node-a")
        s.add("x")
        s.remove("x")
        assert "x" not in s
    
    def test_add_after_remove(self):
        s = ORSet[str]("node-a")
        s.add("x")
        s.remove("x")
        s.add("x")
        assert "x" in s  # Can re-add after remove
    
    def test_concurrent_add_wins(self):
        """Add wins over concurrent remove (add-wins semantics)."""
        a = ORSet[str]("node-a")
        b = ORSet[str]("node-b")
        
        a.add("x")
        b.merge(a)  # Both see "x"
        
        # Concurrent operations
        a.remove("x")  # a removes
        b.add("x")     # b re-adds with new tag
        
        # Merge
        a.merge(b)
        
        # b's add survives because it has a new tag
        assert "x" in a
    
    def test_merge_is_commutative(self):
        a = ORSet[str]("node-a")
        b = ORSet[str]("node-b")
        
        a.add("x")
        a.add("y")
        b.add("y")
        b.add("z")
        
        a_copy = a.clone()
        b_copy = b.clone()
        
        a.merge(b)
        b_copy.merge(a_copy)
        
        assert a.value == b_copy.value


# =============================================================================
# LWWSet Tests
# =============================================================================

class TestLWWSet:
    """Test last-writer-wins set."""
    
    def test_add_and_contains(self):
        s = LWWSet[str]("node-a")
        s.add("x")
        assert "x" in s
    
    def test_remove(self):
        s = LWWSet[str]("node-a")
        s.add("x")
        time.sleep(0.001)
        s.remove("x")
        assert "x" not in s
    
    def test_add_after_remove(self):
        s = LWWSet[str]("node-a")
        s.add("x")
        time.sleep(0.001)
        s.remove("x")
        time.sleep(0.001)
        s.add("x")
        assert "x" in s
    
    def test_later_timestamp_wins(self):
        a = LWWSet[str]("node-a")
        b = LWWSet[str]("node-b")
        
        a.add("x")
        time.sleep(0.001)
        b.remove("x")  # Later remove
        
        a.merge(b)
        
        # Remove was later, so x is removed
        assert "x" not in a


# =============================================================================
# ORMap Tests
# =============================================================================

class TestORMap:
    """Test observed-remove map."""
    
    def test_set_and_get(self):
        m = ORMap[str, PNCounter]("node-a", lambda: PNCounter("node-a"))
        m["score"].increment(10)
        assert m["score"].value == 10
    
    def test_delete_key(self):
        m = ORMap[str, PNCounter]("node-a", lambda: PNCounter("node-a"))
        m["score"].increment(10)
        del m["score"]
        assert "score" not in m
    
    def test_merge_values(self):
        a = ORMap[str, GCounter]("node-a", lambda: GCounter("node-a"))
        b = ORMap[str, GCounter]("node-b", lambda: GCounter("node-b"))
        
        a["count"].increment(5)
        b["count"].increment(3)
        
        a.merge(b)
        
        assert a["count"].value == 8


# =============================================================================
# Semilattice Property Tests
# =============================================================================

class TestSemilatticeProperties:
    """Test that all CRDTs satisfy semilattice properties."""
    
    def test_gcounter_associative(self):
        a = GCounter("node-a")
        b = GCounter("node-b")
        c = GCounter("node-c")
        
        a.increment(1)
        b.increment(2)
        c.increment(3)
        
        # (a ⊔ b) ⊔ c
        ab = a.clone()
        ab.merge(b)
        abc1 = ab.clone()
        abc1.merge(c)
        
        # a ⊔ (b ⊔ c)
        bc = b.clone()
        bc.merge(c)
        abc2 = a.clone()
        abc2.merge(bc)
        
        assert abc1.value == abc2.value
    
    def test_orset_commutative(self):
        a = ORSet[str]("node-a")
        b = ORSet[str]("node-b")
        
        a.add("x")
        a.add("y")
        b.add("y")
        b.add("z")
        
        ab = a.clone()
        ab.merge(b)
        
        ba = b.clone()
        ba.merge(a)
        
        assert ab.value == ba.value
    
    def test_pncounter_idempotent(self):
        a = PNCounter("node-a")
        b = PNCounter("node-b")
        
        a.increment(5)
        b.decrement(2)
        
        a.merge(b)
        val1 = a.value
        
        a.merge(b)
        val2 = a.value
        
        assert val1 == val2


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Test serialization/deserialization."""
    
    def test_gcounter_roundtrip(self):
        original = GCounter("node-a")
        original.increment(42)
        
        data = original.to_dict()
        restored = GCounter.from_dict(data)
        
        assert restored.value == original.value
    
    def test_pncounter_roundtrip(self):
        original = PNCounter("node-a")
        original.increment(10)
        original.decrement(3)
        
        data = original.to_dict()
        restored = PNCounter.from_dict(data)
        
        assert restored.value == original.value
    
    def test_orset_roundtrip(self):
        original = ORSet[str]("node-a")
        original.add("x")
        original.add("y")
        original.remove("x")
        
        data = original.to_dict()
        restored = ORSet.from_dict(data)
        
        assert restored.value == original.value


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests simulating real distributed scenarios."""
    
    def test_three_node_counter_sync(self):
        """Three nodes increment and eventually sync."""
        a = GCounter("node-a")
        b = GCounter("node-b")
        c = GCounter("node-c")
        
        # Each node increments locally
        a.increment(10)
        b.increment(20)
        c.increment(30)
        
        # Partial sync: a syncs with b
        a.merge(b)
        b.merge(a)
        
        # Partial sync: b syncs with c
        b.merge(c)
        c.merge(b)
        
        # Final sync: a syncs with c
        a.merge(c)
        c.merge(a)
        
        # All should converge to 60
        assert a.value == b.value == c.value == 60
    
    def test_shopping_cart_scenario(self):
        """Simulate concurrent shopping cart edits."""
        # Two devices editing the same cart
        cart_phone = ORSet[str]("phone")
        cart_tablet = ORSet[str]("tablet")
        
        # Phone adds items
        cart_phone.add("milk")
        cart_phone.add("bread")
        
        # Sync to tablet
        cart_tablet.merge(cart_phone)
        
        # Concurrent edits
        cart_phone.remove("milk")  # Decided not to buy milk
        cart_tablet.add("eggs")     # Added eggs on tablet
        cart_tablet.add("milk")     # Someone else re-added milk
        
        # Sync both ways
        cart_phone.merge(cart_tablet)
        cart_tablet.merge(cart_phone)
        
        # Both should have: bread, eggs, milk (add-wins)
        assert cart_phone.value == cart_tablet.value
        assert "bread" in cart_phone
        assert "eggs" in cart_phone
        assert "milk" in cart_phone  # Re-add wins
    
    def test_collaborative_vote_counter(self):
        """Simulate upvotes/downvotes from multiple nodes."""
        votes_a = PNCounter("server-a")
        votes_b = PNCounter("server-b")
        votes_c = PNCounter("server-c")
        
        # Users vote through different servers
        votes_a.increment(100)  # 100 upvotes
        votes_b.increment(50)   # 50 upvotes
        votes_b.decrement(20)   # 20 downvotes
        votes_c.decrement(10)   # 10 downvotes
        
        # Merge all
        votes_a.merge(votes_b)
        votes_a.merge(votes_c)
        
        # Final score: 100 + 50 - 20 - 10 = 120
        assert votes_a.value == 120


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
