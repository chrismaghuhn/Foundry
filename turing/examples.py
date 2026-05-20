#!/usr/bin/env python3
"""
Turing Machine Usage Examples

Universal Turing Machine Simulator.
Watch the head dance across the tape!
"""

from turing import (
    # Core
    TuringMachine,
    Tape,
    Direction,
    
    # Visualization
    visualize_execution,
    visualize_transition_table,
    
    # Built-in machines
    create_binary_increment,
    create_unary_addition,
    create_palindrome_checker,
    create_busy_beaver_3,
    
    # Convenience
    get_machine,
    trace,
    MACHINES,
)


def example_basic():
    """
    Example 1: How a Turing Machine Works
    """
    print("=" * 60)
    print("Example 1: How a Turing Machine Works")
    print("=" * 60)
    
    print("""
A Turing machine has:
  1. An infinite tape of cells
  2. A head that reads/writes and moves
  3. A finite set of states
  4. A transition function: δ(state, symbol) → (new_state, write, direction)

Each step:
  1. Read the symbol under the head
  2. Look up the transition
  3. Write new symbol, move head, change state
  4. Repeat until halt
""")
    
    # Create a simple machine that replaces a's with b's
    tm = TuringMachine(
        name="Replace a→b",
        states={'scan', 'halt'},
        alphabet={'a', 'b', '_'},
        transitions={
            ('scan', 'a'): ('scan', 'b', 'R'),  # Replace a with b, move right
            ('scan', 'b'): ('scan', 'b', 'R'),  # Skip b's
            ('scan', '_'): ('halt', '_', 'N'),  # Halt at blank
        },
        initial_state='scan',
        halt_states={'halt'}
    )
    
    result = tm.run("aaab")
    print(f"Input:  'aaab'")
    print(f"Output: '{result.tape_content}'")
    print(f"Steps:  {result.steps}")
    print()


def example_binary_increment():
    """
    Example 2: Binary Increment
    """
    print("=" * 60)
    print("Example 2: 🔢 Binary Increment")
    print("=" * 60)
    
    print("""
This machine adds 1 to a binary number.
Watch the carry propagate!
""")
    
    tm = create_binary_increment()
    
    test_cases = [
        ("0", "1"),      # 0 → 1
        ("1", "10"),     # 1 → 2
        ("10", "11"),    # 2 → 3
        ("11", "100"),   # 3 → 4
        ("111", "1000"), # 7 → 8
        ("1011", "1100"), # 11 → 12
    ]
    
    for input_val, expected in test_cases:
        result = tm.run(input_val)
        decimal_in = int(input_val, 2)
        decimal_out = int(result.tape_content, 2) if result.tape_content else 0
        status = "✓" if result.tape_content == expected else "✗"
        print(f"  {input_val:>6} → {result.tape_content:<6}  ({decimal_in} → {decimal_out}) {status}")
    print()


def example_unary_addition():
    """
    Example 3: Unary Addition
    """
    print("=" * 60)
    print("Example 3: ➕ Unary Addition")
    print("=" * 60)
    
    print("""
Unary numbers: 1 = "1", 2 = "11", 3 = "111", etc.
This machine computes m + n using unary representation.
""")
    
    tm = create_unary_addition()
    
    test_cases = [
        ("1+1", 2),
        ("11+1", 3),
        ("11+111", 5),
        ("111+11", 5),
    ]
    
    for input_val, expected in test_cases:
        result = tm.run(input_val)
        # Count 1s in result
        count = result.tape_content.count('1')
        # Parse input
        parts = input_val.split('+')
        a, b = len(parts[0]), len(parts[1])
        status = "✓" if count == expected else "✗"
        print(f"  {a} + {b} = {count} {status}  ('{input_val}' → '{result.tape_content}')")
    print()


def example_palindrome():
    """
    Example 4: Palindrome Checker
    """
    print("=" * 60)
    print("Example 4: 🪞 Palindrome Checker")
    print("=" * 60)
    
    print("""
Checks if a binary string is a palindrome.
Accepts if palindrome, rejects otherwise.
""")
    
    tm = create_palindrome_checker()
    
    test_cases = [
        ("", True),      # Empty
        ("0", True),     # Single
        ("1", True),     # Single
        ("00", True),    # Palindrome
        ("11", True),    # Palindrome
        ("010", True),   # Palindrome
        ("1001", True),  # Palindrome
        ("10", False),   # Not palindrome
        ("01", False),   # Not palindrome
        ("1010", False), # Not palindrome
    ]
    
    for input_val, is_palindrome in test_cases:
        result = tm.run(input_val)
        accepted = result.final_state == 'accept'
        status = "✓" if accepted == is_palindrome else "✗"
        verdict = "accept" if accepted else "reject"
        display = input_val if input_val else "(empty)"
        print(f"  {display:>6} → {verdict:6} {status}")
    print()


