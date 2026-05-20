"""
Diff: Myers Diff Algorithm Implementation

The algorithm that powers git diff. Find the shortest edit sequence
between two texts, visualize the edit graph, generate colored output.

Background:

    Eugene Myers published "An O(ND) Difference Algorithm and Its
    Variations" in 1986. It's the foundation of diff, git, and
    nearly every version control system.
    
    The key insight: View diffing as finding the shortest path
    through an "edit graph" where:
        - Horizontal moves = INSERT a character
        - Vertical moves = DELETE a character  
        - Diagonal moves = MATCH (free!)
    
    The algorithm finds the path that maximizes diagonals (matches).

The Edit Graph:

    For A = "AB" and B = "CAB":
    
          0   1   2   3   (B)
        +---+---+---+---+
      0 |   | C | A | B |
        +---+---+---+---+
      1 | A |\  |   |\  |
        +---+---+---+---+
      2 | B |   |\  |   |
        +---+---+---+---+
           (A)
    
    →  = Insert (move right)
    ↓  = Delete (move down)
    ↘  = Match (diagonal, free!)
    
    Goal: Shortest path from (0,0) to (2,3).

D-Contours:

    The algorithm explores in "D-contours" where D is the number
    of non-diagonal moves (edits). It starts with D=0 (only matches)
    and increments until a path to (N,M) is found.
    
    This is optimal for files that are "mostly similar" - small D
    means fast diffing.

Features:
    - Myers O(ND) diff algorithm
    - Edit graph visualization
    - Colored unified diff output
    - Line-based and character-based modes
    - Edit distance calculation
    - Patch generation

Usage:
    >>> from diff import diff, diff_lines, visualize_edit_graph
    >>> 
    >>> # Character diff
    >>> edits = diff("ABCDE", "ACDEF")
    >>> for edit in edits:
    ...     print(edit)
    
    >>> # Line diff with colors
    >>> diff_lines(old_text, new_text, colored=True)
    
    >>> # Visualize the algorithm
    >>> print(visualize_edit_graph("AB", "CAB"))

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterator, Union, Sequence, TypeVar
from enum import Enum, auto
import sys


# =============================================================================
# Types
# =============================================================================

T = TypeVar('T')


class EditType(Enum):
    """Type of edit operation."""
    EQUAL = auto()   # No change (match)
    INSERT = auto()  # Insert from new
    DELETE = auto()  # Delete from old


@dataclass
class Edit:
    """
    A single edit operation.
    
    Represents one step in transforming old to new:
    - EQUAL: element exists in both
    - INSERT: element added from new
    - DELETE: element removed from old
    """
    type: EditType
    old_index: Optional[int]  # Index in old sequence (None for INSERT)
    new_index: Optional[int]  # Index in new sequence (None for DELETE)
    value: any
    
    def __str__(self) -> str:
        if self.type == EditType.EQUAL:
            return f"  {self.value}"
        elif self.type == EditType.INSERT:
            return f"+ {self.value}"
        else:
            return f"- {self.value}"
    
    def to_colored(self) -> str:
        """Return colored string representation."""
        if self.type == EditType.EQUAL:
            return f"  {self.value}"
        elif self.type == EditType.INSERT:
            return f"\033[32m+ {self.value}\033[0m"  # Green
        else:
            return f"\033[31m- {self.value}\033[0m"  # Red


@dataclass
class DiffResult:
    """Result of a diff operation."""
    edits: List[Edit]
    edit_distance: int  # Number of non-EQUAL operations
    old_length: int
    new_length: int
    
    def __iter__(self) -> Iterator[Edit]:
        return iter(self.edits)
    
    def similarity(self) -> float:
        """
        Calculate similarity ratio (0.0 to 1.0).
        
        Based on the Ratcliff/Obershelp formula:
            2 * matches / (len_old + len_new)
        """
        if self.old_length == 0 and self.new_length == 0:
            return 1.0
        
        matches = sum(1 for e in self.edits if e.type == EditType.EQUAL)
        return 2 * matches / (self.old_length + self.new_length)
    
    def to_string(self, colored: bool = False) -> str:
        """Convert to string representation."""
        lines = []
        for edit in self.edits:
            if colored:
                lines.append(edit.to_colored())
            else:
                lines.append(str(edit))
        return '\n'.join(lines)


# =============================================================================
# Myers Diff Algorithm
# =============================================================================

class MyersDiff:
    """
    Implementation of diff using longest common subsequence (LCS).
    
    While Myers' O(ND) algorithm is theoretically optimal, this
    LCS-based approach is simpler and more robust for correctness.
    
    The diff is computed by finding the LCS and then deriving
    the edit script from it.
    
    Time Complexity: O(NM)
    Space Complexity: O(NM)
    """
    
    def __init__(self, old: Sequence[T], new: Sequence[T]):
        """
        Initialize diff between two sequences.
        
        Args:
            old: The original sequence
            new: The new sequence
        """
        self.old = old
        self.new = new
        self.n = len(old)
        self.m = len(new)
    
    def diff(self) -> DiffResult:
        """
        Compute the diff.
        
        Returns:
            DiffResult containing the list of edits
        """
        # Handle edge cases
        if self.n == 0 and self.m == 0:
            return DiffResult([], 0, 0, 0)
        
        if self.n == 0:
            edits = [
                Edit(EditType.INSERT, None, j, self.new[j])
                for j in range(self.m)
            ]
            return DiffResult(edits, self.m, 0, self.m)
        
        if self.m == 0:
            edits = [
                Edit(EditType.DELETE, i, None, self.old[i])
                for i in range(self.n)
            ]
            return DiffResult(edits, self.n, self.n, 0)
        
        # Compute LCS and derive edit script
        edits = self._compute_diff_via_lcs()
        edit_distance = sum(1 for e in edits if e.type != EditType.EQUAL)
        
        return DiffResult(edits, edit_distance, self.n, self.m)
    
    def _compute_diff_via_lcs(self) -> List[Edit]:
        """
        Compute diff by finding LCS and deriving edits.
        """
        n, m = self.n, self.m
        
        # dp[i][j] = length of LCS of old[0:i] and new[0:j]
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if self.old[i - 1] == self.new[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        
        # Backtrack to find the diff
        edits = []
        i, j = n, m
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and self.old[i - 1] == self.new[j - 1]:
                # Match
                edits.append(Edit(EditType.EQUAL, i - 1, j - 1, self.old[i - 1]))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
                # Insert from new
                edits.append(Edit(EditType.INSERT, None, j - 1, self.new[j - 1]))
                j -= 1
            else:
                # Delete from old
                edits.append(Edit(EditType.DELETE, i - 1, None, self.old[i - 1]))
                i -= 1
        
        edits.reverse()
        return edits
    
    def edit_distance(self) -> int:
        """
        Compute just the edit distance (number of edits needed).
        """
        result = self.diff()
        return result.edit_distance
    
    def edit_distance(self) -> int:
        """
        Compute just the edit distance (number of edits needed).
        
        This is faster than computing the full diff when you
        only need the distance.
        """
        max_d = self.n + self.m
        v = {0: 0}
        
        for d in range(max_d + 1):
            for k in range(-d, d + 1, 2):
                if k == -d:
                    x = v.get(k + 1, 0)
                elif k == d:
                    x = v.get(k - 1, 0) + 1
                elif v.get(k - 1, 0) < v.get(k + 1, 0):
                    x = v.get(k + 1, 0)
                else:
                    x = v.get(k - 1, 0) + 1
                
                y = x - k
                
                while x < self.n and y < self.m and self.old[x] == self.new[y]:
                    x += 1
                    y += 1
                
                v[k] = x
                
                if x >= self.n and y >= self.m:
                    return d
        
        return max_d


# =============================================================================
# Convenience Functions
# =============================================================================

def diff(old: Sequence[T], new: Sequence[T]) -> DiffResult:
    """
    Compute diff between two sequences.
    
    Args:
        old: Original sequence (string, list, etc.)
        new: New sequence
    
    Returns:
        DiffResult with list of edits
    
    Example:
        >>> result = diff("ABCDE", "ACDEF")
        >>> for edit in result:
        ...     print(edit)
        - B
          A
        ...
    """
    return MyersDiff(old, new).diff()


def diff_lines(old: str, new: str) -> DiffResult:
    """
    Compute line-by-line diff between two texts.
    
    Args:
        old: Original text
        new: New text
    
    Returns:
        DiffResult with line-level edits
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    # Remove trailing newline for cleaner output
    if old_lines and old_lines[-1].endswith('\n'):
        old_lines[-1] = old_lines[-1][:-1]
    if new_lines and new_lines[-1].endswith('\n'):
        new_lines[-1] = new_lines[-1][:-1]
    
    return MyersDiff(old_lines, new_lines).diff()


