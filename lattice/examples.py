#!/usr/bin/env python3
"""
Lattice Usage Examples

Demonstrates real-world usage of Conflict-Free Replicated Data Types.
"""

import time
from lattice import (
    GCounter,
    PNCounter,
    LWWRegister,
    MVRegister,
    GSet,
    TwoPSet,
    ORSet,
    LWWSet,
    ORMap,
    merge_all,
)


def example_gcounter():
    """
    Example 1: Grow-Only Counter (Page Views)
    """
    print("=" * 60)
    print("Example 1: GCounter - Distributed Page Views")
    print("=" * 60)
    
    # Three web servers tracking page views
    server_us = GCounter("us-east")
    server_eu = GCounter("eu-west")
    server_asia = GCounter("asia-pac")
    
    # Each server records local views
    print("\nLocal increments:")
    server_us.increment(1500)
    print(f"  US server: {server_us.value} views")
    
    server_eu.increment(2300)
    print(f"  EU server: {server_eu.value} views")
    
    server_asia.increment(1800)
    print(f"  Asia server: {server_asia.value} views")
    
    # Merge all counts
    print("\nAfter merging all servers:")
    server_us.merge(server_eu)
    server_us.merge(server_asia)
    print(f"  Total views: {server_us.value}")
    
    # Idempotent: merging again doesn't change result
    server_us.merge(server_eu)
    print(f"  After re-merge: {server_us.value} (unchanged)")
    print()


def example_pncounter():
    """
    Example 2: Positive-Negative Counter (Vote System)
    """
    print("=" * 60)
    print("Example 2: PNCounter - Reddit-Style Votes")
    print("=" * 60)
    
    # Vote counters on different servers
    votes_a = PNCounter("server-a")
    votes_b = PNCounter("server-b")
    
    print("\nUsers voting through different servers:")
    
    # Server A receives votes
    votes_a.increment(150)  # 150 upvotes
    votes_a.decrement(30)   # 30 downvotes
    print(f"  Server A: +150/-30 = {votes_a.value}")
    
    # Server B receives votes
    votes_b.increment(80)   # 80 upvotes  
    votes_b.decrement(20)   # 20 downvotes
    print(f"  Server B: +80/-20 = {votes_b.value}")
    
    # Merge
    votes_a.merge(votes_b)
    print(f"\nMerged score: {votes_a.value}")
    print(f"  (150+80 upvotes - 30+20 downvotes = 180)")
    print()


def example_lww_register():
    """
    Example 3: Last-Writer-Wins Register (User Profile)
    """
    print("=" * 60)
    print("Example 3: LWWRegister - User Profile Field")
    print("=" * 60)
    
    # User edits profile from two devices
    phone = LWWRegister[str]("phone")
    laptop = LWWRegister[str]("laptop")
    
    print("\nUser updates email from phone:")
    phone.set("user@gmail.com")
    print(f"  Phone: {phone.value}")
    
    time.sleep(0.01)  # Ensure different timestamp
    
    print("\nUser updates email from laptop (later):")
    laptop.set("user@work.com")
    print(f"  Laptop: {laptop.value}")
    
    # Sync
    phone.merge(laptop)
    laptop.merge(phone)
    
    print(f"\nAfter sync:")
    print(f"  Phone sees: {phone.value}")
    print(f"  Laptop sees: {laptop.value}")
    print(f"  (Later write wins)")
    print()


def example_mv_register():
    """
    Example 4: Multi-Value Register (Conflict Detection)
    """
    print("=" * 60)
    print("Example 4: MVRegister - Conflict Detection")
    print("=" * 60)
    
    # Two users edit document title concurrently
    alice = MVRegister[str]("alice")
    bob = MVRegister[str]("bob")
    
    print("\nAlice and Bob edit title concurrently:")
    alice.set("Project Alpha")
    bob.set("Project Beta")
    print(f"  Alice: {alice.value}")
    print(f"  Bob: {bob.value}")
    
    # Merge - both values kept
    alice.merge(bob)
    
    print(f"\nAfter merge (conflict detected):")
    print(f"  Values: {alice.value}")
    print(f"  Is conflicted: {alice.is_conflicted}")
    
    # Resolve conflict
    print(f"\nAlice resolves conflict:")
    alice.set("Project Alpha-Beta")
    print(f"  Final: {alice.value}")
    print(f"  Is conflicted: {alice.is_conflicted}")
    print()