def example_busy_beaver():
    """
    Example 5: The Busy Beaver
    """
    print("=" * 60)
    print("Example 5: 🦫 The Busy Beaver")
    print("=" * 60)
    
    print("""
The Busy Beaver problem: What's the maximum number of 1s
that an n-state Turing machine can write before halting?

This is UNCOMPUTABLE! No algorithm can solve it in general.

For n=3, the answer is 6 ones in 13 steps.
This is the 3-state champion Busy Beaver.
""")
    
    tm = create_busy_beaver_3()
    result = tm.run("", max_steps=100)
    
    print(f"States: A, B, C, HALT")
    print(f"Starting tape: blank")
    print(f"")
    print(f"Final tape: {result.tape_content}")
    print(f"Ones written: {result.tape_content.count('1')}")
    print(f"Steps taken: {result.steps}")
    print()


def example_visualization():
    """
    Example 6: Execution Visualization
    """
    print("=" * 60)
    print("Example 6: 👁️ Watch the Machine Run")
    print("=" * 60)
    
    tm = create_binary_increment()
    print(visualize_execution(tm, "11", max_steps=20))
    print()


def example_transition_table():
    """
    Example 7: Transition Table
    """
    print("=" * 60)
    print("Example 7: 📋 Transition Table")
    print("=" * 60)
    
    tm = create_binary_increment()
    print()
    print(visualize_transition_table(tm))
    print()


def example_custom_machine():
    """
    Example 8: Build Your Own Machine
    """
    print("=" * 60)
    print("Example 8: 🔧 Build Your Own Machine")
    print("=" * 60)
    
    print("""
Let's build a machine that duplicates a string of 1s.
Input: "111" → Output: "111111"
""")
    
    # Simplified duplicator concept demo
    tm = TuringMachine(
        name="Bit Flipper",
        states={'flip', 'done', 'halt'},
        alphabet={'0', '1', '_'},
        transitions={
            # Flip all bits
            ('flip', '0'): ('flip', '1', 'R'),
            ('flip', '1'): ('flip', '0', 'R'),
            ('flip', '_'): ('done', '_', 'L'),
            # Return to start
            ('done', '0'): ('done', '0', 'L'),
            ('done', '1'): ('done', '1', 'L'),
            ('done', '_'): ('halt', '_', 'R'),
        },
        initial_state='flip',
        halt_states={'halt'}
    )
    
    input_val = "1010"
    result = tm.run(input_val)
    
    print(f"Bit Flipper Machine:")
    print(f"  Input:  '{input_val}'")
    print(f"  Output: '{result.tape_content}'")
    print(f"  Steps:  {result.steps}")
    print()


def example_trace():
    """
    Example 9: Step-by-Step Trace
    """
    print("=" * 60)
    print("Example 9: 🔍 Step-by-Step Trace")
    print("=" * 60)
    
    print("\nTracing binary increment of '11' (3 → 4):\n")
    
    tm = create_binary_increment()
    
    for config in trace(tm, "11", max_steps=20):
        tape_window, head_pos = config.tape.get_window(config.head_position, 5)
        print(f"Step {config.step:2d}: |{'|'.join(tape_window)}|  state={config.state}")
        # Show head position
        pointer = "       " + " " * (head_pos * 2) + "▲"
        print(pointer)
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ████████╗██╗   ██╗██████╗ ██╗███╗   ██╗ ██████╗              ║
║  ╚══██╔══╝██║   ██║██╔══██╗██║████╗  ██║██╔════╝              ║
║     ██║   ██║   ██║██████╔╝██║██╔██╗ ██║██║  ███╗             ║
║     ██║   ██║   ██║██╔══██╗██║██║╚██╗██║██║   ██║             ║
║     ██║   ╚██████╔╝██║  ██║██║██║ ╚████║╚██████╔╝             ║
║     ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝              ║
║                                                               ║
║      🖥️  Universal Turing Machine Simulator 🖥️                ║
║                                                               ║
║   Watch the head dance across the tape.                       ║
║   The foundation of all computation.                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_binary_increment()
    example_unary_addition()
    example_palindrome()
    example_busy_beaver()
    example_visualization()
    example_transition_table()
    example_custom_machine()
    example_trace()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Historical Note:
    Alan Turing invented the Turing machine in 1936 to
    formalize the concept of computation. He proved that
    there are problems no algorithm can solve (like the
    halting problem and the Busy Beaver function).
    
    The Church-Turing thesis states: anything "computable"
    can be computed by a Turing machine. Every modern
    computer is essentially an optimized Turing machine.
""")


if __name__ == "__main__":
    main()
