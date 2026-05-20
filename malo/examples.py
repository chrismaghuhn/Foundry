#!/usr/bin/env python3
"""
MALO Usage Examples

Demonstrates real-world scenarios for the Merkle Append-Only Log.
"""

import asyncio
import json
from malo import (
    MerkleLog,
    MerkleVerifier,
    AuditLog,
    InclusionProof,
    ConsistencyProof,
    hash_leaf,
)


async def example_basic_log():
    """
    Example 1: Basic Merkle Log Operations
    """
    print("=" * 60)
    print("Example 1: Basic Merkle Log")
    print("=" * 60)
    
    log = MerkleLog()
    
    print("\nAppending entries:")
    entries = [b"Transaction: Alice -> Bob: $100",
               b"Transaction: Bob -> Charlie: $50", 
               b"Transaction: Charlie -> Alice: $25"]
    
    for entry in entries:
        root = await log.append(entry)
        print(f"  Added: {entry.decode()}")
        print(f"    Root: {root.hex()[:32]}...")
        print(f"    Size: {root.size}")
    
    print(f"\nFinal log size: {log.size}")
    print(f"Final root: {log.root.hex()}")
    print()


async def example_inclusion_proofs():
    """
    Example 2: Generating and Verifying Inclusion Proofs
    """
    print("=" * 60)
    print("Example 2: Inclusion Proofs")
    print("=" * 60)
    
    log = MerkleLog()
    
    # Build a log
    entries = [f"Entry {i}".encode() for i in range(8)]
    for entry in entries:
        await log.append(entry)
    
    print(f"\nLog with {log.size} entries")
    print(f"Root: {log.root.hex()[:32]}...")
    
    # Generate proof for entry 3
    proof = log.get_inclusion_proof(3)
    
    print(f"\nInclusion proof for index 3:")
    print(f"  Entry hash: {proof.entry_hash.hex()[:32]}...")
    print(f"  Siblings: {len(proof.siblings)} hashes")
    
    # Verify the proof
    is_valid = MerkleVerifier.verify_inclusion(b"Entry 3", proof)
    print(f"  Valid: {is_valid}")
    
    # Try with wrong data
    is_valid_wrong = MerkleVerifier.verify_inclusion(b"Wrong Entry", proof)
    print(f"  Valid with wrong data: {is_valid_wrong}")
    
    print()


async def example_audit_log():
    """
    Example 3: High-Level Audit Log API
    """
    print("=" * 60)
    print("Example 3: Audit Log API")
    print("=" * 60)
    
    log = AuditLog()
    
    # Log some events
    print("\nLogging events:")
    
    events = [
        {"action": "login", "user": "alice", "ip": "192.168.1.1"},
        {"action": "view_file", "user": "alice", "file": "secrets.txt"},
        {"action": "download", "user": "alice", "file": "secrets.txt"},
        {"action": "logout", "user": "alice"},
    ]
    
    for event in events:
        entry = await log.append(json.dumps(event).encode())
        print(f"  [{entry.index}] {event['action']} - Root: {entry.root.hex()[:16]}...")
    
    print(f"\nTotal entries: {log.size}")
    
    # Retrieve an entry
    entry = log.get_entry(2)
    print(f"\nEntry at index 2:")
    print(f"  Data: {entry.data.decode()}")
    print(f"  Timestamp: {entry.timestamp}")
    
    # Get proof for auditors
    proof = log.get_proof(2)
    print(f"\nProof for entry 2:")
    print(f"  Index: {proof.index}")
    print(f"  Siblings: {len(proof.siblings)}")
    
    # Verify offline
    is_valid = AuditLog.verify(entry.data, proof)
    print(f"  Verification: {'PASS' if is_valid else 'FAIL'}")
    
    print()


