#!/usr/bin/env python3
"""
Sketch Usage Examples

Demonstrates real-world usage of probabilistic data structures.
"""

import random
from sketch import (
    BloomFilter,
    CountingBloomFilter,
    CuckooFilter,
    HyperLogLog,
    CountMinSketch,
    TopK,
    optimal_bloom_params,
    bloom_fpr,
)


def example_bloom_filter():
    """
    Example 1: Bloom Filter for URL Deduplication
    """
    print("=" * 60)
    print("Example 1: Bloom Filter - Web Crawler Deduplication")
    print("=" * 60)
    
    # Create filter for 1 million URLs with 1% false positive rate
    seen_urls = BloomFilter(expected_items=1_000_000, false_positive_rate=0.01)
    
    print(f"\nFilter parameters:")
    print(f"  Bits: {seen_urls.num_bits:,} ({seen_urls.size_bytes:,} bytes)")
    print(f"  Hash functions: {seen_urls.num_hashes}")
    print(f"  Target FPR: {seen_urls.false_positive_rate:.2%}")
    
    # Simulate crawling
    urls_to_crawl = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page1",  # Duplicate
        "https://example.com/page3",
        "https://example.com/page2",  # Duplicate
    ]
    
    print(f"\nProcessing URLs:")
    for url in urls_to_crawl:
        if url in seen_urls:
            print(f"  SKIP (seen): {url}")
        else:
            print(f"  CRAWL (new): {url}")
            seen_urls.add(url)
    
    print(f"\nUnique URLs crawled: {seen_urls.count}")
    print(f"Estimated FPR: {seen_urls.estimated_fpr():.4%}")
    print()


def example_counting_bloom():
    """
    Example 2: Counting Bloom Filter with Removal
    """
    print("=" * 60)
    print("Example 2: Counting Bloom Filter - Session Tracking")
    print("=" * 60)
    
    active_sessions = CountingBloomFilter(expected_items=10000)
    
    print("\nTracking active sessions:")
    
    # Users log in
    active_sessions.add("user:alice")
    active_sessions.add("user:bob")
    active_sessions.add("user:charlie")
    
    print(f"  After logins: {active_sessions.count} active")
    print(f"  Alice active? {'user:alice' in active_sessions}")
    
    # Alice logs out
    active_sessions.remove("user:alice")
    
    print(f"  After Alice logout: {active_sessions.count} active")
    print(f"  Alice active? {'user:alice' in active_sessions}")
    print(f"  Bob active? {'user:bob' in active_sessions}")
    print()


def example_cuckoo_filter():
    """
    Example 3: Cuckoo Filter - Better Space Efficiency
    """
    print("=" * 60)
    print("Example 3: Cuckoo Filter - IP Blocklist")
    print("=" * 60)
    
    blocklist = CuckooFilter(capacity=10000, fingerprint_bits=12)
    
    print(f"\nFilter capacity: {blocklist.capacity}")
    print(f"Expected FPR: {blocklist.estimated_fpr():.4%}")
    
    # Block some IPs
    blocked_ips = [
        "192.168.1.100",
        "10.0.0.50",
        "172.16.0.1",
    ]
    
    for ip in blocked_ips:
        blocklist.add(ip.encode())
    
    print(f"\nBlocked {blocklist.count} IPs")
    
    # Check incoming IPs
    test_ips = [
        ("192.168.1.100", True),   # Blocked
        ("192.168.1.101", False),  # Not blocked
        ("10.0.0.50", True),       # Blocked
        ("8.8.8.8", False),        # Not blocked
    ]
    
    print("\nChecking incoming connections:")
    for ip, expected_blocked in test_ips:
        is_blocked = ip.encode() in blocklist
        status = "BLOCKED" if is_blocked else "ALLOWED"
        print(f"  {ip}: {status}")
    
    # Remove an IP from blocklist
    print("\nRemoving 192.168.1.100 from blocklist...")
    blocklist.remove("192.168.1.100".encode())
    print(f"  192.168.1.100 blocked? {'192.168.1.100'.encode() in blocklist}")
    print()


