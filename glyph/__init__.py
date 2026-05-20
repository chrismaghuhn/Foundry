"""
Glyph: The ASCII Art Dataflow Compiler

Draw dataflow diagrams in ASCII art. They compile and run.
The diagram IS the program.

Quick Start:
    >>> from glyph import glyph
    >>> 
    >>> # Draw your program!
    >>> source = '''
    ... ┌─────────┐     ┌──────────┐     ┌─────────┐
    ... │  input  │────>│  double  │────>│  print  │
    ... └─────────┘     └──────────┘     └─────────┘
    ... '''
    >>> 
    >>> glyph(source, input_data=[21])
    # Prints: 42

Box Styles Supported:
    ┌───────┐   Unicode single-line
    │ label │
    └───────┘
    
    ╔═══════╗   Unicode double-line
    ║ label ║
    ╚═══════╝
    
    +-------+   ASCII (portable)
    | label |
    +-------+

Built-in Operations:
    input    - Source node (feeds input_data)
    output   - Sink node (collects results)
    print    - Prints and passes through
    double   - Multiplies by 2
    square   - Squares the input
    +1       - Adds 1
    sum      - Sums all inputs
    filter   - Filters falsy values
    delay    - Adds async delay
"""

from .glyph import (
    # Main API
    GlyphCompiler,
    CompiledGlyph,
    glyph,
    parse,
    
    # Graph
    DataflowGraph,
    Node,
    
    # Parsing
    CharGrid,
    Box,
    Arrow,
    BoxDetector,
    ArrowTracer,
    
    # Execution
    Executor,
    ExecutionContext,
    NodeFunction,
    
    # Built-in ops
    BUILTIN_OPS,
    
    # Templates
    TEMPLATES,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Main API
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
