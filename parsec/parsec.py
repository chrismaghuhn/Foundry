"""
Parsec: Parser Combinator Library

Build parsers like LEGO. Combine small parsers into complex grammars.
Elegant, composable, powerful.

What is a Parser Combinator?

    A parser is a function: Input → (Result, Remaining) or Error
    
    A combinator combines parsers into new parsers:
        - sequence: parse A then B
        - choice: try A, if fails try B
        - many: parse zero or more times
        - map: transform the result

Example:
    >>> from parsec import *
    >>> 
    >>> # Parse a number
    >>> number = digit.many1().map(lambda ds: int(''.join(ds)))
    >>> 
    >>> # Parse "123 + 456"
    >>> addition = number << spaces >> string('+') << spaces >> number
    >>> 
    >>> result = addition.parse("123 + 456")
    >>> print(result)  # (123, 456)

The elegance is that complex parsers are built from simple ones,
and the code reads like the grammar it parses.

Features:
    - Core combinators: sequence, choice, many, optional
    - Operators: >> (then), | (or), << (skip right), + (concat)
    - Error handling with position tracking
    - Backtracking with try_()
    - Lazy evaluation for recursive grammars
    - Built-in parsers for common patterns
    - Parse tree visualization

Inspired by Haskell's Parsec library.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    TypeVar, Generic, Callable, List, Optional, Tuple, 
    Any, Union, Iterator, Set
)
from functools import wraps
import re
import string as string_module


# =============================================================================
# Types
# =============================================================================

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')


@dataclass
class Position:
    """Position in input for error reporting."""
    offset: int
    line: int
    column: int
    
    @classmethod
    def start(cls) -> 'Position':
        return cls(offset=0, line=1, column=1)
    
    def advance(self, char: str) -> 'Position':
        """Advance position by one character."""
        if char == '\n':
            return Position(self.offset + 1, self.line + 1, 1)
        return Position(self.offset + 1, self.line, self.column + 1)
    
    def advance_by(self, text: str) -> 'Position':
        """Advance position by a string."""
        pos = self
        for char in text:
            pos = pos.advance(char)
        return pos
    
    def __str__(self) -> str:
        return f"line {self.line}, column {self.column}"


@dataclass
class ParseState:
    """Current state of parsing."""
    input: str
    position: Position
    
    @classmethod
    def from_string(cls, s: str) -> 'ParseState':
        return cls(input=s, position=Position.start())
    
    @property
    def remaining(self) -> str:
        return self.input[self.position.offset:]
    
    @property
    def at_end(self) -> bool:
        return self.position.offset >= len(self.input)
    
    def peek(self, n: int = 1) -> str:
        """Peek at next n characters."""
        return self.remaining[:n]
    
    def advance(self, n: int) -> 'ParseState':
        """Advance by n characters."""
        consumed = self.remaining[:n]
        new_pos = self.position.advance_by(consumed)
        return ParseState(self.input, new_pos)


@dataclass
class ParseError:
    """A parsing error."""
    position: Position
    expected: Set[str]
    actual: str
    
    def __str__(self) -> str:
        expected_str = " or ".join(sorted(self.expected))
        return f"At {self.position}: expected {expected_str}, got {self.actual!r}"
    
    def merge(self, other: 'ParseError') -> 'ParseError':
        """Merge two errors (for choice combinator)."""
        if self.position.offset > other.position.offset:
            return self
        elif other.position.offset > self.position.offset:
            return other
        else:
            # Same position, merge expected
            return ParseError(
                self.position,
                self.expected | other.expected,
                self.actual
            )


@dataclass
class Success(Generic[T]):
    """Successful parse result."""
    value: T
    state: ParseState
    
    def map(self, f: Callable[[T], U]) -> 'Success[U]':
        return Success(f(self.value), self.state)


@dataclass  
class Failure:
    """Failed parse result."""
    error: ParseError
    committed: bool = False  # Has this branch consumed input?


ParseResult = Union[Success[T], Failure]


# =============================================================================
# Parser Base Class
# =============================================================================

class Parser(Generic[T]):
    """
    A parser that consumes input and produces a result.
    
    Parsers are immutable and composable. Combine them with:
        - p1 >> p2: sequence, keep right result
        - p1 << p2: sequence, keep left result
        - p1 | p2: choice (try p1, if fails try p2)
        - p1 + p2: sequence, combine results
        - p.map(f): transform result
        - p.many(): zero or more
        - p.many1(): one or more
        - p.optional(): zero or one
    """
    
    def __init__(self, parse_fn: Callable[[ParseState], ParseResult[T]]):
        self._parse_fn = parse_fn
    
    def run(self, state: ParseState) -> ParseResult[T]:
        """Run the parser on the given state."""
        return self._parse_fn(state)
    
    def parse(self, input_string: str) -> T:
        """
        Parse a string, returning the result or raising an error.
        
        This is the main entry point for using parsers.
        """
        state = ParseState.from_string(input_string)
        result = self.run(state)
        
        if isinstance(result, Failure):
            raise ValueError(str(result.error))
        
        return result.value
    
    def parse_all(self, input_string: str) -> T:
        """Parse and ensure entire input is consumed."""
        parser = self << eof
        return parser.parse(input_string)
    
    def try_parse(self, input_string: str) -> Optional[T]:
        """Parse, returning None on failure instead of raising."""
        try:
            return self.parse(input_string)
        except ValueError:
            return None
    
    # =========================================================================
    # Combinators as Methods
    # =========================================================================
    
    def map(self, f: Callable[[T], U]) -> 'Parser[U]':
        """Transform the result of this parser."""
        def parse_fn(state: ParseState) -> ParseResult[U]:
            result = self.run(state)
            if isinstance(result, Failure):
                return result
            return result.map(f)
        return Parser(parse_fn)
    
    def flatmap(self, f: Callable[[T], 'Parser[U]']) -> 'Parser[U]':
        """
        Chain parsers where the second depends on the first's result.
        
        Also known as 'bind' or '>>='.
        """
        def parse_fn(state: ParseState) -> ParseResult[U]:
            result = self.run(state)
            if isinstance(result, Failure):
                return result
            next_parser = f(result.value)
            return next_parser.run(result.state)
        return Parser(parse_fn)
    
    def then(self, other: 'Parser[U]') -> 'Parser[U]':
        """Parse self then other, keeping other's result."""
        return self.flatmap(lambda _: other)
    
    def skip(self, other: 'Parser[U]') -> 'Parser[T]':
        """Parse self then other, keeping self's result."""
        def parse_fn(state: ParseState) -> ParseResult[T]:
            result = self.run(state)
            if isinstance(result, Failure):
                return result
            
            other_result = other.run(result.state)
            if isinstance(other_result, Failure):
                return other_result
            
            return Success(result.value, other_result.state)
        return Parser(parse_fn)
    
    def or_(self, other: 'Parser[T]') -> 'Parser[T]':
        """Try self, if it fails without consuming, try other."""
        def parse_fn(state: ParseState) -> ParseResult[T]:
            result = self.run(state)
            
            if isinstance(result, Success):
                return result
            
            # Only try alternative if we didn't consume input
            if result.committed:
                return result
            
            other_result = other.run(state)
            
            if isinstance(other_result, Success):
                return other_result
            
            # Merge errors for better messages
            return Failure(result.error.merge(other_result.error))
        
        return Parser(parse_fn)
    
    def try_(self) -> 'Parser[T]':
        """
        Make this parser backtrack on failure.
        
        Normally, once a parser consumes input, alternatives aren't tried.
        try_() allows backtracking even after consuming input.
        """
        def parse_fn(state: ParseState) -> ParseResult[T]:
            result = self.run(state)
            if isinstance(result, Failure):
                return Failure(result.error, committed=False)
            return result
        return Parser(parse_fn)
    
    def many(self) -> 'Parser[List[T]]':
        """Parse zero or more times."""
        def parse_fn(state: ParseState) -> ParseResult[List[T]]:
            results: List[T] = []
            current = state
            
            while True:
                result = self.run(current)
                
                if isinstance(result, Failure):
                    if result.committed:
                        return result
                    break
                
                results.append(result.value)
                current = result.state
            
            return Success(results, current)
        
        return Parser(parse_fn)
    
    def many1(self) -> 'Parser[List[T]]':
        """Parse one or more times."""
        return self.flatmap(
            lambda first: self.many().map(lambda rest: [first] + rest)
        )
    
    def optional(self, default: T = None) -> 'Parser[Optional[T]]':
        """Parse zero or one time."""
        return self.map(lambda x: x) | pure(default)
    
    def sep_by(self, sep: 'Parser') -> 'Parser[List[T]]':
        """Parse zero or more times, separated by sep."""
        def parse_fn(state: ParseState) -> ParseResult[List[T]]:
            results: List[T] = []
            current = state
            
            # Try first element
            result = self.run(current)
            if isinstance(result, Failure):
                if result.committed:
                    return result
                return Success([], state)
            
            results.append(result.value)
            current = result.state
            
            # Try sep + element repeatedly
            while True:
                sep_result = sep.run(current)
                if isinstance(sep_result, Failure):
                    break
                
                elem_result = self.run(sep_result.state)
                if isinstance(elem_result, Failure):
                    break
                
                results.append(elem_result.value)
                current = elem_result.state
            
            return Success(results, current)
        
        return Parser(parse_fn)
    
    def sep_by1(self, sep: 'Parser') -> 'Parser[List[T]]':
        """Parse one or more times, separated by sep."""
        return self.flatmap(
            lambda first: (sep >> self).many().map(lambda rest: [first] + rest)
        )
    
    def between(self, open: 'Parser', close: 'Parser') -> 'Parser[T]':
        """Parse self between open and close."""
        return open >> self << close
    
    def label(self, name: str) -> 'Parser[T]':
        """Give this parser a name for error messages."""
        def parse_fn(state: ParseState) -> ParseResult[T]:
            result = self.run(state)
            if isinstance(result, Failure):
                return Failure(ParseError(
                    result.error.position,
                    {name},
                    result.error.actual
                ), result.committed)
            return result
        return Parser(parse_fn)
    
    def desc(self, description: str) -> 'Parser[T]':
        """Alias for label."""
        return self.label(description)
    
    # =========================================================================
    # Operators
    # =========================================================================
    
    def __rshift__(self, other: 'Parser[U]') -> 'Parser[U]':
        """p1 >> p2: parse p1 then p2, keep p2's result."""
        return self.then(other)
    
    def __lshift__(self, other: 'Parser[U]') -> 'Parser[T]':
        """p1 << p2: parse p1 then p2, keep p1's result."""
        return self.skip(other)
    
    def __or__(self, other: 'Parser[T]') -> 'Parser[T]':
        """p1 | p2: try p1, if fails try p2."""
        return self.or_(other)
    
    def __add__(self, other: 'Parser[U]') -> 'Parser[Tuple[T, U]]':
        """p1 + p2: parse both, return tuple."""
        return sequence(self, other)
    
    def __repr__(self) -> str:
        return f"Parser(...)"


