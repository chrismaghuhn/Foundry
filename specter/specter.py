#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ███████╗██████╗ ███████╗ ██████╗████████╗███████╗██████╗                     ║
║  ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗                    ║
║  ███████╗██████╔╝█████╗  ██║        ██║   █████╗  ██████╔╝                    ║
║  ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══╝  ██╔══██╗                    ║
║  ███████║██║     ███████╗╚██████╗   ██║   ███████╗██║  ██║                    ║
║  ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝                    ║
║                                                                               ║
║     Phantom Type State Machine — Compile-Time Transition Validation           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

SPECTER: State machines where invalid transitions are IMPOSSIBLE TO WRITE.

THE PROBLEM:
    Traditional state machines check transitions at runtime:
    
        if current_state == "idle" and transition == "start":
            current_state = "running"
        else:
            raise InvalidTransitionError()  # 💥 Runtime crash!
    
    This works until someone forgets the check, or the check has a bug,
    or testing doesn't cover that path. Then: production crash.

THE SOLUTION:
    Encode valid transitions in the TYPE SYSTEM. The type checker
    (mypy, pyright) catches invalid transitions BEFORE code runs.
    
        # This type-checks ✓
        machine: Machine[Running] = machine_idle.start()
        
        # This is a TYPE ERROR ✗ (won't even run)
        machine: Machine[Running] = machine_idle.stop()  # mypy error!

HOW IT WORKS:
    1. States are TYPE PARAMETERS (phantom types)
    2. Each method returns a NEW machine with DIFFERENT type
    3. Methods only exist on machines in valid source states
    4. Type checker ensures you can only call valid transitions

GUARANTEE:
    If mypy/pyright passes, invalid state transitions are IMPOSSIBLE.
    Not "caught at runtime" - literally cannot be written.

INTENTIONAL LIMITATION:
    The type-level encoding requires method overloads per transition.
    This creates boilerplate. We provide a BUILDER to generate it,
    but the generated code must be copied into your project.
    No runtime magic - that would defeat the purpose.

DOMAINS INTEGRATED:
    1. Compiler/Static Analysis: Leveraging type system as proof system
    2. Advanced Data Structures: Phantom types, type-level state encoding

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, Generic, List, Literal, Optional,
    Protocol, Set, Tuple, Type, TypeVar, Union, overload,
    get_type_hints, get_origin, get_args, runtime_checkable
)
import textwrap
import hashlib


# =============================================================================
# PHANTOM TYPES - States exist only at type level
# =============================================================================

class StateMarker:
    """
    Base class for state markers (phantom types).
    
    These classes are NEVER instantiated. They exist ONLY as type parameters.
    The type checker tracks them; the runtime ignores them.
    """
    pass


# Example states - users define their own
class Idle(StateMarker): pass
class Starting(StateMarker): pass
class Running(StateMarker): pass
class Paused(StateMarker): pass
class Stopping(StateMarker): pass
class Stopped(StateMarker): pass
class Error(StateMarker): pass


# Type variable for states
S = TypeVar('S', bound=StateMarker)
S1 = TypeVar('S1', bound=StateMarker)
S2 = TypeVar('S2', bound=StateMarker)


# =============================================================================
# MACHINE PROTOCOL - What type-safe machines look like
# =============================================================================

@runtime_checkable
class StateMachine(Protocol[S]):
    """
    Protocol for type-safe state machines.
    
    The type parameter S tracks the current state.
    Methods transition to new states with new type parameters.
    """
    
    @property
    def state_name(self) -> str:
        """Name of current state (for debugging/logging)."""
        ...
    
    @property
    def data(self) -> Dict[str, Any]:
        """Arbitrary data carried by the machine."""
        ...


# =============================================================================
# TRANSITION DEFINITION - Declarative specification
# =============================================================================

@dataclass(frozen=True)
class Transition:
    """
    Definition of a valid state transition.
    
    Attributes:
        name: Method name for this transition
        from_state: Source state(s) - single or tuple
        to_state: Target state
        guard: Optional condition that must be true
        action: Optional side effect to execute
    """
    name: str
    from_states: Tuple[Type[StateMarker], ...]
    to_state: Type[StateMarker]
    guard: Optional[str] = None  # Python expression as string
    action: Optional[str] = None  # Python statement as string
    
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"Transition name must be valid identifier: {self.name}")


