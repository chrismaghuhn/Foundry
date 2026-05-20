#!/usr/bin/env python3
"""
Chrono Usage Examples

Demonstrates real-world scenarios for the distributed clock library.
"""

import asyncio
from chrono import (
    # Clocks
    LamportClock,
    VectorClock,
    HybridLogicalClock,
    
    # Timestamps
    LamportTimestamp,
    VectorTimestamp,
    HLCTimestamp,
    
    # Utilities
    Event,
    EventLog,
    Message,
    Ordering,
    ClockType,
    create_clock,
    CausalBroadcaster,
)


async def example_lamport_basics():
    """
    Example 1: Lamport Clock Basics
    
    Simple logical timestamps for total ordering.
    """
    print("=" * 60)
    print("Example 1: Lamport Clock Basics")
    print("=" * 60)
    
    clock = LamportClock("server-1")
    
    print("\nGenerating timestamps for local events:")
    for i in range(5):
        ts = await clock.tick()
        print(f"  Event {i+1}: {ts}")
    
    print("\nSimulating message exchange:")
    
    # Server 1 sends to Server 2
    clock2 = LamportClock("server-2")
    
    send_ts = await clock.send()
    print(f"  Server 1 sends: {send_ts}")
    
    recv_ts = await clock2.receive(send_ts)
    print(f"  Server 2 receives: {recv_ts}")
    
    # Server 2 does local work
    local_ts = await clock2.tick()
    print(f"  Server 2 local event: {local_ts}")
    
    print("\n✓ Lamport clocks provide total ordering!\n")


async def example_vector_concurrency():
    """
    Example 2: Detecting Concurrent Events with Vector Clocks
    
    Vector clocks can tell you when events are causally independent.
    """
    print("=" * 60)
    print("Example 2: Vector Clocks - Concurrency Detection")
    print("=" * 60)
    
    # Three nodes working independently
    alice = VectorClock("alice")
    bob = VectorClock("bob")
    charlie = VectorClock("charlie")
    
    print("\nAlice and Bob work independently:")
    ts_alice = await alice.tick()
    ts_bob = await bob.tick()
    
    print(f"  Alice's event: {ts_alice}")
    print(f"  Bob's event:   {ts_bob}")
    
    ordering = ts_alice.compare(ts_bob)
    print(f"  Relationship:  {ordering.name}")
    
    print("\nAlice sends message to Bob:")
    alice_send = await alice.send()
    bob_recv = await bob.receive(alice_send)
    
    print(f"  Alice sends: {alice_send}")
    print(f"  Bob receives: {bob_recv}")
    
    print("\nNow Bob's events happen-after Alice's:")
    ordering = alice_send.compare(bob_recv)
    print(f"  {alice_send} → {bob_recv}: {ordering.name}")
    
    print("\nCharlie is still independent:")
    ts_charlie = await charlie.tick()
    print(f"  Charlie's event: {ts_charlie}")
    print(f"  Charlie || Alice? {ts_charlie.concurrent_with(ts_alice)}")
    print(f"  Charlie || Bob?   {ts_charlie.concurrent_with(bob_recv)}")
    
    print("\n✓ Vector clocks detect true concurrency!\n")


async def example_hlc_hybrid():
    """
    Example 3: Hybrid Logical Clocks
    
    Get the best of both worlds: physical time + logical ordering.
    """
    print("=" * 60)
    print("Example 3: Hybrid Logical Clocks")
    print("=" * 60)
    
    # Simulated wall clock
    wall_time = [1705312800000]  # Jan 15, 2024
    
    def get_time():
        return wall_time[0]
    
    clock1 = HybridLogicalClock("dc-east", time_source=get_time)
    clock2 = HybridLogicalClock("dc-west", time_source=get_time)
    
    print("\nGenerating timestamps at same wall time:")
    
    ts1 = await clock1.tick()
    ts2 = await clock1.tick()
    ts3 = await clock1.tick()
    
    print(f"  {ts1}")
    print(f"  {ts2}")
    print(f"  {ts3}")
    print("  (Logical counter increments at same physical time)")
    
    print("\nWall time advances:")
    wall_time[0] += 1000  # 1 second later
    
    ts4 = await clock1.tick()
    print(f"  {ts4}")
    print("  (Logical resets when physical time advances)")
    
    print("\nReceiving from another datacenter:")
    remote = HLCTimestamp(wall_time[0] + 5000, 10, "dc-west")  # Future time!
    ts5 = await clock1.receive(remote)
    print(f"  Remote:   {remote}")
    print(f"  After receive: {ts5}")
    print("  (Takes max physical time, preserves ordering)")
    
    print(f"\nAs datetime: {ts5.to_datetime_str()}")
    
    print("\n✓ HLC combines physical time with logical ordering!\n")


