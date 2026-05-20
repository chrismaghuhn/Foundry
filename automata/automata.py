"""
Automata: Cellular Automata Explorer

Explore cellular automata - Conway's Game of Life, Wolfram's elementary
automata, and Langton's Ant. Watch complexity emerge from simplicity.

Background:

    Cellular automata are discrete dynamical systems where:
    - Space is divided into cells
    - Each cell has a state (e.g., alive/dead)
    - Rules determine the next state based on neighbors
    - All cells update simultaneously
    
    The fascinating discovery: Simple rules can produce complex behavior!

Included Automata:

    1. Conway's Game of Life (1970)
       - 2D grid, cells are alive or dead
       - Rules: B3/S23 (Birth with 3 neighbors, Survive with 2-3)
       - Turing complete!
       - Famous patterns: Glider, Blinker, Glider Gun
    
    2. Elementary Cellular Automata (Stephen Wolfram)
       - 1D, 256 possible rules (Rule 0-255)
       - Rule 110 is Turing complete!
       - Rule 30 generates chaos from order
    
    3. Langton's Ant (1986)
       - Simple ant on a 2D grid
       - Rule: Turn right on white, left on black, flip color, move
       - After ~10,000 steps: Creates a "highway" (emergent order!)

Key Concepts:

    - Emergence: Complex behavior from simple rules
    - Self-organization: Order arising spontaneously
    - Turing completeness: Can simulate any computation
    - Period detection: Finding cycles in evolution

Usage:
    >>> from automata import GameOfLife, Elementary, LangtonsAnt
    >>> 
    >>> # Game of Life
    >>> life = GameOfLife(width=40, height=20)
    >>> life.add_pattern("glider", 5, 5)
    >>> for _ in range(50):
    ...     print(life.render())
    ...     life.step()
    >>> 
    >>> # Elementary CA (Rule 110)
    >>> ca = Elementary(rule=110, width=80)
    >>> for _ in range(40):
    ...     print(ca.render())
    ...     ca.step()

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Callable, Iterator
from enum import Enum
from abc import ABC, abstractmethod
import hashlib


# =============================================================================
# Base Classes
# =============================================================================

class CellularAutomaton(ABC):
    """Base class for all cellular automata."""
    
    @abstractmethod
    def step(self) -> None:
        """Advance one generation."""
        pass
    
    @abstractmethod
    def render(self) -> str:
        """Render current state as string."""
        pass
    
    @abstractmethod
    def get_state_hash(self) -> str:
        """Get hash of current state for cycle detection."""
        pass


# =============================================================================
# Game of Life
# =============================================================================

@dataclass
class Pattern:
    """A pattern for Game of Life."""
    name: str
    cells: List[Tuple[int, int]]
    description: str = ""


# Classic patterns
PATTERNS: Dict[str, Pattern] = {
    "glider": Pattern(
        "Glider",
        [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
        "Moves diagonally, period 4"
    ),
    "blinker": Pattern(
        "Blinker",
        [(0, 0), (0, 1), (0, 2)],
        "Oscillates, period 2"
    ),
    "block": Pattern(
        "Block",
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        "Still life"
    ),
    "beehive": Pattern(
        "Beehive",
        [(0, 1), (0, 2), (1, 0), (1, 3), (2, 1), (2, 2)],
        "Still life"
    ),
    "toad": Pattern(
        "Toad",
        [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2)],
        "Oscillator, period 2"
    ),
    "beacon": Pattern(
        "Beacon",
        [(0, 0), (0, 1), (1, 0), (2, 3), (3, 2), (3, 3)],
        "Oscillator, period 2"
    ),
    "pulsar": Pattern(
        "Pulsar",
        [
            # Top-left quadrant pattern (will be mirrored)
            (0, 2), (0, 3), (0, 4),
            (2, 0), (3, 0), (4, 0),
            (2, 5), (3, 5), (4, 5),
            (5, 2), (5, 3), (5, 4),
            # Mirror to other quadrants
            (0, 8), (0, 9), (0, 10),
            (2, 7), (3, 7), (4, 7),
            (2, 12), (3, 12), (4, 12),
            (5, 8), (5, 9), (5, 10),
            (7, 2), (7, 3), (7, 4),
            (8, 0), (9, 0), (10, 0),
            (8, 5), (9, 5), (10, 5),
            (12, 2), (12, 3), (12, 4),
            (7, 8), (7, 9), (7, 10),
            (8, 7), (9, 7), (10, 7),
            (8, 12), (9, 12), (10, 12),
            (12, 8), (12, 9), (12, 10),
        ],
        "Oscillator, period 3"
    ),
    "glider_gun": Pattern(
        "Gosper Glider Gun",
        [
            # Left block
            (4, 0), (4, 1), (5, 0), (5, 1),
            # Left part
            (4, 10), (5, 10), (6, 10),
            (3, 11), (7, 11),
            (2, 12), (8, 12),
            (2, 13), (8, 13),
            (5, 14),
            (3, 15), (7, 15),
            (4, 16), (5, 16), (6, 16),
            (5, 17),
            # Right part
            (2, 20), (3, 20), (4, 20),
            (2, 21), (3, 21), (4, 21),
            (1, 22), (5, 22),
            (0, 24), (1, 24), (5, 24), (6, 24),
            # Right block
            (2, 34), (3, 34), (2, 35), (3, 35),
        ],
        "Emits gliders periodically"
    ),
    "r_pentomino": Pattern(
        "R-Pentomino",
        [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)],
        "Methuselah, stabilizes after 1103 generations"
    ),
    "diehard": Pattern(
        "Diehard",
        [(0, 6), (1, 0), (1, 1), (2, 1), (2, 5), (2, 6), (2, 7)],
        "Disappears after 130 generations"
    ),
    "acorn": Pattern(
        "Acorn",
        [(0, 1), (1, 3), (2, 0), (2, 1), (2, 4), (2, 5), (2, 6)],
        "Methuselah, stabilizes after 5206 generations"
    ),
    "spaceship": Pattern(
        "Lightweight Spaceship (LWSS)",
        [(0, 1), (0, 4), (1, 0), (2, 0), (3, 0), (3, 4), (4, 0), (4, 1), (4, 2), (4, 3)],
        "Moves horizontally"
    ),
}


class GameOfLife(CellularAutomaton):
    """
    Conway's Game of Life.
    
    Rules (B3/S23):
        - A dead cell with exactly 3 live neighbors becomes alive (birth)
        - A live cell with 2 or 3 live neighbors stays alive (survival)
        - All other live cells die
    
    The grid is toroidal (edges wrap around).
    """
    
    def __init__(
        self,
        width: int = 40,
        height: int = 20,
        birth: Set[int] = None,
        survive: Set[int] = None,
    ):
        """
        Initialize Game of Life.
        
        Args:
            width: Grid width
            height: Grid height
            birth: Set of neighbor counts that cause birth (default {3})
            survive: Set of neighbor counts that allow survival (default {2, 3})
        """
        self.width = width
        self.height = height
        self.birth = birth or {3}
        self.survive = survive or {2, 3}
        
        # Grid: set of (x, y) coordinates of live cells
        self.cells: Set[Tuple[int, int]] = set()
        self.generation = 0
    
    def clear(self) -> None:
        """Clear the grid."""
        self.cells.clear()
        self.generation = 0
    
    def set_cell(self, x: int, y: int, alive: bool = True) -> None:
        """Set a cell's state."""
        x = x % self.width
        y = y % self.height
        
        if alive:
            self.cells.add((x, y))
        else:
            self.cells.discard((x, y))
    
    def get_cell(self, x: int, y: int) -> bool:
        """Get a cell's state."""
        x = x % self.width
        y = y % self.height
        return (x, y) in self.cells
    
    def add_pattern(self, name: str, x: int = 0, y: int = 0) -> None:
        """Add a named pattern at position (x, y)."""
        if name not in PATTERNS:
            raise ValueError(f"Unknown pattern: {name}. Available: {list(PATTERNS.keys())}")
        
        pattern = PATTERNS[name]
        for dx, dy in pattern.cells:
            self.set_cell(x + dx, y + dy, True)
    
    def add_cells(self, cells: List[Tuple[int, int]], x: int = 0, y: int = 0) -> None:
        """Add custom cells at offset."""
        for dx, dy in cells:
            self.set_cell(x + dx, y + dy, True)
    
    def randomize(self, density: float = 0.3) -> None:
        """Fill with random cells."""
        import random
        self.clear()
        for y in range(self.height):
            for x in range(self.width):
                if random.random() < density:
                    self.set_cell(x, y, True)
    
    def count_neighbors(self, x: int, y: int) -> int:
        """Count live neighbors (8-connected, toroidal)."""
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx = (x + dx) % self.width
                ny = (y + dy) % self.height
                if (nx, ny) in self.cells:
                    count += 1
        return count
    
    def step(self) -> None:
        """Advance one generation."""
        new_cells: Set[Tuple[int, int]] = set()
        
        # Check all cells that might change
        candidates: Set[Tuple[int, int]] = set()
        
        for x, y in self.cells:
            candidates.add((x, y))
            # Add neighbors (dead cells that might be born)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx = (x + dx) % self.width
                    ny = (y + dy) % self.height
                    candidates.add((nx, ny))
        
        # Apply rules
        for x, y in candidates:
            neighbors = self.count_neighbors(x, y)
            alive = (x, y) in self.cells
            
            if alive and neighbors in self.survive:
                new_cells.add((x, y))
            elif not alive and neighbors in self.birth:
                new_cells.add((x, y))
        
        self.cells = new_cells
        self.generation += 1
    
    def run(self, generations: int) -> Iterator['GameOfLife']:
        """Run for multiple generations, yielding self each step."""
        for _ in range(generations):
            yield self
            self.step()
        yield self
    
    def render(self, alive_char: str = "█", dead_char: str = " ") -> str:
        """Render grid as string."""
        lines = []
        
        # Top border
        lines.append("┌" + "─" * self.width + "┐")
        
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                if (x, y) in self.cells:
                    row += alive_char
                else:
                    row += dead_char
            lines.append("│" + row + "│")
        
        # Bottom border
        lines.append("└" + "─" * self.width + "┘")
        
        # Stats
        lines.append(f"Generation: {self.generation}  Population: {len(self.cells)}")
        
        return "\n".join(lines)
    
    def get_state_hash(self) -> str:
        """Get hash of current state."""
        cells_sorted = sorted(self.cells)
        return hashlib.md5(str(cells_sorted).encode()).hexdigest()
    
    def population(self) -> int:
        """Return number of live cells."""
        return len(self.cells)
    
    def detect_period(self, max_generations: int = 1000) -> Optional[int]:
        """
        Detect if the pattern becomes periodic.
        
        Returns the period, or None if not periodic within max_generations.
        """
        seen: Dict[str, int] = {}
        
        for gen in range(max_generations):
            state_hash = self.get_state_hash()
            
            if state_hash in seen:
                return gen - seen[state_hash]
            
            seen[state_hash] = gen
            self.step()
        
        return None