# =============================================================================
# Core Combinators
# =============================================================================

def pure(value: T) -> Parser[T]:
    """Parser that succeeds without consuming input."""
    def parse_fn(state: ParseState) -> ParseResult[T]:
        return Success(value, state)
    return Parser(parse_fn)


def fail(message: str) -> Parser[Any]:
    """Parser that always fails."""
    def parse_fn(state: ParseState) -> ParseResult[Any]:
        return Failure(ParseError(
            state.position,
            {message},
            state.peek(10) or "end of input"
        ))
    return Parser(parse_fn)


def lazy(parser_fn: Callable[[], Parser[T]]) -> Parser[T]:
    """
    Delay parser construction for recursive grammars.
    
    Example:
        expr = lazy(lambda: number | (lparen >> expr << rparen))
    """
    def parse_fn(state: ParseState) -> ParseResult[T]:
        return parser_fn().run(state)
    return Parser(parse_fn)


def sequence(*parsers: Parser) -> Parser[Tuple]:
    """Parse all in sequence, return tuple of results."""
    def parse_fn(state: ParseState) -> ParseResult[Tuple]:
        results = []
        current = state
        
        for parser in parsers:
            result = parser.run(current)
            if isinstance(result, Failure):
                return result
            results.append(result.value)
            current = result.state
        
        return Success(tuple(results), current)
    
    return Parser(parse_fn)


