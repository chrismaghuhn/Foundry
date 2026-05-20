"""Tests for chrono."""

import asyncio
import pytest
import time
from chrono import (
    # Core
    Ordering,
    
    # Lamport
    LamportTimestamp,
    LamportClock,
    
    # Vector
    VectorTimestamp,
    VectorClock,
    
    # HLC
    HLCTimestamp,
    HybridLogicalClock,
    
    # Utilities
    Event,
    EventLog,
    Message,
    ClockType,
    create_clock,
    
    # Causal broadcast
    CausalBroadcaster,
)


# =============================================================================
# Lamport Timestamp Tests
# =============================================================================

class TestLamportTimestamp:
    """Test Lamport timestamp operations."""
    
    def test_ordering(self):
        """Timestamps are totally ordered."""
        ts1 = LamportTimestamp(1, "a")
        ts2 = LamportTimestamp(2, "a")
        ts3 = LamportTimestamp(2, "b")
        
        assert ts1 < ts2
        assert ts2 < ts3  # Same counter, node_id tiebreaker
        assert ts1 < ts3
    
    def test_equality(self):
        """Equal timestamps compare equal."""
        ts1 = LamportTimestamp(5, "node-1")
        ts2 = LamportTimestamp(5, "node-1")
        
        assert ts1 == ts2
        assert ts1.compare(ts2) == Ordering.EQUAL
    
    def test_compare_before_after(self):
        """Compare returns BEFORE/AFTER correctly."""
        ts1 = LamportTimestamp(1, "a")
        ts2 = LamportTimestamp(2, "a")
        
        assert ts1.compare(ts2) == Ordering.BEFORE
        assert ts2.compare(ts1) == Ordering.AFTER
    
    def test_serialization(self):
        """Timestamps serialize and deserialize correctly."""
        ts = LamportTimestamp(12345, "node-xyz")
        
        data = ts.to_bytes()
        restored = LamportTimestamp.from_bytes(data)
        
        assert restored == ts
        assert restored.counter == 12345
        assert restored.node_id == "node-xyz"
    
    def test_repr(self):
        """String representation is readable."""
        ts = LamportTimestamp(42, "node-1")
        assert "42" in repr(ts)
        assert "node-1" in repr(ts)


class TestLamportClock:
    """Test Lamport clock operations."""
    
    @pytest.mark.asyncio
    async def test_tick_increments(self):
        """Tick increments counter."""
        clock = LamportClock("node-1")
        
        ts1 = await clock.tick()
        ts2 = await clock.tick()
        ts3 = await clock.tick()
        
        assert ts1.counter == 1
        assert ts2.counter == 2
        assert ts3.counter == 3
    
    @pytest.mark.asyncio
    async def test_send_same_as_tick(self):
        """Send behaves like tick."""
        clock = LamportClock("node-1")
        
        ts1 = await clock.tick()
        ts2 = await clock.send()
        
        assert ts2.counter == ts1.counter + 1
    
    @pytest.mark.asyncio
    async def test_receive_updates_clock(self):
        """Receive updates clock to max + 1."""
        clock = LamportClock("node-1")
        
        await clock.tick()  # counter = 1
        
        # Receive timestamp with higher counter
        remote = LamportTimestamp(100, "node-2")
        ts = await clock.receive(remote)
        
        assert ts.counter == 101  # max(1, 100) + 1
    
    @pytest.mark.asyncio
    async def test_receive_lower_counter(self):
        """Receive with lower counter still increments."""
        clock = LamportClock("node-1")
        
        for _ in range(10):
            await clock.tick()  # counter = 10
        
        remote = LamportTimestamp(5, "node-2")
        ts = await clock.receive(remote)
        
        assert ts.counter == 11  # max(10, 5) + 1
    
    @pytest.mark.asyncio
    async def test_current_no_increment(self):
        """Current returns timestamp without incrementing."""
        clock = LamportClock("node-1")
        
        await clock.tick()
        await clock.tick()
        
        ts1 = await clock.current()
        ts2 = await clock.current()
        
        assert ts1.counter == ts2.counter == 2


# =============================================================================
# Vector Timestamp Tests
# =============================================================================