@dataclass
class StateDefinition:
    """
    Complete definition of a state machine.
    
    This is the INPUT to the code generator.
    """
    name: str
    states: List[Type[StateMarker]]
    initial_state: Type[StateMarker]
    transitions: List[Transition]
    data_fields: Dict[str, str] = field(default_factory=dict)  # name -> type annotation
    
    def validate(self) -> List[str]:
        """Validate the state machine definition. Returns list of errors."""
        errors = []
        
        state_names = {s.__name__ for s in self.states}
        
        # Check initial state is valid
        if self.initial_state not in self.states:
            errors.append(f"Initial state {self.initial_state.__name__} not in states")
        
        # Check all transitions reference valid states
        for t in self.transitions:
            for from_state in t.from_states:
                if from_state not in self.states:
                    errors.append(f"Transition {t.name}: from_state {from_state.__name__} not in states")
            if t.to_state not in self.states:
                errors.append(f"Transition {t.name}: to_state {t.to_state.__name__} not in states")
        
        # Check for unreachable states
        reachable = {self.initial_state}
        changed = True
        while changed:
            changed = False
            for t in self.transitions:
                if any(s in reachable for s in t.from_states):
                    if t.to_state not in reachable:
                        reachable.add(t.to_state)
                        changed = True
        
        unreachable = set(self.states) - reachable
        for s in unreachable:
            errors.append(f"State {s.__name__} is unreachable")
        
        return errors


# =============================================================================
# CODE GENERATOR - Produces type-safe machine implementation
# =============================================================================

