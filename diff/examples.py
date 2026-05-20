#!/usr/bin/env python3
"""
Diff Usage Examples

The algorithm that powers git diff.
"""

from diff import (
    diff,
    diff_lines,
    edit_distance,
    similarity,
    visualize_edit_graph,
    unified_diff,
    diff_stats,
)


def example_basic():
    """
    Example 1: Basic Diff
    """
    print("=" * 60)
    print("Example 1: Basic Diff")
    print("=" * 60)
    
    print("""
Diff finds the minimal set of edits to transform old → new.
    
Edit types:
    EQUAL  (space)  : No change
    INSERT (+)      : Add from new
    DELETE (-)      : Remove from old
""")
    
    result = diff("ABCDE", "ACDF")
    
    print('diff("ABCDE", "ACDF"):')
    for edit in result.edits:
        print(f"  {edit}")
    
    print(f"\nEdit distance: {result.edit_distance}")
    print(f"Similarity: {result.similarity():.1%}")
    print()


def example_edit_graph():
    """
    Example 2: The Edit Graph
    """
    print("=" * 60)
    print("Example 2: 📊 The Edit Graph")
    print("=" * 60)
    
    print("""
Diffing is finding the shortest path through an edit graph:
    → (right)  = Insert
    ↓ (down)   = Delete
    ↘ (diag)   = Match (FREE!)
    
Goal: Maximize diagonals (matches).
""")
    
    graph = visualize_edit_graph("AB", "CAB")
    print(graph)
    print()
    print("* marks the shortest path through the graph.")
    print()


def example_line_diff():
    """
    Example 3: Line-by-Line Diff
    """
    print("=" * 60)
    print("Example 3: 📝 Line-by-Line Diff")
    print("=" * 60)
    
    old_text = """def hello():
    print("Hello")
    return True"""
    
    new_text = """def hello():
    print("Hello, World!")
    print("Goodbye")
    return True"""
    
    print("Old:")
    print(old_text)
    print("\nNew:")
    print(new_text)
    print("\nDiff:")
    print(unified_diff(old_text, new_text, "old.py", "new.py", colored=True))
    print()


def example_similarity():
    """
    Example 4: Similarity Scores
    """
    print("=" * 60)
    print("Example 4: 📏 Similarity Scores")
    print("=" * 60)
    
    pairs = [
        ("hello", "hello"),
        ("hello", "hallo"),
        ("hello", "world"),
        ("abcdef", "abcdef"),
        ("abcdef", "ghijkl"),
    ]
    
    print("Similarity is 2 × matches / (len1 + len2)\n")
    
    for old, new in pairs:
        sim = similarity(old, new)
        dist = edit_distance(old, new)
        print(f"  '{old}' vs '{new}': {sim:.1%} similar, {dist} edits")
    print()


def example_stats():
    """
    Example 5: Diff Statistics
    """
    print("=" * 60)
    print("Example 5: 📈 Diff Statistics")
    print("=" * 60)
    
    old = """Line 1
Line 2
Line 3
Line 4"""
    
    new = """Line 1
Modified Line 2
Line 3
New Line 4
Line 5"""
    
    stats = diff_stats(old, new)
    
    print("Old text: 4 lines")
    print("New text: 5 lines")
    print()
    print("Statistics:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2%}")
        else:
            print(f"  {key}: {value}")
    print()


def example_algorithm():
    """
    Example 6: Understanding the Algorithm
    """
    print("=" * 60)
    print("Example 6: 🧠 Understanding the Algorithm")
    print("=" * 60)
    
    print("""
The diff algorithm finds the Longest Common Subsequence (LCS)
and derives edits from it.

Example: "ABCDEF" → "ACDF"

LCS = "ACDF" (length 4)

Edits derived:
  - A matches
  - B deleted (not in LCS)
  - C matches
  - D matches
  - E deleted (not in LCS)
  - F matches
""")
    
    result = diff("ABCDEF", "ACDF")
    print("Actual diff:")
    for edit in result.edits:
        print(f"  {edit}")
    print()


def example_real_world():
    """
    Example 7: Real-World Code Diff
    """
    print("=" * 60)
    print("Example 7: 💻 Real-World Code Diff")  
    print("=" * 60)
    
    old_code = '''function add(a, b) {
    return a + b;
}

function multiply(a, b) {
    return a * b;
}'''
    
    new_code = '''function add(a, b) {
    // Add two numbers
    return a + b;
}

function subtract(a, b) {
    return a - b;
}

function multiply(a, b) {
    return a * b;
}'''
    
    print("Unified diff (like git diff):\n")
    print(unified_diff(old_code, new_code, "math.js", "math.js", colored=True))
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ██████╗ ██╗███████╗███████╗                                  ║
║  ██╔══██╗██║██╔════╝██╔════╝                                  ║
║  ██║  ██║██║█████╗  █████╗                                    ║
║  ██║  ██║██║██╔══╝  ██╔══╝                                    ║
║  ██████╔╝██║██║     ██║                                       ║
║  ╚═════╝ ╚═╝╚═╝     ╚═╝                                       ║
║                                                               ║
║     📊 The Algorithm That Powers Git Diff 📊                  ║
║                                                               ║
║   "An O(ND) Difference Algorithm" - Eugene Myers, 1986        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_edit_graph()
    example_line_diff()
    example_similarity()
    example_stats()
    example_algorithm()
    example_real_world()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
The Diff Algorithm:

    1. Build an edit graph where:
       → = Insert, ↓ = Delete, ↘ = Match (free)
       
    2. Find shortest path from (0,0) to (N,M)
       using Longest Common Subsequence (LCS)
       
    3. The path defines the edit script

This is the foundation of:
    - git diff
    - Code review tools
    - Merge algorithms
    - Patch generation
""")


if __name__ == "__main__":
    main()
