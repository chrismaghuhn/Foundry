"""
Diff: The Algorithm That Powers Git Diff

Find the minimal set of edits to transform one sequence into another.
Visualize the edit graph, generate colored diff output.

Quick Start:
    >>> from diff import diff, unified_diff
    >>> 
    >>> # Character diff
    >>> result = diff("ABCDE", "ACDF")
    >>> for edit in result:
    ...     print(edit)
    
    >>> # Line diff with colors
    >>> print(unified_diff(old_text, new_text))

The Algorithm:
    Diffing is finding the shortest path through an edit graph:
        → (right)  = Insert
        ↓ (down)   = Delete  
        ↘ (diag)   = Match (free!)
    
    Goal: Maximize diagonals (matches) = minimal edits.

Based on Eugene Myers' 1986 paper:
"An O(ND) Difference Algorithm and Its Variations"
"""

from .diff import (
    # Types
    EditType,
    Edit,
    DiffResult,
    
    # Core
    MyersDiff,
    diff,
    diff_lines,
    edit_distance,
    similarity,
    
    # Visualization
    visualize_edit_graph,
    visualize_diff,
    unified_diff,
    
    # Statistics
    diff_stats,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Types
    'EditType', 'Edit', 'DiffResult',
    
    # Core
    'MyersDiff', 'diff', 'diff_lines',
    'edit_distance', 'similarity',
    
    # Visualization
    'visualize_edit_graph', 'visualize_diff', 'unified_diff',
    
    # Statistics
    'diff_stats',
]