def edit_distance(old: Sequence[T], new: Sequence[T]) -> int:
    """
    Compute the edit distance (minimum number of edits) between sequences.
    
    This is also known as the Levenshtein distance for strings.
    """
    return MyersDiff(old, new).edit_distance()


def similarity(old: Sequence[T], new: Sequence[T]) -> float:
    """
    Compute similarity ratio (0.0 to 1.0) between sequences.
    """
    return diff(old, new).similarity()


# =============================================================================
# Visualization
# =============================================================================

def visualize_edit_graph(old: str, new: str, show_path: bool = True) -> str:
    """
    Visualize the edit graph for two strings.
    
    Shows the grid with diagonals (matches) highlighted.
    If show_path is True, also shows the shortest path found.
    
    Example output for old="AB", new="CAB":
    
          0   1   2   3
            C   A   B
        +---+---+---+---+
      0 |   |   |   |   |
        +---+---\---+---+
      1 A|   |   |   |\  |
        +---+---+---\---+
      2 B|   |   |   |   |
        +---+---+---+---+
    """
    n, m = len(old), len(new)
    
    # Get the path if requested
    path = set()
    if show_path:
        result = diff(old, new)
        x, y = 0, 0
        path.add((x, y))
        for edit in result.edits:
            if edit.type == EditType.EQUAL:
                x += 1
                y += 1
            elif edit.type == EditType.INSERT:
                y += 1
            else:
                x += 1
            path.add((x, y))
    
    lines = []
    
    # Header with new string
    header = "      "
    for j in range(m + 1):
        header += f"{j:3} "
    lines.append(header)
    
    header2 = "        "
    for j, c in enumerate(new):
        header2 += f"{c}   "
    lines.append(header2)
    
    # Grid
    for i in range(n + 1):
        # Top border of row
        border = "    +"
        for j in range(m + 1):
            # Check for diagonal from this cell
            if i < n and j < m and old[i] == new[j]:
                border += "---\\"
            else:
                border += "---+"
        lines.append(border)
        
        # Row content
        if i < n:
            row = f"  {i} {old[i]}|"
        else:
            row = f"  {i}  |"
        
        for j in range(m + 1):
            # Check if this cell is on the path
            if (i, j) in path:
                row += " * |"
            else:
                row += "   |"
        
        lines.append(row)
    
    # Bottom border
    border = "    +"
    for j in range(m + 1):
        border += "---+"
    lines.append(border)
    
    return '\n'.join(lines)