async def example_event_sourcing():
    """
    Example 4: Event Sourcing with Logical Clocks
    
    Build an event log with proper causality tracking.
    """
    print("=" * 60)
    print("Example 4: Event Sourcing")
    print("=" * 60)
    
    log = EventLog[VectorTimestamp]()
    
    # Simulate distributed system
    service_a = VectorClock("orders")
    service_b = VectorClock("inventory")
    service_c = VectorClock("shipping")
    
    print("\nRecording events from multiple services:")
    
    # Order placed
    ts1 = await service_a.tick()
    event1 = Event("order-created", ts1, "orders", {"order_id": "ORD-001"})
    await log.append(event1)
    print(f"  {event1.id}: {event1.timestamp}")
    
    # Inventory checked (after receiving order notification)
    ts2 = await service_b.receive(ts1)
    event2 = Event("inventory-reserved", ts2, "inventory", {"sku": "WIDGET-X"})
    await log.append(event2)
    print(f"  {event2.id}: {event2.timestamp}")
    
    # Concurrent: Another order comes in
    ts3 = await service_a.tick()
    event3 = Event("order-created", ts3, "orders", {"order_id": "ORD-002"})
    await log.append(event3)
    print(f"  {event3.id}: {event3.timestamp}")
    
    # Shipping starts (after inventory)
    ts4 = await service_c.receive(ts2)
    event4 = Event("shipment-created", ts4, "shipping", {"tracking": "TRK-123"})
    await log.append(event4)
    print(f"  {event4.id}: {event4.timestamp}")
    
    print("\nCausality analysis:")
    print(f"  order-created(1) → inventory-reserved? {event1.happens_before(event2)}")
    print(f"  inventory-reserved → shipment-created? {event2.happens_before(event4)}")
    print(f"  order-created(1) || order-created(2)?  {event1.concurrent_with(event3)}")
    
    print("\nEvent DAG visualization:")
    dag = await log.visualize_dag()
    print(dag)
    
    print("\n✓ Event sourcing with causality tracking!\n")


async def example_message_protocol():
    """
    Example 5: Message Protocol with Timestamps
    
    Send timestamped messages between services.
    """
    print("=" * 60)
    print("Example 5: Message Protocol")
    print("=" * 60)
    
    clock_sender = LamportClock("sender")
    clock_receiver = LamportClock("receiver")
    
    print("\nSender prepares message:")
    ts = await clock_sender.send()
    
    message = Message(
        payload={"type": "user_update", "user_id": 123, "name": "Alice"},
        timestamp=ts,
        sender_id="sender"
    )
    
    print(f"  Payload: {message.payload}")
    print(f"  Timestamp: {message.timestamp}")
    
    print("\nSerializing for network:")
    wire_data = message.to_bytes()
    print(f"  Size: {len(wire_data)} bytes")
    
    print("\nReceiver deserializes and processes:")
    received = Message.from_bytes(wire_data, LamportTimestamp)
    print(f"  Received payload: {received.payload}")
    print(f"  From: {received.sender_id}")
    
    # Update receiver's clock
    new_ts = await clock_receiver.receive(received.timestamp)
    print(f"  Clock updated: {received.timestamp} → {new_ts}")
    
    print("\n✓ Messages carry timestamps for ordering!\n")


async def example_conflict_resolution():
    """
    Example 6: Conflict Resolution with Vector Clocks
    
    Detect and handle concurrent writes.
    """
    print("=" * 60)
    print("Example 6: Conflict Resolution")
    print("=" * 60)
    
    # Simulating a distributed key-value store
    class VersionedValue:
        def __init__(self, value, timestamp):
            self.value = value
            self.timestamp = timestamp
        
        def __repr__(self):
            return f"({self.value}, {self.timestamp})"
    
    replica_a = VectorClock("replica-a")
    replica_b = VectorClock("replica-b")
    
    print("\nInitial state: key='config' value='v1'")
    initial_ts = VectorTimestamp({"replica-a": 1})
    store = {"config": VersionedValue("v1", initial_ts)}
    
    print(f"  store['config'] = {store['config']}")
    
    print("\nConcurrent updates at both replicas:")
    
    # Replica A writes
    ts_a = await replica_a.tick()
    write_a = VersionedValue("v2-from-A", ts_a)
    print(f"  Replica A writes: {write_a}")
    
    # Replica B writes (without seeing A's write)
    ts_b = await replica_b.tick()
    write_b = VersionedValue("v2-from-B", ts_b)
    print(f"  Replica B writes: {write_b}")
    
    print("\nConflict detection:")
    ordering = ts_a.compare(ts_b)
    print(f"  {ts_a} vs {ts_b}: {ordering.name}")
    
    if ordering == Ordering.CONCURRENT:
        print("\n  ⚠️  CONFLICT DETECTED!")
        print("  Resolution strategies:")
        print("    1. Last-writer-wins (use node_id as tiebreaker)")
        print("    2. Keep both versions (multi-value)")
        print("    3. Application-level merge")
        
        # LWW example
        winner = write_a if "replica-a" < "replica-b" else write_b
        print(f"\n  LWW winner: {winner}")
    
    print("\n✓ Vector clocks enable conflict detection!\n")