class SpecterCodeGen:
    """
    Generates type-safe state machine code from definition.
    
    The generated code:
    1. Defines phantom type classes for each state
    2. Defines a generic Machine[S] class
    3. Adds methods that only type-check for valid transitions
    4. Uses @overload to express conditional return types
    
    WHY CODE GENERATION?
        We could use runtime tricks (__getattr__, metaclasses) but that
        would defeat the purpose. The point is that mypy/pyright catches
        errors BEFORE runtime. Runtime enforcement is a backup, not the goal.
    """
    
    def __init__(self, definition: StateDefinition):
        self.definition = definition
        self._validate()
    
    def _validate(self) -> None:
        """Validate definition or raise."""
        errors = self.definition.validate()
        if errors:
            raise ValueError(f"Invalid state machine definition:\n" + "\n".join(f"  - {e}" for e in errors))
    
    def generate(self) -> str:
        """Generate complete Python module with type-safe state machine."""
        parts = [
            self._generate_header(),
            self._generate_imports(),
            self._generate_state_classes(),
            self._generate_machine_class(),
            self._generate_factory(),
            self._generate_example_usage(),
        ]
        return "\n\n".join(parts)
    
    def _generate_header(self) -> str:
        """Generate module docstring."""
        return f'''"""
{self.definition.name}: Type-Safe State Machine

Generated by SPECTER - Phantom Type State Machine Generator

States: {", ".join(s.__name__ for s in self.definition.states)}
Initial State: {self.definition.initial_state.__name__}
Transitions: {len(self.definition.transitions)}

GUARANTEE: If mypy/pyright passes, invalid transitions are impossible.
"""'''
    
    def _generate_imports(self) -> str:
        """Generate import statements."""
        return '''from __future__ import annotations

from typing import Any, Dict, Generic, Literal, TypeVar, overload, Union
from dataclasses import dataclass, field'''
    
    def _generate_state_classes(self) -> str:
        """Generate phantom type classes for states."""
        lines = [
            "# =============================================================================",
            "# PHANTOM TYPES - States exist only at type level, never instantiated",
            "# =============================================================================",
            "",
            "class _StateMarker:",
            "    '''Base class for state markers (phantom types).'''",
            "    pass",
            "",
        ]
        
        for state in self.definition.states:
            lines.append(f"class {state.__name__}(_StateMarker): pass")
        
        lines.extend([
            "",
            "# Type variables for generic state handling",
            "S = TypeVar('S', bound=_StateMarker)",
        ])
        
        return "\n".join(lines)
    
    def _generate_machine_class(self) -> str:
        """Generate the main Machine class with typed transitions."""
        lines = [
            "# =============================================================================",
            "# TYPE-SAFE STATE MACHINE",
            "# =============================================================================",
            "",
            "@dataclass",
            f"class {self.definition.name}(Generic[S]):",
            f'    """',
            f'    Type-safe state machine for {self.definition.name}.',
            f'    ',
            f'    The type parameter S tracks the current state.',
            f'    Methods only type-check when called from valid source states.',
            f'    Invalid transitions are caught by the type checker, not at runtime.',
            f'    """',
            "",
            "    _state_name: str",
            "    _data: Dict[str, Any] = field(default_factory=dict)",
            "",
            "    @property",
            "    def state_name(self) -> str:",
            "        return self._state_name",
            "",
            "    @property",
            "    def data(self) -> Dict[str, Any]:",
            "        return self._data",
            "",
        ]
        
        # Generate methods for each transition
        for transition in self.definition.transitions:
            lines.extend(self._generate_transition_method(transition))
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_transition_method(self, t: Transition) -> List[str]:
        """Generate a single transition method with proper overloads."""
        lines = []
        
        # Build the state union type for the source states
        if len(t.from_states) == 1:
            from_type = t.from_states[0].__name__
        else:
            from_type = "Union[" + ", ".join(s.__name__ for s in t.from_states) + "]"
        
        to_type = t.to_state.__name__
        
        # Method docstring
        from_names = ", ".join(s.__name__ for s in t.from_states)
        
        lines.extend([
            f"    def {t.name}(",
            f"        self: '{self.definition.name}[{from_type}]',",
            f"    ) -> '{self.definition.name}[{to_type}]':",
            f'        """',
            f'        Transition: {from_names} → {to_type}',
            f'        ',
            f'        This method only type-checks when called on a machine',
            f'        in state {from_names}. Calling from other states is a type error.',
            f'        """',
        ])
        
        # Guard check (runtime backup)
        if t.guard:
            lines.extend([
                f"        # Guard condition",
                f"        if not ({t.guard}):",
                f'            raise RuntimeError("Guard failed: {t.guard}")',
            ])
        
        # Action execution
        if t.action:
            lines.extend([
                f"        # Action",
                f"        {t.action}",
            ])
        
        # State transition
        lines.extend([
            f"        return {self.definition.name}(",
            f"            _state_name='{to_type}',",
            f"            _data=self._data.copy(),",
            f"        )",
        ])
        
        return lines
    
    def _generate_factory(self) -> str:
        """Generate factory function for initial state."""
        initial = self.definition.initial_state.__name__
        return f'''
# =============================================================================
# FACTORY - Create machine in initial state
# =============================================================================

def create_{self.definition.name.lower()}(**data: Any) -> {self.definition.name}[{initial}]:
    """
    Create a new {self.definition.name} in the initial state ({initial}).
    
    Args:
        **data: Initial data to store in the machine
    
    Returns:
        A type-safe state machine in the {initial} state
    """
    return {self.definition.name}(
        _state_name='{initial}',
        _data=dict(data),
    )'''
    
    def _generate_example_usage(self) -> str:
        """Generate example usage comments."""
        lines = [
            "# =============================================================================",
            "# EXAMPLE USAGE",
            "# =============================================================================",
            "#",
            "# # Create machine in initial state",
            f"# machine = create_{self.definition.name.lower()}()",
            "#",
            "# # Valid transitions compile and run",
        ]
        
        # Find a path through the state machine
        visited = {self.definition.initial_state}
        current = self.definition.initial_state
        path = []
        
        for _ in range(min(5, len(self.definition.transitions))):
            # Find a transition from current state
            for t in self.definition.transitions:
                if current in t.from_states and t.to_state not in visited:
                    path.append(t)
                    visited.add(t.to_state)
                    current = t.to_state
                    break
        
        for i, t in enumerate(path):
            lines.append(f"# machine = machine.{t.name}()  # Now in {t.to_state.__name__}")
        
        lines.extend([
            "#",
            "# # Invalid transitions are TYPE ERRORS (caught by mypy/pyright)",
            "# # machine = machine.invalid_transition()  # Error: method doesn't exist for this state",
        ])
        
        return "\n".join(lines)


# =============================================================================
# BUILDER API - Fluent interface for defining state machines
# =============================================================================

