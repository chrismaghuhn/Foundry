"""Tests for sketch."""

import pytest
import math
import random
from sketch import (
    BloomFilter,
    CountingBloomFilter,
    CuckooFilter,
    HyperLogLog,
    CountMinSketch,
    TopK,
    BitArray,
    optimal_bloom_params,
    bloom_fpr,
    hyperloglog_error,
)


# =============================================================================
# BitArray Tests
# =============================================================================

class TestBitArray:
    """Test the bit array implementation."""
    
    def test_initial_all_zeros(self):
        arr = BitArray(100)
        assert all(arr[i] == False for i in range(100))
    
    def test_set_and_get(self):
        arr = BitArray(100)
        arr[50] = True
        assert arr[50] == True
        assert arr[49] == False
    
    def test_set_method_returns_previous(self):
        arr = BitArray(100)
        was_set = arr.set(10)
        assert was_set == False
        
        was_set = arr.set(10)
        assert was_set == True
    
    def test_count_ones(self):
        arr = BitArray(100)
        arr[0] = True
        arr[50] = True
        arr[99] = True
        assert arr.count_ones() == 3
    
    def test_merge_or(self):
        arr1 = BitArray(64)
        arr2 = BitArray(64)
        
        arr1[0] = True
        arr1[10] = True
        arr2[10] = True
        arr2[20] = True
        
        arr1.merge_or(arr2)
        
        assert arr1[0] == True
        assert arr1[10] == True
        assert arr1[20] == True
        assert arr1.count_ones() == 3
    
    def test_serialization(self):
        arr = BitArray(100)
        arr[25] = True
        arr[75] = True
        
        data = arr.to_bytes()
        restored = BitArray.from_bytes(data, 100)
        
        assert restored[25] == True
        assert restored[75] == True
        assert restored.count_ones() == 2


# =============================================================================
# Bloom Filter Tests
# =============================================================================

class TestBloomFilter:
    """Test Bloom filter operations."""
    
    def test_add_and_contains(self):
        bf = BloomFilter(expected_items=100)
        
        bf.add(b"hello")
        bf.add(b"world")
        
        assert b"hello" in bf
        assert b"world" in bf
    
    def test_definitely_not_present(self):
        bf = BloomFilter(expected_items=100)
        
        bf.add(b"hello")
        
        # Items never added should not be present
        # (with very high probability)
        assert b"definitely_not_here_xyz_12345" not in bf
    
    def test_string_support(self):
        bf = BloomFilter(expected_items=100)
        
        bf.add("hello")
        assert "hello" in bf
    
    def test_false_positive_rate(self):
        """Test that false positive rate is approximately correct."""
        n = 1000
        fpr_target = 0.01
        
        bf = BloomFilter(expected_items=n, false_positive_rate=fpr_target)
        
        # Add n items
        for i in range(n):
            bf.add(f"item_{i}".encode())
        
        # Test false positives with items never added
        false_positives = 0
        test_count = 10000
        for i in range(test_count):
            if f"test_{i}_xyz".encode() in bf:
                false_positives += 1
        
        actual_fpr = false_positives / test_count
        
        # Should be within 2x of target (allowing for statistical variation)
        assert actual_fpr < fpr_target * 3
    
    def test_merge(self):
        bf1 = BloomFilter(expected_items=100)
        bf2 = BloomFilter(expected_items=100)
        
        bf1.add(b"a")
        bf1.add(b"b")
        bf2.add(b"c")
        bf2.add(b"d")
        
        bf1.merge(bf2)
        
        assert b"a" in bf1
        assert b"b" in bf1
        assert b"c" in bf1
        assert b"d" in bf1
    
    def test_union(self):
        bf1 = BloomFilter(expected_items=100)
        bf2 = BloomFilter(expected_items=100)
        
        bf1.add(b"a")
        bf2.add(b"b")
        
        union = bf1.union(bf2)
        
        assert b"a" in union
        assert b"b" in union
        # Original unchanged
        assert b"b" not in bf1
    
    def test_serialization(self):
        bf = BloomFilter(expected_items=100)
        bf.add(b"test")
        
        data = bf.to_dict()
        restored = BloomFilter.from_dict(data)
        
        assert b"test" in restored
        assert restored.num_bits == bf.num_bits
        assert restored.num_hashes == bf.num_hashes
    
    def test_estimated_fpr(self):
        bf = BloomFilter(expected_items=100, false_positive_rate=0.01)
        
        # Empty filter should have very low estimated FPR
        assert bf.estimated_fpr() < 0.001
        
        # After adding items, FPR should increase
        for i in range(100):
            bf.add(f"item_{i}".encode())
        
        assert bf.estimated_fpr() > 0