def choice(*parsers: Parser[T]) -> Parser[T]:
    """Try parsers in order, return first success."""
    def parse_fn(state: ParseState) -> ParseResult[T]:
        error = None
        
        for parser in parsers:
            result = parser.run(state)
            if isinstance(result, Success):
                return result
            
            if result.committed:
                return result
            
            if error is None:
                error = result.error
            else:
                error = error.merge(result.error)
        
        return Failure(error or ParseError(state.position, {"something"}, "nothing"))
    
    return Parser(parse_fn)


# =============================================================================
# Primitive Parsers
# =============================================================================

def satisfy(predicate: Callable[[str], bool], expected: str = "character") -> Parser[str]:
    """Parse a character that satisfies the predicate."""
    def parse_fn(state: ParseState) -> ParseResult[str]:
        if state.at_end:
            return Failure(ParseError(
                state.position,
                {expected},
                "end of input"
            ))
        
        char = state.remaining[0]
        if predicate(char):
            return Success(char, state.advance(1))
        
        return Failure(ParseError(
            state.position,
            {expected},
            repr(char)
        ))
    
    return Parser(parse_fn)


def char(c: str) -> Parser[str]:
    """Parse a specific character."""
    return satisfy(lambda x: x == c, repr(c))


def string(s: str) -> Parser[str]:
    """Parse an exact string."""
    def parse_fn(state: ParseState) -> ParseResult[str]:
        if state.remaining.startswith(s):
            return Success(s, state.advance(len(s)))
        
        actual = state.peek(len(s)) or "end of input"
        return Failure(ParseError(
            state.position,
            {repr(s)},
            repr(actual)
        ), committed=False)
    
    return Parser(parse_fn)


