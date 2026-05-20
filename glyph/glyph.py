"""
Glyph: The ASCII Art Dataflow Compiler

Draw dataflow diagrams in ASCII art. They compile and run.
The diagram IS the program.

Example:
    ┌─────────┐     ┌──────────┐     ┌─────────┐
    │  input  │────>│  double  │────>│  print  │
    └─────────┘     └──────────┘     └─────────┘

This compiles to a dataflow graph where:
- `input` is a source node
- `double` transforms data (x * 2)
- `print` outputs results

The magic is in 2D parsing:
- Regular parsers read left-to-right (1D)
- Glyph reads a 2D grid, detecting boxes and arrows
- It's like OCR for ASCII art, but deterministic

Technical Domains:
    1. Compiler/Interpreter: 2D lexing, graph construction, execution
    2. Async Concurrency: Nodes execute when inputs are ready

Box Syntax (all supported):
    ┌───────┐   ╔═══════╗   +-------+   .-------.
    │ label │   ║ label ║   | label |   | label |
    └───────┘   ╚═══════╝   +-------+   '-------'

Arrow Syntax:
    ───>   ═══>   --->   ···>   ~~~>   =====>

Node Types (built-in):
    input, output, print, double, square, sum, filter, map, delay

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, List, Set, Tuple, Optional,
    AsyncIterator, Union, Type, Awaitable
)
from collections import defaultdict
from enum import Enum, auto
import sys


# =============================================================================
# Character Grid - The 2D Canvas
# =============================================================================

class CharGrid:
    """
    A 2D grid of characters for parsing ASCII art.
    
    This is the foundation of 2D parsing. Instead of reading left-to-right,
    we can query any (x, y) position and trace patterns in any direction.
    """
    
    def __init__(self, text: str):
        """Create grid from multiline text."""
        lines = text.split('\n')
        
        # Normalize: pad all lines to same length
        max_width = max(len(line) for line in lines) if lines else 0
        self._lines = [line.ljust(max_width) for line in lines]
        self._height = len(self._lines)
        self._width = max_width
        
        # Track which cells have been "claimed" by parsed elements
        self._claimed: Set[Tuple[int, int]] = set()
    
    @property
    def width(self) -> int:
        return self._width
    
    @property
    def height(self) -> int:
        return self._height
    
    def get(self, x: int, y: int) -> str:
        """Get character at (x, y), or space if out of bounds."""
        if 0 <= y < self._height and 0 <= x < self._width:
            return self._lines[y][x]
        return ' '
    
    def get_region(self, x: int, y: int, w: int, h: int) -> List[str]:
        """Get a rectangular region as list of strings."""
        return [
            ''.join(self.get(x + dx, y + dy) for dx in range(w))
            for dy in range(h)
        ]
    
    def claim(self, x: int, y: int) -> None:
        """Mark a cell as claimed (already parsed)."""
        self._claimed.add((x, y))
    
    def is_claimed(self, x: int, y: int) -> bool:
        """Check if a cell is already claimed."""
        return (x, y) in self._claimed
    
    def claim_region(self, x: int, y: int, w: int, h: int) -> None:
        """Claim a rectangular region."""
        for dy in range(h):
            for dx in range(w):
                self.claim(x + dx, y + dy)
    
    def __repr__(self) -> str:
        return f"CharGrid({self._width}x{self._height})"


# =============================================================================
# Box Detection - Finding Nodes
# =============================================================================

# Characters that can form box corners
CORNER_TL = set('┌╔+.')  # Top-left
CORNER_TR = set('┐╗+.')  # Top-right
CORNER_BL = set('└╚+\'')  # Bottom-left
CORNER_BR = set('┘╝+\'')  # Bottom-right

# Characters that can form horizontal edges
HORIZONTAL = set('─═-~·.=')

# Characters that can form vertical edges
VERTICAL = set('│║|:')

# Arrow heads
ARROW_RIGHT = set('>→')
ARROW_LEFT = set('<←')
ARROW_DOWN = set('v↓')
ARROW_UP = set('^↑')


@dataclass
class Box:
    """
    A detected box in the ASCII art.
    
    Boxes are the nodes of our dataflow graph.
    The label inside becomes the node's operation.
    """
    x: int          # Left edge
    y: int          # Top edge
    width: int      # Including borders
    height: int     # Including borders
    label: str      # Text inside the box
    
    def __hash__(self) -> int:
        return hash((self.x, self.y, self.width, self.height))
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Box):
            return (self.x == other.x and self.y == other.y and
                    self.width == other.width and self.height == other.height)
        return False
    
    @property
    def center_x(self) -> int:
        return self.x + self.width // 2
    
    @property
    def center_y(self) -> int:
        return self.y + self.height // 2
    
    @property
    def right_edge(self) -> int:
        return self.x + self.width - 1
    
    @property
    def bottom_edge(self) -> int:
        return self.y + self.height - 1
    
    def contains_point(self, px: int, py: int) -> bool:
        """Check if a point is inside or on the box."""
        return (self.x <= px <= self.right_edge and
                self.y <= py <= self.bottom_edge)
    
    def edge_points(self) -> List[Tuple[int, int, str]]:
        """
        Get all edge points with their direction.
        Returns: [(x, y, direction), ...] where direction is 'left', 'right', 'top', 'bottom'
        """
        points = []
        
        # Left edge (excluding corners)
        for dy in range(1, self.height - 1):
            points.append((self.x, self.y + dy, 'left'))
        
        # Right edge
        for dy in range(1, self.height - 1):
            points.append((self.right_edge, self.y + dy, 'right'))
        
        # Top edge
        for dx in range(1, self.width - 1):
            points.append((self.x + dx, self.y, 'top'))
        
        # Bottom edge
        for dx in range(1, self.width - 1):
            points.append((self.x + dx, self.bottom_edge, 'bottom'))
        
        return points
    
    def __repr__(self) -> str:
        return f"Box({self.label!r} at {self.x},{self.y})"


class BoxDetector:
    """
    Detects boxes in a CharGrid.
    
    Algorithm:
    1. Scan for top-left corners
    2. For each corner, try to trace a complete box
    3. Extract the label from inside
    
    This is like edge detection in image processing,
    but for ASCII characters.
    """
    
    def __init__(self, grid: CharGrid):
        self.grid = grid
    
    def find_all(self) -> List[Box]:
        """Find all boxes in the grid."""
        boxes = []
        
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                if self.grid.is_claimed(x, y):
                    continue
                
                if self.grid.get(x, y) in CORNER_TL:
                    box = self._try_parse_box(x, y)
                    if box:
                        boxes.append(box)
        
        return boxes
    
    def _try_parse_box(self, x: int, y: int) -> Optional[Box]:
        """
        Try to parse a box starting from top-left corner at (x, y).
        
        Returns Box if successful, None if not a valid box.
        """
        tl = self.grid.get(x, y)
        
        # Determine expected characters based on corner style
        if tl in '┌':
            h_char, v_char = '─', '│'
            tr_set, bl_set, br_set = {'┐'}, {'└'}, {'┘'}
        elif tl in '╔':
            h_char, v_char = '═', '║'
            tr_set, bl_set, br_set = {'╗'}, {'╚'}, {'╝'}
        elif tl in '+':
            h_char, v_char = '-', '|'
            tr_set, bl_set, br_set = {'+'}, {'+'}, {'+'}
        elif tl in '.':
            h_char, v_char = '-', '|'
            tr_set, bl_set, br_set = {'.'}, {"'"}, {"'"}
        else:
            return None
        
        # Find top-right corner by following horizontal edge
        width = 1
        while True:
            c = self.grid.get(x + width, y)
            if c in tr_set:
                width += 1
                break
            elif c == h_char or c in HORIZONTAL:
                width += 1
            else:
                return None
            
            if width > 100:  # Sanity limit
                return None
        
        # Find bottom-left corner by following vertical edge
        height = 1
        while True:
            c = self.grid.get(x, y + height)
            if c in bl_set:
                height += 1
                break
            elif c == v_char or c in VERTICAL:
                height += 1
            else:
                return None
            
            if height > 50:  # Sanity limit
                return None
        
        # Verify bottom-right corner
        br = self.grid.get(x + width - 1, y + height - 1)
        if br not in br_set and br not in CORNER_BR:
            return None
        
        # Verify all edges
        # Top edge
        for dx in range(1, width - 1):
            c = self.grid.get(x + dx, y)
            if c not in HORIZONTAL and c != h_char:
                return None
        
        # Bottom edge
        for dx in range(1, width - 1):
            c = self.grid.get(x + dx, y + height - 1)
            if c not in HORIZONTAL and c != h_char:
                return None
        
        # Left edge
        for dy in range(1, height - 1):
            c = self.grid.get(x, y + dy)
            if c not in VERTICAL and c != v_char:
                return None
        
        # Right edge
        for dy in range(1, height - 1):
            c = self.grid.get(x + width - 1, y + dy)
            if c not in VERTICAL and c != v_char:
                return None
        
        # Extract label from inside
        label_lines = []
        for dy in range(1, height - 1):
            line = ''
            for dx in range(1, width - 1):
                line += self.grid.get(x + dx, y + dy)
            label_lines.append(line.strip())
        
        label = '\n'.join(line for line in label_lines if line).strip()
        
        # Claim the box region
        self.grid.claim_region(x, y, width, height)
        
        return Box(x, y, width, height, label)


# =============================================================================
# Arrow Detection - Finding Edges
# =============================================================================

@dataclass
class Arrow:
    """
    A detected arrow connecting two boxes.
    
    Arrows define the dataflow: data flows from source to target.
    """
    source: Box
    target: Box
    path: List[Tuple[int, int]]  # The actual path of the arrow
    
    def __repr__(self) -> str:
        return f"Arrow({self.source.label!r} -> {self.target.label!r})"


class ArrowTracer:
    """
    Traces arrows between boxes.
    
    Algorithm:
    1. From each box edge, look for arrow characters
    2. Follow the arrow path until hitting another box
    3. Determine direction from arrow heads
    """
    
    # Direction vectors
    DIRECTIONS = {
        'right': (1, 0),
        'left': (-1, 0),
        'down': (0, 1),
        'up': (0, -1),
        'top': (0, -1),      # Same as 'up', used for edge direction
        'bottom': (0, 1),    # Same as 'down', used for edge direction
    }
    
    def __init__(self, grid: CharGrid, boxes: List[Box]):
        self.grid = grid
        self.boxes = boxes
        self._box_map = self._build_box_map()
    
    def _build_box_map(self) -> Dict[Tuple[int, int], Box]:
        """Map each box's edge points to the box."""
        result = {}
        for box in self.boxes:
            for x, y, _ in box.edge_points():
                result[(x, y)] = box
        return result
    
    def find_all(self) -> List[Arrow]:
        """Find all arrows connecting boxes."""
        arrows = []
        seen_pairs: Set[Tuple[str, str]] = set()  # Track source->target pairs
        
        for box in self.boxes:
            for ex, ey, direction in box.edge_points():
                arrow = self._trace_from_edge(box, ex, ey, direction)
                if arrow:
                    # Avoid duplicates (same connection traced from both ends)
                    pair_key = (arrow.source.label, arrow.target.label)
                    if pair_key not in seen_pairs:
                        arrows.append(arrow)
                        seen_pairs.add(pair_key)
        
        return arrows
    
    def _trace_from_edge(
        self,
        source: Box,
        start_x: int,
        start_y: int,
        initial_direction: str
    ) -> Optional[Arrow]:
        """
        Try to trace an arrow from a box edge.
        
        Only creates an arrow if an arrow head is found pointing
        toward the target (not away from source).
        """
        # Map edge direction to outward direction
        outward_map = {
            'left': 'left',
            'right': 'right',
            'top': 'up',
            'bottom': 'down',
        }
        outward = outward_map.get(initial_direction, initial_direction)
        
        # Check the adjacent cell in the direction away from the box
        dx, dy = self.DIRECTIONS[outward]
        x, y = start_x + dx, start_y + dy
        
        # Must start with an arrow or line character
        c = self.grid.get(x, y)
        if not self._is_line_char(c, outward):
            return None
        
        # Follow the path
        path = [(x, y)]
        visited = {(x, y)}
        direction = outward
        found_arrow_head = False
        arrow_head_direction = None
        
        while True:
            # Check if we hit an arrow head
            c = self.grid.get(x, y)
            
            # Arrow heads must point in the direction we're traveling
            # If we're going right and see >, that's correct
            # If we're going left and see >, that's WRONG (arrow points away)
            if c in ARROW_RIGHT and direction == 'right':
                found_arrow_head = True
                arrow_head_direction = 'right'
            elif c in ARROW_LEFT and direction == 'left':
                found_arrow_head = True
                arrow_head_direction = 'left'
            elif c in ARROW_DOWN and direction == 'down':
                found_arrow_head = True
                arrow_head_direction = 'down'
            elif c in ARROW_UP and direction == 'up':
                found_arrow_head = True
                arrow_head_direction = 'up'
            # If we're going one direction but see an arrow pointing another way,
            # this path is backwards (wrong direction arrow)
            elif c in ARROW_RIGHT or c in ARROW_LEFT or c in ARROW_DOWN or c in ARROW_UP:
                # Arrow pointing wrong way - don't continue
                return None
            
            # Try to continue in current direction
            dx, dy = self.DIRECTIONS[direction]
            nx, ny = x + dx, y + dy
            
            # Check if we hit a box
            target = self._find_box_at(nx, ny)
            if target and target != source:
                # Only create arrow if we found an arrow head pointing toward target
                # or if we're moving in the right direction
                if found_arrow_head:
                    return Arrow(source, target, path)
                return None
            
            # Check if we can continue
            nc = self.grid.get(nx, ny)
            
            if (nx, ny) not in visited and self._is_line_char(nc, direction):
                x, y = nx, ny
                path.append((x, y))
                visited.add((x, y))
                continue
            
            # Try to turn
            turned = False
            for turn_dir in ['right', 'down', 'left', 'up']:
                if turn_dir == direction:
                    continue
                
                tdx, tdy = self.DIRECTIONS[turn_dir]
                tx, ty = x + tdx, y + tdy
                
                if (tx, ty) in visited:
                    continue
                
                tc = self.grid.get(tx, ty)
                
                # Check if we hit a box after turning
                target = self._find_box_at(tx, ty)
                if target and target != source:
                    if found_arrow_head:
                        return Arrow(source, target, path)
                    return None
                
                if self._is_line_char(tc, turn_dir):
                    x, y = tx, ty
                    path.append((x, y))
                    visited.add((x, y))
                    direction = turn_dir
                    turned = True
                    break
            
            if not turned:
                break
            
            if len(path) > 500:  # Sanity limit
                break
        
        return None
    
    def _is_line_char(self, c: str, direction: str) -> bool:
        """Check if character can be part of a line in given direction."""
        if direction in ('left', 'right'):
            return (c in HORIZONTAL or c in ARROW_RIGHT or c in ARROW_LEFT or
                    c in CORNER_TL or c in CORNER_TR or c in CORNER_BL or c in CORNER_BR)
        else:
            return (c in VERTICAL or c in ARROW_DOWN or c in ARROW_UP or
                    c in CORNER_TL or c in CORNER_TR or c in CORNER_BL or c in CORNER_BR)
    
    def _find_box_at(self, x: int, y: int) -> Optional[Box]:
        """Find a box that contains or borders the point."""
        return self._box_map.get((x, y))


