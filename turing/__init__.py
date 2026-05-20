"""
Turing: Universal Turing Machine Simulator

A complete Turing machine simulator with visualization.
Watch the head dance across the tape. Understand computation.

Quick Start:
    >>> from turing import create_binary_increment, visualize
    >>> 
    >>> tm = create_binary_increment()
    >>> result = tm.run("1011")  # 11 in binary
    >>> print(result.tape_content)  # "1100" (12 in binary)
    >>> 
    >>> # Watch the execution
    >>> print(visualize(tm, "11"))

Built-in Machines:
    - binary_increment: Add 1 to a binary number
    - unary_addition: Add two unary numbers (111+11 = 11111)
    - palindrome: Check if binary string is a palindrome
    - busy_beaver_3: The 3-state Busy Beaver champion

Create Your Own:
    >>> from turing import TuringMachine
    >>> 
    >>> tm = TuringMachine(
    ...     name="My Machine",
    ...     states={'q0', 'q1', 'halt'},
    ...     alphabet={'0', '1', '_'},
    ...     transitions={
    ...         ('q0', '0'): ('q0', '1', 'R'),
    ...         ('q0', '_'): ('halt', '_', 'N'),
    ...     },
    ...     initial_state='q0',
    ...     halt_states={'halt'}
    ... )

The Turing machine is the theoretical foundation of all computers.
"""

from .turing import (
    # Core classes
    TuringMachine,
    Tape,
    Configuration,
    ExecutionResult,
    Direction,
    
    # Visualization
    visualize_execution,
    visualize_transition_table,
    
    # Built-in machines
    create_binary_increment,
    create_unary_addition,
    create_palindrome_checker,
    create_busy_beaver_3,
    create_binary_to_unary,
    
    # Convenience
    get_machine,
    run,
    visualize,
    trace,
    MACHINES,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core
    'TuringMachine', 'Tape', 'Configuration',
    'ExecutionResult', 'Direction',
    
    # Visualization
    'visualize_execution', 'visualize_transition_table',
    
    # Built-in machines
    'create_binary_increment', 'create_unary_addition',
    'create_palindrome_checker', 'create_busy_beaver_3',
    'create_binary_to_unary',
    
    # Convenience
    'get_machine', 'run', 'visualize', 'trace', 'MACHINES',
]