async def example_checkpoints():
    """
    Example 4: Checkpoints and Consistency Proofs
    """
    print("=" * 60)
    print("Example 4: Checkpoints & Consistency")
    print("=" * 60)
    
    log = AuditLog()
    
    # Phase 1: Initial entries
    print("\nPhase 1: Adding initial entries")
    for i in range(4):
        await log.append(f"Entry {i}".encode())
    
    # Create checkpoint
    checkpoint1 = log.checkpoint()
    print(f"  Checkpoint 1: size={checkpoint1.size}, root={checkpoint1.hex()[:16]}...")
    
    # Phase 2: More entries
    print("\nPhase 2: Adding more entries")
    for i in range(4, 8):
        await log.append(f"Entry {i}".encode())
    
    checkpoint2 = log.checkpoint()
    print(f"  Checkpoint 2: size={checkpoint2.size}, root={checkpoint2.hex()[:16]}...")
    
    # Prove consistency between checkpoints
    print("\nConsistency proof (checkpoint1 → checkpoint2):")
    proof = log.get_consistency_proof(checkpoint1.size, checkpoint2.size)
    print(f"  Old size: {proof.old_size}")
    print(f"  New size: {proof.new_size}")
    print(f"  Proof nodes: {len(proof.proof_nodes)}")
    
    # This proves no entries were modified or deleted
    print("\n  This proves the log was only appended to, never modified!")
    
    print()


async def example_tamper_detection():
    """
    Example 5: Tamper Detection
    """
    print("=" * 60)
    print("Example 5: Tamper Detection")
    print("=" * 60)
    
    log = MerkleLog()
    
    # Build log
    await log.append(b"Legitimate entry 1")
    await log.append(b"Legitimate entry 2")
    await log.append(b"Legitimate entry 3")
    
    # Get proof for entry 1
    proof = log.get_inclusion_proof(1)
    
    print("\nOriginal proof verification:")
    is_valid = MerkleVerifier.verify_inclusion(b"Legitimate entry 2", proof)
    print(f"  Entry 'Legitimate entry 2': {is_valid}")
    
    # Attacker tries to claim different content
    print("\nAttacker claims entry was 'Tampered entry':")
    is_valid_tampered = MerkleVerifier.verify_inclusion(b"Tampered entry", proof)
    print(f"  Entry 'Tampered entry': {is_valid_tampered}")
    print("  ⚠️  TAMPER DETECTED!")
    
    # Attacker tries to modify proof
    print("\nAttacker modifies proof siblings:")
    tampered_siblings = ((b'\x00' * 32, True),) + proof.siblings[1:]
    tampered_proof = InclusionProof(
        index=proof.index,
        entry_hash=hash_leaf(b"Tampered entry"),
        siblings=tampered_siblings,
        root=proof.root
    )
    is_valid_tampered_proof = MerkleVerifier.verify_inclusion(b"Tampered entry", tampered_proof)
    print(f"  With tampered proof: {is_valid_tampered_proof}")
    print("  ⚠️  TAMPER DETECTED!")
    
    print()


async def example_serialization():
    """
    Example 6: Proof Serialization for Network Transfer
    """
    print("=" * 60)
    print("Example 6: Proof Serialization")
    print("=" * 60)
    
    log = MerkleLog()
    
    # Build log
    for i in range(10):
        await log.append(f"Entry {i}".encode())
    
    # Get proof
    proof = log.get_inclusion_proof(5)
    
    # Serialize to JSON-compatible dict
    proof_dict = proof.to_dict()
    
    print("\nSerialized proof (JSON-compatible):")
    print(f"  index: {proof_dict['index']}")
    print(f"  entry_hash: {proof_dict['entry_hash'][:32]}...")
    print(f"  siblings: {len(proof_dict['siblings'])} items")
    print(f"  root_hash: {proof_dict['root_hash'][:32]}...")
    
    # Can be sent over network as JSON
    json_str = json.dumps(proof_dict)
    print(f"\n  JSON size: {len(json_str)} bytes")
    
    # Reconstruct on receiving end
    received_dict = json.loads(json_str)
    restored_proof = InclusionProof.from_dict(received_dict)
    
    # Verify with restored proof
    is_valid = MerkleVerifier.verify_inclusion(b"Entry 5", restored_proof)
    print(f"\n  Verification with restored proof: {is_valid}")
    
    print()