class TestVectorTimestamp:
    """Test Vector timestamp operations."""
    
    def test_empty_vector(self):
        """Empty vector has zero for all nodes."""
        ts = VectorTimestamp()
        
        assert ts["any-node"] == 0
        assert ts["another"] == 0
    
    def test_increment(self):
        """Increment creates new timestamp with updated component."""
        ts1 = VectorTimestamp({"a": 1, "b": 2})
        ts2 = ts1.increment("a")
        
        assert ts2["a"] == 2
        assert ts2["b"] == 2
        assert ts1["a"] == 1  # Original unchanged
    
    def test_merge(self):
        """Merge takes component-wise max."""
        ts1 = VectorTimestamp({"a": 3, "b": 1})
        ts2 = VectorTimestamp({"a": 1, "b": 5, "c": 2})
        
        merged = ts1.merge(ts2)
        
        assert merged["a"] == 3
        assert merged["b"] == 5
        assert merged["c"] == 2
    
    def test_compare_equal(self):
        """Equal vectors compare equal."""
        ts1 = VectorTimestamp({"a": 1, "b": 2})
        ts2 = VectorTimestamp({"a": 1, "b": 2})
        
        assert ts1.compare(ts2) == Ordering.EQUAL
    
    def test_compare_before(self):
        """Detect happens-before relationship."""
        ts1 = VectorTimestamp({"a": 1, "b": 1})
        ts2 = VectorTimestamp({"a": 2, "b": 2})
        
        assert ts1.compare(ts2) == Ordering.BEFORE
        assert ts1.happens_before(ts2)
    
    def test_compare_after(self):
        """Detect happens-after relationship."""
        ts1 = VectorTimestamp({"a": 3, "b": 3})
        ts2 = VectorTimestamp({"a": 1, "b": 1})
        
        assert ts1.compare(ts2) == Ordering.AFTER
    
    def test_compare_concurrent(self):
        """Detect concurrent events."""
        ts1 = VectorTimestamp({"a": 2, "b": 1})
        ts2 = VectorTimestamp({"a": 1, "b": 2})
        
        assert ts1.compare(ts2) == Ordering.CONCURRENT
        assert ts1.concurrent_with(ts2)
        assert ts2.concurrent_with(ts1)
    
    def test_serialization(self):
        """Timestamps serialize and deserialize correctly."""
        ts = VectorTimestamp({"node-1": 5, "node-2": 10})
        
        data = ts.to_bytes()
        restored = VectorTimestamp.from_bytes(data)
        
        assert restored["node-1"] == 5
        assert restored["node-2"] == 10


class TestVectorClock:
    """Test Vector clock operations."""
    
    @pytest.mark.asyncio
    async def test_tick_increments_own_component(self):
        """Tick only increments own node's component."""
        clock = VectorClock("node-1")
        
        ts1 = await clock.tick()
        ts2 = await clock.tick()
        
        assert ts1["node-1"] == 1
        assert ts2["node-1"] == 2
    
    @pytest.mark.asyncio
    async def test_receive_merges_and_increments(self):
        """Receive merges remote clock and increments local."""
        clock = VectorClock("node-1")
        
        await clock.tick()  # {node-1: 1}
        
        remote = VectorTimestamp({"node-2": 5, "node-3": 3})
        ts = await clock.receive(remote)
        
        assert ts["node-1"] == 2  # Incremented
        assert ts["node-2"] == 5  # From remote
        assert ts["node-3"] == 3  # From remote
    
    @pytest.mark.asyncio
    async def test_causality_preserved(self):
        """Events at same node are causally ordered."""
        clock = VectorClock("node-1")
        
        ts1 = await clock.tick()
        ts2 = await clock.tick()
        ts3 = await clock.tick()
        
        assert ts1.happens_before(ts2)
        assert ts2.happens_before(ts3)
        assert ts1.happens_before(ts3)
    
    @pytest.mark.asyncio
    async def test_concurrent_events_detected(self):
        """Events at different nodes without communication are concurrent."""
        clock1 = VectorClock("node-1")
        clock2 = VectorClock("node-2")
        
        ts1 = await clock1.tick()
        ts2 = await clock2.tick()
        
        assert ts1.concurrent_with(ts2)