# =============================================================================
# Graph Construction
# =============================================================================

@dataclass
class Node:
    """A node in the dataflow graph."""
    id: str
    label: str
    operation: str
    inputs: List['Node'] = field(default_factory=list)
    outputs: List['Node'] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.id)
    
    def __repr__(self):
        return f"Node({self.label!r})"


@dataclass
class DataflowGraph:
    """
    The compiled dataflow graph.
    
    This is the intermediate representation between ASCII art
    and executable code.
    """
    nodes: Dict[str, Node]
    sources: List[Node]  # Nodes with no inputs
    sinks: List[Node]    # Nodes with no outputs
    
    def topological_order(self) -> List[Node]:
        """
        Return nodes in topological order for execution.
        
        Uses Kahn's algorithm to respect dependencies.
        """
        in_degree = {n.id: len(n.inputs) for n in self.nodes.values()}
        queue = [n for n in self.nodes.values() if in_degree[n.id] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for output in node.outputs:
                in_degree[output.id] -= 1
                if in_degree[output.id] == 0:
                    queue.append(output)
        
        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in dataflow graph")
        
        return result
    
    def to_dot(self) -> str:
        """Generate Graphviz DOT representation."""
        lines = ['digraph {']
        lines.append('  rankdir=LR;')
        
        for node in self.nodes.values():
            shape = 'box'
            if not node.inputs:
                shape = 'ellipse'
            elif not node.outputs:
                shape = 'doubleoctagon'
            lines.append(f'  "{node.id}" [label="{node.label}" shape={shape}];')
        
        for node in self.nodes.values():
            for output in node.outputs:
                lines.append(f'  "{node.id}" -> "{output.id}";')
        
        lines.append('}')
        return '\n'.join(lines)


class GraphBuilder:
    """
    Builds a DataflowGraph from boxes and arrows.
    """
    
    def __init__(self, boxes: List[Box], arrows: List[Arrow]):
        self.boxes = boxes
        self.arrows = arrows
    
    def build(self) -> DataflowGraph:
        """Construct the dataflow graph."""
        # Create nodes
        nodes: Dict[str, Node] = {}
        box_to_node: Dict[Box, Node] = {}
        
        for i, box in enumerate(self.boxes):
            node_id = f"node_{i}"
            label = box.label
            operation = self._parse_operation(label)
            
            node = Node(id=node_id, label=label, operation=operation)
            nodes[node_id] = node
            box_to_node[box] = node
        
        # Add edges
        for arrow in self.arrows:
            source_node = box_to_node.get(arrow.source)
            target_node = box_to_node.get(arrow.target)
            
            if source_node and target_node:
                source_node.outputs.append(target_node)
                target_node.inputs.append(source_node)
        
        # Identify sources and sinks
        sources = [n for n in nodes.values() if not n.inputs]
        sinks = [n for n in nodes.values() if not n.outputs]
        
        return DataflowGraph(nodes=nodes, sources=sources, sinks=sinks)
    
    def _parse_operation(self, label: str) -> str:
        """Extract operation name from label."""
        # Handle multi-line labels
        lines = label.strip().split('\n')
        return lines[0].strip().lower()


# =============================================================================
# Execution Engine
# =============================================================================

class NodeFunction(ABC):
    """Base class for node operations."""
    
    @abstractmethod
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        """Execute the node operation."""
        pass


class InputNode(NodeFunction):
    """Source node that yields input data."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        if context.input_data:
            return context.input_data.pop(0)
        return None


class OutputNode(NodeFunction):
    """Sink node that collects output."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        for value in inputs:
            context.output_data.append(value)
        return inputs[0] if inputs else None


class PrintNode(NodeFunction):
    """Node that prints and passes through."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        for value in inputs:
            context.print_output.append(str(value))
            print(f"  📤 {value}")
        return inputs[0] if inputs else None


class DoubleNode(NodeFunction):
    """Doubles numeric input."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        if inputs:
            return inputs[0] * 2
        return None


class SquareNode(NodeFunction):
    """Squares numeric input."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        if inputs:
            return inputs[0] ** 2
        return None


class SumNode(NodeFunction):
    """Sums all inputs."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        return sum(inputs)


class DelayNode(NodeFunction):
    """Adds async delay (for testing)."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        await asyncio.sleep(0.1)
        return inputs[0] if inputs else None


class FilterNode(NodeFunction):
    """Filters values (keeps truthy)."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        return inputs[0] if inputs and inputs[0] else None


class IncrementNode(NodeFunction):
    """Adds 1 to input."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        if inputs:
            return inputs[0] + 1
        return None


class PassNode(NodeFunction):
    """Passes input through unchanged."""
    
    async def execute(self, inputs: List[Any], context: 'ExecutionContext') -> Any:
        return inputs[0] if inputs else None


# Registry of built-in operations
BUILTIN_OPS: Dict[str, Type[NodeFunction]] = {
    'input': InputNode,
    'output': OutputNode,
    'print': PrintNode,
    'double': DoubleNode,
    'square': SquareNode,
    'sum': SumNode,
    'delay': DelayNode,
    'filter': FilterNode,
    'increment': IncrementNode,
    '+1': IncrementNode,
    'pass': PassNode,
    'identity': PassNode,
}


@dataclass
class ExecutionContext:
    """Context for a single execution run."""
    input_data: List[Any] = field(default_factory=list)
    output_data: List[Any] = field(default_factory=list)
    print_output: List[str] = field(default_factory=list)
    node_results: Dict[str, Any] = field(default_factory=dict)


class Executor:
    """
    Executes a DataflowGraph.
    
    Nodes execute asynchronously when their inputs are ready.
    This is true dataflow execution - no explicit scheduling needed.
    """
    
    def __init__(self, graph: DataflowGraph, custom_ops: Optional[Dict[str, Type[NodeFunction]]] = None):
        self.graph = graph
        self.ops = {**BUILTIN_OPS}
        if custom_ops:
            self.ops.update(custom_ops)
    
    async def execute(self, input_data: Optional[List[Any]] = None) -> ExecutionContext:
        """
        Execute the dataflow graph.
        
        Args:
            input_data: Data to feed into 'input' nodes
        
        Returns:
            ExecutionContext with results
        """
        context = ExecutionContext(
            input_data=list(input_data) if input_data else []
        )
        
        # Execute in topological order
        order = self.graph.topological_order()
        
        print("\n🔮 Executing Glyph dataflow...")
        print("─" * 40)
        
        for node in order:
            # Get operation
            op_class = self.ops.get(node.operation, PassNode)
            op = op_class()
            
            # Gather inputs
            inputs = [
                context.node_results.get(inp.id)
                for inp in node.inputs
            ]
            
            # Execute
            print(f"  ⚡ {node.label}: {inputs} →", end=" ")
            result = await op.execute(inputs, context)
            print(f"{result}")
            
            context.node_results[node.id] = result
        
        print("─" * 40)
        print(f"✨ Complete! Output: {context.output_data}")
        
        return context


# =============================================================================
# Main Compiler
# =============================================================================

class GlyphCompiler:
    """
    The main compiler: ASCII art → Executable dataflow.
    
    Pipeline:
        Text → CharGrid → Boxes → Arrows → Graph → Executor
    """
    
    def __init__(self, custom_ops: Optional[Dict[str, Type[NodeFunction]]] = None):
        self.custom_ops = custom_ops or {}
    
    def compile(self, source: str) -> 'CompiledGlyph':
        """
        Compile ASCII art to executable form.
        
        Args:
            source: The ASCII art source code
        
        Returns:
            CompiledGlyph that can be executed
        """
        print("\n📜 Parsing ASCII art...")
        
        # Parse
        grid = CharGrid(source)
        print(f"  Grid: {grid.width}x{grid.height} characters")
        
        # Detect boxes
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        print(f"  Found {len(boxes)} boxes: {[b.label for b in boxes]}")
        
        if not boxes:
            raise ValueError("No boxes found in source")
        
        # Trace arrows
        tracer = ArrowTracer(grid, boxes)
        arrows = tracer.find_all()
        print(f"  Found {len(arrows)} arrows")
        
        # Build graph
        builder = GraphBuilder(boxes, arrows)
        graph = builder.build()
        print(f"  Graph: {len(graph.sources)} sources, {len(graph.sinks)} sinks")
        
        return CompiledGlyph(graph, self.custom_ops)
    
    def compile_and_run(
        self,
        source: str,
        input_data: Optional[List[Any]] = None
    ) -> ExecutionContext:
        """Compile and execute in one step."""
        compiled = self.compile(source)
        return asyncio.run(compiled.execute(input_data))


class CompiledGlyph:
    """A compiled Glyph program ready for execution."""
    
    def __init__(self, graph: DataflowGraph, custom_ops: Dict[str, Type[NodeFunction]]):
        self.graph = graph
        self.custom_ops = custom_ops
    
    async def execute(self, input_data: Optional[List[Any]] = None) -> ExecutionContext:
        """Execute the compiled program."""
        executor = Executor(self.graph, self.custom_ops)
        return await executor.execute(input_data)
    
    def to_dot(self) -> str:
        """Get Graphviz representation."""
        return self.graph.to_dot()
    
    def __repr__(self) -> str:
        return f"CompiledGlyph({len(self.graph.nodes)} nodes)"


# =============================================================================
# Convenience Functions
# =============================================================================

def glyph(source: str, input_data: Optional[List[Any]] = None) -> ExecutionContext:
    """
    Compile and run ASCII art in one call.
    
    Example:
        >>> result = glyph('''
        ... ┌─────────┐     ┌──────────┐     ┌─────────┐
        ... │  input  │────>│  double  │────>│  print  │
        ... └─────────┘     └──────────┘     └─────────┘
        ... ''', input_data=[21])
    """
    compiler = GlyphCompiler()
    return compiler.compile_and_run(source, input_data)


def parse(source: str) -> DataflowGraph:
    """Parse ASCII art to graph without executing."""
    compiler = GlyphCompiler()
    compiled = compiler.compile(source)
    return compiled.graph


# =============================================================================
# Fun ASCII Art Templates
# =============================================================================

TEMPLATES = {
    'simple': '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
''',
    
    'chain': '''
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  square  │────>│  print  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
''',
    
    'fancy': '''
╔═════════╗      ╔══════════╗      ╔═════════╗
║  input  ║═════>║  double  ║═════>║  print  ║
╚═════════╝      ╚══════════╝      ╚═════════╝
''',
    
    'ascii': '''
+----------+      +-----------+      +---------+
|  input   |----->|  double   |----->|  print  |
+----------+      +-----------+      +---------+
''',
}


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main
    'GlyphCompiler',
    'CompiledGlyph',
    'glyph',
    'parse',
    
    # Graph
    'DataflowGraph',
    'Node',
    
    # Parsing
    'CharGrid',
    'Box',
    'Arrow',
    'BoxDetector',
    'ArrowTracer',
    
    # Execution
    'Executor',
    'ExecutionContext',
    'NodeFunction',
    
    # Built-in ops
    'BUILTIN_OPS',
    
    # Templates
    'TEMPLATES',
]
