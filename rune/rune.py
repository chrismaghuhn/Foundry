"""
Rune: Sandboxed Expression Evaluator

A safe expression language for user-defined formulas, rules, and computed fields.
Execute untrusted expressions with guaranteed termination, memory bounds, and no I/O.

Design Philosophy:
    1. SAFETY FIRST: No expression can crash, hang, or access unauthorized resources
    2. PREDICTABLE: Same inputs always produce same outputs (deterministic)
    3. DEBUGGABLE: Errors include precise location and context
    4. EMBEDDABLE: Zero dependencies, pure Python, easy to integrate

Language Features:
    - Arithmetic: + - * / % ** (power)
    - Comparison: == != < > <= >=
    - Logical: and or not
    - Conditionals: if condition then expr else expr
    - Lists: [1, 2, 3], list[0], list operations
    - Strings: "hello", string concatenation, interpolation
    - Functions: Built-in and user-registered
    - Variables: From evaluation context

Safety Guarantees:
    - TERMINATION: No loops, no recursion, fuel-based execution limits
    - MEMORY: Operations cost fuel proportional to output size
    - ISOLATION: No access to Python runtime, filesystem, network
    - DETERMINISM: No randomness, no time, no external state

Architecture:
    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Lexer   │ -> │  Parser  │ -> │ Analyzer │ -> │ Executor │
    │ (tokens) │    │  (AST)   │    │ (typed)  │    │ (result) │
    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                          ↑
                                                    ┌──────────┐
                                                    │  Fuel    │
                                                    │ Monitor  │
                                                    └──────────┘

The fuel system is key to safety: every operation consumes fuel, and execution
halts when fuel is exhausted. This provides CPU limits without OS-level intervention.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import re
import math
import operator
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Generic, TypeVar, Union
from functools import reduce


# =============================================================================
# Type System
# =============================================================================

class RuType(Enum):
    """Types in the Rune language."""
    NUMBER = "number"      # 64-bit float
    STRING = "string"      # Unicode string
    BOOLEAN = "boolean"    # true/false
    LIST = "list"          # Homogeneous list
    NULL = "null"          # Absence of value
    ANY = "any"            # Type variable (for generics)
    FUNCTION = "function"  # First-class function


@dataclass(frozen=True)
class TypeSignature:
    """
    Type signature for functions.
    
    We use a simple type system where:
    - Primitives are exact matches
    - ANY matches anything
    - LIST[T] is covariant (LIST[NUMBER] is subtype of LIST[ANY])
    """
    param_types: tuple[RuType, ...]
    return_type: RuType
    variadic: bool = False  # Last param can repeat
    
    def matches(self, arg_types: list[RuType]) -> bool:
        """Check if argument types match this signature."""
        if self.variadic:
            if len(arg_types) < len(self.param_types) - 1:
                return False
            # Check fixed params
            for i, param_type in enumerate(self.param_types[:-1]):
                if not self._type_matches(param_type, arg_types[i]):
                    return False
            # Check variadic params
            variadic_type = self.param_types[-1]
            for arg_type in arg_types[len(self.param_types)-1:]:
                if not self._type_matches(variadic_type, arg_type):
                    return False
            return True
        else:
            if len(arg_types) != len(self.param_types):
                return False
            return all(
                self._type_matches(p, a) 
                for p, a in zip(self.param_types, arg_types)
            )
    
    def _type_matches(self, expected: RuType, actual: RuType) -> bool:
        if expected == RuType.ANY:
            return True
        return expected == actual


# =============================================================================
# Tokens
# =============================================================================

class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    IDENTIFIER = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    POWER = auto()      # **
    
    # Comparison
    EQ = auto()         # ==
    NE = auto()         # !=
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    
    # Logical
    AND = auto()
    OR = auto()
    NOT = auto()
    
    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    QUESTION = auto()
    
    # Keywords
    IF = auto()
    THEN = auto()
    ELSE = auto()
    
    # End
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: Any
    line: int
    column: int
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


@dataclass(frozen=True)
class SourceLocation:
    """Location in source for error reporting."""
    line: int
    column: int
    length: int = 1
    
    def __str__(self) -> str:
        return f"line {self.line}, column {self.column}"


# =============================================================================
# Errors
# =============================================================================

class RuneError(Exception):
    """Base exception for all Rune errors."""
    pass


@dataclass
class LexerError(RuneError):
    """Error during tokenization."""
    message: str
    location: SourceLocation
    
    def __str__(self) -> str:
        return f"Lexer error at {self.location}: {self.message}"


@dataclass
class ParseError(RuneError):
    """Error during parsing."""
    message: str
    location: SourceLocation
    
    def __str__(self) -> str:
        return f"Parse error at {self.location}: {self.message}"


@dataclass
class TypeError(RuneError):
    """Type mismatch error."""
    message: str
    location: SourceLocation
    
    def __str__(self) -> str:
        return f"Type error at {self.location}: {self.message}"


@dataclass
class RuntimeError(RuneError):
    """Error during execution."""
    message: str
    location: SourceLocation | None = None
    
    def __str__(self) -> str:
        loc = f" at {self.location}" if self.location else ""
        return f"Runtime error{loc}: {self.message}"


@dataclass
class FuelExhaustedError(RuneError):
    """Execution exceeded fuel limit."""
    fuel_used: int
    fuel_limit: int
    
    def __str__(self) -> str:
        return f"Execution limit exceeded: used {self.fuel_used} of {self.fuel_limit} fuel"


@dataclass  
class DepthExceededError(RuneError):
    """Call stack exceeded depth limit."""
    depth: int
    limit: int
    
    def __str__(self) -> str:
        return f"Call depth exceeded: {self.depth} > {self.limit}"


# =============================================================================
# Lexer
# =============================================================================

class Lexer:
    """
    Tokenizes Rune expressions.
    
    The lexer is intentionally simple - no complex string escapes,
    no heredocs, no unusual number formats. This reduces attack surface.
    """
    
    KEYWORDS = {
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'null': TokenType.NULL,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
        'if': TokenType.IF,
        'then': TokenType.THEN,
        'else': TokenType.ELSE,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
    
    def tokenize(self) -> list[Token]:
        """Tokenize entire source string."""
        while not self._at_end():
            self._scan_token()
        
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
    
    def _at_end(self) -> bool:
        return self.pos >= len(self.source)
    
    def _peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else '\0'
    
    def _advance(self) -> str:
        char = self.source[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def _add_token(self, token_type: TokenType, value: Any = None) -> None:
        self.tokens.append(Token(token_type, value, self.line, self.column))
    
    def _location(self) -> SourceLocation:
        return SourceLocation(self.line, self.column)
    
    def _scan_token(self) -> None:
        char = self._advance()
        
        # Whitespace
        if char in ' \t\r\n':
            return
        
        # Single-character tokens
        simple = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ':': TokenType.COLON,
            '?': TokenType.QUESTION,
        }
        
        if char in simple:
            self._add_token(simple[char])
            return
        
        # Multi-character operators
        if char == '*':
            if self._peek() == '*':
                self._advance()
                self._add_token(TokenType.POWER)
            else:
                self._add_token(TokenType.STAR)
            return
        
        if char == '=':
            if self._peek() == '=':
                self._advance()
                self._add_token(TokenType.EQ)
            else:
                raise LexerError(f"Unexpected '='. Did you mean '=='?", self._location())
            return
        
        if char == '!':
            if self._peek() == '=':
                self._advance()
                self._add_token(TokenType.NE)
            else:
                raise LexerError(f"Unexpected '!'. Did you mean '!=' or 'not'?", self._location())
            return
        
        if char == '<':
            if self._peek() == '=':
                self._advance()
                self._add_token(TokenType.LE)
            else:
                self._add_token(TokenType.LT)
            return
        
        if char == '>':
            if self._peek() == '=':
                self._advance()
                self._add_token(TokenType.GE)
            else:
                self._add_token(TokenType.GT)
            return
        
        # Numbers
        if char.isdigit():
            self._scan_number(char)
            return
        
        # Strings
        if char in '"\'':
            self._scan_string(char)
            return
        
        # Identifiers and keywords
        if char.isalpha() or char == '_':
            self._scan_identifier(char)
            return
        
        raise LexerError(f"Unexpected character: {char!r}", self._location())
    
    def _scan_number(self, first: str) -> None:
        """
        Scan a numeric literal.
        
        Only supports decimal integers and floats. No hex, octal, or scientific
        notation to minimize complexity and attack surface.
        """
        num_str = first
        
        while not self._at_end() and self._peek().isdigit():
            num_str += self._advance()
        
        # Decimal point
        if self._peek() == '.' and self._peek(1).isdigit():
            num_str += self._advance()  # '.'
            while not self._at_end() and self._peek().isdigit():
                num_str += self._advance()
        
        self._add_token(TokenType.NUMBER, float(num_str))
    
    def _scan_string(self, quote: str) -> None:
        """
        Scan a string literal.
        
        Supports basic escapes: \\, \n, \t, \', \"
        No Unicode escapes, no raw strings, no multi-line strings.
        """
        value = ""
        start_loc = self._location()
        
        while not self._at_end() and self._peek() != quote:
            char = self._advance()
            
            if char == '\n':
                raise LexerError("Unterminated string (newline in string)", start_loc)
            
            if char == '\\':
                if self._at_end():
                    raise LexerError("Unterminated escape sequence", self._location())
                
                escape = self._advance()
                escapes = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'"}
                
                if escape in escapes:
                    value += escapes[escape]
                else:
                    raise LexerError(f"Unknown escape sequence: \\{escape}", self._location())
            else:
                value += char
        
        if self._at_end():
            raise LexerError("Unterminated string", start_loc)
        
        self._advance()  # Closing quote
        self._add_token(TokenType.STRING, value)
    
    def _scan_identifier(self, first: str) -> None:
        """Scan identifier or keyword."""
        ident = first
        
        while not self._at_end() and (self._peek().isalnum() or self._peek() == '_'):
            ident += self._advance()
        
        # Check for keyword
        if ident in self.KEYWORDS:
            self._add_token(self.KEYWORDS[ident], ident)
        else:
            self._add_token(TokenType.IDENTIFIER, ident)


# =============================================================================
# AST Nodes
# =============================================================================

@dataclass
class ASTNode(ABC):
    """Base class for all AST nodes."""
    location: SourceLocation


@dataclass
class NumberLiteral(ASTNode):
    value: float


@dataclass
class StringLiteral(ASTNode):
    value: str


@dataclass
class BoolLiteral(ASTNode):
    value: bool


@dataclass
class NullLiteral(ASTNode):
    pass


@dataclass
class ListLiteral(ASTNode):
    elements: list[ASTNode]


@dataclass
class Identifier(ASTNode):
    name: str


@dataclass
class BinaryOp(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode


@dataclass
class Conditional(ASTNode):
    """if condition then then_expr else else_expr"""
    condition: ASTNode
    then_expr: ASTNode
    else_expr: ASTNode


@dataclass
class TernaryOp(ASTNode):
    """condition ? then_expr : else_expr"""
    condition: ASTNode
    then_expr: ASTNode
    else_expr: ASTNode


@dataclass
class FunctionCall(ASTNode):
    name: str
    arguments: list[ASTNode]


@dataclass
class IndexAccess(ASTNode):
    obj: ASTNode
    index: ASTNode


@dataclass
class PropertyAccess(ASTNode):
    obj: ASTNode
    property: str


# =============================================================================
# Parser
# =============================================================================

class Parser:
    """
    Recursive descent parser for Rune expressions.
    
    Grammar (simplified):
        expr        := ternary
        ternary     := or ('?' expr ':' expr)?
        or          := and ('or' and)*
        and         := not ('and' not)*
        not         := 'not' not | comparison
        comparison  := addition (('==' | '!=' | '<' | '>' | '<=' | '>=') addition)?
        addition    := multiply (('+' | '-') multiply)*
        multiply    := power (('*' | '/' | '%') power)*
        power       := unary ('**' power)?  # Right-associative
        unary       := '-' unary | postfix
        postfix     := primary ('[' expr ']' | '.' IDENT | '(' args ')')*
        primary     := NUMBER | STRING | TRUE | FALSE | NULL | IDENT
                     | '[' list_items ']' | '(' expr ')'
                     | 'if' expr 'then' expr 'else' expr
    """
    
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def parse(self) -> ASTNode:
        """Parse tokens into AST."""
        ast = self._parse_expr()
        
        if not self._at_end():
            raise ParseError(
                f"Unexpected token: {self._peek().type.name}",
                self._location()
            )
        
        return ast
    
    def _at_end(self) -> bool:
        return self._peek().type == TokenType.EOF
    
    def _peek(self, offset: int = 0) -> Token:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]
    
    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        if not self._at_end():
            self.pos += 1
        return token
    
    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types
    
    def _match(self, *types: TokenType) -> Token | None:
        if self._check(*types):
            return self._advance()
        return None
    
    def _expect(self, token_type: TokenType, message: str) -> Token:
        if not self._check(token_type):
            raise ParseError(message, self._location())
        return self._advance()
    
    def _location(self) -> SourceLocation:
        token = self._peek()
        return SourceLocation(token.line, token.column)
    
    # === Grammar Rules ===
    
    def _parse_expr(self) -> ASTNode:
        return self._parse_ternary()
    
    def _parse_ternary(self) -> ASTNode:
        expr = self._parse_or()
        
        if self._match(TokenType.QUESTION):
            then_expr = self._parse_expr()
            self._expect(TokenType.COLON, "Expected ':' in ternary expression")
            else_expr = self._parse_expr()
            return TernaryOp(
                location=expr.location,
                condition=expr,
                then_expr=then_expr,
                else_expr=else_expr
            )
        
        return expr
    
    def _parse_or(self) -> ASTNode:
        left = self._parse_and()
        
        while self._match(TokenType.OR):
            right = self._parse_and()
            left = BinaryOp(left.location, left, 'or', right)
        
        return left
    
    def _parse_and(self) -> ASTNode:
        left = self._parse_not()
        
        while self._match(TokenType.AND):
            right = self._parse_not()
            left = BinaryOp(left.location, left, 'and', right)
        
        return left
    
    def _parse_not(self) -> ASTNode:
        if self._match(TokenType.NOT):
            loc = self._location()
            operand = self._parse_not()
            return UnaryOp(loc, 'not', operand)
        
        return self._parse_comparison()
    
    def _parse_comparison(self) -> ASTNode:
        left = self._parse_addition()
        
        ops = {
            TokenType.EQ: '==',
            TokenType.NE: '!=',
            TokenType.LT: '<',
            TokenType.GT: '>',
            TokenType.LE: '<=',
            TokenType.GE: '>=',
        }
        
        for token_type, op_str in ops.items():
            if self._match(token_type):
                right = self._parse_addition()
                return BinaryOp(left.location, left, op_str, right)
        
        return left
    
    def _parse_addition(self) -> ASTNode:
        left = self._parse_multiply()
        
        while True:
            if self._match(TokenType.PLUS):
                right = self._parse_multiply()
                left = BinaryOp(left.location, left, '+', right)
            elif self._match(TokenType.MINUS):
                right = self._parse_multiply()
                left = BinaryOp(left.location, left, '-', right)
            else:
                break
        
        return left
    
    def _parse_multiply(self) -> ASTNode:
        left = self._parse_power()
        
        while True:
            if self._match(TokenType.STAR):
                right = self._parse_power()
                left = BinaryOp(left.location, left, '*', right)
            elif self._match(TokenType.SLASH):
                right = self._parse_power()
                left = BinaryOp(left.location, left, '/', right)
            elif self._match(TokenType.PERCENT):
                right = self._parse_power()
                left = BinaryOp(left.location, left, '%', right)
            else:
                break
        
        return left
    
    def _parse_power(self) -> ASTNode:
        """Power is right-associative: 2 ** 3 ** 2 = 2 ** (3 ** 2)"""
        left = self._parse_unary()
        
        if self._match(TokenType.POWER):
            right = self._parse_power()  # Recursive for right-associativity
            return BinaryOp(left.location, left, '**', right)
        
        return left
    
    def _parse_unary(self) -> ASTNode:
        if self._match(TokenType.MINUS):
            loc = self._location()
            operand = self._parse_unary()
            return UnaryOp(loc, '-', operand)
        
        return self._parse_postfix()
    
    def _parse_postfix(self) -> ASTNode:
        expr = self._parse_primary()
        
        while True:
            if self._match(TokenType.LBRACKET):
                index = self._parse_expr()
                self._expect(TokenType.RBRACKET, "Expected ']'")
                expr = IndexAccess(expr.location, expr, index)
            
            elif self._match(TokenType.DOT):
                name_token = self._expect(TokenType.IDENTIFIER, "Expected property name")
                expr = PropertyAccess(expr.location, expr, name_token.value)
            
            elif self._match(TokenType.LPAREN):
                # Function call - but the expr must be an identifier
                if isinstance(expr, Identifier):
                    args = self._parse_args()
                    self._expect(TokenType.RPAREN, "Expected ')'")
                    expr = FunctionCall(expr.location, expr.name, args)
                else:
                    raise ParseError("Only named functions can be called", expr.location)
            
            else:
                break
        
        return expr
    
    def _parse_args(self) -> list[ASTNode]:
        """Parse function arguments."""
        args = []
        
        if not self._check(TokenType.RPAREN):
            args.append(self._parse_expr())
            
            while self._match(TokenType.COMMA):
                args.append(self._parse_expr())
        
        return args
    
    def _parse_primary(self) -> ASTNode:
        loc = self._location()
        
        # Literals
        if self._check(TokenType.NUMBER):
            return NumberLiteral(loc, self._advance().value)
        
        if self._check(TokenType.STRING):
            return StringLiteral(loc, self._advance().value)
        
        if self._match(TokenType.TRUE):
            return BoolLiteral(loc, True)
        
        if self._match(TokenType.FALSE):
            return BoolLiteral(loc, False)
        
        if self._match(TokenType.NULL):
            return NullLiteral(loc)
        
        # Identifier
        if self._check(TokenType.IDENTIFIER):
            return Identifier(loc, self._advance().value)
        
        # List literal
        if self._match(TokenType.LBRACKET):
            elements = []
            
            if not self._check(TokenType.RBRACKET):
                elements.append(self._parse_expr())
                
                while self._match(TokenType.COMMA):
                    if self._check(TokenType.RBRACKET):
                        break  # Trailing comma
                    elements.append(self._parse_expr())
            
            self._expect(TokenType.RBRACKET, "Expected ']'")
            return ListLiteral(loc, elements)
        
        # Parenthesized expression
        if self._match(TokenType.LPAREN):
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN, "Expected ')'")
            return expr
        
        # If-then-else
        if self._match(TokenType.IF):
            condition = self._parse_expr()
            self._expect(TokenType.THEN, "Expected 'then'")
            then_expr = self._parse_expr()
            self._expect(TokenType.ELSE, "Expected 'else'")
            else_expr = self._parse_expr()
            return Conditional(loc, condition, then_expr, else_expr)
        
        raise ParseError(f"Unexpected token: {self._peek().type.name}", loc)


# =============================================================================
# Execution Context
# =============================================================================

@dataclass
class FunctionDef:
    """Definition of a callable function."""
    name: str
    impl: Callable[..., Any]
    signature: TypeSignature
    fuel_cost: int = 1  # Base cost per call
    
    def __call__(self, *args) -> Any:
        return self.impl(*args)


@dataclass
class ExecutionLimits:
    """
    Resource limits for execution.
    
    Fuel is the key concept: every operation consumes fuel, and execution
    halts when fuel reaches zero. This provides CPU limiting without
    relying on OS-level mechanisms like signals.
    
    Default values are tuned for typical expression evaluation:
    - 10,000 fuel handles complex expressions but stops infinite work
    - Depth of 50 prevents deep recursion without being restrictive
    """
    max_fuel: int = 10_000
    max_depth: int = 50
    max_string_length: int = 1_000_000
    max_list_length: int = 100_000


@dataclass
class ExecutionContext:
    """
    Runtime context for expression evaluation.
    
    Immutable during execution - all state is passed explicitly.
    This makes the interpreter deterministic and thread-safe.
    """
    variables: dict[str, Any]
    functions: dict[str, FunctionDef]
    limits: ExecutionLimits
    
    # Mutable execution state
    fuel_remaining: int = field(default=0)
    current_depth: int = field(default=0)
    
    def __post_init__(self):
        self.fuel_remaining = self.limits.max_fuel
    
    def consume_fuel(self, amount: int, location: SourceLocation | None = None) -> None:
        """
        Consume fuel for an operation.
        
        Raises FuelExhaustedError if insufficient fuel remains.
        """
        if amount > self.fuel_remaining:
            raise FuelExhaustedError(
                self.limits.max_fuel - self.fuel_remaining + amount,
                self.limits.max_fuel
            )
        self.fuel_remaining -= amount
    
    def enter_call(self) -> None:
        """Enter a function call, checking depth limit."""
        self.current_depth += 1
        if self.current_depth > self.limits.max_depth:
            raise DepthExceededError(self.current_depth, self.limits.max_depth)
    
    def exit_call(self) -> None:
        """Exit a function call."""
        self.current_depth -= 1
    
    def get_variable(self, name: str) -> Any:
        """Get a variable value."""
        if name not in self.variables:
            return None  # Unknown variables are null
        return self.variables[name]
    
    def get_function(self, name: str) -> FunctionDef | None:
        """Get a function definition."""
        return self.functions.get(name)


# =============================================================================
# Evaluator
# =============================================================================

class Evaluator:
    """
    Evaluates AST nodes to produce values.
    
    The evaluator is designed for safety:
    - Every operation consumes fuel
    - String/list operations cost proportional to size
    - No unbounded recursion or iteration
    - All errors include source location
    """
    
    def evaluate(self, node: ASTNode, ctx: ExecutionContext) -> Any:
        """Evaluate an AST node in context."""
        # Base fuel cost for visiting any node
        ctx.consume_fuel(1, node.location)
        
        if isinstance(node, NumberLiteral):
            return node.value
        
        if isinstance(node, StringLiteral):
            return node.value
        
        if isinstance(node, BoolLiteral):
            return node.value
        
        if isinstance(node, NullLiteral):
            return None
        
        if isinstance(node, ListLiteral):
            return self._eval_list(node, ctx)
        
        if isinstance(node, Identifier):
            return ctx.get_variable(node.name)
        
        if isinstance(node, BinaryOp):
            return self._eval_binary(node, ctx)
        
        if isinstance(node, UnaryOp):
            return self._eval_unary(node, ctx)
        
        if isinstance(node, Conditional):
            return self._eval_conditional(node, ctx)
        
        if isinstance(node, TernaryOp):
            return self._eval_ternary(node, ctx)
        
        if isinstance(node, FunctionCall):
            return self._eval_call(node, ctx)
        
        if isinstance(node, IndexAccess):
            return self._eval_index(node, ctx)
        
        if isinstance(node, PropertyAccess):
            return self._eval_property(node, ctx)
        
        raise RuntimeError(f"Unknown node type: {type(node).__name__}", node.location)
    
    def _eval_list(self, node: ListLiteral, ctx: ExecutionContext) -> list:
        """Evaluate list literal with size limits."""
        if len(node.elements) > ctx.limits.max_list_length:
            raise RuntimeError(
                f"List exceeds maximum length ({len(node.elements)} > {ctx.limits.max_list_length})",
                node.location
            )
        
        # Cost proportional to list size
        ctx.consume_fuel(len(node.elements), node.location)
        
        return [self.evaluate(elem, ctx) for elem in node.elements]
    
    def _eval_binary(self, node: BinaryOp, ctx: ExecutionContext) -> Any:
        """Evaluate binary operation."""
        op = node.op
        
        # Short-circuit evaluation for logical operators
        if op == 'and':
            left = self.evaluate(node.left, ctx)
            if not self._is_truthy(left):
                return left
            return self.evaluate(node.right, ctx)
        
        if op == 'or':
            left = self.evaluate(node.left, ctx)
            if self._is_truthy(left):
                return left
            return self.evaluate(node.right, ctx)
        
        left = self.evaluate(node.left, ctx)
        right = self.evaluate(node.right, ctx)
        
        # Comparison operators - check first before arithmetic
        comparison_ops = {
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '>': operator.gt,
            '<=': operator.le,
            '>=': operator.ge,
        }
        
        if op in comparison_ops:
            # Type-safe comparison: different types are not equal
            if op in ('==', '!='):
                # Check type compatibility
                left_type = type(left)
                right_type = type(right)
                same_type = left_type == right_type
                
                # Allow int/float comparison but NOT bool/int
                if isinstance(left, bool) or isinstance(right, bool):
                    # Booleans only compare with booleans
                    same_type = isinstance(left, bool) and isinstance(right, bool)
                elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    same_type = True
                
                if op == '==':
                    return same_type and left == right
                else:  # !=
                    return not same_type or left != right
            
            try:
                return comparison_ops[op](left, right)
            except TypeError:
                raise RuntimeError(
                    f"Cannot compare {type(left).__name__} and {type(right).__name__}",
                    node.location
                )
        
        # String concatenation (only if one is actually a string)
        if op == '+' and isinstance(left, str):
            right_str = "null" if right is None else str(right)
            result = left + right_str
            if len(result) > ctx.limits.max_string_length:
                raise RuntimeError(
                    f"String exceeds maximum length ({len(result)} > {ctx.limits.max_string_length})",
                    node.location
                )
            ctx.consume_fuel(len(result) // 100 + 1, node.location)
            return result
        
        if op == '+' and isinstance(right, str):
            left_str = "null" if left is None else str(left)
            result = left_str + right
            if len(result) > ctx.limits.max_string_length:
                raise RuntimeError(
                    f"String exceeds maximum length ({len(result)} > {ctx.limits.max_string_length})",
                    node.location
                )
            ctx.consume_fuel(len(result) // 100 + 1, node.location)
            return result
        
        # Null arithmetic produces error
        if left is None or right is None:
            raise RuntimeError(
                f"Cannot perform arithmetic on null value",
                node.location
            )
        
        # Arithmetic
        ops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '%': operator.mod,
            '**': operator.pow,
        }
        
        if op == '/':
            if right == 0:
                raise RuntimeError("Division by zero", node.location)
            return left / right
        
        if op in ops:
            try:
                result = ops[op](left, right)
                # Overflow protection for exponentiation
                if op == '**':
                    if isinstance(result, float) and (math.isinf(result) or math.isnan(result)):
                        raise RuntimeError("Numeric overflow", node.location)
                return result
            except (TypeError, ValueError) as e:
                raise RuntimeError(str(e), node.location)
            except OverflowError:
                raise RuntimeError("Numeric overflow", node.location)
        
        raise RuntimeError(f"Unknown operator: {op}", node.location)
    
    def _eval_unary(self, node: UnaryOp, ctx: ExecutionContext) -> Any:
        """Evaluate unary operation."""
        operand = self.evaluate(node.operand, ctx)
        
        if node.op == '-':
            if not isinstance(operand, (int, float)):
                raise RuntimeError(
                    f"Cannot negate {type(operand).__name__}",
                    node.location
                )
            return -operand
        
        if node.op == 'not':
            return not self._is_truthy(operand)
        
        raise RuntimeError(f"Unknown unary operator: {node.op}", node.location)
    
    def _eval_conditional(self, node: Conditional, ctx: ExecutionContext) -> Any:
        """Evaluate if-then-else."""
        condition = self.evaluate(node.condition, ctx)
        
        if self._is_truthy(condition):
            return self.evaluate(node.then_expr, ctx)
        else:
            return self.evaluate(node.else_expr, ctx)
    
    def _eval_ternary(self, node: TernaryOp, ctx: ExecutionContext) -> Any:
        """Evaluate ternary conditional."""
        condition = self.evaluate(node.condition, ctx)
        
        if self._is_truthy(condition):
            return self.evaluate(node.then_expr, ctx)
        else:
            return self.evaluate(node.else_expr, ctx)
    
    def _eval_call(self, node: FunctionCall, ctx: ExecutionContext) -> Any:
        """Evaluate function call."""
        func = ctx.get_function(node.name)
        
        if func is None:
            raise RuntimeError(f"Unknown function: {node.name}", node.location)
        
        # Track call depth BEFORE evaluating arguments
        # This ensures nested calls properly count depth
        ctx.enter_call()
        
        try:
            # Evaluate arguments
            args = [self.evaluate(arg, ctx) for arg in node.arguments]
            
            # Check arity
            sig = func.signature
            if sig.variadic:
                if len(args) < len(sig.param_types) - 1:
                    raise RuntimeError(
                        f"Function {node.name} requires at least {len(sig.param_types) - 1} arguments, got {len(args)}",
                        node.location
                    )
            else:
                if len(args) != len(sig.param_types):
                    raise RuntimeError(
                        f"Function {node.name} requires {len(sig.param_types)} arguments, got {len(args)}",
                        node.location
                    )
            
            # Consume fuel for function call
            ctx.consume_fuel(func.fuel_cost, node.location)
            
            result = func(*args)
            
            # Validate result against limits
            if isinstance(result, str) and len(result) > ctx.limits.max_string_length:
                raise RuntimeError(
                    f"Function result exceeds maximum string length",
                    node.location
                )
            if isinstance(result, list) and len(result) > ctx.limits.max_list_length:
                raise RuntimeError(
                    f"Function result exceeds maximum list length",
                    node.location
                )
            
            return result
        except RuneError:
            raise
        except Exception as e:
            raise RuntimeError(f"Function {node.name} failed: {e}", node.location)
        finally:
            ctx.exit_call()
    
    def _eval_index(self, node: IndexAccess, ctx: ExecutionContext) -> Any:
        """Evaluate index access (list[i] or string[i])."""
        obj = self.evaluate(node.obj, ctx)
        index = self.evaluate(node.index, ctx)
        
        if isinstance(obj, list):
            if not isinstance(index, (int, float)):
                raise RuntimeError(
                    f"List index must be a number, got {type(index).__name__}",
                    node.location
                )
            idx = int(index)
            if idx < 0 or idx >= len(obj):
                return None  # Out of bounds returns null
            return obj[idx]
        
        if isinstance(obj, str):
            if not isinstance(index, (int, float)):
                raise RuntimeError(
                    f"String index must be a number, got {type(index).__name__}",
                    node.location
                )
            idx = int(index)
            if idx < 0 or idx >= len(obj):
                return None
            return obj[idx]
        
        if isinstance(obj, dict):
            return obj.get(index)
        
        raise RuntimeError(
            f"Cannot index into {type(obj).__name__}",
            node.location
        )
    
    def _eval_property(self, node: PropertyAccess, ctx: ExecutionContext) -> Any:
        """Evaluate property access (obj.prop)."""
        obj = self.evaluate(node.obj, ctx)
        
        if isinstance(obj, dict):
            return obj.get(node.property)
        
        # Built-in properties
        if node.property == 'length':
            if isinstance(obj, (str, list)):
                return len(obj)
        
        return None
    
    def _is_truthy(self, value: Any) -> bool:
        """Determine if a value is truthy."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        return True