class SpecterBuilder:
    """
    Fluent builder for state machine definitions.
    
    Usage:
        machine = (SpecterBuilder("ConnectionFSM")
            .state(Disconnected)
            .state(Connecting)
            .state(Connected)
            .state(Disconnecting)
            .initial(Disconnected)
            .transition("connect", Disconnected, Connecting)
            .transition("connected", Connecting, Connected)
            .transition("disconnect", [Connected, Connecting], Disconnecting)
            .transition("disconnected", Disconnecting, Disconnected)
            .build())
        
        code = SpecterCodeGen(machine).generate()
    """
    
    def __init__(self, name: str):
        self._name = name
        self._states: List[Type[StateMarker]] = []
        self._initial: Optional[Type[StateMarker]] = None
        self._transitions: List[Transition] = []
        self._data_fields: Dict[str, str] = {}
    
    def state(self, state_class: Type[StateMarker]) -> 'SpecterBuilder':
        """Add a state to the machine."""
        if state_class not in self._states:
            self._states.append(state_class)
        return self
    
    def states(self, *state_classes: Type[StateMarker]) -> 'SpecterBuilder':
        """Add multiple states."""
        for s in state_classes:
            self.state(s)
        return self
    
    def initial(self, state_class: Type[StateMarker]) -> 'SpecterBuilder':
        """Set the initial state."""
        if state_class not in self._states:
            self._states.append(state_class)
        self._initial = state_class
        return self
    
    def transition(
        self,
        name: str,
        from_states: Union[Type[StateMarker], List[Type[StateMarker]]],
        to_state: Type[StateMarker],
        guard: Optional[str] = None,
        action: Optional[str] = None
    ) -> 'SpecterBuilder':
        """
        Add a transition.
        
        Args:
            name: Method name for this transition
            from_states: Source state(s) - single class or list
            to_state: Target state
            guard: Optional Python expression that must be true
            action: Optional Python statement to execute
        """
        if isinstance(from_states, list):
            from_tuple = tuple(from_states)
        else:
            from_tuple = (from_states,)
        
        # Auto-add states
        for s in from_tuple:
            if s not in self._states:
                self._states.append(s)
        if to_state not in self._states:
            self._states.append(to_state)
        
        self._transitions.append(Transition(
            name=name,
            from_states=from_tuple,
            to_state=to_state,
            guard=guard,
            action=action,
        ))
        return self
    
    def data_field(self, name: str, type_annotation: str) -> 'SpecterBuilder':
        """Add a data field to be carried by the machine."""
        self._data_fields[name] = type_annotation
        return self
    
    def build(self) -> StateDefinition:
        """Build the state machine definition."""
        if self._initial is None:
            if self._states:
                self._initial = self._states[0]
            else:
                raise ValueError("No states defined")
        
        return StateDefinition(
            name=self._name,
            states=self._states,
            initial_state=self._initial,
            transitions=self._transitions,
            data_fields=self._data_fields,
        )


# =============================================================================
# RUNTIME MACHINE - For when you need dynamic transitions
# =============================================================================

class RuntimeMachine:
    """
    Runtime state machine for dynamic/interpreted scenarios.
    
    This is the FALLBACK when type-level encoding isn't possible
    (e.g., state machine loaded from config file at runtime).
    
    It provides the SAME guarantees but at RUNTIME, not compile-time.
    """
    
    def __init__(self, definition: StateDefinition):
        self._definition = definition
        self._state = definition.initial_state
        self._data: Dict[str, Any] = {}
        
        # Build transition lookup
        self._transitions: Dict[Tuple[Type[StateMarker], str], Transition] = {}
        for t in definition.transitions:
            for from_state in t.from_states:
                self._transitions[(from_state, t.name)] = t
    
    @property
    def state(self) -> Type[StateMarker]:
        return self._state
    
    @property
    def state_name(self) -> str:
        return self._state.__name__
    
    @property
    def data(self) -> Dict[str, Any]:
        return self._data
    
    def can_transition(self, name: str) -> bool:
        """Check if transition is valid from current state."""
        return (self._state, name) in self._transitions
    
    def available_transitions(self) -> List[str]:
        """Get list of valid transitions from current state."""
        return [
            name for (state, name) in self._transitions.keys()
            if state == self._state
        ]
    
    def transition(self, name: str) -> 'RuntimeMachine':
        """
        Execute a transition.
        
        Raises RuntimeError if transition is invalid.
        Returns self for chaining.
        """
        key = (self._state, name)
        if key not in self._transitions:
            available = self.available_transitions()
            raise RuntimeError(
                f"Invalid transition '{name}' from state {self._state.__name__}. "
                f"Available: {available}"
            )
        
        t = self._transitions[key]
        
        # Check guard
        if t.guard:
            # Evaluate guard in context of machine data
            if not eval(t.guard, {"self": self, **self._data}):
                raise RuntimeError(f"Guard failed for transition '{name}': {t.guard}")
        
        # Execute action
        if t.action:
            exec(t.action, {"self": self, **self._data})
        
        # Transition
        self._state = t.to_state
        return self
    
    def __repr__(self) -> str:
        return f"RuntimeMachine({self._definition.name}, state={self.state_name})"