# =============================================================================
# Elementary Cellular Automata (1D)
# =============================================================================

class Elementary(CellularAutomaton):
    """
    Elementary Cellular Automata (Wolfram).
    
    1D automata with 2 states and 3-cell neighborhoods.
    256 possible rules, numbered 0-255.
    
    Famous rules:
        - Rule 30: Chaotic, used for random number generation
        - Rule 110: Turing complete!
        - Rule 90: Sierpiński triangle
        - Rule 184: Traffic flow model
    
    Each rule is encoded as an 8-bit number:
        Neighborhood: 111 110 101 100 011 010 001 000
        Rule N:       b7  b6  b5  b4  b3  b2  b1  b0
    """
    
    def __init__(self, rule: int = 110, width: int = 80):
        """
        Initialize elementary CA.
        
        Args:
            rule: Rule number 0-255
            width: Width of the 1D tape
        """
        if not 0 <= rule <= 255:
            raise ValueError(f"Rule must be 0-255, got {rule}")
        
        self.rule = rule
        self.width = width
        
        # Parse rule into lookup table
        self.lookup: Dict[Tuple[int, int, int], int] = {}
        for i in range(8):
            left = (i >> 2) & 1
            center = (i >> 1) & 1
            right = i & 1
            result = (rule >> i) & 1
            self.lookup[(left, center, right)] = result
        
        # State: list of 0/1
        self.cells = [0] * width
        self.generation = 0
        
        # History for visualization
        self.history: List[List[int]] = []
    
    def clear(self) -> None:
        """Clear to all zeros."""
        self.cells = [0] * self.width
        self.generation = 0
        self.history.clear()
    
    def set_single_cell(self) -> None:
        """Set only the center cell (classic initial condition)."""
        self.clear()
        self.cells[self.width // 2] = 1
    
    def randomize(self, density: float = 0.5) -> None:
        """Randomize cells."""
        import random
        self.cells = [1 if random.random() < density else 0 for _ in range(self.width)]
        self.generation = 0
        self.history.clear()
    
    def step(self) -> None:
        """Advance one generation."""
        # Save current state to history
        self.history.append(self.cells.copy())
        
        new_cells = [0] * self.width
        
        for i in range(self.width):
            left = self.cells[(i - 1) % self.width]
            center = self.cells[i]
            right = self.cells[(i + 1) % self.width]
            
            new_cells[i] = self.lookup[(left, center, right)]
        
        self.cells = new_cells
        self.generation += 1
    
    def run(self, generations: int) -> None:
        """Run for multiple generations."""
        for _ in range(generations):
            self.step()
    
    def render(self, alive_char: str = "█", dead_char: str = " ") -> str:
        """Render current state."""
        row = ""
        for cell in self.cells:
            row += alive_char if cell else dead_char
        return row
    
    def render_history(self, alive_char: str = "█", dead_char: str = " ") -> str:
        """Render entire history as 2D pattern."""
        lines = []
        lines.append(f"Rule {self.rule} - {self.generation} generations")
        lines.append("=" * min(self.width, 60))
        
        for row in self.history:
            line = ""
            for cell in row:
                line += alive_char if cell else dead_char
            lines.append(line)
        
        # Current state
        lines.append(self.render(alive_char, dead_char))
        
        return "\n".join(lines)
    
    def get_state_hash(self) -> str:
        """Get hash of current state."""
        return hashlib.md5(str(self.cells).encode()).hexdigest()
    
    @staticmethod
    def rule_description(rule: int) -> str:
        """Get description of a rule."""
        descriptions = {
            30: "Chaotic - Used for random number generation",
            90: "Sierpiński triangle - Self-similar fractal",
            110: "TURING COMPLETE! - Can simulate any computation",
            184: "Traffic flow model",
            0: "All cells die",
            255: "All cells live",
            18: "Binary counter",
            22: "Complex behavior",
            54: "Complex with triangular structures",
            60: "Pascal's triangle mod 2",
            62: "Complex patterns",
            126: "Fast growth then stabilizes",
            150: "Sum mod 2 (XOR of neighbors)",
            182: "Continuous growth",
        }
        return descriptions.get(rule, "No special description")


# =============================================================================
# Langton's Ant
# =============================================================================

class Direction(Enum):
    """Direction for Langton's Ant."""
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3
    
    def turn_right(self) -> 'Direction':
        return Direction((self.value + 1) % 4)
    
    def turn_left(self) -> 'Direction':
        return Direction((self.value - 1) % 4)


class LangtonsAnt(CellularAutomaton):
    """
    Langton's Ant (1986).
    
    A simple 2D Turing machine:
        - Grid of white (0) and black (1) cells
        - Ant at position (x, y) facing a direction
    
    Rules:
        1. If on WHITE: turn RIGHT, flip to BLACK, move forward
        2. If on BLACK: turn LEFT, flip to WHITE, move forward
    
    Emergent Behavior:
        - Initially chaotic
        - After ~10,000 steps: Creates a "highway" pattern!
        - Moves diagonally in a repeating pattern
    
    This is a profound example of emergent complexity from simple rules.
    """
    
    def __init__(self, width: int = 80, height: int = 40):
        """
        Initialize Langton's Ant.
        
        Args:
            width: Grid width
            height: Grid height
        """
        self.width = width
        self.height = height
        
        # Grid: set of black cells
        self.black_cells: Set[Tuple[int, int]] = set()
        
        # Ant position and direction
        self.ant_x = width // 2
        self.ant_y = height // 2
        self.ant_dir = Direction.UP
        
        self.generation = 0
    
    def clear(self) -> None:
        """Reset to initial state."""
        self.black_cells.clear()
        self.ant_x = self.width // 2
        self.ant_y = self.height // 2
        self.ant_dir = Direction.UP
        self.generation = 0
    
    def step(self) -> None:
        """Execute one step of the ant."""
        x, y = self.ant_x, self.ant_y
        is_black = (x, y) in self.black_cells
        
        if is_black:
            # On black: turn left, flip to white
            self.ant_dir = self.ant_dir.turn_left()
            self.black_cells.discard((x, y))
        else:
            # On white: turn right, flip to black
            self.ant_dir = self.ant_dir.turn_right()
            self.black_cells.add((x, y))
        
        # Move forward
        if self.ant_dir == Direction.UP:
            self.ant_y = (self.ant_y - 1) % self.height
        elif self.ant_dir == Direction.DOWN:
            self.ant_y = (self.ant_y + 1) % self.height
        elif self.ant_dir == Direction.LEFT:
            self.ant_x = (self.ant_x - 1) % self.width
        elif self.ant_dir == Direction.RIGHT:
            self.ant_x = (self.ant_x + 1) % self.width
        
        self.generation += 1
    
    def run(self, steps: int) -> None:
        """Run for multiple steps."""
        for _ in range(steps):
            self.step()
    
    def render(
        self,
        white_char: str = " ",
        black_char: str = "█",
        ant_char: str = "◆"
    ) -> str:
        """Render grid with ant."""
        lines = []
        
        # Top border
        lines.append("┌" + "─" * self.width + "┐")
        
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                if x == self.ant_x and y == self.ant_y:
                    row += ant_char
                elif (x, y) in self.black_cells:
                    row += black_char
                else:
                    row += white_char
            lines.append("│" + row + "│")
        
        # Bottom border
        lines.append("└" + "─" * self.width + "┘")
        
        # Stats
        direction_name = self.ant_dir.name
        lines.append(f"Step: {self.generation}  Ant: ({self.ant_x}, {self.ant_y}) {direction_name}  Black: {len(self.black_cells)}")
        
        return "\n".join(lines)
    
    def get_state_hash(self) -> str:
        """Get hash of current state."""
        state = (
            frozenset(self.black_cells),
            self.ant_x,
            self.ant_y,
            self.ant_dir
        )
        return hashlib.md5(str(state).encode()).hexdigest()
    
    def highway_detected(self) -> bool:
        """
        Check if the highway has formed.
        
        The highway appears after ~10,000 steps and has a
        characteristic diagonal growth pattern.
        """
        # Simple heuristic: significant black cells and high step count
        return self.generation > 10000 and len(self.black_cells) > 1000


# =============================================================================
# Visualization Utilities
# =============================================================================

def visualize_rule(rule: int, width: int = 80, generations: int = 40) -> str:
    """Visualize an elementary CA rule."""
    ca = Elementary(rule=rule, width=width)
    ca.set_single_cell()
    ca.run(generations)
    return ca.render_history()


def animate_life(
    life: GameOfLife,
    generations: int = 50,
    delay: float = 0.1
) -> Iterator[str]:
    """Generate frames for Game of Life animation."""
    for _ in range(generations):
        yield life.render()
        life.step()


def compare_rules(rules: List[int], width: int = 40, generations: int = 20) -> str:
    """Compare multiple elementary CA rules side by side."""
    cas = [Elementary(rule=r, width=width) for r in rules]
    
    for ca in cas:
        ca.set_single_cell()
        ca.run(generations)
    
    lines = []
    lines.append("Rule Comparison")
    lines.append("=" * (width * len(rules) + len(rules) - 1))
    
    # Headers
    header = "  ".join(f"Rule {r:3d}".center(width) for r in rules)
    lines.append(header)
    lines.append("-" * len(header))
    
    # Rows
    for i in range(generations):
        row_parts = []
        for ca in cas:
            if i < len(ca.history):
                row = "".join("█" if c else " " for c in ca.history[i])
            else:
                row = " " * width
            row_parts.append(row)
        lines.append("  ".join(row_parts))
    
    return "\n".join(lines)


def analyze_life_pattern(life: GameOfLife, max_gen: int = 500) -> Dict:
    """Analyze a Game of Life pattern."""
    initial_pop = life.population()
    initial_hash = life.get_state_hash()
    
    populations = [initial_pop]
    seen_states: Dict[str, int] = {initial_hash: 0}
    
    period = None
    stabilized_at = None
    
    for gen in range(1, max_gen + 1):
        life.step()
        pop = life.population()
        populations.append(pop)
        
        state_hash = life.get_state_hash()
        
        if state_hash in seen_states:
            period = gen - seen_states[state_hash]
            stabilized_at = seen_states[state_hash]
            break
        
        seen_states[state_hash] = gen
    
    return {
        "initial_population": initial_pop,
        "final_population": populations[-1],
        "max_population": max(populations),
        "generations_run": len(populations) - 1,
        "period": period,
        "stabilized_at": stabilized_at,
        "is_still_life": period == 1 if period else None,
        "is_oscillator": period and period > 1,
    }


# =============================================================================
# Famous Rule Presets
# =============================================================================

FAMOUS_RULES = {
    30: "Chaotic - Used by Wolfram for random numbers",
    90: "Sierpiński triangle",
    110: "TURING COMPLETE!",
    184: "Traffic flow",
    22: "Complex nested patterns",
    54: "Complex patterns",
    60: "Pascal's triangle mod 2",
    150: "XOR rule",
}


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base
    'CellularAutomaton',
    
    # Game of Life
    'GameOfLife',
    'Pattern',
    'PATTERNS',
    
    # Elementary CA
    'Elementary',
    'FAMOUS_RULES',
    
    # Langton's Ant
    'LangtonsAnt',
    'Direction',
    
    # Utilities
    'visualize_rule',
    'animate_life',
    'compare_rules',
    'analyze_life_pattern',
]