def example_gset():
    """
    Example 5: Grow-Only Set (Tag Collection)
    """
    print("=" * 60)
    print("Example 5: GSet - Collecting Tags")
    print("=" * 60)
    
    # Multiple servers collecting article tags
    tags_a = GSet[str]("server-a")
    tags_b = GSet[str]("server-b")
    
    tags_a.add("python")
    tags_a.add("programming")
    tags_a.add("tutorial")
    print(f"Server A tags: {tags_a.value}")
    
    tags_b.add("python")
    tags_b.add("crdt")
    tags_b.add("distributed")
    print(f"Server B tags: {tags_b.value}")
    
    # Merge = union
    tags_a.merge(tags_b)
    print(f"\nMerged tags: {tags_a.value}")
    print()


def example_twopset():
    """
    Example 6: Two-Phase Set (One-Time Removal)
    """
    print("=" * 60)
    print("Example 6: TwoPSet - Permanent Removal")
    print("=" * 60)
    
    # Banned users list (once banned, stays banned)
    banned_a = TwoPSet[str]("server-a")
    banned_b = TwoPSet[str]("server-b")
    
    print("Server A bans 'spammer123':")
    banned_a.add("spammer123")
    banned_a.add("troll456")
    print(f"  Banned: {banned_a.value}")
    
    print("\nServer B unbans 'spammer123' (decision reversed):")
    banned_b.merge(banned_a)
    banned_b.remove("spammer123")
    print(f"  Banned on B: {banned_b.value}")
    
    print("\nLater, trying to re-add 'spammer123' on A:")
    banned_a.add("spammer123")  # Won't work - once removed, stays removed
    banned_a.merge(banned_b)
    print(f"  Banned on A: {banned_a.value}")
    print(f"  (spammer123 stays removed - TwoPSet is permanent)")
    print()


def example_orset():
    """
    Example 7: Observed-Remove Set (Shopping Cart)
    """
    print("=" * 60)
    print("Example 7: ORSet - Shopping Cart")
    print("=" * 60)
    
    # Shopping cart on two devices
    phone = ORSet[str]("phone")
    tablet = ORSet[str]("tablet")
    
    print("Adding items on phone:")
    phone.add("milk")
    phone.add("bread")
    phone.add("eggs")
    print(f"  Phone cart: {phone.value}")
    
    # Sync to tablet
    tablet.merge(phone)
    print(f"\nTablet synced: {tablet.value}")
    
    # Concurrent edits
    print("\nConcurrent edits:")
    print("  Phone removes 'milk'")
    phone.remove("milk")
    
    print("  Tablet re-adds 'milk' and adds 'cheese'")
    tablet.add("milk")
    tablet.add("cheese")
    
    # Merge
    phone.merge(tablet)
    tablet.merge(phone)
    
    print(f"\nAfter sync:")
    print(f"  Phone: {phone.value}")
    print(f"  Tablet: {tablet.value}")
    print(f"  (milk survives - add wins over concurrent remove)")
    print()


def example_lwwset():
    """
    Example 8: Last-Writer-Wins Set (Following List)
    """
    print("=" * 60)
    print("Example 8: LWWSet - Social Media Following")
    print("=" * 60)
    
    following = LWWSet[str]("user-device")
    
    print("Managing followed accounts:")
    following.add("@tech_news")
    following.add("@sports")
    following.add("@music")
    print(f"  Following: {following.value}")
    
    time.sleep(0.01)
    
    print("\nUnfollowing @sports:")
    following.remove("@sports")
    print(f"  Following: {following.value}")
    
    time.sleep(0.01)
    
    print("\nRe-following @sports:")
    following.add("@sports")
    print(f"  Following: {following.value}")
    print()