# =============================================================================
# Main Engine
# =============================================================================

class Rune:
    """
    Main interface for the Rune expression engine.
    
    Usage:
        engine = Rune()
        
        # Register custom functions
        engine.register_function("double", lambda x: x * 2, [RuType.NUMBER], RuType.NUMBER)
        
        # Evaluate with variables
        result = engine.evaluate("price * quantity * (1 - discount)", {
            "price": 100,
            "quantity": 5,
            "discount": 0.1
        })
    """
    
    def __init__(self, limits: ExecutionLimits | None = None):
        self.limits = limits or ExecutionLimits()
        self.functions: dict[str, FunctionDef] = {}
        self._register_builtins()
    
    def _register_builtins(self) -> None:
        """Register built-in functions."""
        # Math functions
        self.register_function("abs", abs, [RuType.NUMBER], RuType.NUMBER)
        self.register_function("floor", math.floor, [RuType.NUMBER], RuType.NUMBER)
        self.register_function("ceil", math.ceil, [RuType.NUMBER], RuType.NUMBER)
        self.register_function("round", round, [RuType.NUMBER], RuType.NUMBER)
        self.register_function("sqrt", math.sqrt, [RuType.NUMBER], RuType.NUMBER)
        self.register_function("min", min, [RuType.NUMBER, RuType.NUMBER], RuType.NUMBER, variadic=True)
        self.register_function("max", max, [RuType.NUMBER, RuType.NUMBER], RuType.NUMBER, variadic=True)
        
        # String functions
        self.register_function("len", len, [RuType.ANY], RuType.NUMBER)
        self.register_function("upper", str.upper, [RuType.STRING], RuType.STRING)
        self.register_function("lower", str.lower, [RuType.STRING], RuType.STRING)
        self.register_function("trim", str.strip, [RuType.STRING], RuType.STRING)
        self.register_function("contains", lambda s, sub: sub in s, [RuType.STRING, RuType.STRING], RuType.BOOLEAN)
        self.register_function("starts_with", str.startswith, [RuType.STRING, RuType.STRING], RuType.BOOLEAN)
        self.register_function("ends_with", str.endswith, [RuType.STRING, RuType.STRING], RuType.BOOLEAN)
        self.register_function("substring", lambda s, start, end=None: s[int(start):int(end) if end else None], 
                              [RuType.STRING, RuType.NUMBER, RuType.NUMBER], RuType.STRING)
        
        # List functions (these are the iteration primitives - no loops needed)
        self.register_function("first", lambda lst: lst[0] if lst else None, [RuType.LIST], RuType.ANY)
        self.register_function("last", lambda lst: lst[-1] if lst else None, [RuType.LIST], RuType.ANY)
        self.register_function("sum", sum, [RuType.LIST], RuType.NUMBER, fuel_cost=10)
        self.register_function("avg", lambda lst: sum(lst) / len(lst) if lst else 0, [RuType.LIST], RuType.NUMBER, fuel_cost=10)
        self.register_function("count", len, [RuType.LIST], RuType.NUMBER)
        self.register_function("reverse", lambda lst: list(reversed(lst)), [RuType.LIST], RuType.LIST, fuel_cost=5)
        self.register_function("sort", sorted, [RuType.LIST], RuType.LIST, fuel_cost=20)
        self.register_function("unique", lambda lst: list(dict.fromkeys(lst)), [RuType.LIST], RuType.LIST, fuel_cost=10)
        self.register_function("concat", lambda a, b: a + b, [RuType.LIST, RuType.LIST], RuType.LIST, fuel_cost=5)
        self.register_function("slice", lambda lst, start, end: lst[int(start):int(end)], 
                              [RuType.LIST, RuType.NUMBER, RuType.NUMBER], RuType.LIST)
        self.register_function("index_of", lambda lst, val: lst.index(val) if val in lst else -1,
                              [RuType.LIST, RuType.ANY], RuType.NUMBER)
        self.register_function("includes", lambda lst, val: val in lst, [RuType.LIST, RuType.ANY], RuType.BOOLEAN)
        
        # Type conversion
        def smart_str(x):
            if isinstance(x, float) and x == int(x):
                return str(int(x))
            return str(x)
        
        self.register_function("str", smart_str, [RuType.ANY], RuType.STRING)
        self.register_function("num", lambda x: float(x) if x is not None else 0, [RuType.ANY], RuType.NUMBER)
        self.register_function("bool", lambda x: bool(x), [RuType.ANY], RuType.BOOLEAN)
        
        # Utility
        self.register_function("default", lambda val, default: val if val is not None else default, 
                              [RuType.ANY, RuType.ANY], RuType.ANY)
        self.register_function("coalesce", lambda *args: next((a for a in args if a is not None), None),
                              [RuType.ANY], RuType.ANY, variadic=True)
    
    def register_function(
        self,
        name: str,
        impl: Callable[..., Any],
        param_types: list[RuType],
        return_type: RuType,
        variadic: bool = False,
        fuel_cost: int = 1
    ) -> None:
        """
        Register a custom function.
        
        Args:
            name: Function name (must be valid identifier)
            impl: Python callable implementing the function
            param_types: List of parameter types
            return_type: Return type
            variadic: If True, last param type can repeat
            fuel_cost: Fuel consumed per call
        """
        if not name.isidentifier():
            raise ValueError(f"Invalid function name: {name}")
        
        self.functions[name] = FunctionDef(
            name=name,
            impl=impl,
            signature=TypeSignature(tuple(param_types), return_type, variadic),
            fuel_cost=fuel_cost
        )
    
    def compile(self, expression: str) -> 'CompiledExpression':
        """
        Compile an expression for repeated evaluation.
        
        Returns a CompiledExpression that can be evaluated multiple times
        with different variables, avoiding re-parsing overhead.
        """
        lexer = Lexer(expression)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        return CompiledExpression(ast, self.functions, self.limits)
    
    def evaluate(
        self,
        expression: str,
        variables: dict[str, Any] | None = None
    ) -> Any:
        """
        Parse and evaluate an expression.
        
        Args:
            expression: The expression string
            variables: Variables available in the expression
        
        Returns:
            The result of evaluation
        
        Raises:
            LexerError: Invalid syntax
            ParseError: Invalid grammar
            RuntimeError: Evaluation failure
            FuelExhaustedError: Execution limit exceeded
        """
        compiled = self.compile(expression)
        return compiled.evaluate(variables)


class CompiledExpression:
    """
    A pre-parsed expression ready for evaluation.
    
    Use this when you need to evaluate the same expression multiple times
    with different variables.
    """
    
    def __init__(
        self,
        ast: ASTNode,
        functions: dict[str, FunctionDef],
        limits: ExecutionLimits
    ):
        self.ast = ast
        self.functions = functions
        self.limits = limits
        self._evaluator = Evaluator()
    
    def evaluate(self, variables: dict[str, Any] | None = None) -> Any:
        """Evaluate with given variables."""
        ctx = ExecutionContext(
            variables=variables or {},
            functions=self.functions,
            limits=self.limits
        )
        
        return self._evaluator.evaluate(self.ast, ctx)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main
    'Rune',
    'CompiledExpression',
    
    # Types
    'RuType',
    'TypeSignature',
    'ExecutionLimits',
    
    # Errors
    'RuneError',
    'LexerError',
    'ParseError',
    'TypeError',
    'RuntimeError',
    'FuelExhaustedError',
    'DepthExceededError',
]
