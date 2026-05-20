"""
Automata: Cellular Automata Explorer

Explore cellular automata - Conway's Game of Life, Wolfram's elementary
automata, and Langton's Ant. Watch complexity emerge from simplicity.

Quick Start:
    >>> from automata import GameOfLife, Elementary, LangtonsAnt
    >>> 
    >>> # Game of Life
    >>> life = GameOfLife(width=40, height=20)
    >>> life.add_pattern("glider", 5, 5)
    >>> life.step()
    >>> print(life.render())
    
    >>> # Elementary CA (Rule 110 - Turing Complete!)
    >>> ca = Elementary(rule=110, width=80)
    >>> ca.set_single_cell()
    >>> ca.run(40)
    >>> print(ca.render_history())
    
    >>> # Langton's Ant
    >>> ant = LangtonsAnt(width=80, height=40)
    >>> ant.run(10000)  # Watch the highway emerge!
    >>> print(ant.render())

Key Concepts:
    - EMERGENCE: Complex behavior from simple rules
    - TURING COMPLETENESS: Rule 110 and Life can compute anything!
    - SELF-ORGANIZATION: Order arises from chaos
"""

from .automata import (
    # Base
    CellularAutomaton,
    
    # Game of Life
    GameOfLife,
    Pattern,
    PATTERNS,
    
    # Elementary CA
    Elementary,
    FAMOUS_RULES,
    
    # Langton's Ant
    LangtonsAnt,
    Direction,
    
    # Utilities
    visualize_rule,
    animate_life,
    compare_rules,
    analyze_life_pattern,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Base
    'CellularAutomaton',
    
    # Game of Life
    'GameOfLife', 'Pattern', 'PATTERNS',
    
    # Elementary CA
    'Elementary', 'FAMOUS_RULES',
    
    # Langton's Ant
    'LangtonsAnt', 'Direction',
    
    # Utilities
    'visualize_rule', 'animate_life', 'compare_rules', 'analyze_life_pattern',
]
