"""
Parsec: Parser Combinator Library

Build parsers like LEGO. Combine small parsers into complex grammars.

Quick Start:
    >>> from parsec import char, string, digit, integer
    >>> 
    >>> # Parse a character
    >>> char('a').parse("abc")  # 'a'
    >>> 
    >>> # Combine parsers
    >>> (char('a') >> char('b')).parse("abc")  # 'b'
    >>> 
    >>> # Parse numbers separated by commas
    >>> integer.sep_by(char(',')).parse("1,2,3")  # [1, 2, 3]

Combinators:
    p1 >> p2        Sequence, keep right
    p1 << p2        Sequence, keep left
    p1 | p2         Choice (try p1, then p2)
    p1 + p2         Sequence, return tuple
    p.map(f)        Transform result
    p.many()        Zero or more
    p.many1()       One or more
    p.optional()    Zero or one
    p.sep_by(s)     Separated by s

The elegance: complex parsers are built from simple ones,
and the code reads like the grammar it parses.
"""

from .parsec import (
    # Core types
    Parser,
    ParseState,
    ParseError,
    Position,
    Success,
    Failure,
    
    # Combinators
    pure,
    fail,
    lazy,
    sequence,
    choice,
    chainl,
    chainr,
    
    # Primitives
    satisfy,
    char,
    string,
    regex,
    
    # Character parsers
    any_char,
    digit,
    letter,
    alphanum,
    space,
    newline,
    tab,
    
    # Common patterns
    spaces,
    spaces1,
    digits,
    letters,
    word,
    eof,
    
    # Numbers
    integer,
    floating,
    number,
    
    # Strings
    quoted_string,
    double_quoted,
    single_quoted,
    
    # Visualization
    ParseNode,
    traced,
    visualize_parse,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core types
    'Parser', 'ParseState', 'ParseError', 'Position',
    'Success', 'Failure',
    
    # Combinators
    'pure', 'fail', 'lazy', 'sequence', 'choice',
    'chainl', 'chainr',
    
    # Primitives
    'satisfy', 'char', 'string', 'regex',
    
    # Character parsers
    'any_char', 'digit', 'letter', 'alphanum',
    'space', 'newline', 'tab',
    
    # Common patterns
    'spaces', 'spaces1', 'digits', 'letters', 'word', 'eof',
    
    # Numbers
    'integer', 'floating', 'number',
    
    # Strings
    'quoted_string', 'double_quoted', 'single_quoted',
    
    # Visualization
    'ParseNode', 'traced', 'visualize_parse',
]