# =============================================================================
# HLC Timestamp Tests
# =============================================================================

class TestHLCTimestamp:
    """Test Hybrid Logical Clock timestamps."""
    
    def test_ordering_by_physical(self):
        """Physical time is primary sort key."""
        ts1 = HLCTimestamp(1000, 5, "a")
        ts2 = HLCTimestamp(2000, 0, "a")
        
        assert ts1 < ts2
    
    def test_ordering_by_logical(self):
        """Logical is secondary sort key."""
        ts1 = HLCTimestamp(1000, 1, "a")
        ts2 = HLCTimestamp(1000, 2, "a")
        
        assert ts1 < ts2
    
    def test_ordering_by_node(self):
        """Node ID is tertiary sort key."""
        ts1 = HLCTimestamp(1000, 1, "a")
        ts2 = HLCTimestamp(1000, 1, "b")
        
        assert ts1 < ts2
    
    def test_equality(self):
        """Equal timestamps compare equal."""
        ts1 = HLCTimestamp(1000, 5, "node-1")
        ts2 = HLCTimestamp(1000, 5, "node-1")
        
        assert ts1 == ts2
    
    def test_serialization(self):
        """Timestamps serialize and deserialize correctly."""
        ts = HLCTimestamp(1705312800000, 42, "node-xyz")
        
        data = ts.to_bytes()
        restored = HLCTimestamp.from_bytes(data)
        
        assert restored == ts
        assert restored.physical == 1705312800000
        assert restored.logical == 42
        assert restored.node_id == "node-xyz"


class TestHybridLogicalClock:
    """Test HLC operations."""
    
    @pytest.mark.asyncio
    async def test_tick_advances_physical(self):
        """Tick uses current wall time."""
        wall_time = 1000
        clock = HybridLogicalClock("node-1", time_source=lambda: wall_time)
        
        ts = await clock.tick()
        
        assert ts.physical == 1000
        assert ts.logical == 0
    
    @pytest.mark.asyncio
    async def test_tick_increments_logical_same_time(self):
        """Multiple ticks at same wall time increment logical."""
        wall_time = 1000
        clock = HybridLogicalClock("node-1", time_source=lambda: wall_time)
        
        ts1 = await clock.tick()
        ts2 = await clock.tick()
        ts3 = await clock.tick()
        
        assert ts1.logical == 0
        assert ts2.logical == 1
        assert ts3.logical == 2
    
    @pytest.mark.asyncio
    async def test_tick_resets_logical_on_time_advance(self):
        """Logical resets when wall time advances."""
        times = iter([1000, 1000, 2000])
        clock = HybridLogicalClock("node-1", time_source=lambda: next(times))
        
        ts1 = await clock.tick()
        ts2 = await clock.tick()
        ts3 = await clock.tick()
        
        assert ts1.logical == 0
        assert ts2.logical == 1
        assert ts3.logical == 0  # Reset!
        assert ts3.physical == 2000
    
    @pytest.mark.asyncio
    async def test_receive_takes_max_physical(self):
        """Receive uses max of local, remote, and wall time."""
        clock = HybridLogicalClock("node-1", time_source=lambda: 1000)
        
        await clock.tick()  # physical=1000, logical=0
        
        remote = HLCTimestamp(2000, 5, "node-2")
        ts = await clock.receive(remote)
        
        assert ts.physical == 2000  # From remote
        assert ts.logical == 6  # remote.logical + 1
    
    @pytest.mark.asyncio
    async def test_receive_same_physical_merges_logical(self):
        """When physical times match, logical is max + 1."""
        clock = HybridLogicalClock("node-1", time_source=lambda: 1000)
        
        await clock.tick()
        await clock.tick()  # physical=1000, logical=1
        
        remote = HLCTimestamp(1000, 5, "node-2")
        ts = await clock.receive(remote)
        
        assert ts.physical == 1000
        assert ts.logical == 6  # max(1, 5) + 1
    
    @pytest.mark.asyncio
    async def test_monotonicity(self):
        """Timestamps are always monotonically increasing."""
        times = iter([1000, 500, 800, 1200])  # Time goes backward!
        clock = HybridLogicalClock("node-1", time_source=lambda: next(times))
        
        timestamps = []
        for _ in range(4):
            timestamps.append(await clock.tick())
        
        # Each timestamp should be > previous
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1]