def example_hyperloglog():
    """
    Example 4: HyperLogLog - Unique Visitor Counting
    """
    print("=" * 60)
    print("Example 4: HyperLogLog - Unique Visitors")
    print("=" * 60)
    
    # Daily visitor counters for 3 servers
    server_us = HyperLogLog(precision=14)
    server_eu = HyperLogLog(precision=14)
    server_asia = HyperLogLog(precision=14)
    
    print(f"\nHyperLogLog parameters:")
    print(f"  Registers: {server_us.num_registers:,}")
    print(f"  Memory: {server_us.size_bytes:,} bytes")
    print(f"  Standard error: {server_us.standard_error:.2%}")
    
    # Simulate visitors (with some overlap between regions)
    print("\nSimulating visitors...")
    
    # US visitors: 0-9999
    for i in range(10000):
        server_us.add(f"user_{i}".encode())
    
    # EU visitors: 5000-14999 (5000 overlap with US)
    for i in range(5000, 15000):
        server_eu.add(f"user_{i}".encode())
    
    # Asia visitors: 12000-17999 (3000 overlap with EU)
    for i in range(12000, 18000):
        server_asia.add(f"user_{i}".encode())
    
    print(f"\n  US server estimate: {server_us.count():,} visitors")
    print(f"  EU server estimate: {server_eu.count():,} visitors")
    print(f"  Asia server estimate: {server_asia.count():,} visitors")
    
    # Merge for global count
    global_visitors = server_us.copy()
    global_visitors.merge(server_eu)
    global_visitors.merge(server_asia)
    
    true_unique = 18000  # 0-17999
    estimated = global_visitors.count()
    error = abs(estimated - true_unique) / true_unique
    
    print(f"\n  Global unique visitors:")
    print(f"    Estimated: {estimated:,}")
    print(f"    Actual: {true_unique:,}")
    print(f"    Error: {error:.2%}")
    print()


def example_count_min_sketch():
    """
    Example 5: Count-Min Sketch - Frequency Estimation
    """
    print("=" * 60)
    print("Example 5: Count-Min Sketch - API Rate Tracking")
    print("=" * 60)
    
    # Track API calls per endpoint
    api_calls = CountMinSketch.from_error(epsilon=0.001, delta=0.01)
    
    print(f"\nSketch dimensions: {api_calls.width} × {api_calls.depth}")
    print(f"Memory: {api_calls.size_bytes:,} bytes")
    
    # Simulate API traffic
    endpoints = {
        "/api/users": 50000,
        "/api/products": 30000,
        "/api/orders": 20000,
        "/api/search": 15000,
        "/api/auth": 10000,
    }
    
    print("\nSimulating API traffic...")
    for endpoint, calls in endpoints.items():
        api_calls.add(endpoint.encode(), calls)
    
    print(f"\nTotal API calls: {api_calls.total:,}")
    
    print("\nFrequency estimates:")
    for endpoint, true_count in endpoints.items():
        estimated = api_calls.count(endpoint.encode())
        print(f"  {endpoint}: {estimated:,} (actual: {true_count:,})")
    print()


def example_topk():
    """
    Example 6: Top-K Heavy Hitters
    """
    print("=" * 60)
    print("Example 6: Top-K - Popular Search Terms")
    print("=" * 60)
    
    # Track top 5 search terms
    popular_searches = TopK(k=5, epsilon=0.0001)
    
    # Simulate search queries with Zipf-like distribution
    search_terms = [
        (b"python tutorial", 10000),
        (b"javascript", 8000),
        (b"machine learning", 6000),
        (b"docker", 4000),
        (b"kubernetes", 3500),
        (b"react hooks", 3000),
        (b"golang", 2500),
        (b"rust programming", 2000),
        (b"aws lambda", 1500),
        (b"terraform", 1000),
    ]
    
    print("\nProcessing search queries...")
    for term, count in search_terms:
        popular_searches.add(term, count)
    
    print("\nTop 5 search terms:")
    for rank, (term, count) in enumerate(popular_searches.get_top(), 1):
        print(f"  {rank}. {term.decode()}: ~{count:,} searches")
    print()


