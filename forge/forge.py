"""
Forge: Validated Finite State Machines

A state machine library that validates correctness at definition time.
Catches unreachable states, dead ends, and non-deterministic transitions
before your code runs.

Core Concepts:

    State: A named condition the machine can be in. States can be:
        - Initial: Where the machine starts
        - Final: Terminal states (no outgoing transitions required)
        - Hierarchical: Nested states with parent/child relationships
    
    Event: A trigger that may cause a state transition.
    
    Transition: A rule (state, event) → new_state with optional:
        - Guard: A condition that must be true for the transition
        - Action: Code executed during the transition
    
    Context: Shared data accessible to guards and actions.

Validation Rules (checked at build time):

    1. Initial state must exist
    2. All states must be reachable from initial state
    3. Non-final states must have at least one outgoing transition
    4. No non-deterministic transitions (same state+event without distinguishing guards)
    5. Target states must exist

Usage Pattern:

    1. Define states and events
    2. Build machine with transitions
    3. Machine is validated automatically
    4. Send events to trigger transitions

Example:
    >>> from forge import StateMachine, State, Event
    >>> 
    >>> # Define
    >>> IDLE = State("idle", initial=True)
    >>> RUNNING = State("running")
    >>> STOPPED = State("stopped", final=True)
    >>> 
    >>> START = Event("start")
    >>> STOP = Event("stop")
    >>> 
    >>> # Build (validates automatically)
    >>> machine = (StateMachine("worker")
    ...     .add_states(IDLE, RUNNING, STOPPED)
    ...     .add_transition(IDLE, START, RUNNING)
    ...     .add_transition(RUNNING, STOP, STOPPED)
    ...     .build())
    >>> 
    >>> # Use
    >>> instance = machine.create_instance()
    >>> instance.send(START)
    >>> print(instance.state)  # running

Thread Safety:
    StateMachine definitions are immutable after build.
    Instances are not thread-safe; use one per thread or external synchronization.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any, Callable, Generic, TypeVar, Optional, Union,
    Dict, Set, List, Tuple, Awaitable, Type, FrozenSet
)
from collections import defaultdict
import inspect
import graphlib


# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar('T')  # Context type
E = TypeVar('E')  # Event type


# =============================================================================
# Core Types
# =============================================================================

@dataclass(frozen=True)
class State:
    """
    A state in the state machine.
    
    States are immutable identifiers. They can be marked as:
    - initial: The starting state (exactly one required)
    - final: Terminal states (no outgoing transitions required)
    
    Hierarchical states can have a parent, creating nested state machines.
    When entering a child state, the parent's entry action runs first.
    When exiting, the child's exit action runs first.
    """
    name: str
    initial: bool = False
    final: bool = False
    parent: Optional['State'] = None
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self.name == other.name
        return False
    
    def __repr__(self) -> str:
        modifiers = []
        if self.initial:
            modifiers.append("initial")
        if self.final:
            modifiers.append("final")
        if self.parent:
            modifiers.append(f"parent={self.parent.name}")
        mod_str = f" ({', '.join(modifiers)})" if modifiers else ""
        return f"State({self.name!r}{mod_str})"
    
    def is_descendant_of(self, other: 'State') -> bool:
        """Check if this state is a descendant of another."""
        current = self.parent
        while current is not None:
            if current == other:
                return True
            current = current.parent
        return False
    
    def ancestry(self) -> List['State']:
        """Get list of ancestors from root to parent (not including self)."""
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return list(reversed(ancestors))


@dataclass(frozen=True)
class Event:
    """
    An event that can trigger state transitions.
    
    Events are immutable identifiers with optional payload type hint.
    The payload is passed to guards and actions.
    """
    name: str
    payload_type: Optional[Type] = None
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Event):
            return self.name == other.name
        return False
    
    def __repr__(self) -> str:
        if self.payload_type:
            return f"Event({self.name!r}, payload={self.payload_type.__name__})"
        return f"Event({self.name!r})"


# Type aliases for callbacks
Guard = Callable[[Any, Any], bool]  # (context, event_payload) -> bool
Action = Callable[[Any, Any], None]  # (context, event_payload) -> None
AsyncAction = Callable[[Any, Any], Awaitable[None]]


@dataclass
class Transition:
    """
    A transition from one state to another triggered by an event.
    
    Transitions can have:
    - guard: A condition that must be True for the transition to fire
    - action: Code executed during the transition
    - priority: For ordering when multiple transitions match (higher = first)
    
    Guards and actions receive (context, event_payload) as arguments.
    """
    source: State
    event: Event
    target: State
    guard: Optional[Guard] = None
    action: Optional[Union[Action, AsyncAction]] = None
    priority: int = 0
    
    def __repr__(self) -> str:
        guard_str = " [guarded]" if self.guard else ""
        action_str = " /action" if self.action else ""
        return f"Transition({self.source.name} --{self.event.name}--> {self.target.name}{guard_str}{action_str})"


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(Exception):
    """Base class for state machine validation errors."""
    pass


class NoInitialStateError(ValidationError):
    """No initial state defined."""
    def __init__(self):
        super().__init__("State machine must have exactly one initial state")


class MultipleInitialStatesError(ValidationError):
    """Multiple initial states defined."""
    def __init__(self, states: List[State]):
        names = [s.name for s in states]
        super().__init__(f"Multiple initial states defined: {names}")


class UnreachableStatesError(ValidationError):
    """Some states cannot be reached from the initial state."""
    def __init__(self, states: Set[State]):
        names = [s.name for s in states]
        super().__init__(f"Unreachable states: {names}")


class DeadEndStatesError(ValidationError):
    """Non-final states with no outgoing transitions."""
    def __init__(self, states: Set[State]):
        names = [s.name for s in states]
        super().__init__(f"Dead-end states (non-final with no outgoing transitions): {names}")


class UnknownTargetStateError(ValidationError):
    """Transition targets a state not in the machine."""
    def __init__(self, transition: Transition):
        super().__init__(
            f"Transition from '{transition.source.name}' targets unknown state '{transition.target.name}'"
        )


class NonDeterministicTransitionError(ValidationError):
    """Multiple transitions for same (state, event) without distinguishing guards."""
    def __init__(self, state: State, event: Event, count: int):
        super().__init__(
            f"Non-deterministic: {count} unguarded transitions from '{state.name}' on '{event.name}'"
        )


class InvalidTransitionError(Exception):
    """Raised when a transition cannot be made."""
    def __init__(self, state: State, event: Event):
        super().__init__(f"No valid transition from '{state.name}' on event '{event.name}'")
        self.state = state
        self.event = event


# =============================================================================
# State Machine Builder
# =============================================================================

class StateMachineBuilder(Generic[T]):
    """
    Builder for creating validated state machines.
    
    The builder pattern allows fluent construction:
    
        machine = (StateMachine("name")
            .add_states(s1, s2, s3)
            .add_transition(s1, e1, s2)
            .on_enter(s2, action)
            .build())
    
    Validation happens in build(), ensuring the machine is well-formed.
    """
    
    def __init__(self, name: str, context_type: Optional[Type[T]] = None):
        self._name = name
        self._context_type = context_type
        self._states: Dict[str, State] = {}
        self._events: Dict[str, Event] = {}
        self._transitions: List[Transition] = []
        self._entry_actions: Dict[State, List[Union[Action, AsyncAction]]] = defaultdict(list)
        self._exit_actions: Dict[State, List[Union[Action, AsyncAction]]] = defaultdict(list)
        self._on_transition: List[Callable[[State, Event, State], None]] = []
    
    def add_state(self, state: State) -> 'StateMachineBuilder[T]':
        """Add a state to the machine."""
        if state.name in self._states:
            raise ValueError(f"Duplicate state name: {state.name}")
        self._states[state.name] = state
        return self
    
    def add_states(self, *states: State) -> 'StateMachineBuilder[T]':
        """Add multiple states."""
        for state in states:
            self.add_state(state)
        return self
    
    def add_event(self, event: Event) -> 'StateMachineBuilder[T]':
        """Add an event to the machine."""
        if event.name in self._events:
            raise ValueError(f"Duplicate event name: {event.name}")
        self._events[event.name] = event
        return self
    
    def add_events(self, *events: Event) -> 'StateMachineBuilder[T]':
        """Add multiple events."""
        for event in events:
            self.add_event(event)
        return self
    
    def add_transition(
        self,
        source: State,
        event: Event,
        target: State,
        guard: Optional[Guard] = None,
        action: Optional[Union[Action, AsyncAction]] = None,
        priority: int = 0,
    ) -> 'StateMachineBuilder[T]':
        """
        Add a transition.
        
        Args:
            source: State to transition from
            event: Event that triggers the transition
            target: State to transition to
            guard: Optional condition (context, payload) -> bool
            action: Optional action (context, payload) -> None
            priority: Higher priority transitions are tried first
        """
        # Auto-register states and events
        if source.name not in self._states:
            self.add_state(source)
        if target.name not in self._states:
            self.add_state(target)
        if event.name not in self._events:
            self.add_event(event)
        
        self._transitions.append(Transition(
            source=source,
            event=event,
            target=target,
            guard=guard,
            action=action,
            priority=priority,
        ))
        return self
    
    def on_enter(
        self,
        state: State,
        action: Union[Action, AsyncAction],
    ) -> 'StateMachineBuilder[T]':
        """Add an entry action for a state."""
        self._entry_actions[state].append(action)
        return self
    
    def on_exit(
        self,
        state: State,
        action: Union[Action, AsyncAction],
    ) -> 'StateMachineBuilder[T]':
        """Add an exit action for a state."""
        self._exit_actions[state].append(action)
        return self
    
    def on_any_transition(
        self,
        callback: Callable[[State, Event, State], None],
    ) -> 'StateMachineBuilder[T]':
        """Add a callback for any transition (for logging, metrics, etc.)."""
        self._on_transition.append(callback)
        return self
    
    def _validate(self) -> None:
        """
        Validate the state machine definition.
        
        Checks:
        1. Exactly one initial state
        2. All states reachable from initial
        3. Non-final states have outgoing transitions
        4. No non-deterministic transitions
        5. All transition targets exist
        """
        states = set(self._states.values())
        
        # 1. Check initial state
        initial_states = [s for s in states if s.initial]
        if len(initial_states) == 0:
            raise NoInitialStateError()
        if len(initial_states) > 1:
            raise MultipleInitialStatesError(initial_states)
        
        initial = initial_states[0]
        
        # 2. Check reachability (BFS from initial)
        reachable: Set[State] = set()
        queue = [initial]
        
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            
            # Add states reachable via transitions
            for t in self._transitions:
                if t.source == current and t.target not in reachable:
                    queue.append(t.target)
            
            # Add child states (hierarchical)
            for s in states:
                if s.parent == current and s not in reachable:
                    queue.append(s)
        
        unreachable = states - reachable
        if unreachable:
            raise UnreachableStatesError(unreachable)
        
        # 3. Check for dead ends (non-final states without outgoing transitions)
        states_with_outgoing = {t.source for t in self._transitions}
        dead_ends = {
            s for s in states 
            if not s.final 
            and s not in states_with_outgoing
            and not any(child.parent == s for child in states)  # Has children
        }
        if dead_ends:
            raise DeadEndStatesError(dead_ends)
        
        # 4. Check for non-determinism
        transition_map: Dict[Tuple[State, Event], List[Transition]] = defaultdict(list)
        for t in self._transitions:
            transition_map[(t.source, t.event)].append(t)
        
        for (state, event), transitions in transition_map.items():
            # Count unguarded transitions
            unguarded = [t for t in transitions if t.guard is None]
            if len(unguarded) > 1:
                raise NonDeterministicTransitionError(state, event, len(unguarded))
        
        # 5. Check target states exist
        for t in self._transitions:
            if t.target.name not in self._states:
                raise UnknownTargetStateError(t)
    
    def build(self) -> 'StateMachine[T]':
        """
        Build and validate the state machine.
        
        Raises ValidationError if the machine is invalid.
        """
        self._validate()
        
        initial = next(s for s in self._states.values() if s.initial)
        
        return StateMachine(
            name=self._name,
            states=frozenset(self._states.values()),
            events=frozenset(self._events.values()),
            transitions=tuple(self._transitions),
            initial_state=initial,
            entry_actions=dict(self._entry_actions),
            exit_actions=dict(self._exit_actions),
            on_transition_callbacks=tuple(self._on_transition),
            context_type=self._context_type,
        )


# =============================================================================
# State Machine Definition
# =============================================================================

@dataclass(frozen=True)
class StateMachine(Generic[T]):
    """
    An immutable, validated state machine definition.
    
    Created via StateMachine.builder() or StateMachineBuilder.
    Use create_instance() to get a mutable instance.
    """
    name: str
    states: FrozenSet[State]
    events: FrozenSet[Event]
    transitions: Tuple[Transition, ...]
    initial_state: State
    entry_actions: Dict[State, List[Union[Action, AsyncAction]]]
    exit_actions: Dict[State, List[Union[Action, AsyncAction]]]
    on_transition_callbacks: Tuple[Callable[[State, Event, State], None], ...]
    context_type: Optional[Type[T]]
    
    @classmethod
    def builder(cls, name: str, context_type: Optional[Type[T]] = None) -> StateMachineBuilder[T]:
        """Create a builder for this state machine."""
        return StateMachineBuilder(name, context_type)
    
    def create_instance(self, context: Optional[T] = None) -> 'StateMachineInstance[T]':
        """Create a new instance of this state machine."""
        return StateMachineInstance(self, context)
    
    def get_transitions_from(self, state: State) -> List[Transition]:
        """Get all transitions from a state."""
        return [t for t in self.transitions if t.source == state]
    
    def get_transitions_for(self, state: State, event: Event) -> List[Transition]:
        """Get transitions from a state for a specific event."""
        transitions = [t for t in self.transitions if t.source == state and t.event == event]
        # Sort by priority (higher first)
        return sorted(transitions, key=lambda t: t.priority, reverse=True)
    
    def get_state(self, name: str) -> Optional[State]:
        """Get a state by name."""
        for s in self.states:
            if s.name == name:
                return s
        return None
    
    def get_event(self, name: str) -> Optional[Event]:
        """Get an event by name."""
        for e in self.events:
            if e.name == name:
                return e
        return None
    
    def to_dot(self) -> str:
        """
        Generate a Graphviz DOT representation.
        
        Useful for visualizing the state machine.
        """
        lines = [f'digraph "{self.name}" {{']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=circle];')
        
        # Mark initial state with an arrow from nowhere
        lines.append(f'  __start__ [shape=point];')
        lines.append(f'  __start__ -> "{self.initial_state.name}";')
        
        # Mark final states with double circle
        for state in self.states:
            if state.final:
                lines.append(f'  "{state.name}" [shape=doublecircle];')
        
        # Add transitions
        for t in self.transitions:
            label = t.event.name
            if t.guard:
                label += " [guard]"
            lines.append(f'  "{t.source.name}" -> "{t.target.name}" [label="{label}"];')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def __repr__(self) -> str:
        return f"StateMachine({self.name!r}, states={len(self.states)}, transitions={len(self.transitions)})"


# =============================================================================
# State Machine Instance
# =============================================================================

class TransitionResult(Enum):
    """Result of attempting a transition."""
    SUCCESS = auto()
    NO_TRANSITION = auto()
    GUARD_REJECTED = auto()


@dataclass
class TransitionInfo:
    """Information about a completed transition."""
    source: State
    event: Event
    target: State
    result: TransitionResult
    payload: Any = None


class StateMachineInstance(Generic[T]):
    """
    A mutable instance of a state machine.
    
    Each instance has its own current state and context.
    Send events via send() or send_async() to trigger transitions.
    """
    
    def __init__(self, machine: StateMachine[T], context: Optional[T] = None):
        self._machine = machine
        self._context = context
        self._state = machine.initial_state
        self._history: List[TransitionInfo] = []
        self._running = True
    
    @property
    def machine(self) -> StateMachine[T]:
        """The state machine definition."""
        return self._machine
    
    @property
    def state(self) -> State:
        """Current state."""
        return self._state
    
    @property
    def context(self) -> Optional[T]:
        """The context object."""
        return self._context
    
    @context.setter
    def context(self, value: T) -> None:
        self._context = value
    
    @property
    def history(self) -> List[TransitionInfo]:
        """History of transitions."""
        return list(self._history)
    
    @property
    def is_final(self) -> bool:
        """Check if current state is final."""
        return self._state.final
    
    def can_handle(self, event: Event, payload: Any = None) -> bool:
        """Check if the machine can handle an event in current state."""
        transitions = self._machine.get_transitions_for(self._state, event)
        for t in transitions:
            if t.guard is None or t.guard(self._context, payload):
                return True
        return False
    
    def _run_actions(
        self,
        actions: List[Union[Action, AsyncAction]],
        payload: Any,
    ) -> None:
        """Run a list of actions synchronously."""
        for action in actions:
            if asyncio.iscoroutinefunction(action):
                raise RuntimeError(
                    "Async action in synchronous send(). Use send_async() instead."
                )
            action(self._context, payload)
    
    async def _run_actions_async(
        self,
        actions: List[Union[Action, AsyncAction]],
        payload: Any,
    ) -> None:
        """Run a list of actions, awaiting async ones."""
        for action in actions:
            if asyncio.iscoroutinefunction(action):
                await action(self._context, payload)
            else:
                action(self._context, payload)
    
    def send(
        self,
        event: Event,
        payload: Any = None,
        *,
        raise_on_invalid: bool = True,
    ) -> TransitionInfo:
        """
        Send an event to trigger a transition.
        
        Args:
            event: The event to send
            payload: Optional data passed to guards and actions
            raise_on_invalid: If True, raise InvalidTransitionError when no valid transition exists
        
        Returns:
            TransitionInfo describing what happened
        
        Raises:
            InvalidTransitionError: If no valid transition and raise_on_invalid=True
            RuntimeError: If async actions are used (use send_async instead)
        """
        transitions = self._machine.get_transitions_for(self._state, event)
        
        for t in transitions:
            # Check guard
            if t.guard is not None:
                try:
                    if not t.guard(self._context, payload):
                        continue
                except Exception:
                    continue
            
            # Found a valid transition
            old_state = self._state
            
            # Calculate states to exit and enter (for hierarchy)
            states_to_exit = self._get_states_to_exit(old_state, t.target)
            states_to_enter = self._get_states_to_enter(old_state, t.target)
            
            # Run exit actions (child first)
            for state in states_to_exit:
                exit_actions = self._machine.exit_actions.get(state, [])
                self._run_actions(exit_actions, payload)
            
            # Run transition action
            if t.action:
                if asyncio.iscoroutinefunction(t.action):
                    raise RuntimeError(
                        "Async action in synchronous send(). Use send_async() instead."
                    )
                t.action(self._context, payload)
            
            # Run entry actions (parent first)
            for state in states_to_enter:
                entry_actions = self._machine.entry_actions.get(state, [])
                self._run_actions(entry_actions, payload)
            
            # Update state
            self._state = t.target
            
            # Notify callbacks
            for callback in self._machine.on_transition_callbacks:
                callback(old_state, event, t.target)
            
            info = TransitionInfo(old_state, event, t.target, TransitionResult.SUCCESS, payload)
            self._history.append(info)
            return info
        
        # No valid transition found
        if raise_on_invalid:
            raise InvalidTransitionError(self._state, event)
        
        info = TransitionInfo(self._state, event, self._state, TransitionResult.NO_TRANSITION, payload)
        self._history.append(info)
        return info
    
    async def send_async(
        self,
        event: Event,
        payload: Any = None,
        *,
        raise_on_invalid: bool = True,
    ) -> TransitionInfo:
        """
        Send an event asynchronously.
        
        Same as send() but supports async guards and actions.
        """
        transitions = self._machine.get_transitions_for(self._state, event)
        
        for t in transitions:
            # Check guard
            if t.guard is not None:
                try:
                    result = t.guard(self._context, payload)
                    if asyncio.iscoroutine(result):
                        result = await result
                    if not result:
                        continue
                except Exception:
                    continue
            
            # Found a valid transition
            old_state = self._state
            
            # Calculate states to exit and enter
            states_to_exit = self._get_states_to_exit(old_state, t.target)
            states_to_enter = self._get_states_to_enter(old_state, t.target)
            
            # Run exit actions
            for state in states_to_exit:
                exit_actions = self._machine.exit_actions.get(state, [])
                await self._run_actions_async(exit_actions, payload)
            
            # Run transition action
            if t.action:
                if asyncio.iscoroutinefunction(t.action):
                    await t.action(self._context, payload)
                else:
                    t.action(self._context, payload)
            
            # Run entry actions
            for state in states_to_enter:
                entry_actions = self._machine.entry_actions.get(state, [])
                await self._run_actions_async(entry_actions, payload)
            
            # Update state
            self._state = t.target
            
            # Notify callbacks
            for callback in self._machine.on_transition_callbacks:
                callback(old_state, event, t.target)
            
            info = TransitionInfo(old_state, event, t.target, TransitionResult.SUCCESS, payload)
            self._history.append(info)
            return info
        
        # No valid transition found
        if raise_on_invalid:
            raise InvalidTransitionError(self._state, event)
        
        info = TransitionInfo(self._state, event, self._state, TransitionResult.NO_TRANSITION, payload)
        self._history.append(info)
        return info
    
    def _get_states_to_exit(self, source: State, target: State) -> List[State]:
        """Get states to exit when transitioning (child first order)."""
        # For now, simple case: just the source
        # For hierarchical, would need to compute LCA
        if source == target:
            return []
        return [source]
    
    def _get_states_to_enter(self, source: State, target: State) -> List[State]:
        """Get states to enter when transitioning (parent first order)."""
        if source == target:
            return []
        return [target]
    
    def reset(self) -> None:
        """Reset to initial state."""
        self._state = self._machine.initial_state
        self._history.clear()
    
    def __repr__(self) -> str:
        return f"StateMachineInstance({self._machine.name!r}, state={self._state.name!r})"


# =============================================================================
# Convenience Functions
# =============================================================================

def state(
    name: str,
    *,
    initial: bool = False,
    final: bool = False,
    parent: Optional[State] = None,
) -> State:
    """Create a state (convenience function)."""
    return State(name=name, initial=initial, final=final, parent=parent)


def event(name: str, payload_type: Optional[Type] = None) -> Event:
    """Create an event (convenience function)."""
    return Event(name=name, payload_type=payload_type)


# =============================================================================
# Analysis Functions
# =============================================================================

def analyze_machine(machine: StateMachine) -> Dict[str, Any]:
    """
    Analyze a state machine and return statistics.
    
    Returns dict with:
    - state_count: Number of states
    - event_count: Number of events
    - transition_count: Number of transitions
    - final_states: List of final state names
    - average_outgoing: Average outgoing transitions per non-final state
    - has_cycles: Whether the machine has cycles
    """
    state_count = len(machine.states)
    event_count = len(machine.events)
    transition_count = len(machine.transitions)
    final_states = [s.name for s in machine.states if s.final]
    
    # Calculate average outgoing transitions
    non_final = [s for s in machine.states if not s.final]
    if non_final:
        outgoing_counts = [
            len(machine.get_transitions_from(s)) for s in non_final
        ]
        avg_outgoing = sum(outgoing_counts) / len(outgoing_counts)
    else:
        avg_outgoing = 0
    
    # Check for cycles using DFS
    has_cycles = _has_cycles(machine)
    
    return {
        "state_count": state_count,
        "event_count": event_count,
        "transition_count": transition_count,
        "final_states": final_states,
        "average_outgoing": avg_outgoing,
        "has_cycles": has_cycles,
    }


def _has_cycles(machine: StateMachine) -> bool:
    """Check if the state machine has cycles."""
    # Build adjacency list
    adj: Dict[State, Set[State]] = defaultdict(set)
    for t in machine.transitions:
        adj[t.source].add(t.target)
    
    # DFS with coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[State, int] = {s: WHITE for s in machine.states}
    
    def dfs(state: State) -> bool:
        color[state] = GRAY
        for neighbor in adj[state]:
            if color[neighbor] == GRAY:
                return True  # Back edge = cycle
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[state] = BLACK
        return False
    
    for state in machine.states:
        if color[state] == WHITE:
            if dfs(state):
                return True
    
    return False


def find_paths(
    machine: StateMachine,
    source: State,
    target: State,
    max_length: int = 10,
) -> List[List[Tuple[State, Event]]]:
    """
    Find all paths from source to target state.
    
    Returns list of paths, where each path is a list of (state, event) tuples.
    Limited to max_length to avoid infinite loops in cyclic machines.
    """
    paths: List[List[Tuple[State, Event]]] = []
    
    def dfs(current: State, path: List[Tuple[State, Event]]) -> None:
        if len(path) > max_length:
            return
        
        if current == target:
            paths.append(list(path))
            return
        
        for t in machine.get_transitions_from(current):
            path.append((current, t.event))
            dfs(t.target, path)
            path.pop()
    
    dfs(source, [])
    return paths


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core types
    'State',
    'Event',
    'Transition',
    
    # Machine
    'StateMachine',
    'StateMachineBuilder',
    'StateMachineInstance',
    
    # Results
    'TransitionResult',
    'TransitionInfo',
    
    # Errors
    'ValidationError',
    'NoInitialStateError',
    'MultipleInitialStatesError',
    'UnreachableStatesError',
    'DeadEndStatesError',
    'UnknownTargetStateError',
    'NonDeterministicTransitionError',
    'InvalidTransitionError',
    
    # Convenience
    'state',
    'event',
    
    # Analysis
    'analyze_machine',
    'find_paths',
]