# =============================================================================
# Event Log Tests
# =============================================================================

class TestEventLog:
    """Test event logging and ordering."""
    
    @pytest.mark.asyncio
    async def test_append_and_retrieve(self):
        """Events can be appended and retrieved."""
        log = EventLog[LamportTimestamp]()
        
        e1 = Event("e1", LamportTimestamp(1, "a"), "node-1")
        e2 = Event("e2", LamportTimestamp(2, "a"), "node-1")
        
        await log.append(e1)
        await log.append(e2)
        
        events = await log.get_ordered()
        assert len(events) == 2
    
    @pytest.mark.asyncio
    async def test_ordered_retrieval(self):
        """Events are returned in timestamp order."""
        log = EventLog[LamportTimestamp]()
        
        # Add out of order
        await log.append(Event("e3", LamportTimestamp(3, "a"), "node-1"))
        await log.append(Event("e1", LamportTimestamp(1, "a"), "node-1"))
        await log.append(Event("e2", LamportTimestamp(2, "a"), "node-1"))
        
        events = await log.get_ordered()
        
        assert events[0].id == "e1"
        assert events[1].id == "e2"
        assert events[2].id == "e3"
    
    @pytest.mark.asyncio
    async def test_find_concurrent_with_vector_clocks(self):
        """Find concurrent events using vector clocks."""
        log = EventLog[VectorTimestamp]()
        
        # Causally related events
        ts1 = VectorTimestamp({"a": 1})
        ts2 = VectorTimestamp({"a": 2})
        
        # Concurrent event
        ts3 = VectorTimestamp({"b": 1})
        
        await log.append(Event("e1", ts1, "node-a"))
        await log.append(Event("e2", ts2, "node-a"))
        await log.append(Event("e3", ts3, "node-b"))
        
        concurrent = await log.find_concurrent()
        
        # ts1 || ts3 and ts2 || ts3
        assert len(concurrent) == 2


# =============================================================================
# Message Tests
# =============================================================================

class TestMessage:
    """Test message serialization."""
    
    def test_lamport_message_serialization(self):
        """Messages with Lamport timestamps serialize correctly."""
        msg = Message(
            payload={"action": "update", "value": 42},
            timestamp=LamportTimestamp(10, "sender"),
            sender_id="node-1"
        )
        
        data = msg.to_bytes()
        restored = Message.from_bytes(data, LamportTimestamp)
        
        assert restored.payload == {"action": "update", "value": 42}
        assert restored.timestamp.counter == 10
        assert restored.sender_id == "node-1"
    
    def test_vector_message_serialization(self):
        """Messages with Vector timestamps serialize correctly."""
        msg = Message(
            payload={"data": [1, 2, 3]},
            timestamp=VectorTimestamp({"a": 1, "b": 2}),
            sender_id="node-a"
        )
        
        data = msg.to_bytes()
        restored = Message.from_bytes(data, VectorTimestamp)
        
        assert restored.payload == {"data": [1, 2, 3]}
        assert restored.timestamp["a"] == 1
        assert restored.timestamp["b"] == 2


# =============================================================================
# Clock Factory Tests
# =============================================================================

class TestClockFactory:
    """Test clock factory function."""
    
    def test_create_lamport(self):
        """Factory creates Lamport clock."""
        clock = create_clock(ClockType.LAMPORT, "node-1")
        assert isinstance(clock, LamportClock)
    
    def test_create_vector(self):
        """Factory creates Vector clock."""
        clock = create_clock(ClockType.VECTOR, "node-1")
        assert isinstance(clock, VectorClock)
    
    def test_create_hlc(self):
        """Factory creates HLC."""
        clock = create_clock(ClockType.HLC, "node-1")
        assert isinstance(clock, HybridLogicalClock)


# =============================================================================
# Causal Broadcast Tests
# =============================================================================