def regex(pattern: str, group: int = 0) -> Parser[str]:
    """Parse using a regular expression."""
    compiled = re.compile(pattern)
    
    def parse_fn(state: ParseState) -> ParseResult[str]:
        match = compiled.match(state.remaining)
        if match:
            matched = match.group(group)
            full_match = match.group(0)
            return Success(matched, state.advance(len(full_match)))
        
        return Failure(ParseError(
            state.position,
            {f"/{pattern}/"},
            state.peek(10) or "end of input"
        ))
    
    return Parser(parse_fn)


# Built-in character parsers
any_char = satisfy(lambda _: True, "any character")
digit = satisfy(str.isdigit, "digit")
letter = satisfy(str.isalpha, "letter")
alphanum = satisfy(str.isalnum, "alphanumeric")
space = satisfy(str.isspace, "whitespace")
newline = char('\n').label("newline")
tab = char('\t').label("tab")

# Common patterns
spaces = space.many().map(lambda xs: ''.join(xs))
spaces1 = space.many1().map(lambda xs: ''.join(xs))
digits = digit.many1().map(lambda xs: ''.join(xs))
letters = letter.many1().map(lambda xs: ''.join(xs))
word = alphanum.many1().map(lambda xs: ''.join(xs))

# End of input
def _eof_parse(state: ParseState) -> ParseResult[None]:
    if state.at_end:
        return Success(None, state)
    return Failure(ParseError(
        state.position,
        {"end of input"},
        repr(state.peek(10))
    ))

eof: Parser[None] = Parser(_eof_parse)


# =============================================================================
# Numeric Parsers
# =============================================================================

integer = regex(r'-?[0-9]+').map(int).label("integer")
floating = regex(r'-?[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?').map(float).label("number")

def number() -> Parser[Union[int, float]]:
    """Parse an integer or floating point number."""
    return (
        regex(r'-?[0-9]+\.[0-9]+([eE][+-]?[0-9]+)?').map(float) |
        regex(r'-?[0-9]+').map(int)
    ).label("number")


# =============================================================================
# String Parsers
# =============================================================================

def quoted_string(quote: str = '"', escape: str = '\\') -> Parser[str]:
    """Parse a quoted string with escape sequences."""
    def parse_fn(state: ParseState) -> ParseResult[str]:
        if not state.remaining.startswith(quote):
            return Failure(ParseError(
                state.position, {f"string starting with {quote}"}, 
                state.peek(1) or "end"
            ))
        
        current = state.advance(len(quote))
        chars = []
        escaped = False
        
        while not current.at_end:
            c = current.remaining[0]
            
            if escaped:
                # Handle escape sequences
                if c == 'n':
                    chars.append('\n')
                elif c == 't':
                    chars.append('\t')
                elif c == 'r':
                    chars.append('\r')
                elif c == '\\':
                    chars.append('\\')
                elif c == quote:
                    chars.append(quote)
                else:
                    chars.append(c)
                escaped = False
            elif c == escape:
                escaped = True
            elif c == quote:
                return Success(''.join(chars), current.advance(len(quote)))
            else:
                chars.append(c)
            
            current = current.advance(1)
        
        return Failure(ParseError(
            state.position,
            {"closing quote"},
            "end of input"
        ))
    
    return Parser(parse_fn)


double_quoted = quoted_string('"')
single_quoted = quoted_string("'")


# =============================================================================
# Expression Parsing
# =============================================================================