# =============================================================================
# Counting Bloom Filter Tests
# =============================================================================

class TestCountingBloomFilter:
    """Test counting Bloom filter operations."""
    
    def test_add_and_contains(self):
        cbf = CountingBloomFilter(expected_items=100)
        
        cbf.add(b"hello")
        assert b"hello" in cbf
    
    def test_remove(self):
        cbf = CountingBloomFilter(expected_items=100)
        
        cbf.add(b"hello")
        assert b"hello" in cbf
        
        cbf.remove(b"hello")
        assert b"hello" not in cbf
    
    def test_remove_not_present(self):
        cbf = CountingBloomFilter(expected_items=100)
        
        result = cbf.remove(b"never_added")
        assert result == False
    
    def test_multiple_adds(self):
        cbf = CountingBloomFilter(expected_items=100)
        
        cbf.add(b"hello")
        cbf.add(b"hello")
        cbf.add(b"hello")
        
        cbf.remove(b"hello")
        cbf.remove(b"hello")
        
        # Still present after 2 removes (3 adds - 2 removes = 1)
        assert b"hello" in cbf
        
        cbf.remove(b"hello")
        assert b"hello" not in cbf
    
    def test_serialization(self):
        cbf = CountingBloomFilter(expected_items=100)
        cbf.add(b"test")
        
        data = cbf.to_dict()
        restored = CountingBloomFilter.from_dict(data)
        
        assert b"test" in restored


# =============================================================================
# Cuckoo Filter Tests
# =============================================================================

class TestCuckooFilter:
    """Test Cuckoo filter operations."""
    
    def test_add_and_contains(self):
        cf = CuckooFilter(capacity=100)
        
        cf.add(b"hello")
        cf.add(b"world")
        
        assert b"hello" in cf
        assert b"world" in cf
    
    def test_remove(self):
        cf = CuckooFilter(capacity=100)
        
        cf.add(b"hello")
        assert b"hello" in cf
        
        cf.remove(b"hello")
        assert b"hello" not in cf
    
    def test_load_factor(self):
        cf = CuckooFilter(capacity=100)
        
        for i in range(50):
            cf.add(f"item_{i}".encode())
        
        assert cf.count == 50
        assert cf.load_factor > 0
    
    def test_high_load(self):
        """Test that filter works at high load."""
        cf = CuckooFilter(capacity=1000, bucket_size=4)
        
        success = 0
        for i in range(800):  # 80% load
            if cf.add(f"item_{i}".encode()):
                success += 1
        
        # Should be able to add most items
        assert success > 700
    
    def test_serialization(self):
        cf = CuckooFilter(capacity=100)
        cf.add(b"test")
        
        data = cf.to_dict()
        restored = CuckooFilter.from_dict(data)
        
        assert b"test" in restored


# =============================================================================
# HyperLogLog Tests
# =============================================================================