async def example_causal_broadcast():
    """
    Example 7: Causal Broadcast Protocol
    
    Ensure messages are delivered in causal order.
    """
    print("=" * 60)
    print("Example 7: Causal Broadcast")
    print("=" * 60)
    
    # Three-node setup
    node1 = CausalBroadcaster("node-1", ["node-2", "node-3"])
    node2 = CausalBroadcaster("node-2", ["node-1", "node-3"])
    node3 = CausalBroadcaster("node-3", ["node-1", "node-2"])
    
    print("\nNode 1 broadcasts two messages:")
    msg1 = await node1.broadcast({"seq": 1, "content": "Hello"})
    msg2 = await node1.broadcast({"seq": 2, "content": "World"})
    
    print(f"  Message 1: {msg1.payload}")
    print(f"  Message 2: {msg2.payload}")
    
    print("\nNode 2 receives in order:")
    delivered = await node2.receive(msg1)
    print(f"  After msg1: delivered {len(delivered)} message(s)")
    delivered = await node2.receive(msg2)
    print(f"  After msg2: delivered {len(delivered)} message(s)")
    
    print("\nNode 3 receives OUT OF ORDER:")
    delivered = await node3.receive(msg2)  # msg2 arrives first!
    print(f"  After msg2 (out of order): delivered {len(delivered)} message(s)")
    print("  (msg2 buffered, waiting for msg1)")
    
    delivered = await node3.receive(msg1)
    print(f"  After msg1: delivered {len(delivered)} message(s)")
    for msg in delivered:
        data = msg.payload.get("data", {})
        print(f"    - seq={data.get('seq')}: {data.get('content')}")
    
    print("\n✓ Causal broadcast ensures correct ordering!\n")


async def example_clock_comparison():
    """
    Example 8: Comparing Clock Types
    
    See the trade-offs between different clock types.
    """
    print("=" * 60)
    print("Example 8: Clock Type Comparison")
    print("=" * 60)
    
    print("""
    | Property              | Lamport | Vector | HLC    |
    |-----------------------|---------|--------|--------|
    | Size                  | O(1)    | O(n)   | O(1)   |
    | Detect Concurrency    | No      | Yes    | No     |
    | Physical Time         | No      | No     | Yes    |
    | Total Ordering        | Yes     | No     | Yes    |
    """)
    
    print("Creating one of each:")
    
    lamport = create_clock(ClockType.LAMPORT, "node-1")
    vector = create_clock(ClockType.VECTOR, "node-1")
    hlc = create_clock(ClockType.HLC, "node-1")
    
    print(f"\n  Lamport: {type(lamport).__name__}")
    ts_l = await lamport.tick()
    print(f"    Timestamp: {ts_l}")
    print(f"    Bytes: {len(ts_l.to_bytes())}")
    
    print(f"\n  Vector: {type(vector).__name__}")
    ts_v = await vector.tick()
    print(f"    Timestamp: {ts_v}")
    print(f"    Bytes: {len(ts_v.to_bytes())}")
    
    print(f"\n  HLC: {type(hlc).__name__}")
    ts_h = await hlc.tick()
    print(f"    Timestamp: {ts_h}")
    print(f"    Bytes: {len(ts_h.to_bytes())}")
    
    print("\nRecommendations:")
    print("  - Lamport: Simple ordering, high throughput")
    print("  - Vector:  Need conflict detection (CRDTs)")
    print("  - HLC:     Want timestamps close to wall time")
    
    print("\n✓ Choose the right clock for your use case!\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  CHRONO DISTRIBUTED CLOCK LIBRARY - EXAMPLES")
    print("=" * 60 + "\n")
    
    await example_lamport_basics()
    await example_vector_concurrency()
    await example_hlc_hybrid()
    await example_event_sourcing()
    await example_message_protocol()
    await example_conflict_resolution()
    await example_causal_broadcast()
    await example_clock_comparison()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
