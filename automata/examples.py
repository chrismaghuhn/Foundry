#!/usr/bin/env python3
"""
Automata Usage Examples

Cellular Automata: Where complexity emerges from simplicity.
"""

from automata import (
    GameOfLife,
    Elementary,
    LangtonsAnt,
    PATTERNS,
    FAMOUS_RULES,
    visualize_rule,
    analyze_life_pattern,
    compare_rules,
)


def example_game_of_life():
    """
    Example 1: Conway's Game of Life
    """
    print("=" * 60)
    print("Example 1: 🎮 Conway's Game of Life")
    print("=" * 60)
    
    print("""
Rules (B3/S23):
    - Birth: Dead cell with exactly 3 neighbors → alive
    - Survive: Live cell with 2-3 neighbors → stays alive
    - Death: All other live cells die

These simple rules create incredible complexity!
""")
    
    life = GameOfLife(width=30, height=15)
    life.add_pattern("glider", 2, 2)
    
    print("Initial state with a Glider:")
    print(life.render())
    
    print("\nAfter 4 generations (one glider cycle):")
    for _ in range(4):
        life.step()
    print(life.render())
    print()


def example_patterns():
    """
    Example 2: Famous Patterns
    """
    print("=" * 60)
    print("Example 2: 🌟 Famous Patterns")
    print("=" * 60)
    
    print("Available patterns:\n")
    for name, pattern in list(PATTERNS.items())[:8]:
        print(f"  {name:15} - {pattern.description}")
    
    print("\n--- Blinker (oscillator, period 2) ---")
    life = GameOfLife(width=10, height=5)
    life.add_pattern("blinker", 4, 2)
    print(life.render())
    
    life.step()
    print("\nAfter 1 step:")
    print(life.render())
    print()


def example_still_life():
    """
    Example 3: Still Lifes
    """
    print("=" * 60)
    print("Example 3: 🧱 Still Lifes")
    print("=" * 60)
    
    print("""
Still lifes are patterns that never change.
They're in perfect equilibrium.
""")
    
    life = GameOfLife(width=15, height=8)
    life.add_pattern("block", 2, 2)
    life.add_pattern("beehive", 8, 2)
    
    print("Block and Beehive:")
    print(life.render())
    
    # Verify they don't change
    hash_before = life.get_state_hash()
    life.step()
    hash_after = life.get_state_hash()
    
    print(f"After step: {'Unchanged ✓' if hash_before == hash_after else 'Changed!'}")
    print()


def example_elementary():
    """
    Example 4: Elementary Cellular Automata
    """
    print("=" * 60)
    print("Example 4: 📏 Elementary Cellular Automata")
    print("=" * 60)
    
    print("""
Stephen Wolfram's 1D automata with 256 possible rules.
Each rule defines how a cell changes based on itself
and its two neighbors.

Famous rules:
    Rule 30:  Chaotic (used for random numbers)
    Rule 90:  Sierpiński triangle
    Rule 110: TURING COMPLETE!
""")
    
    print("\n--- Rule 110 (Turing Complete!) ---")
    ca = Elementary(rule=110, width=60)
    ca.set_single_cell()
    ca.run(25)
    print(ca.render_history())
    print()


def example_rule_30():
    """
    Example 5: Rule 30 - Chaos from Order
    """
    print("=" * 60)
    print("Example 5: 🌀 Rule 30 - Chaos from Order")
    print("=" * 60)
    
    print("""
Rule 30 produces chaotic patterns from a single cell.
Wolfram used it as a random number generator!
""")
    
    ca = Elementary(rule=30, width=60)
    ca.set_single_cell()
    ca.run(20)
    print(ca.render_history())
    print()


def example_langtons_ant():
    """
    Example 6: Langton's Ant
    """
    print("=" * 60)
    print("Example 6: 🐜 Langton's Ant")
    print("=" * 60)
    
    print("""
Simple rules:
    On WHITE: turn RIGHT, flip to BLACK, move forward
    On BLACK: turn LEFT, flip to WHITE, move forward

Initially chaotic, but after ~10,000 steps...
it creates a "highway" - emergent order from chaos!
""")
    
    ant = LangtonsAnt(width=50, height=25)
    
    # Show early chaos
    ant.run(50)
    print("After 50 steps (chaotic):")
    print(ant.render())
    
    # Run more to see pattern developing
    ant.run(200)
    print(f"\nAfter {ant.generation} steps:")
    print(ant.render())
    print()


def example_pattern_analysis():
    """
    Example 7: Pattern Analysis
    """
    print("=" * 60)
    print("Example 7: 🔬 Pattern Analysis")
    print("=" * 60)
    
    print("Analyzing the Blinker oscillator:\n")
    
    life = GameOfLife(width=10, height=10)
    life.add_pattern("blinker", 4, 4)
    
    analysis = analyze_life_pattern(life, max_gen=100)
    
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    print()


def example_rule_comparison():
    """
    Example 8: Rule Comparison
    """
    print("=" * 60)
    print("Example 8: 📊 Rule Comparison")
    print("=" * 60)
    
    print("Comparing famous rules side by side:\n")
    
    print(compare_rules([30, 90, 110], width=20, generations=15))
    print()


def example_turing_complete():
    """
    Example 9: Turing Completeness
    """
    print("=" * 60)
    print("Example 9: 🖥️ Turing Completeness")
    print("=" * 60)
    
    print("""
Both Rule 110 and Conway's Game of Life are TURING COMPLETE!

This means they can compute anything computable.
With enough space and time, they could run any program.

Rule 110:
    - Proven Turing complete by Matthew Cook in 2004
    - Just 8 simple transitions!

Game of Life:
    - Proven Turing complete (can build logic gates)
    - People have built working computers in it!

The profound insight:
    Universal computation can emerge from simple rules.
""")
    
    print("Rule 110 - a Turing complete system:")
    ca = Elementary(rule=110, width=80)
    ca.set_single_cell()
    ca.run(30)
    print(ca.render_history())
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   █████╗ ██╗   ██╗████████╗ ██████╗ ███╗   ███╗ █████╗ ████████╗ █████╗  ║
║  ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗ ║
║  ███████║██║   ██║   ██║   ██║   ██║██╔████╔██║███████║   ██║   ███████║ ║
║  ██╔══██║██║   ██║   ██║   ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══██║ ║
║  ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║ ║
║  ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ║
║                                                               ║
║  🌌 Cellular Automata Explorer 🌌                              ║
║                                                               ║
║  "It from bit." - John Wheeler                                ║
║  Simple rules. Emergent complexity.                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_game_of_life()
    example_patterns()
    example_still_life()
    example_elementary()
    example_rule_30()
    example_langtons_ant()
    example_pattern_analysis()
    example_rule_comparison()
    example_turing_complete()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Key Insights:

    1. EMERGENCE: Complex behavior from simple rules
    
    2. SELF-ORGANIZATION: Order arises spontaneously
       (Langton's Ant highway appears after chaos)
    
    3. TURING COMPLETENESS: Simple systems can compute
       anything that can be computed
    
    4. UNIVERSALITY: The same patterns appear in:
       - Biology (morphogenesis)
       - Physics (crystal growth)
       - Computer science (computation)

"Cellular automata are a portal into a universe
 where complexity emerges from simplicity."
""")


if __name__ == "__main__":
    main()