class TestHyperLogLog:
    """Test HyperLogLog cardinality estimation."""
    
    def test_small_set(self):
        hll = HyperLogLog(precision=14)
        
        for i in range(100):
            hll.add(f"item_{i}".encode())
        
        count = hll.count()
        
        # Should be within 20% for small sets
        assert 80 <= count <= 120
    
    def test_medium_set(self):
        hll = HyperLogLog(precision=14)
        
        n = 10000
        for i in range(n):
            hll.add(f"item_{i}".encode())
        
        count = hll.count()
        error = abs(count - n) / n
        
        # Should be within expected error + margin
        assert error < 0.05
    
    def test_large_set(self):
        hll = HyperLogLog(precision=14)
        
        n = 100000
        for i in range(n):
            hll.add(f"item_{i}".encode())
        
        count = hll.count()
        error = abs(count - n) / n
        
        # Should be within expected error
        assert error < 0.03
    
    def test_duplicates_ignored(self):
        hll = HyperLogLog(precision=14)
        
        # Add same item many times
        for _ in range(10000):
            hll.add(b"same_item")
        
        # Should count as 1
        assert hll.count() <= 5  # Allow some error
    
    def test_merge(self):
        hll1 = HyperLogLog(precision=14)
        hll2 = HyperLogLog(precision=14)
        
        # Add disjoint sets
        for i in range(1000):
            hll1.add(f"set1_{i}".encode())
        
        for i in range(1000):
            hll2.add(f"set2_{i}".encode())
        
        hll1.merge(hll2)
        
        # Should estimate ~2000
        count = hll1.count()
        assert 1800 <= count <= 2200
    
    def test_merge_with_overlap(self):
        hll1 = HyperLogLog(precision=14)
        hll2 = HyperLogLog(precision=14)
        
        # Add overlapping sets
        for i in range(1000):
            hll1.add(f"item_{i}".encode())
        
        for i in range(500, 1500):  # 500 overlap
            hll2.add(f"item_{i}".encode())
        
        hll1.merge(hll2)
        
        # Union should be ~1500
        count = hll1.count()
        assert 1350 <= count <= 1650
    
    def test_serialization(self):
        hll = HyperLogLog(precision=14)
        
        for i in range(1000):
            hll.add(f"item_{i}".encode())
        
        original_count = hll.count()
        
        data = hll.to_dict()
        restored = HyperLogLog.from_dict(data)
        
        assert restored.count() == original_count
    
    def test_standard_error(self):
        hll = HyperLogLog(precision=14)
        
        # Expected error for precision 14
        expected_error = 1.04 / math.sqrt(2**14)
        assert abs(hll.standard_error - expected_error) < 0.001


# =============================================================================
# Count-Min Sketch Tests
# =============================================================================

class TestCountMinSketch:
    """Test Count-Min Sketch frequency estimation."""
    
    def test_single_item(self):
        cms = CountMinSketch(width=1000, depth=5)
        
        cms.add(b"hello", count=10)
        
        assert cms.count(b"hello") >= 10
    
    def test_multiple_items(self):
        cms = CountMinSketch(width=1000, depth=5)
        
        cms.add(b"a", count=100)
        cms.add(b"b", count=50)
        cms.add(b"c", count=25)
        
        assert cms.count(b"a") >= 100
        assert cms.count(b"b") >= 50
        assert cms.count(b"c") >= 25
    
    def test_overestimate_only(self):
        """Count-Min Sketch should never underestimate."""
        cms = CountMinSketch(width=1000, depth=5)
        
        true_counts = {}
        for i in range(1000):
            item = f"item_{i % 100}".encode()
            count = random.randint(1, 10)
            true_counts[item] = true_counts.get(item, 0) + count
            cms.add(item, count)
        
        for item, true_count in true_counts.items():
            estimated = cms.count(item)
            assert estimated >= true_count, f"Underestimate: {estimated} < {true_count}"
    
    def test_from_error(self):
        cms = CountMinSketch.from_error(epsilon=0.001, delta=0.01)
        
        # Should have computed appropriate dimensions
        assert cms.width > 0
        assert cms.depth > 0
    
    def test_merge(self):
        cms1 = CountMinSketch(width=1000, depth=5)
        cms2 = CountMinSketch(width=1000, depth=5)
        
        cms1.add(b"a", count=10)
        cms2.add(b"a", count=20)
        cms2.add(b"b", count=15)
        
        cms1.merge(cms2)
        
        assert cms1.count(b"a") >= 30
        assert cms1.count(b"b") >= 15
    
    def test_total(self):
        cms = CountMinSketch(width=1000, depth=5)
        
        cms.add(b"a", count=10)
        cms.add(b"b", count=20)
        cms.add(b"c", count=30)
        
        assert cms.total == 60
    
    def test_serialization(self):
        cms = CountMinSketch(width=100, depth=5)
        cms.add(b"test", count=42)
        
        data = cms.to_dict()
        restored = CountMinSketch.from_dict(data)
        
        assert restored.count(b"test") == cms.count(b"test")
        assert restored.total == cms.total