def chainl(operand: Parser[T], operator: Parser[Callable[[T, T], T]], default: T = None) -> Parser[T]:
    """
    Parse left-associative binary expressions.
    
    Example:
        add_op = (char('+') >> pure(lambda a, b: a + b)) | (char('-') >> pure(lambda a, b: a - b))
        expr = chainl(number, add_op)
        expr.parse("1+2-3")  # ((1+2)-3) = 0
    """
    def parse_fn(state: ParseState) -> ParseResult[T]:
        # Parse first operand
        result = operand.run(state)
        if isinstance(result, Failure):
            if default is not None:
                return Success(default, state)
            return result
        
        acc = result.value
        current = result.state
        
        # Parse (op operand)* 
        while True:
            op_result = operator.run(current)
            if isinstance(op_result, Failure):
                break
            
            op_fn = op_result.value
            rhs_result = operand.run(op_result.state)
            
            if isinstance(rhs_result, Failure):
                break
            
            acc = op_fn(acc, rhs_result.value)
            current = rhs_result.state
        
        return Success(acc, current)
    
    return Parser(parse_fn)


def chainr(operand: Parser[T], operator: Parser[Callable[[T, T], T]], default: T = None) -> Parser[T]:
    """
    Parse right-associative binary expressions.
    
    Example:
        pow_op = char('^') >> pure(lambda a, b: a ** b)
        expr = chainr(number, pow_op)
        expr.parse("2^3^2")  # 2^(3^2) = 512
    """
    def parse_fn(state: ParseState) -> ParseResult[T]:
        result = operand.run(state)
        if isinstance(result, Failure):
            if default is not None:
                return Success(default, state)
            return result
        
        first = result.value
        current = result.state
        
        # Check for operator
        op_result = operator.run(current)
        if isinstance(op_result, Failure):
            return Success(first, current)
        
        # Recursively parse rest (right-associative)
        rest_result = chainr(operand, operator, default).run(op_result.state)
        if isinstance(rest_result, Failure):
            return Success(first, current)
        
        op_fn = op_result.value
        return Success(op_fn(first, rest_result.value), rest_result.state)
    
    return Parser(parse_fn)


# =============================================================================
# Visualization
# =============================================================================

@dataclass
class ParseNode:
    """A node in the parse tree for visualization."""
    name: str
    value: Any
    children: List['ParseNode']
    
    def to_string(self, indent: int = 0) -> str:
        prefix = "  " * indent
        result = f"{prefix}{self.name}"
        if self.value is not None and not self.children:
            result += f": {self.value!r}"
        result += "\n"
        for child in self.children:
            result += child.to_string(indent + 1)
        return result


def traced(name: str, parser: Parser[T]) -> Parser[Tuple[T, ParseNode]]:
    """Wrap a parser to build a parse tree."""
    def parse_fn(state: ParseState) -> ParseResult[Tuple[T, ParseNode]]:
        result = parser.run(state)
        if isinstance(result, Failure):
            return result
        
        node = ParseNode(name, result.value, [])
        return Success((result.value, node), result.state)
    
    return Parser(parse_fn)


def visualize_parse(parser: Parser[T], input_string: str) -> str:
    """Visualize a parse attempt."""
    state = ParseState.from_string(input_string)
    result = parser.run(state)
    
    lines = []
    lines.append("=" * 50)
    lines.append("PARSE RESULT")
    lines.append("=" * 50)
    lines.append(f"Input: {input_string!r}")
    lines.append("")
    
    if isinstance(result, Success):
        lines.append(f"✓ Success!")
        lines.append(f"  Value: {result.value!r}")
        lines.append(f"  Remaining: {result.state.remaining!r}")
    else:
        lines.append(f"✗ Failure")
        lines.append(f"  {result.error}")
    
    return '\n'.join(lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core types
    'Parser',
    'ParseState',
    'ParseError',
    'Position',
    'Success',
    'Failure',
    
    # Combinators
    'pure',
    'fail',
    'lazy',
    'sequence',
    'choice',
    'chainl',
    'chainr',
    
    # Primitives
    'satisfy',
    'char',
    'string',
    'regex',
    
    # Character parsers
    'any_char',
    'digit',
    'letter',
    'alphanum',
    'space',
    'newline',
    'tab',
    
    # Common patterns
    'spaces',
    'spaces1',
    'digits',
    'letters',
    'word',
    'eof',
    
    # Numbers
    'integer',
    'floating',
    'number',
    
    # Strings
    'quoted_string',
    'double_quoted',
    'single_quoted',
    
    # Visualization
    'ParseNode',
    'traced',
    'visualize_parse',
]
