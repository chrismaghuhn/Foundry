"""
Phantom: The Regex Engine You Can See

A regex engine built from scratch with visualization.
See the automaton. Watch the matching step by step.
Finally understand why your regex doesn't work.

This implements:
    1. A recursive descent parser for regex syntax
    2. Thompson's NFA construction algorithm
    3. NFA simulation with ε-closure
    4. Step-by-step matching visualization

Supported Syntax:
    a        Literal character
    .        Any character (except newline)
    a|b      Alternation (or)
    ab       Concatenation (sequence)
    a*       Zero or more (Kleene star)
    a+       One or more
    a?       Zero or one (optional)
    a{n}     Exactly n repetitions
    a{n,}    At least n repetitions
    a{n,m}   Between n and m repetitions
    [abc]    Character class
    [^abc]   Negated character class
    [a-z]    Character range
    (...)    Grouping
    ^        Start anchor
    $        End anchor
    \\d      Digit [0-9]
    \\w      Word char [a-zA-Z0-9_]
    \\s      Whitespace
    \\.      Escaped special char

Technical Background:

    Thompson's Construction (1968) builds an NFA where:
    - Each regex operation creates a small NFA fragment
    - Fragments are composed with ε-transitions
    - The resulting NFA has at most 2n states for regex of length n
    
    NFA Simulation:
    - Track all currently active states as a set
    - On each input character, compute next state set
    - Use ε-closure to handle ε-transitions
    - Accept if any active state is an accept state

Why NFA over DFA?
    - NFA construction is O(n), DFA can be O(2^n)
    - NFA shows "parallel universes" - all paths being explored
    - More educational - you see the non-determinism
    - DFA would hide the branching structure

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    List, Set, Dict, Optional, Tuple, FrozenSet,
    Iterator, Callable, Any, Union
)
from enum import Enum, auto
import string


# =============================================================================
# Abstract Syntax Tree (AST)
# =============================================================================

class ASTNode(ABC):
    """Base class for regex AST nodes."""
    
    @abstractmethod
    def accept(self, visitor: 'ASTVisitor') -> Any:
        """Visitor pattern for tree traversal."""
        pass


@dataclass
class Literal(ASTNode):
    """Matches a single literal character."""
    char: str
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_literal(self)
    
    def __repr__(self) -> str:
        return f"Lit({self.char!r})"


@dataclass
class Dot(ASTNode):
    """Matches any character (except newline)."""
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_dot(self)
    
    def __repr__(self) -> str:
        return "Dot()"


@dataclass
class CharClass(ASTNode):
    """Matches any character in a set."""
    chars: FrozenSet[str]
    negated: bool = False
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_char_class(self)
    
    def __repr__(self) -> str:
        neg = "^" if self.negated else ""
        chars = "".join(sorted(self.chars)[:10])
        if len(self.chars) > 10:
            chars += "..."
        return f"Class([{neg}{chars}])"


@dataclass
class Concat(ASTNode):
    """Concatenation of two expressions."""
    left: ASTNode
    right: ASTNode
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_concat(self)
    
    def __repr__(self) -> str:
        return f"Concat({self.left}, {self.right})"


@dataclass
class Alternate(ASTNode):
    """Alternation (or) of two expressions."""
    left: ASTNode
    right: ASTNode
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_alternate(self)
    
    def __repr__(self) -> str:
        return f"Alt({self.left}, {self.right})"


@dataclass
class Star(ASTNode):
    """Zero or more repetitions (Kleene star)."""
    child: ASTNode
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_star(self)
    
    def __repr__(self) -> str:
        return f"Star({self.child})"


@dataclass
class Plus(ASTNode):
    """One or more repetitions."""
    child: ASTNode
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_plus(self)
    
    def __repr__(self) -> str:
        return f"Plus({self.child})"


@dataclass
class Question(ASTNode):
    """Zero or one (optional)."""
    child: ASTNode
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_question(self)
    
    def __repr__(self) -> str:
        return f"Opt({self.child})"


@dataclass
class Repeat(ASTNode):
    """Bounded repetition {n,m}."""
    child: ASTNode
    min_count: int
    max_count: Optional[int]  # None means unlimited
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_repeat(self)
    
    def __repr__(self) -> str:
        if self.max_count is None:
            return f"Repeat({self.child}, {self.min_count},∞)"
        return f"Repeat({self.child}, {self.min_count},{self.max_count})"


@dataclass
class Anchor(ASTNode):
    """Start (^) or end ($) anchor."""
    is_start: bool  # True for ^, False for $
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_anchor(self)
    
    def __repr__(self) -> str:
        return "Anchor(^)" if self.is_start else "Anchor($)"


@dataclass
class Empty(ASTNode):
    """Empty expression (matches empty string)."""
    
    def accept(self, visitor: 'ASTVisitor') -> Any:
        return visitor.visit_empty(self)
    
    def __repr__(self) -> str:
        return "Empty()"


class ASTVisitor(ABC):
    """Visitor interface for AST traversal."""
    
    @abstractmethod
    def visit_literal(self, node: Literal) -> Any: pass
    
    @abstractmethod
    def visit_dot(self, node: Dot) -> Any: pass
    
    @abstractmethod
    def visit_char_class(self, node: CharClass) -> Any: pass
    
    @abstractmethod
    def visit_concat(self, node: Concat) -> Any: pass
    
    @abstractmethod
    def visit_alternate(self, node: Alternate) -> Any: pass
    
    @abstractmethod
    def visit_star(self, node: Star) -> Any: pass
    
    @abstractmethod
    def visit_plus(self, node: Plus) -> Any: pass
    
    @abstractmethod
    def visit_question(self, node: Question) -> Any: pass
    
    @abstractmethod
    def visit_repeat(self, node: Repeat) -> Any: pass
    
    @abstractmethod
    def visit_anchor(self, node: Anchor) -> Any: pass
    
    @abstractmethod
    def visit_empty(self, node: Empty) -> Any: pass


# =============================================================================
# Parser - Converts regex string to AST
# =============================================================================

class ParseError(Exception):
    """Error during regex parsing."""
    def __init__(self, message: str, position: int):
        super().__init__(f"{message} at position {position}")
        self.position = position


class Parser:
    """
    Recursive descent parser for regular expressions.
    
    Grammar (informal):
        regex    → alternate
        alternate → concat ('|' concat)*
        concat   → repeat+
        repeat   → atom ('*' | '+' | '?' | '{n,m}')?
        atom     → literal | '.' | class | '(' regex ')' | anchor
        class    → '[' '^'? (char | range)+ ']'
    """
    
    # Special characters that need escaping
    SPECIAL = set('\\^$.|?*+()[]{}')
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0
        self.length = len(pattern)
    
    def parse(self) -> ASTNode:
        """Parse the entire pattern."""
        if self.length == 0:
            return Empty()
        
        ast = self._parse_alternate()
        
        if self.pos < self.length:
            raise ParseError(f"Unexpected character '{self.pattern[self.pos]}'", self.pos)
        
        return ast
    
    def _peek(self) -> Optional[str]:
        """Look at current character without consuming."""
        if self.pos < self.length:
            return self.pattern[self.pos]
        return None
    
    def _advance(self) -> Optional[str]:
        """Consume and return current character."""
        if self.pos < self.length:
            c = self.pattern[self.pos]
            self.pos += 1
            return c
        return None
    
    def _expect(self, char: str) -> None:
        """Consume expected character or raise error."""
        if self._peek() != char:
            raise ParseError(f"Expected '{char}'", self.pos)
        self._advance()
    
    def _parse_alternate(self) -> ASTNode:
        """Parse alternation: a|b|c"""
        left = self._parse_concat()
        
        while self._peek() == '|':
            self._advance()
            right = self._parse_concat()
            left = Alternate(left, right)
        
        return left
    
    def _parse_concat(self) -> ASTNode:
        """Parse concatenation: abc"""
        nodes: List[ASTNode] = []
        
        while self._peek() is not None and self._peek() not in '|)':
            nodes.append(self._parse_repeat())
        
        if not nodes:
            return Empty()
        
        # Build left-associative tree
        result = nodes[0]
        for node in nodes[1:]:
            result = Concat(result, node)
        
        return result
    
    def _parse_repeat(self) -> ASTNode:
        """Parse repetition operators: *, +, ?, {n,m}"""
        atom = self._parse_atom()
        
        if self._peek() == '*':
            self._advance()
            return Star(atom)
        
        if self._peek() == '+':
            self._advance()
            return Plus(atom)
        
        if self._peek() == '?':
            self._advance()
            return Question(atom)
        
        if self._peek() == '{':
            return self._parse_bounded_repeat(atom)
        
        return atom
    
    def _parse_bounded_repeat(self, atom: ASTNode) -> ASTNode:
        """Parse {n}, {n,}, {n,m}"""
        self._expect('{')
        
        # Parse minimum
        min_str = ''
        while self._peek() and self._peek().isdigit():
            min_str += self._advance()
        
        if not min_str:
            raise ParseError("Expected number in repetition", self.pos)
        
        min_count = int(min_str)
        max_count: Optional[int] = min_count
        
        if self._peek() == ',':
            self._advance()
            
            # Parse maximum (optional)
            max_str = ''
            while self._peek() and self._peek().isdigit():
                max_str += self._advance()
            
            if max_str:
                max_count = int(max_str)
            else:
                max_count = None  # Unlimited
        
        self._expect('}')
        
        return Repeat(atom, min_count, max_count)
    
    def _parse_atom(self) -> ASTNode:
        """Parse atomic expressions."""
        c = self._peek()
        
        if c is None:
            raise ParseError("Unexpected end of pattern", self.pos)
        
        # Grouping
        if c == '(':
            self._advance()
            inner = self._parse_alternate()
            self._expect(')')
            return inner
        
        # Character class
        if c == '[':
            return self._parse_char_class()
        
        # Any character
        if c == '.':
            self._advance()
            return Dot()
        
        # Anchors
        if c == '^':
            self._advance()
            return Anchor(is_start=True)
        
        if c == '$':
            self._advance()
            return Anchor(is_start=False)
        
        # Escape sequences
        if c == '\\':
            return self._parse_escape()
        
        # Special characters that shouldn't appear here
        if c in '*+?|){}':
            raise ParseError(f"Unexpected '{c}'", self.pos)
        
        # Literal character
        self._advance()
        return Literal(c)
    
    def _parse_escape(self) -> ASTNode:
        """Parse escape sequences: \\d, \\w, \\s, \\., etc."""
        self._expect('\\')
        
        c = self._advance()
        if c is None:
            raise ParseError("Unexpected end after backslash", self.pos)
        
        # Character class shortcuts
        if c == 'd':
            return CharClass(frozenset(string.digits))
        if c == 'D':
            return CharClass(frozenset(string.digits), negated=True)
        if c == 'w':
            return CharClass(frozenset(string.ascii_letters + string.digits + '_'))
        if c == 'W':
            return CharClass(frozenset(string.ascii_letters + string.digits + '_'), negated=True)
        if c == 's':
            return CharClass(frozenset(' \t\n\r\f\v'))
        if c == 'S':
            return CharClass(frozenset(' \t\n\r\f\v'), negated=True)
        
        # Special escapes
        if c == 'n':
            return Literal('\n')
        if c == 't':
            return Literal('\t')
        if c == 'r':
            return Literal('\r')
        
        # Escaped special character
        return Literal(c)
    
    def _parse_char_class(self) -> CharClass:
        """Parse character class: [abc], [^abc], [a-z]"""
        self._expect('[')
        
        negated = False
        if self._peek() == '^':
            self._advance()
            negated = True
        
        chars: Set[str] = set()
        
        while self._peek() is not None and self._peek() != ']':
            c = self._advance()
            
            # Escape in character class
            if c == '\\':
                c = self._advance()
                if c is None:
                    raise ParseError("Unexpected end in character class", self.pos)
                if c == 'd':
                    chars.update(string.digits)
                    continue
                elif c == 'w':
                    chars.update(string.ascii_letters + string.digits + '_')
                    continue
                elif c == 's':
                    chars.update(' \t\n\r\f\v')
                    continue
                elif c == 'n':
                    c = '\n'
                elif c == 't':
                    c = '\t'
                elif c == 'r':
                    c = '\r'
            
            # Range: a-z
            if self._peek() == '-' and self.pos + 1 < self.length and self.pattern[self.pos + 1] != ']':
                self._advance()  # consume '-'
                end = self._advance()
                if end is None:
                    raise ParseError("Unexpected end in range", self.pos)
                
                if end == '\\':
                    end = self._advance()
                    if end is None:
                        raise ParseError("Unexpected end in range", self.pos)
                
                # Add range
                for code in range(ord(c), ord(end) + 1):
                    chars.add(chr(code))
            else:
                chars.add(c)
        
        self._expect(']')
        
        return CharClass(frozenset(chars), negated)


# =============================================================================
# NFA (Non-deterministic Finite Automaton)
# =============================================================================

@dataclass
class NFAState:
    """
    A state in the NFA.
    
    Each state has:
    - An ID for identification/visualization
    - A set of transitions (char -> set of states)
    - A set of ε-transitions (free moves)
    - Whether it's an accept state
    """
    id: int
    transitions: Dict[str, Set['NFAState']] = field(default_factory=dict)
    epsilon: Set['NFAState'] = field(default_factory=set)
    is_accept: bool = False
    is_start_anchor: bool = False   # Must be at start of string
    is_end_anchor: bool = False     # Must be at end of string
    
    def add_transition(self, char: str, target: 'NFAState') -> None:
        """Add a transition on a character."""
        if char not in self.transitions:
            self.transitions[char] = set()
        self.transitions[char].add(target)
    
    def add_epsilon(self, target: 'NFAState') -> None:
        """Add an ε-transition."""
        self.epsilon.add(target)
    
    def __hash__(self) -> int:
        return self.id
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, NFAState):
            return self.id == other.id
        return False
    
    def __repr__(self) -> str:
        acc = "*" if self.is_accept else ""
        return f"S{self.id}{acc}"


@dataclass
class NFA:
    """
    A complete NFA with start and accept states.
    
    Thompson's construction guarantees:
    - Exactly one start state
    - Exactly one accept state
    - At most 2n states for regex of length n
    """
    start: NFAState
    accept: NFAState
    states: List[NFAState]
    
    def __repr__(self) -> str:
        return f"NFA({len(self.states)} states, start=S{self.start.id}, accept=S{self.accept.id})"


class NFABuilder(ASTVisitor):
    """
    Builds an NFA from an AST using Thompson's construction.
    
    Thompson's Construction (1968):
    - Each AST node creates a small NFA fragment
    - Fragments have one start and one accept state
    - Composition uses ε-transitions
    - Result has O(n) states for regex of length n
    """
    
    def __init__(self):
        self._state_counter = 0
        self._all_states: List[NFAState] = []
    
    def _new_state(self) -> NFAState:
        """Create a new state with unique ID."""
        state = NFAState(id=self._state_counter)
        self._state_counter += 1
        self._all_states.append(state)
        return state
    
    def build(self, ast: ASTNode) -> NFA:
        """Build NFA from AST."""
        self._state_counter = 0
        self._all_states = []
        
        start, accept = ast.accept(self)
        accept.is_accept = True
        
        return NFA(start=start, accept=accept, states=self._all_states)
    
    def visit_literal(self, node: Literal) -> Tuple[NFAState, NFAState]:
        """
        Literal 'a':
        
            ──(a)──>●
        """
        start = self._new_state()
        accept = self._new_state()
        start.add_transition(node.char, accept)
        return start, accept
    
    def visit_dot(self, node: Dot) -> Tuple[NFAState, NFAState]:
        """
        Dot (any char):
        
            ──(.)──>●
        
        We use a special marker that matches any char (except newline).
        """
        start = self._new_state()
        accept = self._new_state()
        start.add_transition('\x00DOT\x00', accept)  # Special marker for any char
        return start, accept
    
    def visit_char_class(self, node: CharClass) -> Tuple[NFAState, NFAState]:
        """
        Character class [abc]:
        
                 ┌─(a)─┐
            ──ε──┼─(b)─┼──ε──>●
                 └─(c)─┘
        
        For negated classes, we use a special transition marker.
        """
        start = self._new_state()
        accept = self._new_state()
        
        if node.negated:
            # Store negated class as special marker with the chars embedded
            marker = f'[^CLASS:{id(node)}]'
            start.add_transition(marker, accept)
            # Store chars in a way we can retrieve
            start._negated_chars = node.chars  # type: ignore
        else:
            for char in node.chars:
                start.add_transition(char, accept)
        
        return start, accept
    
    def visit_concat(self, node: Concat) -> Tuple[NFAState, NFAState]:
        """
        Concatenation ab:
        
            ──(a)──ε──(b)──>●
        """
        left_start, left_accept = node.left.accept(self)
        right_start, right_accept = node.right.accept(self)
        
        # Connect left's accept to right's start
        left_accept.add_epsilon(right_start)
        
        return left_start, right_accept
    
    def visit_alternate(self, node: Alternate) -> Tuple[NFAState, NFAState]:
        """
        Alternation a|b:
        
                  ┌──(a)──┐
            ──ε──┤        ├──ε──>●
                  └──(b)──┘
        """
        start = self._new_state()
        accept = self._new_state()
        
        left_start, left_accept = node.left.accept(self)
        right_start, right_accept = node.right.accept(self)
        
        start.add_epsilon(left_start)
        start.add_epsilon(right_start)
        
        left_accept.add_epsilon(accept)
        right_accept.add_epsilon(accept)
        
        return start, accept
    
    def visit_star(self, node: Star) -> Tuple[NFAState, NFAState]:
        """
        Kleene star a*:
        
                  ┌─────ε─────┐
                  │           ↓
            ──ε──>○──(a)──>○──ε──>●
                  ↑           │
                  └─────ε─────┘
        """
        start = self._new_state()
        accept = self._new_state()
        
        child_start, child_accept = node.child.accept(self)
        
        # Can skip entirely (zero repetitions)
        start.add_epsilon(accept)
        
        # Enter the child
        start.add_epsilon(child_start)
        
        # Can repeat (loop back)
        child_accept.add_epsilon(child_start)
        
        # Can exit
        child_accept.add_epsilon(accept)
        
        return start, accept
    
    def visit_plus(self, node: Plus) -> Tuple[NFAState, NFAState]:
        """
        One or more a+:
        
            ──(a)──>○──ε──>●
                    ↑     │
                    └──ε──┘
        
        Equivalent to aa*
        """
        start = self._new_state()
        accept = self._new_state()
        
        child_start, child_accept = node.child.accept(self)
        
        start.add_epsilon(child_start)
        
        # Can repeat
        child_accept.add_epsilon(child_start)
        
        # Can exit
        child_accept.add_epsilon(accept)
        
        return start, accept
    
    def visit_question(self, node: Question) -> Tuple[NFAState, NFAState]:
        """
        Optional a?:
        
                  ┌────ε────┐
                  │         ↓
            ──ε──>○──(a)──>●
        """
        start = self._new_state()
        accept = self._new_state()
        
        child_start, child_accept = node.child.accept(self)
        
        # Can skip
        start.add_epsilon(accept)
        
        # Or take the child
        start.add_epsilon(child_start)
        child_accept.add_epsilon(accept)
        
        return start, accept
    
    def visit_repeat(self, node: Repeat) -> Tuple[NFAState, NFAState]:
        """
        Bounded repetition a{n,m}:
        
        Build as: a...a (n times) followed by a?...a? (m-n times)
        """
        if node.min_count == 0 and node.max_count == 0:
            return self.visit_empty(Empty())
        
        # Build minimum required repetitions
        parts: List[Tuple[NFAState, NFAState]] = []
        
        for _ in range(node.min_count):
            parts.append(node.child.accept(self))
        
        # Build optional repetitions
        if node.max_count is None:
            # Unlimited: add a* at the end
            star_start, star_accept = self.visit_star(Star(node.child))
            parts.append((star_start, star_accept))
        else:
            # Limited: add (max - min) optional copies
            for _ in range(node.max_count - node.min_count):
                opt_start, opt_accept = self.visit_question(Question(node.child))
                parts.append((opt_start, opt_accept))
        
        if not parts:
            return self.visit_empty(Empty())
        
        # Chain all parts together
        start = parts[0][0]
        for i in range(len(parts) - 1):
            parts[i][1].add_epsilon(parts[i + 1][0])
        accept = parts[-1][1]
        
        return start, accept
    
    def visit_anchor(self, node: Anchor) -> Tuple[NFAState, NFAState]:
        """
        Anchors ^ and $:
        
        These are special states that consume no input but have constraints.
        """
        start = self._new_state()
        accept = self._new_state()
        
        if node.is_start:
            start.is_start_anchor = True
        else:
            start.is_end_anchor = True
        
        start.add_epsilon(accept)
        
        return start, accept
    
    def visit_empty(self, node: Empty) -> Tuple[NFAState, NFAState]:
        """
        Empty expression:
        
            ──ε──>●
        """
        start = self._new_state()
        accept = self._new_state()
        start.add_epsilon(accept)
        return start, accept


# =============================================================================
# NFA Matcher
# =============================================================================

@dataclass
class MatchStep:
    """One step in the matching process (for visualization)."""
    position: int
    char: Optional[str]
    active_states: FrozenSet[NFAState]
    matched: bool
    note: str = ""


@dataclass 
class MatchResult:
    """Result of a match attempt."""
    matched: bool
    match_start: int
    match_end: int
    steps: List[MatchStep]
    
    @property
    def matched_text(self) -> Optional[str]:
        """Get the matched substring (if match succeeded)."""
        return None  # Filled in by caller


class NFAMatcher:
    """
    Simulates an NFA to match strings.
    
    Algorithm:
    1. Start with ε-closure of start state
    2. For each input character:
       a. Compute transitions from active states
       b. Take ε-closure of result
    3. Accept if any active state is an accept state
    
    The ε-closure is computed using BFS/DFS to find all states
    reachable through ε-transitions alone.
    """
    
    def __init__(self, nfa: NFA, record_steps: bool = True):
        self.nfa = nfa
        self.record_steps = record_steps
        self._char_class_cache: Dict[int, FrozenSet[str]] = {}
    
    def _epsilon_closure(self, states: Set[NFAState]) -> FrozenSet[NFAState]:
        """
        Compute ε-closure: all states reachable via ε-transitions.
        
        This is the key to NFA simulation - we follow all ε-transitions
        to find the full set of "active" states.
        """
        closure: Set[NFAState] = set(states)
        stack = list(states)
        
        while stack:
            state = stack.pop()
            for target in state.epsilon:
                if target not in closure:
                    closure.add(target)
                    stack.append(target)
        
        return frozenset(closure)
    
    def _compute_transitions(
        self,
        states: FrozenSet[NFAState],
        char: str,
        position: int,
        text_length: int
    ) -> Set[NFAState]:
        """
        Compute next states after reading a character.
        
        Handles:
        - Literal matches
        - Dot (any char except newline)
        - Character classes (including negated)
        - Anchors (position constraints)
        """
        next_states: Set[NFAState] = set()
        
        for state in states:
            # Check anchors
            if state.is_start_anchor and position != 0:
                continue
            if state.is_end_anchor and position != text_length:
                continue
            
            # Check transitions
            for trans_char, targets in state.transitions.items():
                matched = False
                
                if trans_char == char:
                    # Exact match
                    matched = True
                elif trans_char == '\x00DOT\x00' and char != '\n':
                    # Dot matches any except newline
                    matched = True
                elif trans_char.startswith('[^CLASS:'):
                    # Negated character class - get chars from state
                    negated_chars = getattr(state, '_negated_chars', frozenset())
                    matched = char not in negated_chars and char != '\n'
                
                if matched:
                    next_states.update(targets)
        
        return next_states
    
    def match_at(self, text: str, start_pos: int = 0) -> MatchResult:
        """
        Try to match starting at a specific position.
        
        Returns MatchResult with detailed steps.
        """
        steps: List[MatchStep] = []
        
        # Check if pattern has start anchor - if so, only position 0 is valid
        has_start_anchor = any(s.is_start_anchor for s in self.nfa.states)
        if has_start_anchor and start_pos != 0:
            return MatchResult(
                matched=False,
                match_start=start_pos,
                match_end=-1,
                steps=[]
            )
        
        # Start with ε-closure of start state
        active = self._epsilon_closure({self.nfa.start})
        
        if self.record_steps:
            steps.append(MatchStep(
                position=start_pos,
                char=None,
                active_states=active,
                matched=self.nfa.accept in active,
                note="Initial ε-closure"
            ))
        
        best_match_end = -1
        if self.nfa.accept in active:
            best_match_end = start_pos
        
        position = start_pos
        
        while position < len(text) and active:
            char = text[position]
            
            # Compute transitions
            next_states = self._compute_transitions(
                active, char, position, len(text)
            )
            
            # Take ε-closure
            active = self._epsilon_closure(next_states)
            
            position += 1
            
            # Check if we reached accept state
            matched = self.nfa.accept in active
            if matched:
                best_match_end = position
            
            if self.record_steps:
                steps.append(MatchStep(
                    position=position,
                    char=char,
                    active_states=active,
                    matched=matched,
                    note=f"Read '{char}'"
                ))
            
            if not active:
                break
        
        # Check end anchor if at end of string
        if position == len(text) and active:
            for state in active:
                if state.is_end_anchor:
                    # Can transition through end anchor
                    next_states = self._compute_transitions(
                        active, '', position, len(text)
                    )
                    active = self._epsilon_closure(next_states)
                    if self.nfa.accept in active:
                        best_match_end = position
                    break
        
        return MatchResult(
            matched=best_match_end >= start_pos,
            match_start=start_pos,
            match_end=best_match_end,
            steps=steps
        )
    
    def search(self, text: str) -> MatchResult:
        """
        Search for first match anywhere in text.
        """
        for start_pos in range(len(text) + 1):
            result = self.match_at(text, start_pos)
            if result.matched:
                return result
        
        # No match found
        return MatchResult(
            matched=False,
            match_start=0,
            match_end=-1,
            steps=[]
        )
    
    def fullmatch(self, text: str) -> MatchResult:
        """
        Match the entire string.
        """
        result = self.match_at(text, 0)
        if result.matched and result.match_end == len(text):
            return result
        
        return MatchResult(
            matched=False,
            match_start=0,
            match_end=-1,
            steps=result.steps
        )


# =============================================================================
# Visualization
# =============================================================================

class NFAVisualizer:
    """
    Visualizes NFA as ASCII art and DOT format.
    """
    
    @staticmethod
    def to_dot(nfa: NFA) -> str:
        """Generate Graphviz DOT representation."""
        lines = ['digraph NFA {']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=circle];')
        
        # Start marker
        lines.append('  __start__ [shape=point];')
        lines.append(f'  __start__ -> S{nfa.start.id};')
        
        # Accept state (double circle)
        lines.append(f'  S{nfa.accept.id} [shape=doublecircle];')
        
        # States and transitions
        for state in nfa.states:
            # ε-transitions
            for target in state.epsilon:
                lines.append(f'  S{state.id} -> S{target.id} [label="ε"];')
            
            # Character transitions
            for char, targets in state.transitions.items():
                label = char if len(char) == 1 else char[:5]
                if char == '\x00DOT\x00':
                    label = '.'
                elif char.startswith('[^CLASS:'):
                    label = '[^...]'
                for target in targets:
                    lines.append(f'  S{state.id} -> S{target.id} [label="{label}"];')
        
        lines.append('}')
        return '\n'.join(lines)
    
    @staticmethod
    def to_ascii(nfa: NFA) -> str:
        """Generate ASCII representation of NFA."""
        lines = []
        lines.append(f"NFA: {len(nfa.states)} states")
        lines.append(f"Start: S{nfa.start.id}")
        lines.append(f"Accept: S{nfa.accept.id}")
        lines.append("")
        
        for state in nfa.states:
            prefix = ">" if state == nfa.start else " "
            suffix = "*" if state == nfa.accept else ""
            
            # Transitions
            trans = []
            for target in state.epsilon:
                trans.append(f"──ε──> S{target.id}")
            for char, targets in state.transitions.items():
                for target in targets:
                    if char == '\x00DOT\x00':
                        c = '.'
                    elif char.startswith('[^CLASS:'):
                        c = '[^]'
                    elif len(char) == 1:
                        c = char
                    else:
                        c = '?'
                    trans.append(f"──{c}──> S{target.id}")
            
            if trans:
                lines.append(f"{prefix}S{state.id}{suffix}: {', '.join(trans)}")
            else:
                lines.append(f"{prefix}S{state.id}{suffix}")
        
        return '\n'.join(lines)


class MatchVisualizer:
    """
    Visualizes the matching process step by step.
    """
    
    @staticmethod
    def visualize(text: str, result: MatchResult, show_all: bool = False) -> str:
        """
        Create ASCII visualization of matching process.
        
        Shows:
        - The input text with position marker
        - Active states at each step
        - Final match result
        """
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append("🔍 PHANTOM MATCH TRACE")
        lines.append("=" * 60)
        lines.append(f"Text: \"{text}\"")
        lines.append("")
        
        # Show each step
        for i, step in enumerate(result.steps):
            if not show_all and i > 0 and not step.matched and i < len(result.steps) - 1:
                continue
            
            # Position indicator
            pos_line = " " * step.position + "▼"
            text_line = text
            
            # Active states
            state_names = sorted([f"S{s.id}" for s in step.active_states])
            state_str = "{" + ", ".join(state_names) + "}"
            
            lines.append(f"Step {i}: {step.note}")
            lines.append(f"  Position: {step.position}")
            lines.append(f"  Text:     \"{text_line}\"")
            lines.append(f"            {pos_line}")
            lines.append(f"  Active:   {state_str}")
            lines.append(f"  Accept?:  {'✓ YES' if step.matched else '✗ no'}")
            lines.append("")
        
        # Final result
        lines.append("─" * 60)
        if result.matched:
            matched = text[result.match_start:result.match_end]
            lines.append(f"✅ MATCH: \"{matched}\"")
            lines.append(f"   Position: {result.match_start}..{result.match_end}")
        else:
            lines.append("❌ NO MATCH")
        
        return '\n'.join(lines)


# =============================================================================
# Main Regex Class
# =============================================================================

class Regex:
    """
    A compiled regular expression with visualization support.
    
    Usage:
        >>> rx = Regex(r"a+b*")
        >>> rx.match("aaab")
        MatchResult(matched=True, ...)
        >>> rx.visualize_nfa()
        >>> rx.trace("aaab")
    """
    
    def __init__(self, pattern: str):
        """
        Compile a regular expression pattern.
        
        Args:
            pattern: The regex pattern string
        
        Raises:
            ParseError: If the pattern is invalid
        """
        self.pattern = pattern
        
        # Parse to AST
        parser = Parser(pattern)
        self.ast = parser.parse()
        
        # Build NFA
        builder = NFABuilder()
        self.nfa = builder.build(self.ast)
        
        # Create matcher
        self._matcher = NFAMatcher(self.nfa)
    
    def match(self, text: str) -> MatchResult:
        """
        Match at the beginning of the string.
        """
        return self._matcher.match_at(text, 0)
    
    def search(self, text: str) -> MatchResult:
        """
        Search for first match anywhere in string.
        """
        return self._matcher.search(text)
    
    def fullmatch(self, text: str) -> MatchResult:
        """
        Match the entire string.
        """
        return self._matcher.fullmatch(text)
    
    def trace(self, text: str, show_all: bool = True) -> str:
        """
        Match with detailed step-by-step trace.
        
        Returns ASCII visualization of matching process.
        """
        result = self._matcher.match_at(text, 0)
        return MatchVisualizer.visualize(text, result, show_all)
    
    def visualize_nfa(self) -> str:
        """Get ASCII representation of NFA."""
        return NFAVisualizer.to_ascii(self.nfa)
    
    def to_dot(self) -> str:
        """Get Graphviz DOT representation of NFA."""
        return NFAVisualizer.to_dot(self.nfa)
    
    def __repr__(self) -> str:
        return f"Regex({self.pattern!r})"


# =============================================================================
# Convenience Functions
# =============================================================================

def compile(pattern: str) -> Regex:
    """Compile a regex pattern."""
    return Regex(pattern)


def match(pattern: str, text: str) -> MatchResult:
    """Match pattern at start of text."""
    return Regex(pattern).match(text)


def search(pattern: str, text: str) -> MatchResult:
    """Search for pattern anywhere in text."""
    return Regex(pattern).search(text)


def fullmatch(pattern: str, text: str) -> MatchResult:
    """Match pattern against entire text."""
    return Regex(pattern).fullmatch(text)


def trace(pattern: str, text: str, show_all: bool = True) -> str:
    """Get step-by-step matching trace."""
    return Regex(pattern).trace(text, show_all)


def visualize(pattern: str) -> str:
    """Visualize the NFA for a pattern."""
    return Regex(pattern).visualize_nfa()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main class
    'Regex',
    
    # Results
    'MatchResult',
    'MatchStep',
    
    # Convenience functions
    'compile',
    'match',
    'search',
    'fullmatch',
    'trace',
    'visualize',
    
    # AST (for advanced users)
    'ASTNode',
    'Parser',
    'ParseError',
    
    # NFA (for advanced users)
    'NFA',
    'NFAState',
    'NFABuilder',
    'NFAMatcher',
    
    # Visualization
    'NFAVisualizer',
    'MatchVisualizer',
]