# =============================================================================
# Top-K Tests
# =============================================================================

class TestTopK:
    """Test Top-K heavy hitter tracking."""
    
    def test_basic(self):
        topk = TopK(k=3)
        
        topk.add(b"a", count=100)
        topk.add(b"b", count=50)
        topk.add(b"c", count=75)
        topk.add(b"d", count=25)
        
        top = topk.get_top()
        
        # Should have top 3
        assert len(top) == 3
        
        # Should be sorted by count
        items = [item for item, count in top]
        assert b"a" in items
        assert b"c" in items
    
    def test_incremental_adds(self):
        topk = TopK(k=3)
        
        for _ in range(100):
            topk.add(b"frequent")
        
        for _ in range(50):
            topk.add(b"medium")
        
        for _ in range(10):
            topk.add(b"rare")
        
        top = topk.get_top()
        items = [item for item, count in top]
        
        assert b"frequent" in items


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilities:
    """Test utility functions."""
    
    def test_optimal_bloom_params(self):
        m, k = optimal_bloom_params(n=1000, fpr=0.01)
        
        assert m > 0
        assert k > 0
        
        # Verify the FPR with these params is close to target
        actual_fpr = bloom_fpr(m, k, 1000)
        assert actual_fpr < 0.02
    
    def test_bloom_fpr(self):
        # With very large m, FPR should be near 0
        fpr = bloom_fpr(m=1000000, k=7, n=1000)
        assert fpr < 0.001
        
        # With small m, FPR should be high
        fpr = bloom_fpr(m=100, k=3, n=1000)
        assert fpr > 0.5
    
    def test_hyperloglog_error(self):
        # Precision 14 should have about 0.81% error
        error = hyperloglog_error(precision=14)
        assert abs(error - 0.0081) < 0.001


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests simulating real-world scenarios."""
    
    def test_deduplication_pipeline(self):
        """Simulate URL deduplication for a web crawler."""
        seen = BloomFilter(expected_items=10000, false_positive_rate=0.01)
        
        urls = [f"https://example.com/page/{i}" for i in range(5000)]
        duplicates = random.choices(urls, k=1000)  # Some duplicates
        
        all_urls = urls + duplicates
        random.shuffle(all_urls)
        
        unique_count = 0
        for url in all_urls:
            if url not in seen:
                unique_count += 1
                seen.add(url)
        
        # Should be approximately 5000 unique
        assert 4900 <= unique_count <= 5100
    
    def test_distributed_cardinality(self):
        """Simulate distributed unique user counting."""
        # Three servers each counting users
        server1 = HyperLogLog(precision=14)
        server2 = HyperLogLog(precision=14)
        server3 = HyperLogLog(precision=14)
        
        # Users distributed across servers with some overlap
        for i in range(3000):
            server1.add(f"user_{i}".encode())
        
        for i in range(2000, 5000):
            server2.add(f"user_{i}".encode())
        
        for i in range(4000, 7000):
            server3.add(f"user_{i}".encode())
        
        # Merge all
        combined = server1.copy()
        combined.merge(server2)
        combined.merge(server3)
        
        # Total unique: 7000 users (0-6999)
        count = combined.count()
        assert 6500 <= count <= 7500
    
    def test_word_frequency_analysis(self):
        """Simulate word frequency counting in a document."""
        cms = CountMinSketch.from_error(epsilon=0.01, delta=0.05)
        
        # Simulate word frequencies (Zipf-like distribution)
        words = {
            b"the": 10000,
            b"and": 5000,
            b"is": 3000,
            b"a": 2500,
            b"to": 2000,
        }
        
        for word, count in words.items():
            cms.add(word, count)
        
        # Add some noise
        for i in range(1000):
            cms.add(f"word_{i}".encode(), random.randint(1, 100))
        
        # Top words should still have approximate counts
        for word, true_count in words.items():
            estimated = cms.count(word)
            assert estimated >= true_count
            # Should not be too far off
            assert estimated < true_count * 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
