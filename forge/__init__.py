"""
Forge: Validated Finite State Machines

A state machine library that validates correctness at definition time.
Catches unreachable states, dead ends, and non-deterministic transitions
before your code runs.

Quick Start:
    >>> from forge import State, Event, StateMachine
    >>> 
    >>> # Define states
    >>> IDLE = State("idle", initial=True)
    >>> RUNNING = State("running")
    >>> DONE = State("done", final=True)
    >>> 
    >>> # Define events
    >>> START = Event("start")
    >>> FINISH = Event("finish")
    >>> 
    >>> # Build machine (validates automatically!)
    >>> machine = (StateMachine.builder("workflow")
    ...     .add_transition(IDLE, START, RUNNING)
    ...     .add_transition(RUNNING, FINISH, DONE)
    ...     .build())
    >>> 
    >>> # Use it
    >>> instance = machine.create_instance()
    >>> instance.send(START)
    >>> instance.send(FINISH)
    >>> instance.is_final  # True

Validation catches errors at build time:
    - NoInitialStateError: No initial state defined
    - MultipleInitialStatesError: More than one initial state
    - UnreachableStatesError: States that can't be reached
    - DeadEndStatesError: Non-final states with no outgoing transitions
    - NonDeterministicTransitionError: Ambiguous transitions

With guards and actions:
    >>> def is_ready(ctx, payload):
    ...     return ctx.get("ready", False)
    >>> 
    >>> def log_start(ctx, payload):
    ...     print("Starting!")
    >>> 
    >>> machine = (StateMachine.builder("guarded")
    ...     .add_transition(IDLE, START, RUNNING, 
    ...                     guard=is_ready, 
    ...                     action=log_start)
    ...     .build())

Async support:
    >>> async def async_action(ctx, payload):
    ...     await some_async_operation()
    >>> 
    >>> await instance.send_async(EVENT)
"""

from .forge import (
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
    UnknownTargetStateError,
    NonDeterministicTransitionError,
    InvalidTransitionError,
    
    # Convenience
    state,
    event,
    
    # Analysis
    analyze_machine,
    find_paths,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

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
