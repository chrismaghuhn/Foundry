"""Tests for forge."""

import pytest
import asyncio
from forge import (
    # Core types
    State,
    Event,
    Transition,
    
    # Machine
    StateMachine,
    StateMachineBuilder,
    StateMachineInstance,
    
    # Results
    TransitionResult,
    TransitionInfo,
    
    # Errors
    ValidationError,
    NoInitialStateError,
    MultipleInitialStatesError,
    UnreachableStatesError,
    DeadEndStatesError,
    NonDeterministicTransitionError,
    InvalidTransitionError,
    
    # Convenience
    state,
    event,
    
    # Analysis
    analyze_machine,
    find_paths,
)


# =============================================================================
# State Tests
# =============================================================================

class TestState:
    """Test State creation and properties."""
    
    def test_basic_state(self):
        s = State("idle")
        assert s.name == "idle"
        assert not s.initial
        assert not s.final
        assert s.parent is None
    
    def test_initial_state(self):
        s = State("start", initial=True)
        assert s.initial
    
    def test_final_state(self):
        s = State("end", final=True)
        assert s.final
    
    def test_state_equality(self):
        s1 = State("idle")
        s2 = State("idle")
        s3 = State("running")
        
        assert s1 == s2
        assert s1 != s3
    
    def test_state_hash(self):
        s1 = State("idle")
        s2 = State("idle")
        
        # Should be usable in sets/dicts
        states = {s1, s2}
        assert len(states) == 1
    
    def test_hierarchical_state(self):
        parent = State("active")
        child = State("processing", parent=parent)
        
        assert child.parent == parent
        assert child.is_descendant_of(parent)
    
    def test_ancestry(self):
        root = State("root")
        level1 = State("level1", parent=root)
        level2 = State("level2", parent=level1)
        
        ancestry = level2.ancestry()
        assert ancestry == [root, level1]
    
    def test_convenience_function(self):
        s = state("idle", initial=True, final=False)
        assert s.name == "idle"
        assert s.initial


# =============================================================================
# Event Tests
# =============================================================================

