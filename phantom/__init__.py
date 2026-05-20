"""
Phantom: The Regex Engine You Can See

A regex engine built from scratch with visualization.
See the automaton. Watch the matching step by step.
Finally understand why your regex doesn't work.

Quick Start:
    >>> from phantom import match, search, trace
    >>> 
    >>> # Basic matching
    >>> match("hello", "hello world").matched  # True
    >>> search("world", "hello world").matched  # True
    >>> 
    >>> # See the NFA!
    >>> from phantom import visualize
    >>> print(visualize("a+b*"))
    >>> 
    >>> # Watch it think!
    >>> print(trace("a+b", "aaab"))

Supported Syntax:
    a        Literal character
    .        Any character (except newline)
    a|b      Alternation (or)
    ab       Concatenation
    a*       Zero or more
    a+       One or more
    a?       Zero or one
    a{n,m}   Bounded repetition
    [abc]    Character class
    [^abc]   Negated class
    [a-z]    Range
    \\d \\w \\s  Shortcuts
    (...)    Grouping
    ^ $      Anchors

Technical Details:
    - Thompson's NFA construction (1968)
    - ε-closure based simulation
    - O(nm) matching complexity
    - Visualization of state transitions
"""

from .phantom import (
    # Main class
    Regex,
    
    # Results
    MatchResult,
    MatchStep,
    
    # Convenience functions
    compile,
    match,
    search,
    fullmatch,
    trace,
    visualize,
    
    # AST (for advanced users)
    ASTNode,
    Parser,
    ParseError,
    Literal,
    Concat,
    Alternate,
    Star,
    Plus,
    Question,
    
    # NFA (for advanced users)
    NFA,
    NFAState,
    NFABuilder,
    NFAMatcher,
    
    # Visualization
    NFAVisualizer,
    MatchVisualizer,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Main
    'Regex',
    'MatchResult',
    'MatchStep',
    
    # Convenience
    'compile',
    'match',
    'search',
    'fullmatch',
    'trace',
    'visualize',
    
    # AST
    'ASTNode',
    'Parser',
    'ParseError',
    'Literal',
    'Concat',
    'Alternate',
    'Star',
    'Plus',
    'Question',
    
    # NFA
    'NFA',
    'NFAState',
    'NFABuilder',
    'NFAMatcher',
    
    # Visualization
    'NFAVisualizer',
    'MatchVisualizer',
]