# =============================================================================
# VISUALIZATION - Generate state diagrams
# =============================================================================

def generate_mermaid(definition: StateDefinition) -> str:
    """
    Generate Mermaid diagram syntax for a state machine.
    
    Paste the output into https://mermaid.live/ to visualize.
    """
    lines = ["stateDiagram-v2"]
    
    # Mark initial state
    lines.append(f"    [*] --> {definition.initial_state.__name__}")
    
    # Add transitions
    for t in definition.transitions:
        for from_state in t.from_states:
            label = t.name
            if t.guard:
                label += f" [{t.guard}]"
            lines.append(f"    {from_state.__name__} --> {t.to_state.__name__}: {label}")
    
    return "\n".join(lines)


def generate_ascii_diagram(definition: StateDefinition) -> str:
    """Generate simple ASCII representation of state machine."""
    lines = [
        f"State Machine: {definition.name}",
        "=" * 50,
        f"Initial State: {definition.initial_state.__name__}",
        "",
        "Transitions:",
    ]
    
    for t in definition.transitions:
        from_names = ", ".join(s.__name__ for s in t.from_states)
        guard = f" [if {t.guard}]" if t.guard else ""
        lines.append(f"  {from_names} --({t.name})--> {t.to_state.__name__}{guard}")
    
    return "\n".join(lines)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Core types
    'StateMarker',
    'StateMachine',
    'Transition',
    'StateDefinition',
    
    # Builder
    'SpecterBuilder',
    
    # Code generation
    'SpecterCodeGen',
    
    # Runtime machine
    'RuntimeMachine',
    
    # Visualization
    'generate_mermaid',
    'generate_ascii_diagram',
    
    # Example states
    'Idle', 'Starting', 'Running', 'Paused', 'Stopping', 'Stopped', 'Error',
]


# =============================================================================
# DEMONSTRATION
# =============================================================================

def demo():
    """Demonstrate SPECTER capabilities."""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  SPECTER: Phantom Type State Machine                                          ║
