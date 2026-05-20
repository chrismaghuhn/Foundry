"""
Lambda: Pure Lambda Calculus Interpreter

An interpreter for the pure untyped lambda calculus with
Church encoding, step-by-step reduction, and visualization.

Lambda calculus (Alonzo Church, 1930s) is the foundation of
functional programming. It has only three constructs:

    1. Variables:      x, y, z
    2. Abstraction:    λx.body    (function definition)
    3. Application:    f x        (function call)

That's it. No numbers, no booleans, no if-else, no loops.
Yet it can compute ANYTHING a Turing machine can compute.

The Magic - Church Encoding:

    Numbers as functions:
        0 = λf.λx.x           (apply f zero times)
        1 = λf.λx.f x         (apply f once)
        2 = λf.λx.f (f x)     (apply f twice)
        3 = λf.λx.f (f (f x)) (apply f three times)
    
    Booleans as functions:
        TRUE  = λt.λf.t       (select first)
        FALSE = λt.λf.f       (select second)
    
    Arithmetic as functions:
        SUCC = λn.λf.λx.f (n f x)     (n + 1)
        ADD  = λm.λn.m SUCC n         (m + n)
        MUL  = λm.λn.m (ADD n) 0      (m * n)

Key Concepts:

    α-conversion: Rename bound variables (λx.x = λy.y)
    β-reduction:  Apply function ((λx.body) arg → body[x:=arg])
    η-conversion: λx.f x = f (if x not free in f)

This interpreter implements:
    - Full parser for lambda expressions
    - β-reduction with configurable strategy
    - Church encoding for numbers, booleans, pairs
    - Step-by-step reduction visualization
    - Pretty printing of terms

Syntax:
    λx.body     or  \\x.body    (lambda)
    f x                         (application, left-associative)
    (term)                      (grouping)

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Set, List, Optional, Tuple, Iterator
from enum import Enum, auto
import re


# =============================================================================
# Abstract Syntax Tree
# =============================================================================

class Term(ABC):
    """Base class for lambda calculus terms."""
    
    @abstractmethod
    def free_variables(self) -> Set[str]:
        """Return set of free (unbound) variables."""
        pass
    
    @abstractmethod
    def substitute(self, var: str, replacement: 'Term') -> 'Term':
        """Substitute all free occurrences of var with replacement."""
        pass
    
    @abstractmethod
    def __eq__(self, other: object) -> bool:
        pass
    
    @abstractmethod
    def __hash__(self) -> int:
        pass


@dataclass(frozen=True)
class Var(Term):
    """
    A variable.
    
    Variables are the atoms of lambda calculus.
    They can be bound (inside a λ) or free.
    """
    name: str
    
    def free_variables(self) -> Set[str]:
        return {self.name}
    
    def substitute(self, var: str, replacement: Term) -> Term:
        if self.name == var:
            return replacement
        return self
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"Var({self.name!r})"


@dataclass(frozen=True)
class Abs(Term):
    """
    Lambda abstraction (function definition).
    
    λx.body represents a function that takes x and returns body.
    The variable x is bound within body.
    """
    param: str
    body: Term
    
    def free_variables(self) -> Set[str]:
        return self.body.free_variables() - {self.param}
    
    def substitute(self, var: str, replacement: Term) -> Term:
        if var == self.param:
            # var is bound here, don't substitute in body
            return self
        
        if self.param in replacement.free_variables():
            # Need α-conversion to avoid capture
            new_param = fresh_variable(
                self.param,
                self.body.free_variables() | replacement.free_variables()
            )
            new_body = self.body.substitute(self.param, Var(new_param))
            return Abs(new_param, new_body.substitute(var, replacement))
        
        return Abs(self.param, self.body.substitute(var, replacement))
    
    def __str__(self) -> str:
        return f"λ{self.param}.{self.body}"
    
    def __repr__(self) -> str:
        return f"Abs({self.param!r}, {self.body!r})"


@dataclass(frozen=True)
class App(Term):
    """
    Application (function call).
    
    (f x) applies function f to argument x.
    This is the only way to "do" something in lambda calculus.
    """
    func: Term
    arg: Term
    
    def free_variables(self) -> Set[str]:
        return self.func.free_variables() | self.arg.free_variables()
    
    def substitute(self, var: str, replacement: Term) -> Term:
        return App(
            self.func.substitute(var, replacement),
            self.arg.substitute(var, replacement)
        )
    
    def __str__(self) -> str:
        func_str = str(self.func)
        arg_str = str(self.arg)
        
        # Add parens around complex args
        if isinstance(self.arg, (App, Abs)):
            arg_str = f"({arg_str})"
        
        # Add parens around abstractions in function position
        if isinstance(self.func, Abs):
            func_str = f"({func_str})"
        
        return f"{func_str} {arg_str}"
    
    def __repr__(self) -> str:
        return f"App({self.func!r}, {self.arg!r})"


# =============================================================================
# Helper Functions
# =============================================================================

def fresh_variable(base: str, avoid: Set[str]) -> str:
    """
    Generate a fresh variable name that's not in the avoid set.
    
    Used for α-conversion to prevent variable capture.
    """
    if base not in avoid:
        return base
    
    # Try adding primes
    candidate = base + "'"
    while candidate in avoid:
        candidate += "'"
    
    return candidate


def alpha_equivalent(t1: Term, t2: Term) -> bool:
    """
    Check if two terms are α-equivalent (same up to renaming).
    
    λx.x and λy.y are α-equivalent.
    """
    def normalize(term: Term, env: Dict[str, int], depth: int) -> Term:
        if isinstance(term, Var):
            if term.name in env:
                return Var(f"#{env[term.name]}")
            return term
        elif isinstance(term, Abs):
            new_env = {**env, term.param: depth}
            return Abs(f"#{depth}", normalize(term.body, new_env, depth + 1))
        elif isinstance(term, App):
            return App(
                normalize(term.func, env, depth),
                normalize(term.arg, env, depth)
            )
        return term
    
    return normalize(t1, {}, 0) == normalize(t2, {}, 0)


# =============================================================================
# Parser
# =============================================================================

class ParseError(Exception):
    """Error during parsing."""
    pass


class Lexer:
    """
    Tokenizer for lambda calculus expressions.
    
    Tokens:
        LAMBDA: λ or \\
        DOT: .
        LPAREN: (
        RPAREN: )
        VAR: identifier
    """
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
    
    def peek(self) -> Optional[str]:
        self._skip_whitespace()
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def _skip_whitespace(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos].isspace():
            self.pos += 1
    
    def next_token(self) -> Optional[Tuple[str, str]]:
        """Return (type, value) or None if EOF."""
        self._skip_whitespace()
        
        if self.pos >= len(self.source):
            return None
        
        char = self.source[self.pos]
        
        # Lambda
        if char in 'λ\\':
            self.pos += 1
            return ('LAMBDA', char)
        
        # Dot
        if char == '.':
            self.pos += 1
            return ('DOT', '.')
        
        # Parens
        if char == '(':
            self.pos += 1
            return ('LPAREN', '(')
        
        if char == ')':
            self.pos += 1
            return ('RPAREN', ')')
        
        # Variable (identifier) - can start with letter, underscore, or digit
        if char.isalnum() or char == '_':
            start = self.pos
            while self.pos < len(self.source) and (
                self.source[self.pos].isalnum() or self.source[self.pos] in "_'"
            ):
                self.pos += 1
            return ('VAR', self.source[start:self.pos])
        
        raise ParseError(f"Unexpected character: {char!r} at position {self.pos}")


class Parser:
    """
    Recursive descent parser for lambda calculus.
    
    Grammar:
        term    := abstraction | application
        abstraction := LAMBDA VAR+ DOT term
        application := atom+
        atom    := VAR | LPAREN term RPAREN
    """
    
    def __init__(self, source: str):
        self.lexer = Lexer(source)
        self.current: Optional[Tuple[str, str]] = None
        self._advance()
    
    def _advance(self) -> None:
        self.current = self.lexer.next_token()
    
    def _expect(self, token_type: str) -> str:
        if self.current is None or self.current[0] != token_type:
            expected = token_type
            got = self.current[0] if self.current else 'EOF'
            raise ParseError(f"Expected {expected}, got {got}")
        value = self.current[1]
        self._advance()
        return value
    
    def parse(self) -> Term:
        """Parse a complete lambda term."""
        term = self._parse_term()
        
        if self.current is not None:
            raise ParseError(f"Unexpected token: {self.current}")
        
        return term
    
    def _parse_term(self) -> Term:
        """Parse a term (abstraction or application)."""
        if self.current and self.current[0] == 'LAMBDA':
            return self._parse_abstraction()
        return self._parse_application()
    
    def _parse_abstraction(self) -> Term:
        """Parse λx.body or λx y z.body (multi-param)."""
        self._expect('LAMBDA')
        
        # Collect parameters
        params = []
        while self.current and self.current[0] == 'VAR':
            params.append(self.current[1])
            self._advance()
        
        if not params:
            raise ParseError("Lambda requires at least one parameter")
        
        self._expect('DOT')
        body = self._parse_term()
        
        # Build nested abstractions (right to left)
        result = body
        for param in reversed(params):
            result = Abs(param, result)
        
        return result
    
    def _parse_application(self) -> Term:
        """Parse f x y z (left-associative)."""
        atoms = []
        
        while self.current and self.current[0] in ('VAR', 'LPAREN', 'LAMBDA'):
            if self.current[0] == 'LAMBDA':
                atoms.append(self._parse_abstraction())
            else:
                atoms.append(self._parse_atom())
        
        if not atoms:
            raise ParseError("Expected term")
        
        # Build left-associative application
        result = atoms[0]
        for atom in atoms[1:]:
            result = App(result, atom)
        
        return result
    
    def _parse_atom(self) -> Term:
        """Parse variable or parenthesized term."""
        if self.current is None:
            raise ParseError("Unexpected end of input")
        
        if self.current[0] == 'VAR':
            name = self.current[1]
            self._advance()
            return Var(name)
        
        if self.current[0] == 'LPAREN':
            self._advance()
            term = self._parse_term()
            self._expect('RPAREN')
            return term
        
        raise ParseError(f"Expected variable or '(', got {self.current[0]}")


def parse(source: str) -> Term:
    """Parse a lambda calculus expression."""
    return Parser(source).parse()


# =============================================================================
# Reduction
# =============================================================================

class ReductionStrategy(Enum):
    """β-reduction evaluation strategies."""
    NORMAL = auto()      # Leftmost-outermost (call-by-name)
    APPLICATIVE = auto() # Leftmost-innermost (call-by-value)


@dataclass
class ReductionStep:
    """One step in the reduction process."""
    before: Term
    after: Term
    redex: str  # Description of what was reduced
    

class Reducer:
    """
    Performs β-reduction on lambda terms.
    
    β-reduction is the computational rule of lambda calculus:
        (λx.body) arg  →  body[x := arg]
    
    The expression (λx.body) arg is called a "redex" (reducible expression).
    """
    
    def __init__(
        self,
        strategy: ReductionStrategy = ReductionStrategy.NORMAL,
        max_steps: int = 1000
    ):
        self.strategy = strategy
        self.max_steps = max_steps
    
    def is_redex(self, term: Term) -> bool:
        """Check if term is a β-redex: (λx.body) arg"""
        return isinstance(term, App) and isinstance(term.func, Abs)
    
    def beta_reduce(self, term: App) -> Term:
        """Perform one β-reduction: (λx.body) arg → body[x:=arg]"""
        assert isinstance(term.func, Abs)
        return term.func.body.substitute(term.func.param, term.arg)
    
    def find_redex_normal(self, term: Term) -> Optional[Tuple[Term, List[str]]]:
        """
        Find leftmost-outermost redex (normal order).
        
        Returns (redex, path) where path describes location.
        """
        if self.is_redex(term):
            return (term, [])
        
        if isinstance(term, App):
            # Check function position first (leftmost)
            result = self.find_redex_normal(term.func)
            if result:
                redex, path = result
                return (redex, ['func'] + path)
            
            # Then argument
            result = self.find_redex_normal(term.arg)
            if result:
                redex, path = result
                return (redex, ['arg'] + path)
        
        elif isinstance(term, Abs):
            result = self.find_redex_normal(term.body)
            if result:
                redex, path = result
                return (redex, ['body'] + path)
        
        return None
    
    def find_redex_applicative(self, term: Term) -> Optional[Tuple[Term, List[str]]]:
        """
        Find leftmost-innermost redex (applicative order).
        
        Reduces arguments before function application.
        """
        if isinstance(term, App):
            # Check inside function first
            result = self.find_redex_applicative(term.func)
            if result:
                redex, path = result
                return (redex, ['func'] + path)
            
            # Check inside argument
            result = self.find_redex_applicative(term.arg)
            if result:
                redex, path = result
                return (redex, ['arg'] + path)
            
            # Then this application itself
            if self.is_redex(term):
                return (term, [])
        
        elif isinstance(term, Abs):
            result = self.find_redex_applicative(term.body)
            if result:
                redex, path = result
                return (redex, ['body'] + path)
        
        return None
    
    def step(self, term: Term) -> Optional[Tuple[Term, ReductionStep]]:
        """
        Perform one reduction step.
        
        Returns (new_term, step_info) or None if in normal form.
        """
        if self.strategy == ReductionStrategy.NORMAL:
            found = self.find_redex_normal(term)
        else:
            found = self.find_redex_applicative(term)
        
        if found is None:
            return None
        
        redex, path = found
        
        # Perform the reduction
        def reduce_at_path(t: Term, p: List[str]) -> Term:
            if not p:
                assert self.is_redex(t)
                return self.beta_reduce(t)
            
            direction = p[0]
            rest = p[1:]
            
            if isinstance(t, App):
                if direction == 'func':
                    return App(reduce_at_path(t.func, rest), t.arg)
                else:
                    return App(t.func, reduce_at_path(t.arg, rest))
            elif isinstance(t, Abs):
                return Abs(t.param, reduce_at_path(t.body, rest))
            
            raise RuntimeError("Invalid path")
        
        new_term = reduce_at_path(term, path)
        
        step = ReductionStep(
            before=term,
            after=new_term,
            redex=f"β: {redex} → {self.beta_reduce(redex)}"
        )
        
        return (new_term, step)
    
    def reduce(self, term: Term) -> Tuple[Term, List[ReductionStep]]:
        """
        Reduce term to normal form (or until max_steps).
        
        Returns (normal_form, steps).
        """
        steps: List[ReductionStep] = []
        current = term
        
        for _ in range(self.max_steps):
            result = self.step(current)
            if result is None:
                break
            
            current, step = result
            steps.append(step)
        
        return (current, steps)
    
    def reduce_with_trace(self, term: Term) -> Iterator[Tuple[Term, Optional[ReductionStep]]]:
        """
        Generator that yields each reduction step.
        
        Yields (current_term, step) where step is None for final term.
        """
        yield (term, None)
        
        current = term
        for _ in range(self.max_steps):
            result = self.step(current)
            if result is None:
                break
            
            current, step = result
            yield (current, step)


def reduce(term: Term, max_steps: int = 1000) -> Term:
    """Reduce term to normal form."""
    reducer = Reducer(max_steps=max_steps)
    result, _ = reducer.reduce(term)
    return result


def reduce_steps(term: Term, max_steps: int = 1000) -> List[ReductionStep]:
    """Get all reduction steps."""
    reducer = Reducer(max_steps=max_steps)
    _, steps = reducer.reduce(term)
    return steps


# =============================================================================
# Church Encoding
# =============================================================================

class Church:
    """
    Church encoding: representing data as pure lambda terms.
    
    This is the magic of lambda calculus - everything is a function!
    """
    
    # =========================================================================
    # Church Numerals
    # =========================================================================
    
    @staticmethod
    def numeral(n: int) -> Term:
        """
        Create Church numeral for n.
        
        n = λf.λx.f (f (f ... (f x)))  [n applications of f]
        
        0 = λf.λx.x
        1 = λf.λx.f x
        2 = λf.λx.f (f x)
        3 = λf.λx.f (f (f x))
        """
        if n < 0:
            raise ValueError("Church numerals are non-negative")
        
        # Build f (f (f ... (f x)))
        body: Term = Var('x')
        for _ in range(n):
            body = App(Var('f'), body)
        
        return Abs('f', Abs('x', body))
    
    @staticmethod
    def to_int(term: Term, max_steps: int = 1000) -> Optional[int]:
        """
        Convert a Church numeral back to int.
        
        Apply the numeral to a successor function and zero,
        then count how many times successor was applied.
        """
        # Reduce to normal form first
        term = reduce(term, max_steps)
        
        # Check if it's in numeral form: λf.λx.body
        if not isinstance(term, Abs):
            return None
        if not isinstance(term.body, Abs):
            return None
        
        f_name = term.param
        x_name = term.body.param
        body = term.body.body
        
        # Count applications of f
        count = 0
        current = body
        
        while isinstance(current, App):
            if not (isinstance(current.func, Var) and current.func.name == f_name):
                return None
            count += 1
            current = current.arg
        
        # Should end with x
        if not (isinstance(current, Var) and current.name == x_name):
            return None
        
        return count
    
    # Church arithmetic terms
    ZERO = parse("λf.λx.x")
    ONE = parse("λf.λx.f x")
    TWO = parse("λf.λx.f (f x)")
    THREE = parse("λf.λx.f (f (f x))")
    
    SUCC = parse("λn.λf.λx.f (n f x)")
    ADD = parse("λm.λn.λf.λx.m f (n f x)")
    MUL = parse("λm.λn.λf.m (n f)")
    POW = parse("λm.λn.n m")  # m^n
    PRED = parse("λn.λf.λx.n (λg.λh.h (g f)) (λu.x) (λu.u)")
    SUB = parse("λm.λn.n (λn.λf.λx.n (λg.λh.h (g f)) (λu.x) (λu.u)) m")
    
    # =========================================================================
    # Church Booleans
    # =========================================================================
    
    TRUE = parse("λt.λf.t")
    FALSE = parse("λt.λf.f")
    
    AND = parse("λp.λq.p q p")
    OR = parse("λp.λq.p p q")
    NOT = parse("λp.p (λt.λf.f) (λt.λf.t)")
    IF = parse("λp.λa.λb.p a b")
    
    ISZERO = parse("λn.n (λx.λt.λf.f) (λt.λf.t)")
    
    @staticmethod
    def to_bool(term: Term, max_steps: int = 1000) -> Optional[bool]:
        """Convert Church boolean to Python bool."""
        term = reduce(term, max_steps)
        
        if alpha_equivalent(term, Church.TRUE):
            return True
        if alpha_equivalent(term, Church.FALSE):
            return False
        
        return None
    
    # =========================================================================
    # Church Pairs
    # =========================================================================
    
    PAIR = parse("λx.λy.λf.f x y")
    FST = parse("λp.p (λx.λy.x)")
    SND = parse("λp.p (λx.λy.y)")
    
    # =========================================================================
    # Recursion (Y Combinator)
    # =========================================================================
    
    # The Y combinator enables recursion in lambda calculus!
    # Y f = f (Y f)
    Y = parse("λf.(λx.f (x x)) (λx.f (x x))")
    
    # Z combinator (call-by-value version)
    Z = parse("λf.(λx.f (λy.x x y)) (λx.f (λy.x x y))")


# =============================================================================
# Visualization
# =============================================================================

def visualize_reduction(term: Term, max_steps: int = 20) -> str:
    """
    Create a visualization of the reduction process.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("λ REDUCTION TRACE")
    lines.append("=" * 60)
    lines.append(f"\nInitial: {term}")
    lines.append("")
    
    reducer = Reducer(max_steps=max_steps)
    current = term
    step_num = 0
    
    for _ in range(max_steps):
        result = reducer.step(current)
        if result is None:
            break
        
        current, step = result
        step_num += 1
        
        lines.append(f"Step {step_num}:")
        lines.append(f"  {step.redex}")
        lines.append(f"  → {current}")
        lines.append("")
    
    lines.append("─" * 60)
    if reducer.step(current) is None:
        lines.append(f"✓ Normal form: {current}")
    else:
        lines.append(f"⚠ Stopped after {max_steps} steps")
        lines.append(f"  Current: {current}")
    
    return '\n'.join(lines)