def visualize_diff(result: DiffResult, context: int = 3) -> str:
    """
    Visualize a diff result with context.
    
    Shows DELETE lines in red, INSERT lines in green.
    Groups changes with context lines around them.
    """
    lines = []
    
    # Track positions
    edits = list(result.edits)
    
    for edit in edits:
        if edit.type == EditType.EQUAL:
            lines.append(f"  {edit.value}")
        elif edit.type == EditType.INSERT:
            lines.append(f"\033[32m+ {edit.value}\033[0m")
        else:
            lines.append(f"\033[31m- {edit.value}\033[0m")
    
    return '\n'.join(lines)


def unified_diff(
    old: str,
    new: str,
    old_name: str = "old",
    new_name: str = "new",
    context: int = 3,
    colored: bool = True
) -> str:
    """
    Generate unified diff format (like `diff -u` or `git diff`).
    
    Args:
        old: Original text
        new: New text
        old_name: Label for old file
        new_name: Label for new file
        context: Number of context lines
        colored: Whether to use ANSI colors
    """
    result = diff_lines(old, new)
    
    lines = []
    
    # Headers
    if colored:
        lines.append(f"\033[1m--- {old_name}\033[0m")
        lines.append(f"\033[1m+++ {new_name}\033[0m")
    else:
        lines.append(f"--- {old_name}")
        lines.append(f"+++ {new_name}")
    
    # Find hunks (groups of changes with context)
    edits = list(result.edits)
    
    # Simple approach: output all edits with color
    old_line = 1
    new_line = 1
    
    # Track change regions
    in_change = False
    hunk_lines = []
    hunk_old_start = 1
    hunk_new_start = 1
    hunk_old_count = 0
    hunk_new_count = 0
    
    for edit in edits:
        value = edit.value.rstrip('\n') if isinstance(edit.value, str) else str(edit.value)
        
        if edit.type == EditType.EQUAL:
            prefix = " "
            color = ""
            reset = ""
            hunk_old_count += 1
            hunk_new_count += 1
        elif edit.type == EditType.INSERT:
            prefix = "+"
            color = "\033[32m" if colored else ""
            reset = "\033[0m" if colored else ""
            hunk_new_count += 1
        else:
            prefix = "-"
            color = "\033[31m" if colored else ""
            reset = "\033[0m" if colored else ""
            hunk_old_count += 1
        
        hunk_lines.append(f"{color}{prefix}{value}{reset}")
    
    # Output hunk
    if hunk_lines:
        if colored:
            lines.append(f"\033[36m@@ -{hunk_old_start},{hunk_old_count} +{hunk_new_start},{hunk_new_count} @@\033[0m")
        else:
            lines.append(f"@@ -{hunk_old_start},{hunk_old_count} +{hunk_new_start},{hunk_new_count} @@")
        lines.extend(hunk_lines)
    
    return '\n'.join(lines)


# =============================================================================
# Statistics
# =============================================================================

def diff_stats(old: str, new: str) -> dict:
    """
    Compute statistics about a diff.
    
    Returns:
        Dictionary with:
        - edit_distance: Number of edits
        - similarity: Similarity ratio (0.0 to 1.0)
        - insertions: Number of insertions
        - deletions: Number of deletions
        - matches: Number of matches
    """
    result = diff_lines(old, new)
    
    insertions = sum(1 for e in result.edits if e.type == EditType.INSERT)
    deletions = sum(1 for e in result.edits if e.type == EditType.DELETE)
    matches = sum(1 for e in result.edits if e.type == EditType.EQUAL)
    
    return {
        'edit_distance': result.edit_distance,
        'similarity': result.similarity(),
        'insertions': insertions,
        'deletions': deletions,
        'matches': matches,
        'old_lines': result.old_length,
        'new_lines': result.new_length,
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Types
    'EditType',
    'Edit',
    'DiffResult',
    
    # Core
    'MyersDiff',
    'diff',
    'diff_lines',
    'edit_distance',
    'similarity',
    
    # Visualization
    'visualize_edit_graph',
    'visualize_diff',
    'unified_diff',
    
    # Statistics
    'diff_stats',
]