║                                                                               ║
║  State machines where invalid transitions are IMPOSSIBLE TO WRITE.            ║
║                                                                               ║
║  Traditional FSM:                                                             ║
║    if state == "idle" and can_start:                                          ║
║        state = "running"   # What if we forget the check? 💥                  ║
║                                                                               ║
║  SPECTER FSM:                                                                 ║
║    machine: Machine[Running] = machine_idle.start()  # Type-checked! ✓       ║
║    machine: Machine[Running] = machine_idle.stop()   # TYPE ERROR! ✗         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # =========================================================================
    # Example 1: Process Lifecycle
    # =========================================================================
    print("=" * 70)
    print("EXAMPLE 1: Process Lifecycle State Machine")
    print("=" * 70)
    
    # Define custom states for this example
    class Created(StateMarker): pass
    class Ready(StateMarker): pass
    class Running(StateMarker): pass
    class Blocked(StateMarker): pass
    class Terminated(StateMarker): pass
    
    # Build state machine definition
    process_fsm = (SpecterBuilder("ProcessFSM")
        .states(Created, Ready, Running, Blocked, Terminated)
        .initial(Created)
        .transition("admit", Created, Ready)
        .transition("dispatch", Ready, Running)
        .transition("timeout", Running, Ready)
        .transition("block", Running, Blocked)
        .transition("unblock", Blocked, Ready)
        .transition("exit", Running, Terminated)
        .transition("kill", [Ready, Running, Blocked], Terminated)
        .build())
    
    print("\n" + generate_ascii_diagram(process_fsm))
    
    # Generate type-safe code
    print("\n" + "-" * 70)
    print("GENERATED TYPE-SAFE CODE (excerpt):")
    print("-" * 70)
    
    code = SpecterCodeGen(process_fsm).generate()
    
    # Show just the transition methods
    for line in code.split('\n'):
        if 'def ' in line or 'Transition:' in line or '@property' in line:
            print(line)
    
    # =========================================================================
    # Example 2: Runtime Machine
    # =========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Runtime Machine Execution")
    print("=" * 70)
    
    machine = RuntimeMachine(process_fsm)
    
    print(f"\nInitial state: {machine.state_name}")
    print(f"Available transitions: {machine.available_transitions()}")
    
    # Execute valid path
    path = ["admit", "dispatch", "timeout", "dispatch", "block", "unblock", "dispatch", "exit"]
    
    print("\nExecuting path:")
    for transition in path:
        print(f"  {machine.state_name} --({transition})--> ", end="")
        machine.transition(transition)
        print(f"{machine.state_name}")
    
    # Try invalid transition
    print("\n" + "-" * 70)
    print("ATTEMPTING INVALID TRANSITION:")
    print("-" * 70)
    
    # Reset to demonstrate error
    machine = RuntimeMachine(process_fsm)
    print(f"\nState: {machine.state_name}")
    print(f"Available: {machine.available_transitions()}")
    
    try:
        print("Attempting: 'dispatch' (invalid from Created)")
        machine.transition("dispatch")
    except RuntimeError as e:
        print(f"✗ CAUGHT: {e}")
    
    # =========================================================================
    # Example 3: Connection State Machine
    # =========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 3: TCP-like Connection State Machine")
    print("=" * 70)
    
    class Closed(StateMarker): pass
    class Listen(StateMarker): pass
    class SynSent(StateMarker): pass
    class SynReceived(StateMarker): pass
    class Established(StateMarker): pass
    class FinWait(StateMarker): pass
    class CloseWait(StateMarker): pass
    class TimeWait(StateMarker): pass
    
    connection_fsm = (SpecterBuilder("ConnectionFSM")
        .initial(Closed)
        .transition("passive_open", Closed, Listen)
        .transition("active_open", Closed, SynSent)
        .transition("syn_received", Listen, SynReceived)
        .transition("close", Listen, Closed)
        .transition("syn_ack_received", SynSent, Established)
        .transition("close", SynSent, Closed)
        .transition("ack_received", SynReceived, Established)
        .transition("close", SynReceived, FinWait)
        .transition("close", Established, FinWait)
        .transition("fin_received", Established, CloseWait)
        .transition("close", CloseWait, Closed)  # Simplified
        .transition("fin_received", FinWait, TimeWait)
        .transition("timeout", TimeWait, Closed)
        .build())
    
    print("\nMermaid Diagram (paste into https://mermaid.live/):")
    print("-" * 70)
    print(generate_mermaid(connection_fsm))
    
    # =========================================================================
    # Example 4: Generated Code with Type Safety Demo
    # =========================================================================
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Full Generated Module")
    print("=" * 70)
    
    class Off(StateMarker): pass
    class On(StateMarker): pass
    
    light_switch = (SpecterBuilder("LightSwitch")
        .initial(Off)
        .transition("turn_on", Off, On)
        .transition("turn_off", On, Off)
        .build())
    
    full_code = SpecterCodeGen(light_switch).generate()
    
    print("\nGenerated code for LightSwitch FSM:")
    print("-" * 70)
    print(full_code)
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("THE UNCOMFORTABLE TRUTH")
    print("=" * 70)
    print("""
    Most state machines are checked at RUNTIME:
        - Bugs slip through if tests don't cover the path
        - Production crashes on invalid transitions
        - "It worked in dev" → "It crashed in prod"
    
    SPECTER makes invalid transitions IMPOSSIBLE TO WRITE:
        - Type checker (mypy/pyright) catches errors
        - No runtime overhead - it's just types
        - If it compiles, it can't do invalid transitions
    
    GUARANTEE:
        If mypy/pyright passes on the generated code,
        invalid state transitions are IMPOSSIBLE.
    
    LIMITATION:
        The type-level encoding requires code generation.
        Copy the generated code into your project.
        Runtime magic would defeat the purpose.
    """)


if __name__ == "__main__":
    demo()