class TestCausalBroadcaster:
    """Test causal broadcast protocol."""
    
    @pytest.mark.asyncio
    async def test_broadcast_creates_message(self):
        """Broadcast creates properly timestamped message."""
        broadcaster = CausalBroadcaster("node-1", ["node-2", "node-3"])
        
        msg = await broadcaster.broadcast({"action": "hello"})
        
        assert msg.sender_id == "node-1"
        assert msg.timestamp["node-1"] == 1
    
    @pytest.mark.asyncio
    async def test_receive_delivers_single_message(self):
        """Single message is delivered immediately."""
        b1 = CausalBroadcaster("node-1", ["node-2"])
        b2 = CausalBroadcaster("node-2", ["node-1"])
        
        msg = await b1.broadcast({"data": "test"})
        delivered = await b2.receive(msg)
        
        assert len(delivered) == 1
        assert delivered[0].payload["data"]["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_out_of_order_delivery_buffered(self):
        """Out of order messages are buffered until dependencies arrive."""
        b1 = CausalBroadcaster("node-1", ["node-2"])
        b2 = CausalBroadcaster("node-2", ["node-1"])
        
        # Node 1 sends two messages
        msg1 = await b1.broadcast({"seq": 1})
        msg2 = await b1.broadcast({"seq": 2})
        
        # Node 2 receives msg2 first (out of order)
        delivered = await b2.receive(msg2)
        assert len(delivered) == 0  # Buffered, waiting for msg1
        
        # Now msg1 arrives
        delivered = await b2.receive(msg1)
        assert len(delivered) == 2  # Both delivered in order
        assert delivered[0].payload["data"]["seq"] == 1
        assert delivered[1].payload["data"]["seq"] == 2


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_three_node_lamport_scenario(self):
        """Simulate three nodes communicating with Lamport clocks."""
        clock_a = LamportClock("A")
        clock_b = LamportClock("B")
        clock_c = LamportClock("C")
        
        # A does local work
        ts_a1 = await clock_a.tick()
        
        # A sends to B
        ts_a2 = await clock_a.send()
        ts_b1 = await clock_b.receive(ts_a2)
        
        # B sends to C
        ts_b2 = await clock_b.send()
        ts_c1 = await clock_c.receive(ts_b2)
        
        # Verify causal ordering
        assert ts_a1 < ts_a2
        assert ts_a2 < ts_b1
        assert ts_b1 < ts_b2
        assert ts_b2 < ts_c1
    
    @pytest.mark.asyncio
    async def test_vector_clock_concurrent_detection(self):
        """Vector clocks correctly identify concurrent events."""
        clock_a = VectorClock("A")
        clock_b = VectorClock("B")
        
        # Both nodes do local work without communication
        ts_a1 = await clock_a.tick()
        ts_a2 = await clock_a.tick()
        
        ts_b1 = await clock_b.tick()
        ts_b2 = await clock_b.tick()
        
        # All events from A are concurrent with all events from B
        assert ts_a1.concurrent_with(ts_b1)
        assert ts_a1.concurrent_with(ts_b2)
        assert ts_a2.concurrent_with(ts_b1)
        assert ts_a2.concurrent_with(ts_b2)
        
        # A sends to B, breaking concurrency
        ts_a3 = await clock_a.send()
        ts_b3 = await clock_b.receive(ts_a3)
        
        # Now ts_b3 happens after ts_a3
        assert ts_a3.happens_before(ts_b3)
    
    @pytest.mark.asyncio
    async def test_hlc_stays_close_to_wall_time(self):
        """HLC timestamps stay close to wall clock time."""
        wall_time = [1000000]  # Start at 1M ms
        
        def advance_time():
            wall_time[0] += 100  # 100ms per call
            return wall_time[0]
        
        clock = HybridLogicalClock("node-1", time_source=advance_time)
        
        # Generate several timestamps
        timestamps = []
        for _ in range(10):
            timestamps.append(await clock.tick())
        
        # All physical times should be close to wall time
        for ts in timestamps:
            assert abs(ts.physical - wall_time[0]) < 1000  # Within 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