async def example_batch_operations():
    """
    Example 7: Batch Operations for Performance
    """
    print("=" * 60)
    print("Example 7: Batch Operations")
    print("=" * 60)
    
    log = MerkleLog()
    
    # Batch append is more efficient for multiple entries
    print("\nBatch appending 1000 entries...")
    
    import time
    entries = [f"Batch entry {i}".encode() for i in range(1000)]
    
    start = time.time()
    root = await log.append_batch(entries)
    elapsed = time.time() - start
    
    print(f"  Entries: {log.size}")
    print(f"  Time: {elapsed*1000:.2f}ms")
    print(f"  Rate: {log.size/elapsed:.0f} entries/sec")
    print(f"  Final root: {root.hex()[:32]}...")
    
    # Proof size is still O(log n)
    proof = log.get_inclusion_proof(500)
    print(f"\n  Proof for entry 500 has {len(proof.siblings)} siblings")
    print(f"  (log2(1000) ≈ 10)")
    
    print()


async def example_compliance_audit():
    """
    Example 8: Real-World Compliance Audit Scenario
    """
    print("=" * 60)
    print("Example 8: Compliance Audit Scenario")
    print("=" * 60)
    
    # Company's internal audit log
    company_log = AuditLog()
    
    # Simulate a month of activity
    print("\nSimulating company activity log...")
    
    activities = [
        {"date": "2024-01-01", "type": "access", "user": "admin", "resource": "database"},
        {"date": "2024-01-02", "type": "modify", "user": "alice", "resource": "config"},
        {"date": "2024-01-03", "type": "delete", "user": "bob", "resource": "temp_files"},
        {"date": "2024-01-04", "type": "access", "user": "charlie", "resource": "reports"},
        {"date": "2024-01-05", "type": "export", "user": "alice", "resource": "customer_data"},
    ]
    
    for activity in activities:
        await company_log.append(json.dumps(activity).encode())
    
    print(f"  Logged {company_log.size} activities")
    
    # Weekly checkpoint for regulators
    weekly_checkpoint = company_log.checkpoint()
    print(f"\n  Weekly checkpoint: {weekly_checkpoint.hex()[:32]}...")
    print("  (This hash is submitted to regulator)")
    
    # More activity
    for i in range(5, 10):
        await company_log.append(json.dumps({
            "date": f"2024-01-0{i+1}", 
            "type": "access", 
            "user": "user",
            "resource": "file"
        }).encode())
    
    # Auditor arrives with the checkpoint hash
    print("\n  Auditor arrives with checkpoint hash...")
    
    # Company proves log integrity
    consistency_proof = company_log.get_consistency_proof(weekly_checkpoint.size)
    
    print(f"  Consistency proof: old={consistency_proof.old_size} → new={consistency_proof.new_size}")
    print("  ✓ Company proves no entries were modified since checkpoint")
    
    # Auditor can verify specific entry
    entry = company_log.get_entry(4)
    proof = company_log.get_proof(4)
    
    print(f"\n  Auditor requests entry 4:")
    print(f"    Content: {json.loads(entry.data.decode())}")
    print(f"    Verification: {AuditLog.verify(entry.data, proof)}")
    
    print()


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  MALO - MERKLE APPEND-ONLY LOG EXAMPLES")
    print("=" * 60 + "\n")
    
    await example_basic_log()
    await example_inclusion_proofs()
    await example_audit_log()
    await example_checkpoints()
    await example_tamper_detection()
    await example_serialization()
    await example_batch_operations()
    await example_compliance_audit()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