def example_ormap():
    """
    Example 9: Observed-Remove Map (User Scores)
    """
    print("=" * 60)
    print("Example 9: ORMap - Game Leaderboard")
    print("=" * 60)
    
    # Game scores tracked across servers
    scores_a = ORMap[str, PNCounter]("server-a", lambda: PNCounter("shared"))
    scores_b = ORMap[str, PNCounter]("server-b", lambda: PNCounter("shared"))
    
    print("Server A tracking scores:")
    scores_a["alice"].increment(100)
    scores_a["bob"].increment(50)
    print(f"  alice: {scores_a['alice'].value}")
    print(f"  bob: {scores_a['bob'].value}")
    
    print("\nServer B tracking scores:")
    scores_b["alice"].increment(25)  # Alice gets more points
    scores_b["charlie"].increment(75)  # New player
    print(f"  alice: {scores_b['alice'].value}")
    print(f"  charlie: {scores_b['charlie'].value}")
    
    # Merge
    scores_a.merge(scores_b)
    
    print(f"\nMerged leaderboard:")
    for player in sorted(scores_a.keys()):
        print(f"  {player}: {scores_a[player].value}")
    print()


def example_distributed_shopping():
    """
    Example 10: Real-World Scenario - Distributed Shopping Cart
    """
    print("=" * 60)
    print("Example 10: Full Shopping Cart Scenario")
    print("=" * 60)
    
    # Three replicas of shopping cart
    cart_mobile = ORSet[str]("mobile")
    cart_web = ORSet[str]("web")
    cart_pos = ORSet[str]("point-of-sale")  # In-store kiosk
    
    print("Customer browses on mobile:")
    cart_mobile.add("laptop")
    cart_mobile.add("mouse")
    cart_mobile.add("keyboard")
    print(f"  Mobile: {cart_mobile.value}")
    
    # Sync to web
    cart_web.merge(cart_mobile)
    
    print("\nCustomer continues on web (removes mouse, adds monitor):")
    cart_web.remove("mouse")
    cart_web.add("monitor")
    print(f"  Web: {cart_web.value}")
    
    print("\nMeanwhile, mobile adds mouse back and webcam (offline):")
    cart_mobile.add("mouse")  # Concurrent with web's remove
    cart_mobile.add("webcam")
    print(f"  Mobile (offline): {cart_mobile.value}")
    
    print("\nIn-store kiosk gets partial sync from web:")
    cart_pos.merge(cart_web)
    cart_pos.add("usb-hub")
    print(f"  POS: {cart_pos.value}")
    
    print("\nFinal sync - all devices merge:")
    cart_mobile.merge(cart_web)
    cart_mobile.merge(cart_pos)
    cart_web.merge(cart_mobile)
    cart_pos.merge(cart_mobile)
    
    print(f"\n  Final cart (all devices agree):")
    print(f"    Mobile: {cart_mobile.value}")
    print(f"    Web: {cart_web.value}")
    print(f"    POS: {cart_pos.value}")
    
    assert cart_mobile.value == cart_web.value == cart_pos.value
    print(f"\n  ✓ All replicas converged!")
    print()


def example_merge_utility():
    """
    Example 11: Merge Multiple CRDTs
    """
    print("=" * 60)
    print("Example 11: merge_all Utility")
    print("=" * 60)
    
    counters = [
        GCounter(f"node-{i}") for i in range(5)
    ]
    
    # Each counter increments
    for i, counter in enumerate(counters):
        counter.increment((i + 1) * 10)
        print(f"  Node {i}: {counter.value}")
    
    # Merge all at once
    result = merge_all(*counters)
    
    print(f"\nMerged total: {result.value}")
    print(f"  (10 + 20 + 30 + 40 + 50 = 150)")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  LATTICE - CRDT EXAMPLES")
    print("=" * 60 + "\n")
    
    example_gcounter()
    example_pncounter()
    example_lww_register()
    example_mv_register()
    example_gset()
    example_twopset()
    example_orset()
    example_lwwset()
    example_ormap()
    example_distributed_shopping()
    example_merge_utility()
    
    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