class TestEvent:
    """Test Event creation and properties."""
    
    def test_basic_event(self):
        e = Event("start")
        assert e.name == "start"
        assert e.payload_type is None
    
    def test_event_with_payload(self):
        e = Event("data", payload_type=dict)
        assert e.payload_type == dict
    
    def test_event_equality(self):
        e1 = Event("start")
        e2 = Event("start")
        e3 = Event("stop")
        
        assert e1 == e2
        assert e1 != e3
    
    def test_convenience_function(self):
        e = event("click", payload_type=int)
        assert e.name == "click"
        assert e.payload_type == int


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Test state machine validation."""
    
    def test_no_initial_state(self):
        with pytest.raises(NoInitialStateError):
            (StateMachine.builder("test")
                .add_state(State("a"))
                .add_state(State("b"))
                .add_transition(State("a"), Event("e"), State("b"))
                .build())
    
    def test_multiple_initial_states(self):
        with pytest.raises(MultipleInitialStatesError):
            (StateMachine.builder("test")
                .add_state(State("a", initial=True))
                .add_state(State("b", initial=True))
                .add_transition(State("a"), Event("e"), State("b"))
                .build())
    
    def test_unreachable_states(self):
        with pytest.raises(UnreachableStatesError):
            (StateMachine.builder("test")
                .add_state(State("a", initial=True))
                .add_state(State("b"))
                .add_state(State("c", final=True))  # Unreachable
                .add_transition(State("a"), Event("e"), State("b"))
                .add_transition(State("b"), Event("f"), State("a"))
                .build())
    
    def test_dead_end_states(self):
        with pytest.raises(DeadEndStatesError):
            (StateMachine.builder("test")
                .add_state(State("a", initial=True))
                .add_state(State("b"))  # Dead end (not final, no outgoing)
                .add_transition(State("a"), Event("e"), State("b"))
                .build())
    
    def test_non_deterministic_transitions(self):
        with pytest.raises(NonDeterministicTransitionError):
            s1 = State("a", initial=True)
            s2 = State("b", final=True)
            e = Event("e")
            
            (StateMachine.builder("test")
                .add_transition(s1, e, s2)
                .add_transition(s1, e, s2)  # Duplicate unguarded
                .build())
    
    def test_valid_machine(self):
        """A valid machine should build without errors."""
        IDLE = State("idle", initial=True)
        RUNNING = State("running")
        DONE = State("done", final=True)
        
        START = Event("start")
        FINISH = Event("finish")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .add_transition(RUNNING, FINISH, DONE)
            .build())
        
        assert len(machine.states) == 3
        assert len(machine.transitions) == 2


# =============================================================================
# Transition Tests
# =============================================================================

class TestTransitions:
    """Test state transitions."""
    
    def test_basic_transition(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .build())
        
        instance = machine.create_instance()
        assert instance.state == IDLE
        
        instance.send(START)
        assert instance.state == RUNNING
    
    def test_transition_with_guard(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        def only_when_ready(ctx, payload):
            return ctx.get("ready", False)
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING, guard=only_when_ready)
            .build())
        
        context = {"ready": False}
        instance = machine.create_instance(context)
        
        # Should fail guard
        with pytest.raises(InvalidTransitionError):
            instance.send(START)
        
        assert instance.state == IDLE
        
        # Now make ready
        context["ready"] = True
        instance.send(START)
        assert instance.state == RUNNING
    
    def test_transition_with_action(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        def record_start(ctx, payload):
            ctx["started"] = True
            ctx["payload"] = payload
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING, action=record_start)
            .build())
        
        context = {}
        instance = machine.create_instance(context)
        instance.send(START, payload="test_data")
        
        assert context["started"] == True
        assert context["payload"] == "test_data"
    
    def test_entry_exit_actions(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        log = []
        
        def on_exit_idle(ctx, payload):
            log.append("exit_idle")
        
        def on_enter_running(ctx, payload):
            log.append("enter_running")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .on_exit(IDLE, on_exit_idle)
            .on_enter(RUNNING, on_enter_running)
            .build())
        
        instance = machine.create_instance()
        instance.send(START)
        
        assert log == ["exit_idle", "enter_running"]
    
    def test_guarded_transitions_priority(self):
        """Multiple guarded transitions should be tried in priority order."""
        IDLE = State("idle", initial=True)
        LOW = State("low", final=True)
        HIGH = State("high", final=True)
        CHECK = Event("check")
        
        def is_high(ctx, payload):
            return ctx.get("level", 0) > 10
        
        def is_low(ctx, payload):
            return ctx.get("level", 0) <= 10
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, CHECK, HIGH, guard=is_high, priority=10)
            .add_transition(IDLE, CHECK, LOW, guard=is_low, priority=5)
            .build())
        
        # Low level
        instance1 = machine.create_instance({"level": 5})
        instance1.send(CHECK)
        assert instance1.state == LOW
        
        # High level
        instance2 = machine.create_instance({"level": 15})
        instance2.send(CHECK)
        assert instance2.state == HIGH

    def test_guard_exception_skips_transition(self):
        """Guards that raise are treated like a failed guard (transition skipped)."""
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")

        def broken_guard(ctx, payload):
            raise RuntimeError("guard bug")

        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING, guard=broken_guard)
            .build())

        instance = machine.create_instance()
        with pytest.raises(InvalidTransitionError):
            instance.send(START)
        assert instance.state == IDLE
    
    def test_invalid_transition(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        STOP = Event("stop")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .build())
        
        instance = machine.create_instance()
        
        with pytest.raises(InvalidTransitionError) as exc_info:
            instance.send(STOP)
        
        assert exc_info.value.state == IDLE
        assert exc_info.value.event == STOP
    
    def test_invalid_transition_no_raise(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        STOP = Event("stop")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .build())
        
        instance = machine.create_instance()
        result = instance.send(STOP, raise_on_invalid=False)
        
        assert result.result == TransitionResult.NO_TRANSITION
        assert instance.state == IDLE


# =============================================================================
# Async Tests
# =============================================================================

class TestAsyncTransitions:
    """Test async transitions."""
    
    @pytest.mark.asyncio
    async def test_async_action(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        async def async_action(ctx, payload):
            await asyncio.sleep(0.01)
            ctx["async_done"] = True
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING, action=async_action)
            .build())
        
        context = {}
        instance = machine.create_instance(context)
        await instance.send_async(START)
        
        assert context["async_done"] == True
        assert instance.state == RUNNING
    
    @pytest.mark.asyncio
    async def test_async_entry_exit(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        log = []
        
        async def async_exit(ctx, payload):
            await asyncio.sleep(0.01)
            log.append("async_exit")
        
        async def async_enter(ctx, payload):
            await asyncio.sleep(0.01)
            log.append("async_enter")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .on_exit(IDLE, async_exit)
            .on_enter(RUNNING, async_enter)
            .build())
        
        instance = machine.create_instance()
        await instance.send_async(START)
        
        assert log == ["async_exit", "async_enter"]
    
    def test_async_in_sync_raises(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        async def async_action(ctx, payload):
            await asyncio.sleep(0.01)
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING, action=async_action)
            .build())
        
        instance = machine.create_instance()
        
        with pytest.raises(RuntimeError, match="Async action"):
            instance.send(START)


# =============================================================================
# Instance Tests
# =============================================================================

class TestInstance:
    """Test state machine instance behavior."""
    
    def test_history(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running")
        DONE = State("done", final=True)
        START = Event("start")
        FINISH = Event("finish")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .add_transition(RUNNING, FINISH, DONE)
            .build())
        
        instance = machine.create_instance()
        instance.send(START)
        instance.send(FINISH)
        
        history = instance.history
        assert len(history) == 2
        assert history[0].source == IDLE
        assert history[0].target == RUNNING
        assert history[1].source == RUNNING
        assert history[1].target == DONE
    
    def test_can_handle(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        STOP = Event("stop")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .build())
        
        instance = machine.create_instance()
        
        assert instance.can_handle(START)
        assert not instance.can_handle(STOP)
    
    def test_is_final(self):
        IDLE = State("idle", initial=True)
        DONE = State("done", final=True)
        FINISH = Event("finish")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, FINISH, DONE)
            .build())
        
        instance = machine.create_instance()
        assert not instance.is_final
        
        instance.send(FINISH)
        assert instance.is_final
    
    def test_reset(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .build())
        
        instance = machine.create_instance()
        instance.send(START)
        assert instance.state == RUNNING
        
        instance.reset()
        assert instance.state == IDLE
        assert len(instance.history) == 0
    
    def test_on_transition_callback(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        transitions_logged = []
        
        def log_transition(source, event, target):
            transitions_logged.append((source.name, event.name, target.name))
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .on_any_transition(log_transition)
            .build())
        
        instance = machine.create_instance()
        instance.send(START)
        
        assert transitions_logged == [("idle", "start", "running")]


# =============================================================================
# Analysis Tests
# =============================================================================

class TestAnalysis:
    """Test analysis functions."""
    
    def test_analyze_machine(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running")
        PAUSED = State("paused")
        DONE = State("done", final=True)
        
        START = Event("start")
        PAUSE = Event("pause")
        RESUME = Event("resume")
        FINISH = Event("finish")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .add_transition(RUNNING, PAUSE, PAUSED)
            .add_transition(PAUSED, RESUME, RUNNING)
            .add_transition(RUNNING, FINISH, DONE)
            .build())
        
        analysis = analyze_machine(machine)
        
        assert analysis["state_count"] == 4
        assert analysis["event_count"] == 4
        assert analysis["transition_count"] == 4
        assert analysis["final_states"] == ["done"]
        assert analysis["has_cycles"] == True  # RUNNING <-> PAUSED
    
    def test_find_paths(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running")
        DONE = State("done", final=True)
        
        START = Event("start")
        FINISH = Event("finish")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .add_transition(RUNNING, FINISH, DONE)
            .build())
        
        paths = find_paths(machine, IDLE, DONE)
        
        assert len(paths) == 1
        assert len(paths[0]) == 2
        assert paths[0][0] == (IDLE, START)
        assert paths[0][1] == (RUNNING, FINISH)
    
    def test_to_dot(self):
        IDLE = State("idle", initial=True)
        RUNNING = State("running", final=True)
        START = Event("start")
        
        machine = (StateMachine.builder("test")
            .add_transition(IDLE, START, RUNNING)
            .build())
        
        dot = machine.to_dot()
        
        assert 'digraph "test"' in dot
        assert '"idle"' in dot
        assert '"running"' in dot
        assert 'doublecircle' in dot  # Final state marking


# =============================================================================
# Real-World Scenario Tests
# =============================================================================

class TestRealWorldScenarios:
    """Test realistic state machine scenarios."""
    
    def test_traffic_light(self):
        """Classic traffic light state machine."""
        RED = State("red", initial=True)
        YELLOW = State("yellow")
        GREEN = State("green")
        
        TIMER = Event("timer")
        
        machine = (StateMachine.builder("traffic_light")
            .add_transition(RED, TIMER, GREEN)
            .add_transition(GREEN, TIMER, YELLOW)
            .add_transition(YELLOW, TIMER, RED)
            .build())
        
        instance = machine.create_instance()
        
        # Cycle through
        assert instance.state == RED
        instance.send(TIMER)
        assert instance.state == GREEN
        instance.send(TIMER)
        assert instance.state == YELLOW
        instance.send(TIMER)
        assert instance.state == RED
    
    def test_order_workflow(self):
        """E-commerce order workflow."""
        PENDING = State("pending", initial=True)
        PAID = State("paid")
        SHIPPED = State("shipped")
        DELIVERED = State("delivered", final=True)
        CANCELLED = State("cancelled", final=True)
        
        PAY = Event("pay")
        SHIP = Event("ship")
        DELIVER = Event("deliver")
        CANCEL = Event("cancel")
        
        def has_inventory(ctx, payload):
            return ctx.get("inventory", 0) > 0
        
        machine = (StateMachine.builder("order")
            .add_transition(PENDING, PAY, PAID, guard=has_inventory)
            .add_transition(PENDING, CANCEL, CANCELLED)
            .add_transition(PAID, SHIP, SHIPPED)
            .add_transition(PAID, CANCEL, CANCELLED)
            .add_transition(SHIPPED, DELIVER, DELIVERED)
            .build())
        
        # Happy path
        order1 = machine.create_instance({"inventory": 10})
        order1.send(PAY)
        order1.send(SHIP)
        order1.send(DELIVER)
        assert order1.state == DELIVERED
        
        # No inventory
        order2 = machine.create_instance({"inventory": 0})
        with pytest.raises(InvalidTransitionError):
            order2.send(PAY)
        
        # Cancel after payment
        order3 = machine.create_instance({"inventory": 5})
        order3.send(PAY)
        order3.send(CANCEL)
        assert order3.state == CANCELLED
    
    def test_connection_state(self):
        """Network connection state machine."""
        DISCONNECTED = State("disconnected", initial=True)
        CONNECTING = State("connecting")
        CONNECTED = State("connected")
        RECONNECTING = State("reconnecting")
        
        CONNECT = Event("connect")
        CONNECTED_EVENT = Event("connected")
        DISCONNECT = Event("disconnect")
        ERROR = Event("error")
        
        retry_count = {"value": 0}
        
        def increment_retry(ctx, payload):
            retry_count["value"] += 1
        
        def can_retry(ctx, payload):
            return retry_count["value"] < 3
        
        machine = (StateMachine.builder("connection")
            .add_transition(DISCONNECTED, CONNECT, CONNECTING)
            .add_transition(CONNECTING, CONNECTED_EVENT, CONNECTED)
            .add_transition(CONNECTING, ERROR, RECONNECTING, action=increment_retry)
            .add_transition(CONNECTED, DISCONNECT, DISCONNECTED)
            .add_transition(CONNECTED, ERROR, RECONNECTING, action=increment_retry)
            .add_transition(RECONNECTING, CONNECTED_EVENT, CONNECTED)
            .add_transition(RECONNECTING, ERROR, DISCONNECTED, guard=lambda c, p: not can_retry(c, p))
            .add_transition(RECONNECTING, ERROR, RECONNECTING, guard=can_retry, action=increment_retry)
            .build())
        
        instance = machine.create_instance()
        
        instance.send(CONNECT)
        assert instance.state == CONNECTING
        
        instance.send(ERROR)
        assert instance.state == RECONNECTING
        assert retry_count["value"] == 1
        
        instance.send(CONNECTED_EVENT)
        assert instance.state == CONNECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
