"""
Turing: Universal Turing Machine Simulator

A complete Turing machine simulator with visualization.
Watch the head dance across the tape. Understand what "computable" really means.

Background:

    In 1936, Alan Turing defined the Turing machine as a mathematical model
    of computation. It's the theoretical foundation of computer science.
    
    The Church-Turing thesis states that anything "computable" can be
    computed by a Turing machine. Every modern computer is essentially
    an optimized, finite approximation of a Turing machine.

How It Works:

    A Turing machine consists of:
    1. An infinite tape divided into cells (we simulate with lazy expansion)
    2. A head that reads/writes symbols and moves left/right
    3. A finite set of states
    4. A transition function: δ(state, symbol) → (new_state, write, direction)
    
    Execution:
    1. Read symbol under head
    2. Look up transition for (current_state, symbol)
    3. Write new symbol, move head, change state
    4. Repeat until halt state or no transition

Example - Binary Increment:
    
    Input:  "1011" (11 in binary)
    Output: "1100" (12 in binary)
    
    The machine scans right to find the end, then propagates
    the carry left, just like you would do by hand.

Built-in Programs:

    - Binary increment
    - Unary addition  
    - Palindrome checker
    - Busy Beaver (3-state)
    - Binary to unary converter

Usage:
    >>> from turing import TuringMachine, run_with_trace
    >>> 
    >>> # Define a simple machine
    >>> tm = TuringMachine(
    ...     states={'q0', 'q1', 'halt'},
    ...     alphabet={'0', '1', '_'},
    ...     transitions={
    ...         ('q0', '0'): ('q0', '0', 'R'),
    ...         ('q0', '1'): ('q0', '1', 'R'),
    ...         ('q0', '_'): ('halt', '_', 'N'),
    ...     },
    ...     initial_state='q0',
    ...     halt_states={'halt'},
    ...     blank_symbol='_'
    ... )
    >>> 
    >>> result = tm.run("1011")
    >>> print(result.tape_content)

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional, List, Iterator, Any, Callable
from collections import deque
from enum import Enum
import time


# =============================================================================
# Types and Constants
# =============================================================================

class Direction(Enum):
    """Head movement direction."""
    LEFT = 'L'
    RIGHT = 'R'
    NONE = 'N'  # Stay in place
    
    @classmethod
    def from_str(cls, s: str) -> 'Direction':
        """Parse direction from string."""
        s = s.upper()
        if s in ('L', 'LEFT'):
            return cls.LEFT
        if s in ('R', 'RIGHT'):
            return cls.RIGHT
        if s in ('N', 'NONE', 'S', 'STAY'):
            return cls.NONE
        raise ValueError(f"Invalid direction: {s}")


# Transition: (state, symbol) -> (new_state, write_symbol, direction)
Transition = Tuple[str, str, Direction]
TransitionTable = Dict[Tuple[str, str], Transition]


# =============================================================================
# Tape - The Infinite Memory
# =============================================================================

class Tape:
    """
    An infinite tape for the Turing machine.
    
    The tape is theoretically infinite in both directions.
    We implement it with lazy expansion using a deque and offset tracking.
    
    Implementation:
        - deque for O(1) append/prepend
        - offset tracks where index 0 is in the deque
        - Negative indices expand left, large indices expand right
    """
    
    def __init__(self, initial: str = "", blank: str = "_"):
        """
        Initialize tape with optional initial content.
        
        Args:
            initial: Initial tape content (head starts at position 0)
            blank: The blank symbol (default '_')
        """
        self.blank = blank
        self._tape: deque = deque()
        self._offset = 0  # tape[0] corresponds to position -offset
        
        # Initialize with content
        if initial:
            self._tape.extend(initial)
        else:
            self._tape.append(blank)
    
    def _ensure_position(self, pos: int) -> None:
        """Ensure position exists by expanding tape if needed."""
        # Real index in deque
        real_idx = pos + self._offset
        
        # Expand left if needed
        while real_idx < 0:
            self._tape.appendleft(self.blank)
            self._offset += 1
            real_idx = pos + self._offset
        
        # Expand right if needed
        while real_idx >= len(self._tape):
            self._tape.append(self.blank)
    
    def read(self, pos: int) -> str:
        """Read symbol at position."""
        self._ensure_position(pos)
        return self._tape[pos + self._offset]
    
    def write(self, pos: int, symbol: str) -> None:
        """Write symbol at position."""
        self._ensure_position(pos)
        self._tape[pos + self._offset] = symbol
    
    def get_content(self, strip_blanks: bool = True) -> str:
        """Get tape content as string."""
        content = ''.join(self._tape)
        if strip_blanks:
            content = content.strip(self.blank)
        return content
    
    def get_window(self, center: int, width: int = 10) -> Tuple[str, int]:
        """
        Get a window of the tape around a position.
        
        Returns:
            (content, head_position_in_window)
        """
        start = center - width
        end = center + width + 1
        
        chars = []
        for i in range(start, end):
            chars.append(self.read(i))
        
        return ''.join(chars), width
    
    def __repr__(self) -> str:
        return f"Tape({self.get_content()!r})"


# =============================================================================
# Configuration - Machine State Snapshot
# =============================================================================

@dataclass
class Configuration:
    """
    A complete snapshot of the Turing machine's state.
    
    This captures everything needed to continue execution:
    - Current state
    - Head position
    - Tape content
    """
    state: str
    head_position: int
    tape: Tape
    step: int = 0
    
    def to_string(self, window_width: int = 15) -> str:
        """Create a visual representation."""
        tape_window, head_in_window = self.tape.get_window(
            self.head_position, window_width
        )
        
        # Build visualization
        lines = []
        
        # Tape with brackets
        lines.append(f"  |{'|'.join(tape_window)}|")
        
        # Head pointer
        pointer_pos = 2 + head_in_window * 2 + 1
        pointer_line = ' ' * pointer_pos + '▲'
        lines.append(pointer_line)
        
        # State info
        lines.append(f"  State: {self.state}  Step: {self.step}")
        
        return '\n'.join(lines)


# =============================================================================
# Execution Result
# =============================================================================

@dataclass
class ExecutionResult:
    """Result of running a Turing machine."""
    halted: bool
    final_state: str
    tape_content: str
    steps: int
    history: List[Configuration] = field(default_factory=list)
    halt_reason: str = ""
    
    def __repr__(self) -> str:
        status = "HALTED" if self.halted else "TIMEOUT/STUCK"
        return f"ExecutionResult({status}, state={self.final_state}, tape={self.tape_content!r}, steps={self.steps})"


# =============================================================================
# Turing Machine
# =============================================================================

class TuringMachine:
    """
    A Universal Turing Machine simulator.
    
    This simulates a deterministic single-tape Turing machine with:
    - Finite set of states
    - Finite alphabet (including blank symbol)
    - Transition function δ: Q × Σ → Q × Σ × {L, R, N}
    - Designated initial and halt states
    
    The machine halts when:
    1. It reaches a halt state
    2. No transition is defined (stuck)
    3. Step limit is reached (timeout)
    
    Example:
        >>> tm = TuringMachine(
        ...     states={'q0', 'q1', 'halt'},
        ...     alphabet={'0', '1', '_'},
        ...     transitions={
        ...         ('q0', '1'): ('q1', '0', 'R'),
        ...         ('q1', '1'): ('q1', '1', 'R'),
        ...     },
        ...     initial_state='q0',
        ...     halt_states={'halt'}
        ... )
        >>> result = tm.run("111")
    """
    
    def __init__(
        self,
        states: Set[str],
        alphabet: Set[str],
        transitions: Dict[Tuple[str, str], Tuple[str, str, str]],
        initial_state: str,
        halt_states: Set[str],
        blank_symbol: str = "_",
        name: str = "TM",
    ):
        """
        Initialize a Turing machine.
        
        Args:
            states: Set of all states
            alphabet: Set of tape symbols (including blank)
            transitions: Dict mapping (state, symbol) to (new_state, write, direction)
            initial_state: Starting state
            halt_states: Set of accepting/halting states
            blank_symbol: The blank symbol (default '_')
            name: Name for this machine
        """
        self.states = states
        self.alphabet = alphabet
        self.blank_symbol = blank_symbol
        self.initial_state = initial_state
        self.halt_states = halt_states
        self.name = name
        
        # Parse and validate transitions
        self.transitions: TransitionTable = {}
        for (state, symbol), (new_state, write, direction) in transitions.items():
            if state not in states:
                raise ValueError(f"Unknown state in transition: {state}")
            if new_state not in states:
                raise ValueError(f"Unknown target state: {new_state}")
            if symbol not in alphabet:
                raise ValueError(f"Unknown symbol: {symbol}")
            if write not in alphabet:
                raise ValueError(f"Unknown write symbol: {write}")
            
            dir_enum = Direction.from_str(direction) if isinstance(direction, str) else direction
            self.transitions[(state, symbol)] = (new_state, write, dir_enum)
        
        # Validate initial state
        if initial_state not in states:
            raise ValueError(f"Initial state {initial_state} not in states")
        
        # Validate halt states
        for hs in halt_states:
            if hs not in states:
                raise ValueError(f"Halt state {hs} not in states")
    
    def step(self, config: Configuration) -> Optional[Configuration]:
        """
        Execute one step of the machine.
        
        Returns:
            New configuration, or None if halted/stuck
        """
        # Check if already halted
        if config.state in self.halt_states:
            return None
        
        # Read current symbol
        symbol = config.tape.read(config.head_position)
        
        # Look up transition
        key = (config.state, symbol)
        if key not in self.transitions:
            return None  # Stuck - no transition defined
        
        new_state, write_symbol, direction = self.transitions[key]
        
        # Write symbol
        config.tape.write(config.head_position, write_symbol)
        
        # Move head
        new_position = config.head_position
        if direction == Direction.LEFT:
            new_position -= 1
        elif direction == Direction.RIGHT:
            new_position += 1
        
        return Configuration(
            state=new_state,
            head_position=new_position,
            tape=config.tape,
            step=config.step + 1
        )
    
    def run(
        self,
        input_string: str = "",
        max_steps: int = 10000,
        record_history: bool = False,
    ) -> ExecutionResult:
        """
        Run the machine on input.
        
        Args:
            input_string: Initial tape content
            max_steps: Maximum steps before timeout
            record_history: Whether to record all configurations
        
        Returns:
            ExecutionResult with final state and tape
        """
        # Initialize
        tape = Tape(input_string, self.blank_symbol)
        config = Configuration(
            state=self.initial_state,
            head_position=0,
            tape=tape,
            step=0
        )
        
        history: List[Configuration] = []
        if record_history:
            history.append(Configuration(
                state=config.state,
                head_position=config.head_position,
                tape=Tape(tape.get_content(strip_blanks=False), self.blank_symbol),
                step=0
            ))
        
        # Run
        halt_reason = ""
        while config.step < max_steps:
            # Check halt
            if config.state in self.halt_states:
                halt_reason = f"Reached halt state: {config.state}"
                break
            
            # Step
            new_config = self.step(config)
            
            if new_config is None:
                # Stuck
                symbol = tape.read(config.head_position)
                halt_reason = f"No transition for ({config.state}, {symbol!r})"
                break
            
            config = new_config
            
            if record_history:
                history.append(Configuration(
                    state=config.state,
                    head_position=config.head_position,
                    tape=Tape(tape.get_content(strip_blanks=False), self.blank_symbol),
                    step=config.step
                ))
        else:
            halt_reason = f"Timeout after {max_steps} steps"
        
        return ExecutionResult(
            halted=config.state in self.halt_states or halt_reason.startswith("No transition"),
            final_state=config.state,
            tape_content=tape.get_content(),
            steps=config.step,
            history=history,
            halt_reason=halt_reason,
        )
    
    def run_with_trace(
        self,
        input_string: str = "",
        max_steps: int = 1000,
        delay: float = 0,
    ) -> Iterator[Configuration]:
        """
        Run with step-by-step trace (generator).
        
        Yields configurations as the machine runs.
        Useful for visualization.
        """
        tape = Tape(input_string, self.blank_symbol)
        config = Configuration(
            state=self.initial_state,
            head_position=0,
            tape=tape,
            step=0
        )
        
        yield config
        
        while config.step < max_steps:
            if config.state in self.halt_states:
                break
            
            new_config = self.step(config)
            if new_config is None:
                break
            
            config = new_config
            yield config
            
            if delay > 0:
                time.sleep(delay)
    
    def __repr__(self) -> str:
        return f"TuringMachine({self.name}, states={len(self.states)}, transitions={len(self.transitions)})"


# =============================================================================
# Visualization
# =============================================================================

def visualize_execution(
    tm: TuringMachine,
    input_string: str,
    max_steps: int = 100,
    window_width: int = 12,
) -> str:
    """
    Create ASCII visualization of Turing machine execution.
    """
    result = tm.run(input_string, max_steps=max_steps, record_history=True)
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"🖥️  TURING MACHINE: {tm.name}")
    lines.append("=" * 60)
    lines.append(f"Input: \"{input_string}\"")
    lines.append(f"Initial state: {tm.initial_state}")
    lines.append(f"Halt states: {tm.halt_states}")
    lines.append("")
    lines.append("Execution Trace:")
    lines.append("-" * 60)
    
    for config in result.history[:50]:  # Limit display
        # Get tape window
        tape_window, head_idx = config.tape.get_window(config.head_position, window_width)
        
        # Format tape
        tape_str = '|' + '|'.join(tape_window) + '|'
        
        # Head marker
        marker_pos = head_idx * 2 + 1
        marker = ' ' * marker_pos + '▲'
        
        lines.append(f"Step {config.step:3d}: {tape_str}")
        lines.append(f"         {marker} [{config.state}]")
    
    if len(result.history) > 50:
        lines.append(f"  ... ({len(result.history) - 50} more steps)")
    
    lines.append("-" * 60)
    lines.append(f"Result: {result.halt_reason}")
    lines.append(f"Final tape: \"{result.tape_content}\"")
    lines.append(f"Total steps: {result.steps}")
    lines.append("=" * 60)
    
    return '\n'.join(lines)


def visualize_transition_table(tm: TuringMachine) -> str:
    """Create a formatted transition table."""
    lines = []
    lines.append(f"Transition Table: {tm.name}")
    lines.append("=" * 50)
    lines.append(f"{'State':<10} {'Read':<6} {'Write':<6} {'Move':<6} {'Next':<10}")
    lines.append("-" * 50)
    
    for (state, symbol), (new_state, write, direction) in sorted(tm.transitions.items()):
        dir_str = direction.value
        lines.append(f"{state:<10} {symbol!r:<6} {write!r:<6} {dir_str:<6} {new_state:<10}")
    
    return '\n'.join(lines)


# =============================================================================
# Built-in Turing Machines
# =============================================================================

def create_binary_increment() -> TuringMachine:
    """
    Binary increment machine.
    
    Adds 1 to a binary number.
    Example: 1011 (11) → 1100 (12)
    
    Algorithm:
    1. Scan right to find end of number
    2. Scan left, flipping 1s to 0s until finding a 0
    3. Flip that 0 to 1
    4. Handle carry overflow (add new 1 at front)
    """
    return TuringMachine(
        name="Binary Increment",
        states={'scan_right', 'add', 'carry', 'done', 'halt'},
        alphabet={'0', '1', '_'},
        transitions={
            # Scan right to find end
            ('scan_right', '0'): ('scan_right', '0', 'R'),
            ('scan_right', '1'): ('scan_right', '1', 'R'),
            ('scan_right', '_'): ('add', '_', 'L'),
            
            # Add 1: flip 1s to 0s, 0 to 1
            ('add', '1'): ('add', '0', 'L'),  # Carry
            ('add', '0'): ('done', '1', 'L'),  # No more carry
            ('add', '_'): ('done', '1', 'N'),  # Overflow: add new 1
            
            # Scan back to start (optional cleanup)
            ('done', '0'): ('done', '0', 'L'),
            ('done', '1'): ('done', '1', 'L'),
            ('done', '_'): ('halt', '_', 'R'),
        },
        initial_state='scan_right',
        halt_states={'halt'},
        blank_symbol='_'
    )


def create_unary_addition() -> TuringMachine:
    """
    Unary addition machine.
    
    Adds two unary numbers separated by '+'.
    Example: 111+11 (3+2) → 11111 (5)
    
    Algorithm:
    1. Remove the '+' 
    2. Remove one '1' from the right group
    3. Result is the concatenation
    """
    return TuringMachine(
        name="Unary Addition",
        states={'find_plus', 'remove_plus', 'go_end', 'remove_one', 'halt'},
        alphabet={'1', '+', '_'},
        transitions={
            # Find the '+' symbol
            ('find_plus', '1'): ('find_plus', '1', 'R'),
            ('find_plus', '+'): ('remove_plus', '1', 'R'),  # Replace + with 1
            
            # Go to end
            ('remove_plus', '1'): ('remove_plus', '1', 'R'),
            ('remove_plus', '_'): ('remove_one', '_', 'L'),
            
            # Remove one '1' (to compensate for the + we replaced)
            ('remove_one', '1'): ('halt', '_', 'N'),
        },
        initial_state='find_plus',
        halt_states={'halt'},
        blank_symbol='_'
    )


def create_palindrome_checker() -> TuringMachine:
    """
    Palindrome checker for binary strings.
    
    Accepts if input is a palindrome, rejects otherwise.
    Example: 1001 → accept, 1010 → reject
    
    Algorithm:
    1. Read leftmost symbol, erase it
    2. Go to rightmost, check if same
    3. If same, erase and repeat from step 1
    4. If empty, accept
    """
    return TuringMachine(
        name="Palindrome Checker",
        states={'read_left', 'go_right_0', 'go_right_1', 'check_0', 'check_1',
                'go_left', 'accept', 'reject'},
        alphabet={'0', '1', '_'},
        transitions={
            # Read leftmost
            ('read_left', '0'): ('go_right_0', '_', 'R'),
            ('read_left', '1'): ('go_right_1', '_', 'R'),
            ('read_left', '_'): ('accept', '_', 'N'),  # Empty = palindrome
            
            # Go right (looking for 0 at end)
            ('go_right_0', '0'): ('go_right_0', '0', 'R'),
            ('go_right_0', '1'): ('go_right_0', '1', 'R'),
            ('go_right_0', '_'): ('check_0', '_', 'L'),
            
            # Go right (looking for 1 at end)
            ('go_right_1', '0'): ('go_right_1', '0', 'R'),
            ('go_right_1', '1'): ('go_right_1', '1', 'R'),
            ('go_right_1', '_'): ('check_1', '_', 'L'),
            
            # Check rightmost (expecting 0)
            ('check_0', '0'): ('go_left', '_', 'L'),
            ('check_0', '1'): ('reject', '1', 'N'),
            ('check_0', '_'): ('accept', '_', 'N'),  # Single char = palindrome
            
            # Check rightmost (expecting 1)
            ('check_1', '1'): ('go_left', '_', 'L'),
            ('check_1', '0'): ('reject', '0', 'N'),
            ('check_1', '_'): ('accept', '_', 'N'),
            
            # Go back left
            ('go_left', '0'): ('go_left', '0', 'L'),
            ('go_left', '1'): ('go_left', '1', 'L'),
            ('go_left', '_'): ('read_left', '_', 'R'),
        },
        initial_state='read_left',
        halt_states={'accept', 'reject'},
        blank_symbol='_'
    )


def create_busy_beaver_3() -> TuringMachine:
    """
    3-state Busy Beaver.
    
    The Busy Beaver problem asks: what is the maximum number of 1s
    that an n-state Turing machine can print before halting?
    
    For n=3, the answer is 6 ones in 14 steps.
    This is the champion 3-state Busy Beaver.
    
    This demonstrates that simple rules can produce complex behavior!
    """
    return TuringMachine(
        name="Busy Beaver (3-state)",
        states={'A', 'B', 'C', 'HALT'},
        alphabet={'0', '1'},
        transitions={
            ('A', '0'): ('B', '1', 'R'),
            ('A', '1'): ('C', '1', 'L'),
            ('B', '0'): ('A', '1', 'L'),
            ('B', '1'): ('B', '1', 'R'),
            ('C', '0'): ('B', '1', 'L'),
            ('C', '1'): ('HALT', '1', 'R'),
        },
        initial_state='A',
        halt_states={'HALT'},
        blank_symbol='0'
    )


def create_binary_to_unary() -> TuringMachine:
    """
    Converts a binary number to unary.
    
    Example: 101 (5 in binary) → 11111 (5 in unary)
    
    This is a more complex machine demonstrating
    the power of Turing machines for number conversion.
    
    Algorithm:
    1. Process binary digits right to left
    2. For each '1' bit at position n, add 2^n to the result
    3. Build up the unary representation
    """
    # Simplified version: just demonstrates the concept
    # Full implementation would be much larger
    return TuringMachine(
        name="Binary to Unary (Simple)",
        states={'start', 'mark', 'count', 'back', 'halt'},
        alphabet={'0', '1', 'X', '|', '_'},
        transitions={
            # Mark start, convert first 1
            ('start', '0'): ('start', '0', 'R'),
            ('start', '1'): ('mark', 'X', 'R'),
            ('start', '_'): ('halt', '_', 'N'),
            ('start', '|'): ('halt', '|', 'N'),
            
            # Continue to end
            ('mark', '0'): ('mark', '0', 'R'),
            ('mark', '1'): ('mark', '1', 'R'),
            ('mark', '_'): ('count', '|', 'L'),
            ('mark', '|'): ('count', '|', 'L'),
            
            # Go back
            ('count', '0'): ('count', '0', 'L'),
            ('count', '1'): ('count', '1', 'L'),
            ('count', 'X'): ('start', 'X', 'R'),
        },
        initial_state='start',
        halt_states={'halt'},
        blank_symbol='_'
    )


# =============================================================================
# Presets Dictionary
# =============================================================================

MACHINES: Dict[str, Callable[[], TuringMachine]] = {
    'binary_increment': create_binary_increment,
    'unary_addition': create_unary_addition,
    'palindrome': create_palindrome_checker,
    'busy_beaver_3': create_busy_beaver_3,
    'binary_to_unary': create_binary_to_unary,
}


def get_machine(name: str) -> TuringMachine:
    """Get a built-in Turing machine by name."""
    if name not in MACHINES:
        raise ValueError(f"Unknown machine: {name}. Available: {list(MACHINES.keys())}")
    return MACHINES[name]()


# =============================================================================
# Convenience Functions
# =============================================================================

def run(machine: TuringMachine, input_string: str, max_steps: int = 10000) -> ExecutionResult:
    """Run a Turing machine on input."""
    return machine.run(input_string, max_steps)


def visualize(machine: TuringMachine, input_string: str, max_steps: int = 100) -> str:
    """Visualize Turing machine execution."""
    return visualize_execution(machine, input_string, max_steps)


def trace(machine: TuringMachine, input_string: str, max_steps: int = 100) -> Iterator[Configuration]:
    """Get execution trace as iterator."""
    return machine.run_with_trace(input_string, max_steps)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core classes
    'TuringMachine',
    'Tape',
    'Configuration',
    'ExecutionResult',
    'Direction',
    
    # Visualization
    'visualize_execution',
    'visualize_transition_table',
    
    # Built-in machines
    'create_binary_increment',
    'create_unary_addition',
    'create_palindrome_checker',
    'create_busy_beaver_3',
    'create_binary_to_unary',
    
    # Convenience
    'get_machine',
    'run',
    'visualize',
    'trace',
    'MACHINES',
]
