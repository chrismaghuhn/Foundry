#!/usr/bin/env python3
"""
Styx Usage Examples

Demonstrates real-world scenarios for the Styx secret sharing library.
"""

import asyncio
from styx import (
    Styx,
    SecretSharer,
    Peer,
    generate_hmac_key,
    shares_to_hex,
    shares_from_hex,
)


def example_basic_split_and_reconstruct():
    """
    Example 1: Basic Secret Splitting
    
    Split an encryption key so that any 3 of 5 custodians can recover it.
    """
    print("=" * 60)
    print("Example 1: Basic Split and Reconstruct")
    print("=" * 60)
    
    # Generate a consistent HMAC key (in production, persist this securely)
    hmac_key = generate_hmac_key()
    
    # Create the sharer
    sharer = SecretSharer(hmac_key=hmac_key)
    
    # The secret: could be an AES key, API token, etc.
    secret = b"super-secret-encryption-key-256!"
    print(f"Original secret: {secret}")
    
    # Split into 5 shares, any 3 can reconstruct
    shares = sharer.split(secret, n=5, k=3)
    
    print(f"\nGenerated {len(shares)} shares (threshold: 3)")
    for share in shares:
        print(f"  Share {share.index}: {len(share.data)} bytes, HMAC: {share.hmac[:8].hex()}...")
    
    # Simulate: Only custodians 1, 3, and 5 are available
    available_shares = [shares[0], shares[2], shares[4]]
    print(f"\nReconstructing with shares: {[s.index for s in available_shares]}")
    
    recovered = sharer.reconstruct(available_shares)
    print(f"Recovered secret: {recovered}")
    
    assert recovered == secret
    print("✓ Success! Secret recovered correctly.\n")


def example_share_serialization():
    """
    Example 2: Serialize Shares for Storage
    
    Convert shares to hex strings for storage in databases, files, or QR codes.
    """
    print("=" * 60)
    print("Example 2: Share Serialization")
    print("=" * 60)
    
    sharer = SecretSharer(hmac_key=b"storage-example-key-32-bytes!!!!")
    
    secret = b"API_KEY_12345"
    shares = sharer.split(secret, n=3, k=2)
    
    # Convert to hex for storage
    hex_shares = shares_to_hex(shares)
    
    print("Shares as hex strings (for database/file storage):")
    for i, hex_str in enumerate(hex_shares):
        print(f"  Share {i + 1}: {hex_str[:40]}...")
    
    # Later: restore from hex
    restored_shares = shares_from_hex(hex_shares)
    
    # Reconstruct
    recovered = sharer.reconstruct(restored_shares[:2])
    print(f"\nRecovered from serialized shares: {recovered}")
    
    assert recovered == secret
    print("✓ Success! Serialization roundtrip works.\n")


async def example_distributed_collection():
    """
    Example 3: Distributed Share Collection
    
    Simulate collecting shares from multiple network peers.
    """
    print("=" * 60)
    print("Example 3: Distributed Share Collection")
    print("=" * 60)
    
    async with Styx() as styx:
        secret = b"distributed-system-master-key"
        
        # Define our peer network (in production: real IP addresses)
        peers = [
            Peer(peer_id="datacenter-us-east", address="10.0.1.1", port=8443),
            Peer(peer_id="datacenter-us-west", address="10.0.2.1", port=8443),
            Peer(peer_id="datacenter-eu", address="10.0.3.1", port=8443),
            Peer(peer_id="datacenter-asia", address="10.0.4.1", port=8443),
            Peer(peer_id="cold-storage", address="10.0.5.1", port=8443),
        ]
        
        # Split secret: need 3 of 5 datacenters to recover
        shares = styx.split(secret, n=5, k=3)
        print(f"Split secret into {len(shares)} shares (threshold: 3)")
        
        # Distribute to peers
        print("\nDistributing shares to peers...")
        results = await styx.distribute(shares, peers)
        
        for peer_id, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {peer_id}")
        
        # Simulate: only 3 datacenters respond
        available_peers = peers[:3]
        print(f"\nCollecting from available peers: {[p.peer_id for p in available_peers]}")
        
        collection = await styx.collect(
            available_peers, 
            threshold=3,
            timeout_per_peer=5.0
        )
        
        print(f"Collection result: {'success' if collection.success else 'failed'}")
        print(f"  Shares collected: {len(collection.shares)}")
        print(f"  Time elapsed: {collection.elapsed_seconds:.3f}s")
        
        if collection.success:
            recovered = styx.reconstruct(collection.shares)
            print(f"  Recovered secret: {recovered}")
            assert recovered == secret
            print("✓ Success! Distributed reconstruction works.\n")