def visualize_church_arithmetic(m: int, n: int, op: str) -> str:
    """
    Visualize Church arithmetic: m op n.
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"λ CHURCH ARITHMETIC: {m} {op} {n}")
    lines.append("=" * 60)
    
    m_term = Church.numeral(m)
    n_term = Church.numeral(n)
    
    lines.append(f"\n{m} = {m_term}")
    lines.append(f"{n} = {n_term}")
    
    if op == '+':
        op_term = Church.ADD
        expected = m + n
        lines.append(f"ADD = {op_term}")
        expr = App(App(op_term, m_term), n_term)
    elif op == '*':
        op_term = Church.MUL
        expected = m * n
        lines.append(f"MUL = {op_term}")
        expr = App(App(op_term, m_term), n_term)
    elif op == '^':
        op_term = Church.POW
        expected = m ** n if n >= 0 else 0
        lines.append(f"POW = {op_term}")
        expr = App(App(op_term, m_term), n_term)
    else:
        raise ValueError(f"Unknown operation: {op}")
    
    lines.append(f"\nExpression: {expr}")
    lines.append("")
    
    # Reduce
    reducer = Reducer(max_steps=100)
    result, steps = reducer.reduce(expr)
    
    lines.append(f"Reducing... ({len(steps)} steps)")
    lines.append(f"Result: {result}")
    
    # Convert back to int
    result_int = Church.to_int(result)
    
    lines.append("")
    lines.append("─" * 60)
    if result_int is not None:
        lines.append(f"✓ {m} {op} {n} = {result_int}")
        if result_int == expected:
            lines.append(f"  Matches expected: {expected}")
        else:
            lines.append(f"  ⚠ Expected: {expected}")
    else:
        lines.append(f"⚠ Could not convert result to integer")
    
    return '\n'.join(lines)


def pretty_print(term: Term, indent: int = 0) -> str:
    """Pretty print a term as a tree."""
    prefix = "  " * indent
    
    if isinstance(term, Var):
        return f"{prefix}Var: {term.name}"
    elif isinstance(term, Abs):
        lines = [f"{prefix}λ{term.param}."]
        lines.append(pretty_print(term.body, indent + 1))
        return '\n'.join(lines)
    elif isinstance(term, App):
        lines = [f"{prefix}App:"]
        lines.append(f"{prefix}  func:")
        lines.append(pretty_print(term.func, indent + 2))
        lines.append(f"{prefix}  arg:")
        lines.append(pretty_print(term.arg, indent + 2))
        return '\n'.join(lines)
    
    return f"{prefix}???"


# =============================================================================
# REPL Helpers
# =============================================================================

# Standard library of useful terms
STDLIB: Dict[str, Term] = {
    # Numbers
    '0': Church.ZERO,
    '1': Church.ONE,
    '2': Church.TWO,
    '3': Church.THREE,
    
    # Arithmetic
    'succ': Church.SUCC,
    'add': Church.ADD,
    'mul': Church.MUL,
    'pow': Church.POW,
    'pred': Church.PRED,
    
    # Booleans
    'true': Church.TRUE,
    'false': Church.FALSE,
    'and': Church.AND,
    'or': Church.OR,
    'not': Church.NOT,
    'if': Church.IF,
    'iszero': Church.ISZERO,
    
    # Pairs
    'pair': Church.PAIR,
    'fst': Church.FST,
    'snd': Church.SND,
    
    # Combinators
    'I': parse("λx.x"),           # Identity
    'K': parse("λx.λy.x"),        # Constant
    'S': parse("λx.λy.λz.x z (y z)"),  # Substitution
    'B': parse("λf.λg.λx.f (g x)"),    # Composition
    'C': parse("λf.λx.λy.f y x"),      # Flip
    'W': parse("λf.λx.f x x"),         # Duplicate
    'Y': Church.Y,                # Y combinator
    'omega': parse("(λx.x x) (λx.x x)"),  # Ω (diverges!)
}


def expand_stdlib(term: Term, lib: Dict[str, Term] = STDLIB) -> Term:
    """Replace standard library names with their definitions."""
    if isinstance(term, Var):
        if term.name in lib:
            return lib[term.name]
        return term
    elif isinstance(term, Abs):
        # Don't expand if parameter shadows a stdlib name
        new_lib = {k: v for k, v in lib.items() if k != term.param}
        return Abs(term.param, expand_stdlib(term.body, new_lib))
    elif isinstance(term, App):
        return App(
            expand_stdlib(term.func, lib),
            expand_stdlib(term.arg, lib)
        )
    return term


def evaluate(source: str, max_steps: int = 1000) -> Term:
    """Parse, expand stdlib, and reduce."""
    term = parse(source)
    term = expand_stdlib(term)
    return reduce(term, max_steps)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # AST
    'Term',
    'Var',
    'Abs',
    'App',
    
    # Parsing
    'parse',
    'ParseError',
    
    # Reduction
    'Reducer',
    'ReductionStrategy',
    'ReductionStep',
    'reduce',
    'reduce_steps',
    
    # Church encoding
    'Church',
    
    # Utilities
    'alpha_equivalent',
    'fresh_variable',
    'expand_stdlib',
    'evaluate',
    
    # Visualization
    'visualize_reduction',
    'visualize_church_arithmetic',
    'pretty_print',
    
    # Standard library
    'STDLIB',
]