def example_distributed_merge():
    """
    Example 7: Merging Sketches from Distributed Nodes
    """
    print("=" * 60)
    print("Example 7: Distributed Sketch Merging")
    print("=" * 60)
    
    # Three nodes tracking page views
    node1 = CountMinSketch(width=1000, depth=5)
    node2 = CountMinSketch(width=1000, depth=5)
    node3 = CountMinSketch(width=1000, depth=5)
    
    # Each node sees different pages (with some overlap)
    pages = [
        "/home",
        "/products",
        "/about",
        "/contact",
    ]
    
    print("\nEach node records page views...")
    
    for i in range(1000):
        page = random.choice(pages).encode()
        count = random.randint(1, 10)
        
        # Randomly route to a node
        node = random.choice([node1, node2, node3])
        node.add(page, count)
    
    print(f"  Node 1 total: {node1.total}")
    print(f"  Node 2 total: {node2.total}")
    print(f"  Node 3 total: {node3.total}")
    
    # Merge all nodes
    combined = node1.copy()
    combined.merge(node2)
    combined.merge(node3)
    
    print(f"\nCombined total: {combined.total}")
    print("\nCombined page view estimates:")
    for page in pages:
        print(f"  {page}: ~{combined.count(page.encode())}")
    print()


def example_space_comparison():
    """
    Example 8: Space Comparison - Exact vs Probabilistic
    """
    print("=" * 60)
    print("Example 8: Space Comparison")
    print("=" * 60)
    
    n = 1_000_000  # 1 million items
    
    # Exact set (Python set)
    # Average string length ~20 bytes, plus set overhead
    exact_memory = n * 50  # Rough estimate: 50 bytes per entry
    
    # Bloom filter for membership (1% FPR)
    bf = BloomFilter(expected_items=n, false_positive_rate=0.01)
    bloom_memory = bf.size_bytes
    
    # HyperLogLog for cardinality
    hll = HyperLogLog(precision=14)
    hll_memory = hll.size_bytes
    
    # Count-Min Sketch for frequency (0.1% error)
    cms = CountMinSketch.from_error(epsilon=0.001, delta=0.01)
    cms_memory = cms.size_bytes
    
    print(f"\nFor {n:,} items:")
    print(f"\n  Exact set (membership):     ~{exact_memory:>12,} bytes")
    print(f"  Bloom filter (1% FPR):       {bloom_memory:>12,} bytes")
    print(f"  Savings: {(1 - bloom_memory/exact_memory)*100:.1f}%")
    
    print(f"\n  Exact count (cardinality):  ~{exact_memory:>12,} bytes")
    print(f"  HyperLogLog ({hll.standard_error:.2%} error):  {hll_memory:>12,} bytes")
    print(f"  Savings: {(1 - hll_memory/exact_memory)*100:.2f}%")
    
    print(f"\n  Exact frequency (dict):     ~{exact_memory:>12,} bytes")
    print(f"  Count-Min (0.1% error):      {cms_memory:>12,} bytes")
    print(f"  Savings: {(1 - cms_memory/exact_memory)*100:.1f}%")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  SKETCH - PROBABILISTIC DATA STRUCTURES EXAMPLES")
    print("=" * 60 + "\n")
    
    example_bloom_filter()
    example_counting_bloom()
    example_cuckoo_filter()
    example_hyperloglog()
    example_count_min_sketch()
    example_topk()
    example_distributed_merge()
    example_space_comparison()
    
    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