def example_key_escrow():
    """
    Example 4: Cryptographic Key Escrow
    
    Real-world scenario: Company wants to escrow their signing key
    with executives and legal counsel.
    """
    print("=" * 60)
    print("Example 4: Corporate Key Escrow")
    print("=" * 60)
    
    # The company's code signing key
    signing_key = b"-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg..."  # Truncated for example
    
    # Corporate escrow policy: Need 3 of 5 custodians
    # Custodians: CEO, CFO, CTO, General Counsel, Board Chair
    custodians = ["CEO", "CFO", "CTO", "Legal", "Board"]
    
    # HMAC key should be derived from company master secret
    hmac_key = b"company-master-escrow-key-2024!!"
    sharer = SecretSharer(hmac_key=hmac_key)
    
    # Split the key
    shares = sharer.split(signing_key, n=5, k=3)
    
    print("Key Escrow Distribution:")
    for custodian, share in zip(custodians, shares):
        # In production: encrypt share with custodian's public key
        print(f"  {custodian}: Share #{share.index} ({len(share.data)} bytes)")
    
    # Scenario: CEO is unavailable, need emergency access
    available_custodians = ["CFO", "CTO", "Legal"]
    available_shares = [shares[1], shares[2], shares[3]]  # CFO, CTO, Legal
    
    print(f"\nEmergency Recovery (available: {available_custodians})")
    recovered_key = sharer.reconstruct(available_shares)
    
    assert recovered_key == signing_key
    print("✓ Key successfully recovered by 3 custodians.\n")


def example_dead_mans_switch():
    """
    Example 5: Dead Man's Switch / Digital Inheritance
    
    Scenario: Distribute access credentials to trusted parties,
    requiring multiple to collaborate to access the vault.
    """
    print("=" * 60)
    print("Example 5: Digital Inheritance Vault")
    print("=" * 60)
    
    # The vault passphrase
    vault_passphrase = b"correct-horse-battery-staple-42"
    
    # Beneficiaries
    beneficiaries = {
        "spouse": 2,      # Gets 2 shares (most trusted)
        "child_1": 1,     # Each child gets 1 share
        "child_2": 1,
        "attorney": 1,    # Attorney holds 1 share
        "bank": 1,        # Bank holds 1 share
    }
    
    total_shares = sum(beneficiaries.values())  # 6 shares
    threshold = 3  # Need 3 shares to access
    
    hmac_key = b"inheritance-vault-key-secure!!!!"
    sharer = SecretSharer(hmac_key=hmac_key)
    
    shares = sharer.split(vault_passphrase, n=total_shares, k=threshold)
    
    print(f"Vault Configuration: {threshold} of {total_shares} shares needed")
    print("\nShare Distribution:")
    
    share_idx = 0
    distribution = {}
    for beneficiary, count in beneficiaries.items():
        beneficiary_shares = shares[share_idx:share_idx + count]
        distribution[beneficiary] = beneficiary_shares
        print(f"  {beneficiary}: {count} share(s) - indices {[s.index for s in beneficiary_shares]}")
        share_idx += count
    
    # Scenario 1: Spouse alone cannot access (only 2 shares)
    print("\n--- Scenario 1: Spouse alone ---")
    try:
        sharer.reconstruct(distribution["spouse"])
        print("  ✗ Incorrectly allowed access")
    except Exception as e:
        print(f"  ✓ Access denied (need {threshold} shares, have 2)")
    
    # Scenario 2: Spouse + Attorney can access (2 + 1 = 3)
    print("\n--- Scenario 2: Spouse + Attorney ---")
    combined = distribution["spouse"] + distribution["attorney"]
    recovered = sharer.reconstruct(combined)
    print(f"  ✓ Access granted! Passphrase: {recovered.decode()}")
    
    # Scenario 3: Both children + bank (1 + 1 + 1 = 3)
    print("\n--- Scenario 3: Children + Bank ---")
    combined = distribution["child_1"] + distribution["child_2"] + distribution["bank"]
    recovered = sharer.reconstruct(combined)
    print(f"  ✓ Access granted! Passphrase: {recovered.decode()}")
    
    print("\n✓ Dead man's switch configured successfully.\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  STYX SECRET SHARING LIBRARY - EXAMPLES")
    print("=" * 60 + "\n")
    
    # Synchronous examples
    example_basic_split_and_reconstruct()
    example_share_serialization()
    example_key_escrow()
    example_dead_mans_switch()
    
    # Async example
    await example_distributed_collection()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
