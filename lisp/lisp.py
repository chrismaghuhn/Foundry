"""
Lisp: A Lisp Interpreter from Scratch

A complete Lisp interpreter with REPL, macros, and tail call optimization.
Understand why "Code is Data" changed everything.

Historical Background:

    Lisp was invented by John McCarthy in 1958, making it the second
    oldest high-level programming language (after Fortran). It introduced:
    
    - Homoiconicity: Code IS data (programs are lists)
    - Garbage Collection: First language to have it
    - REPL: Interactive development
    - Recursion: As a primary control structure
    - Conditional Expressions: if-then-else
    - First-class Functions: Functions as values

The Key Insight:

    In Lisp, the expression (+ 1 2) is BOTH:
    - A program that adds 1 and 2
    - A list containing +, 1, and 2
    
    This means programs can manipulate programs as easily as data.
    This is the foundation of macros - code that writes code.

Syntax (S-Expressions):

    Atoms:
        42          ; Number
        3.14        ; Float
        "hello"     ; String
        foo         ; Symbol
        #t, #f      ; Boolean
        nil         ; Empty list / false
    
    Lists:
        (+ 1 2)             ; Function call
        (define x 10)       ; Definition
        (lambda (x) (* x x)) ; Anonymous function
        '(1 2 3)            ; Quoted list (data, not code)

Special Forms:

    (define name value)      ; Define a variable
    (define (name args) body) ; Define a function
    (lambda (args) body)     ; Anonymous function
    (if test then else)      ; Conditional
    (quote expr) or 'expr    ; Prevent evaluation
    (let ((x 1) (y 2)) body) ; Local bindings
    (begin expr1 expr2 ...)  ; Sequence
    (set! name value)        ; Mutation

Built-in Functions:

    Arithmetic: +, -, *, /, mod, abs
    Comparison: =, <, >, <=, >=, eq?
    Lists: cons, car, cdr, list, length, append, null?
    Logic: and, or, not
    Type checks: number?, string?, symbol?, list?, procedure?
    I/O: display, newline

Usage:
    >>> from lisp import Lisp, repl
    >>> 
    >>> lisp = Lisp()
    >>> lisp.eval("(+ 1 2 3)")  # 6
    >>> lisp.eval("(define (square x) (* x x))")
    >>> lisp.eval("(square 5)")  # 25
    >>> 
    >>> # Start interactive REPL
    >>> repl()

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Iterator
from abc import ABC, abstractmethod
import re
import math
import operator


# =============================================================================
# Lisp Values
# =============================================================================

class LispValue(ABC):
    """Base class for all Lisp values."""
    
    @abstractmethod
    def to_string(self) -> str:
        """Convert to Lisp-readable string."""
        pass
    
    def __str__(self) -> str:
        return self.to_string()


@dataclass(frozen=True)
class LispNumber(LispValue):
    """A number (integer or float)."""
    value: Union[int, float]
    
    def to_string(self) -> str:
        if isinstance(self.value, float) and self.value.is_integer():
            return str(int(self.value))
        return str(self.value)


@dataclass(frozen=True)
class LispString(LispValue):
    """A string."""
    value: str
    
    def to_string(self) -> str:
        return f'"{self.value}"'


@dataclass(frozen=True)
class LispSymbol(LispValue):
    """A symbol (identifier)."""
    name: str
    
    def to_string(self) -> str:
        return self.name


@dataclass(frozen=True)
class LispBool(LispValue):
    """A boolean."""
    value: bool
    
    def to_string(self) -> str:
        return "#t" if self.value else "#f"


class LispNil(LispValue):
    """The nil value (empty list, false in some contexts)."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def to_string(self) -> str:
        return "nil"
    
    def __bool__(self) -> bool:
        return False


NIL = LispNil()


@dataclass
class LispList(LispValue):
    """A list (the fundamental Lisp data structure)."""
    elements: List[LispValue] = field(default_factory=list)
    
    def to_string(self) -> str:
        if not self.elements:
            return "()"
        inner = " ".join(elem.to_string() for elem in self.elements)
        return f"({inner})"
    
    def __len__(self) -> int:
        return len(self.elements)
    
    def __getitem__(self, index: int) -> LispValue:
        return self.elements[index]
    
    def __iter__(self) -> Iterator[LispValue]:
        return iter(self.elements)
    
    def __bool__(self) -> bool:
        return len(self.elements) > 0


@dataclass
class LispProcedure(LispValue):
    """A user-defined procedure (lambda)."""
    params: List[str]
    body: LispValue
    env: 'Environment'
    name: Optional[str] = None
    
    def to_string(self) -> str:
        name = self.name or "lambda"
        params = " ".join(self.params)
        return f"#<procedure:{name} ({params})>"


@dataclass
class LispBuiltin(LispValue):
    """A built-in procedure."""
    name: str
    func: Callable
    
    def to_string(self) -> str:
        return f"#<builtin:{self.name}>"


@dataclass
class LispMacro(LispValue):
    """A macro (code that generates code)."""
    params: List[str]
    body: LispValue
    env: 'Environment'
    name: str
    
    def to_string(self) -> str:
        return f"#<macro:{self.name}>"


# =============================================================================
# Environment
# =============================================================================

class Environment:
    """
    An environment maps symbols to values.
    
    Environments form a chain - each environment has a parent.
    Variable lookup walks up the chain until found.
    
    This implements lexical scoping.
    """
    
    def __init__(self, parent: Optional['Environment'] = None):
        self.bindings: Dict[str, LispValue] = {}
        self.parent = parent
    
    def define(self, name: str, value: LispValue) -> None:
        """Define a new binding in this environment."""
        self.bindings[name] = value
    
    def lookup(self, name: str) -> LispValue:
        """Look up a binding, walking up the chain."""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise LispError(f"Undefined variable: {name}")
    
    def set(self, name: str, value: LispValue) -> None:
        """Set an existing binding (mutation)."""
        if name in self.bindings:
            self.bindings[name] = value
        elif self.parent is not None:
            self.parent.set(name, value)
        else:
            raise LispError(f"Cannot set undefined variable: {name}")
    
    def extend(self, params: List[str], args: List[LispValue]) -> 'Environment':
        """Create a new environment extending this one with param bindings."""
        if len(params) != len(args):
            raise LispError(f"Expected {len(params)} arguments, got {len(args)}")
        
        new_env = Environment(parent=self)
        for param, arg in zip(params, args):
            new_env.define(param, arg)
        return new_env


# =============================================================================
# Errors
# =============================================================================

class LispError(Exception):
    """Base error for Lisp operations."""
    pass


class ParseError(LispError):
    """Error during parsing."""
    pass


class EvalError(LispError):
    """Error during evaluation."""
    pass


# =============================================================================
# Lexer
# =============================================================================

class Token:
    """A token from the lexer."""
    pass


@dataclass
class TokenLParen(Token):
    pass


@dataclass
class TokenRParen(Token):
    pass


@dataclass
class TokenQuote(Token):
    pass


@dataclass
class TokenQuasiquote(Token):
    pass


@dataclass
class TokenUnquote(Token):
    pass


@dataclass 
class TokenUnquoteSplicing(Token):
    pass


@dataclass
class TokenNumber(Token):
    value: Union[int, float]


@dataclass
class TokenString(Token):
    value: str


@dataclass
class TokenSymbol(Token):
    name: str


@dataclass
class TokenBool(Token):
    value: bool


class Lexer:
    """
    Tokenizer for Lisp S-expressions.
    
    Handles:
    - Parentheses: ( )
    - Numbers: 42, 3.14, -17
    - Strings: "hello"
    - Symbols: foo, +, <=
    - Booleans: #t, #f
    - Quote: '
    - Quasiquote: `, ,, ,@
    """
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
    
    def peek(self) -> Optional[str]:
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def advance(self) -> str:
        char = self.source[self.pos]
        self.pos += 1
        return char
    
    def skip_whitespace_and_comments(self) -> None:
        while self.pos < len(self.source):
            char = self.source[self.pos]
            if char.isspace():
                self.pos += 1
            elif char == ';':
                # Skip comment until end of line
                while self.pos < len(self.source) and self.source[self.pos] != '\n':
                    self.pos += 1
            else:
                break
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source."""
        tokens = []
        
        while True:
            self.skip_whitespace_and_comments()
            
            if self.pos >= len(self.source):
                break
            
            char = self.peek()
            
            if char == '(':
                self.advance()
                tokens.append(TokenLParen())
            
            elif char == ')':
                self.advance()
                tokens.append(TokenRParen())
            
            elif char == "'":
                self.advance()
                tokens.append(TokenQuote())
            
            elif char == '`':
                self.advance()
                tokens.append(TokenQuasiquote())
            
            elif char == ',':
                self.advance()
                if self.peek() == '@':
                    self.advance()
                    tokens.append(TokenUnquoteSplicing())
                else:
                    tokens.append(TokenUnquote())
            
            elif char == '"':
                tokens.append(self._read_string())
            
            elif char == '#':
                tokens.append(self._read_hash())
            
            elif char.isdigit() or (char == '-' and self._peek_ahead_is_digit()):
                tokens.append(self._read_number())
            
            else:
                tokens.append(self._read_symbol())
        
        return tokens
    
    def _peek_ahead_is_digit(self) -> bool:
        if self.pos + 1 >= len(self.source):
            return False
        return self.source[self.pos + 1].isdigit()
    
    def _read_string(self) -> TokenString:
        self.advance()  # Skip opening "
        chars = []
        
        while self.pos < len(self.source):
            char = self.advance()
            
            if char == '"':
                return TokenString(''.join(chars))
            
            if char == '\\':
                if self.pos >= len(self.source):
                    raise ParseError("Unexpected end of string")
                escaped = self.advance()
                if escaped == 'n':
                    chars.append('\n')
                elif escaped == 't':
                    chars.append('\t')
                elif escaped == '\\':
                    chars.append('\\')
                elif escaped == '"':
                    chars.append('"')
                else:
                    chars.append(escaped)
            else:
                chars.append(char)
        
        raise ParseError("Unterminated string")
    
    def _read_hash(self) -> Token:
        self.advance()  # Skip #
        
        if self.pos >= len(self.source):
            raise ParseError("Unexpected end after #")
        
        char = self.advance()
        
        if char == 't':
            return TokenBool(True)
        elif char == 'f':
            return TokenBool(False)
        else:
            raise ParseError(f"Unknown # sequence: #{char}")
    
    def _read_number(self) -> TokenNumber:
        chars = []
        
        # Handle negative
        if self.peek() == '-':
            chars.append(self.advance())
        
        # Integer part
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            chars.append(self.advance())
        
        # Decimal part
        if self.pos < len(self.source) and self.source[self.pos] == '.':
            chars.append(self.advance())
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                chars.append(self.advance())
        
        num_str = ''.join(chars)
        
        if '.' in num_str:
            return TokenNumber(float(num_str))
        else:
            return TokenNumber(int(num_str))
    
    def _read_symbol(self) -> TokenSymbol:
        chars = []
        
        while self.pos < len(self.source):
            char = self.source[self.pos]
            
            if char.isspace() or char in '()";':
                break
            
            chars.append(self.advance())
        
        return TokenSymbol(''.join(chars))


# =============================================================================
# Parser
# =============================================================================

class Parser:
    """
    Parser for Lisp S-expressions.
    
    Converts tokens to Lisp values (AST).
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def peek(self) -> Optional[Token]:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]
    
    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token
    
    def parse(self) -> LispValue:
        """Parse a single expression."""
        token = self.peek()
        
        if token is None:
            raise ParseError("Unexpected end of input")
        
        if isinstance(token, TokenLParen):
            return self._parse_list()
        
        if isinstance(token, TokenQuote):
            self.advance()
            return LispList([LispSymbol("quote"), self.parse()])
        
        if isinstance(token, TokenQuasiquote):
            self.advance()
            return LispList([LispSymbol("quasiquote"), self.parse()])
        
        if isinstance(token, TokenUnquote):
            self.advance()
            return LispList([LispSymbol("unquote"), self.parse()])
        
        if isinstance(token, TokenUnquoteSplicing):
            self.advance()
            return LispList([LispSymbol("unquote-splicing"), self.parse()])
        
        return self._parse_atom()
    
    def _parse_list(self) -> LispList:
        self.advance()  # Skip (
        
        elements = []
        
        while True:
            token = self.peek()
            
            if token is None:
                raise ParseError("Unexpected end of list")
            
            if isinstance(token, TokenRParen):
                self.advance()
                return LispList(elements)
            
            elements.append(self.parse())
    
    def _parse_atom(self) -> LispValue:
        token = self.advance()
        
        if isinstance(token, TokenNumber):
            return LispNumber(token.value)
        
        if isinstance(token, TokenString):
            return LispString(token.value)
        
        if isinstance(token, TokenSymbol):
            if token.name == "nil":
                return NIL
            return LispSymbol(token.name)
        
        if isinstance(token, TokenBool):
            return LispBool(token.value)
        
        raise ParseError(f"Unexpected token: {token}")
    
    def parse_all(self) -> List[LispValue]:
        """Parse all expressions in the token stream."""
        exprs = []
        while self.pos < len(self.tokens):
            exprs.append(self.parse())
        return exprs


def parse(source: str) -> LispValue:
    """Parse a single Lisp expression."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    if not tokens:
        raise ParseError("Empty input")
    
    parser = Parser(tokens)
    return parser.parse()


def parse_all(source: str) -> List[LispValue]:
    """Parse multiple Lisp expressions."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    if not tokens:
        return []
    
    parser = Parser(tokens)
    return parser.parse_all()


# =============================================================================
# Evaluator
# =============================================================================

class Evaluator:
    """
    The Lisp evaluator (interpreter).
    
    Implements:
    - Special forms (if, define, lambda, etc.)
    - Function application
    - Macro expansion
    - Tail call optimization (via trampolining)
    """
    
    # Special forms (not evaluated normally)
    SPECIAL_FORMS = {
        'quote', 'if', 'define', 'lambda', 'let', 'let*', 'letrec',
        'begin', 'set!', 'cond', 'and', 'or', 'defmacro',
        'quasiquote', 'unquote', 'unquote-splicing'
    }
    
    def __init__(self, env: Environment):
        self.env = env
        self.macros: Dict[str, LispMacro] = {}
    
    def eval(self, expr: LispValue, env: Optional[Environment] = None) -> LispValue:
        """Evaluate a Lisp expression."""
        if env is None:
            env = self.env
        
        # Trampoline for tail call optimization
        while True:
            # Self-evaluating values
            if isinstance(expr, (LispNumber, LispString, LispBool, LispNil,
                                LispProcedure, LispBuiltin, LispMacro)):
                return expr
            
            # Symbol lookup
            if isinstance(expr, LispSymbol):
                return env.lookup(expr.name)
            
            # List (function call or special form)
            if isinstance(expr, LispList):
                if len(expr) == 0:
                    return NIL
                
                # Get the operator
                op = expr[0]
                
                # Check for special form
                if isinstance(op, LispSymbol) and op.name in self.SPECIAL_FORMS:
                    result = self._eval_special_form(op.name, expr, env)
                    
                    # Handle tail call
                    if isinstance(result, tuple) and len(result) == 2:
                        expr, env = result
                        continue
                    return result
                
                # Macro expansion
                if isinstance(op, LispSymbol) and op.name in self.macros:
                    expanded = self._expand_macro(op.name, expr)
                    expr = expanded
                    continue
                
                # Function application
                func = self.eval(op, env)
                args = [self.eval(arg, env) for arg in expr.elements[1:]]
                
                if isinstance(func, LispBuiltin):
                    return func.func(*args)
                
                if isinstance(func, LispProcedure):
                    # Set up for tail call
                    new_env = func.env.extend(func.params, args)
                    expr = func.body
                    env = new_env
                    continue
                
                raise EvalError(f"Not a function: {func}")
            
            raise EvalError(f"Cannot evaluate: {expr}")
    
    def _eval_special_form(
        self,
        form: str,
        expr: LispList,
        env: Environment
    ) -> Union[LispValue, Tuple[LispValue, Environment]]:
        """Evaluate a special form."""
        
        if form == 'quote':
            if len(expr) != 2:
                raise EvalError("quote requires exactly 1 argument")
            return expr[1]
        
        if form == 'if':
            if len(expr) < 3 or len(expr) > 4:
                raise EvalError("if requires 2 or 3 arguments")
            
            test = self.eval(expr[1], env)
            
            if self._is_truthy(test):
                return (expr[2], env)  # Tail call
            elif len(expr) == 4:
                return (expr[3], env)  # Tail call
            else:
                return NIL
        
        if form == 'define':
            return self._eval_define(expr, env)
        
        if form == 'lambda':
            return self._eval_lambda(expr, env)
        
        if form == 'let':
            return self._eval_let(expr, env)
        
        if form == 'let*':
            return self._eval_let_star(expr, env)
        
        if form == 'begin':
            if len(expr) < 2:
                return NIL
            
            # Evaluate all but last
            for e in expr.elements[1:-1]:
                self.eval(e, env)
            
            # Tail call for last
            return (expr[-1], env)
        
        if form == 'set!':
            if len(expr) != 3:
                raise EvalError("set! requires exactly 2 arguments")
            
            if not isinstance(expr[1], LispSymbol):
                raise EvalError("set! first argument must be a symbol")
            
            value = self.eval(expr[2], env)
            env.set(expr[1].name, value)
            return value
        
        if form == 'cond':
            return self._eval_cond(expr, env)
        
        if form == 'and':
            return self._eval_and(expr, env)
        
        if form == 'or':
            return self._eval_or(expr, env)
        
        if form == 'defmacro':
            return self._eval_defmacro(expr, env)
        
        if form == 'quasiquote':
            return self._eval_quasiquote(expr[1], env)
        
        raise EvalError(f"Unknown special form: {form}")
    
    def _is_truthy(self, value: LispValue) -> bool:
        """Check if a value is truthy."""
        if isinstance(value, LispBool):
            return value.value
        if isinstance(value, LispNil):
            return False
        if isinstance(value, LispList):
            return len(value) > 0
        return True
    
    def _eval_define(self, expr: LispList, env: Environment) -> LispValue:
        """Evaluate define special form."""
        if len(expr) < 3:
            raise EvalError("define requires at least 2 arguments")
        
        target = expr[1]
        
        # (define x value)
        if isinstance(target, LispSymbol):
            value = self.eval(expr[2], env)
            env.define(target.name, value)
            return value
        
        # (define (name args) body) - function shorthand
        if isinstance(target, LispList) and len(target) > 0:
            if not isinstance(target[0], LispSymbol):
                raise EvalError("Function name must be a symbol")
            
            name = target[0].name
            params = [p.name for p in target.elements[1:] if isinstance(p, LispSymbol)]
            
            # Handle multi-expression body
            if len(expr) > 3:
                body = LispList([LispSymbol("begin")] + list(expr.elements[2:]))
            else:
                body = expr[2]
            
            proc = LispProcedure(params=params, body=body, env=env, name=name)
            env.define(name, proc)
            return proc
        
        raise EvalError(f"Invalid define target: {target}")
    
    def _eval_lambda(self, expr: LispList, env: Environment) -> LispProcedure:
        """Evaluate lambda special form."""
        if len(expr) < 3:
            raise EvalError("lambda requires at least 2 arguments")
        
        params_expr = expr[1]
        
        if not isinstance(params_expr, LispList):
            raise EvalError("lambda parameters must be a list")
        
        params = []
        for p in params_expr:
            if not isinstance(p, LispSymbol):
                raise EvalError(f"Parameter must be a symbol: {p}")
            params.append(p.name)
        
        # Handle multi-expression body
        if len(expr) > 3:
            body = LispList([LispSymbol("begin")] + list(expr.elements[2:]))
        else:
            body = expr[2]
        
        return LispProcedure(params=params, body=body, env=env)
    
    def _eval_let(self, expr: LispList, env: Environment) -> Tuple[LispValue, Environment]:
        """Evaluate let special form."""
        if len(expr) < 3:
            raise EvalError("let requires at least 2 arguments")
        
        bindings = expr[1]
        
        if not isinstance(bindings, LispList):
            raise EvalError("let bindings must be a list")
        
        new_env = Environment(parent=env)
        
        for binding in bindings:
            if not isinstance(binding, LispList) or len(binding) != 2:
                raise EvalError(f"Invalid let binding: {binding}")
            
            name, value_expr = binding[0], binding[1]
            
            if not isinstance(name, LispSymbol):
                raise EvalError("let binding name must be a symbol")
            
            value = self.eval(value_expr, env)  # Evaluate in original env
            new_env.define(name.name, value)
        
        # Handle multi-expression body
        if len(expr) > 3:
            body = LispList([LispSymbol("begin")] + list(expr.elements[2:]))
        else:
            body = expr[2]
        
        return (body, new_env)
    
    def _eval_let_star(self, expr: LispList, env: Environment) -> Tuple[LispValue, Environment]:
        """Evaluate let* special form (sequential bindings)."""
        if len(expr) < 3:
            raise EvalError("let* requires at least 2 arguments")
        
        bindings = expr[1]
        
        if not isinstance(bindings, LispList):
            raise EvalError("let* bindings must be a list")
        
        new_env = Environment(parent=env)
        
        for binding in bindings:
            if not isinstance(binding, LispList) or len(binding) != 2:
                raise EvalError(f"Invalid let* binding: {binding}")
            
            name, value_expr = binding[0], binding[1]
            
            if not isinstance(name, LispSymbol):
                raise EvalError("let* binding name must be a symbol")
            
            value = self.eval(value_expr, new_env)  # Evaluate in new env
            new_env.define(name.name, value)
        
        # Handle body
        if len(expr) > 3:
            body = LispList([LispSymbol("begin")] + list(expr.elements[2:]))
        else:
            body = expr[2]
        
        return (body, new_env)
    
    def _eval_cond(self, expr: LispList, env: Environment) -> LispValue:
        """Evaluate cond special form."""
        for clause in expr.elements[1:]:
            if not isinstance(clause, LispList) or len(clause) < 2:
                raise EvalError(f"Invalid cond clause: {clause}")
            
            test = clause[0]
            
            # else clause
            if isinstance(test, LispSymbol) and test.name == "else":
                if len(clause) > 2:
                    body = LispList([LispSymbol("begin")] + list(clause.elements[1:]))
                else:
                    body = clause[1]
                return self.eval(body, env)
            
            # Normal clause
            if self._is_truthy(self.eval(test, env)):
                if len(clause) > 2:
                    body = LispList([LispSymbol("begin")] + list(clause.elements[1:]))
                else:
                    body = clause[1]
                return self.eval(body, env)
        
        return NIL
    
    def _eval_and(self, expr: LispList, env: Environment) -> LispValue:
        """Evaluate and special form (short-circuit)."""
        result: LispValue = LispBool(True)
        
        for e in expr.elements[1:]:
            result = self.eval(e, env)
            if not self._is_truthy(result):
                return result
        
        return result
    
    def _eval_or(self, expr: LispList, env: Environment) -> LispValue:
        """Evaluate or special form (short-circuit)."""
        for e in expr.elements[1:]:
            result = self.eval(e, env)
            if self._is_truthy(result):
                return result
        
        return LispBool(False)
    
    def _eval_defmacro(self, expr: LispList, env: Environment) -> LispMacro:
        """Evaluate defmacro special form."""
        if len(expr) < 4:
            raise EvalError("defmacro requires at least 3 arguments")
        
        if not isinstance(expr[1], LispSymbol):
            raise EvalError("Macro name must be a symbol")
        
        name = expr[1].name
        params_expr = expr[2]
        
        if not isinstance(params_expr, LispList):
            raise EvalError("Macro parameters must be a list")
        
        params = []
        for p in params_expr:
            if not isinstance(p, LispSymbol):
                raise EvalError(f"Macro parameter must be a symbol: {p}")
            params.append(p.name)
        
        # Handle body
        if len(expr) > 4:
            body = LispList([LispSymbol("begin")] + list(expr.elements[3:]))
        else:
            body = expr[3]
        
        macro = LispMacro(params=params, body=body, env=env, name=name)
        self.macros[name] = macro
        return macro
    
    def _expand_macro(self, name: str, expr: LispList) -> LispValue:
        """Expand a macro call."""
        macro = self.macros[name]
        args = list(expr.elements[1:])  # Unevaluated!
        
        if len(args) != len(macro.params):
            raise EvalError(
                f"Macro {name} expected {len(macro.params)} args, got {len(args)}"
            )
        
        # Bind args to params
        new_env = macro.env.extend(macro.params, args)
        
        # Evaluate macro body to get expansion
        return self.eval(macro.body, new_env)
    
    def _eval_quasiquote(self, expr: LispValue, env: Environment) -> LispValue:
        """Evaluate quasiquote (template with unquotes)."""
        if not isinstance(expr, LispList):
            return expr
        
        if len(expr) == 0:
            return expr
        
        # Check for unquote
        if (isinstance(expr[0], LispSymbol) and 
            expr[0].name == "unquote" and len(expr) == 2):
            return self.eval(expr[1], env)
        
        # Process list elements
        result = []
        for elem in expr:
            if (isinstance(elem, LispList) and len(elem) >= 2 and
                isinstance(elem[0], LispSymbol)):
                
                if elem[0].name == "unquote":
                    result.append(self.eval(elem[1], env))
                elif elem[0].name == "unquote-splicing":
                    spliced = self.eval(elem[1], env)
                    if isinstance(spliced, LispList):
                        result.extend(spliced.elements)
                    else:
                        raise EvalError("unquote-splicing requires a list")
                else:
                    result.append(self._eval_quasiquote(elem, env))
            else:
                result.append(self._eval_quasiquote(elem, env))
        
        return LispList(result)


# =============================================================================
# Built-in Functions
# =============================================================================

def create_builtins() -> Dict[str, LispBuiltin]:
    """Create the standard library of built-in functions."""
    builtins = {}
    
    def builtin(name: str):
        """Decorator to register a builtin."""
        def decorator(func: Callable) -> Callable:
            builtins[name] = LispBuiltin(name, func)
            return func
        return decorator
    
    # Arithmetic
    @builtin('+')
    def add(*args):
        return LispNumber(sum(a.value for a in args))
    
    @builtin('-')
    def sub(a, *args):
        if not args:
            return LispNumber(-a.value)
        return LispNumber(a.value - sum(x.value for x in args))
    
    @builtin('*')
    def mul(*args):
        result = 1
        for a in args:
            result *= a.value
        return LispNumber(result)
    
    @builtin('/')
    def div(a, b):
        if b.value == 0:
            raise EvalError("Division by zero")
        return LispNumber(a.value / b.value)
    
    @builtin('mod')
    def mod(a, b):
        return LispNumber(a.value % b.value)
    
    @builtin('abs')
    def abs_fn(a):
        return LispNumber(abs(a.value))
    
    @builtin('sqrt')
    def sqrt_fn(a):
        return LispNumber(math.sqrt(a.value))
    
    @builtin('expt')
    def expt(base, exp):
        return LispNumber(base.value ** exp.value)
    
    # Comparison
    @builtin('=')
    def eq(*args):
        if len(args) < 2:
            return LispBool(True)
        first = args[0].value
        return LispBool(all(a.value == first for a in args[1:]))
    
    @builtin('<')
    def lt(a, b):
        return LispBool(a.value < b.value)
    
    @builtin('>')
    def gt(a, b):
        return LispBool(a.value > b.value)
    
    @builtin('<=')
    def le(a, b):
        return LispBool(a.value <= b.value)
    
    @builtin('>=')
    def ge(a, b):
        return LispBool(a.value >= b.value)
    
    @builtin('eq?')
    def eq_q(a, b):
        if type(a) != type(b):
            return LispBool(False)
        if isinstance(a, LispSymbol):
            return LispBool(a.name == b.name)
        if isinstance(a, (LispNumber, LispString, LispBool)):
            return LispBool(a.value == b.value)
        return LispBool(a is b)
    
    @builtin('equal?')
    def equal_q(a, b):
        return LispBool(str(a) == str(b))
    
    # List operations
    @builtin('cons')
    def cons(head, tail):
        if isinstance(tail, LispList):
            return LispList([head] + list(tail.elements))
        return LispList([head, tail])
    
    @builtin('car')
    def car(lst):
        if not isinstance(lst, LispList) or len(lst) == 0:
            raise EvalError("car requires a non-empty list")
        return lst[0]
    
    @builtin('cdr')
    def cdr(lst):
        if not isinstance(lst, LispList) or len(lst) == 0:
            raise EvalError("cdr requires a non-empty list")
        return LispList(list(lst.elements[1:]))
    
    @builtin('list')
    def list_fn(*args):
        return LispList(list(args))
    
    @builtin('length')
    def length(lst):
        if not isinstance(lst, LispList):
            raise EvalError("length requires a list")
        return LispNumber(len(lst))
    
    @builtin('append')
    def append(*lists):
        result = []
        for lst in lists:
            if isinstance(lst, LispList):
                result.extend(lst.elements)
            else:
                result.append(lst)
        return LispList(result)
    
    @builtin('reverse')
    def reverse(lst):
        if not isinstance(lst, LispList):
            raise EvalError("reverse requires a list")
        return LispList(list(reversed(lst.elements)))
    
    @builtin('null?')
    def null_q(x):
        if isinstance(x, LispNil):
            return LispBool(True)
        if isinstance(x, LispList):
            return LispBool(len(x) == 0)
        return LispBool(False)
    
    @builtin('pair?')
    def pair_q(x):
        return LispBool(isinstance(x, LispList) and len(x) > 0)
    
    # Logic
    @builtin('not')
    def not_fn(x):
        if isinstance(x, LispBool):
            return LispBool(not x.value)
        if isinstance(x, LispNil):
            return LispBool(True)
        return LispBool(False)
    
    # Type predicates
    @builtin('number?')
    def number_q(x):
        return LispBool(isinstance(x, LispNumber))
    
    @builtin('string?')
    def string_q(x):
        return LispBool(isinstance(x, LispString))
    
    @builtin('symbol?')
    def symbol_q(x):
        return LispBool(isinstance(x, LispSymbol))
    
    @builtin('list?')
    def list_q(x):
        return LispBool(isinstance(x, LispList))
    
    @builtin('procedure?')
    def procedure_q(x):
        return LispBool(isinstance(x, (LispProcedure, LispBuiltin)))
    
    @builtin('boolean?')
    def boolean_q(x):
        return LispBool(isinstance(x, LispBool))
    
    # I/O
    @builtin('display')
    def display(x):
        if isinstance(x, LispString):
            print(x.value, end='')
        else:
            print(x.to_string(), end='')
        return NIL
    
    @builtin('newline')
    def newline():
        print()
        return NIL
    
    @builtin('print')
    def print_fn(x):
        print(x.to_string())
        return NIL
    
    # Higher-order functions
    @builtin('map')
    def map_fn(func, lst):
        if not isinstance(lst, LispList):
            raise EvalError("map requires a list as second argument")
        
        results = []
        for elem in lst:
            if isinstance(func, LispBuiltin):
                results.append(func.func(elem))
            elif isinstance(func, LispProcedure):
                # Need evaluator for this
                raise EvalError("map with procedures requires eval context")
            else:
                raise EvalError("map requires a function")
        return LispList(results)
    
    @builtin('filter')
    def filter_fn(func, lst):
        if not isinstance(lst, LispList):
            raise EvalError("filter requires a list as second argument")
        
        results = []
        for elem in lst:
            if isinstance(func, LispBuiltin):
                result = func.func(elem)
                if isinstance(result, LispBool) and result.value:
                    results.append(elem)
            else:
                raise EvalError("filter requires a builtin function")
        return LispList(results)
    
    # Utility
    @builtin('error')
    def error(msg):
        if isinstance(msg, LispString):
            raise EvalError(msg.value)
        raise EvalError(str(msg))
    
    @builtin('apply')
    def apply_fn(func, args):
        if not isinstance(args, LispList):
            raise EvalError("apply requires a list of arguments")
        
        if isinstance(func, LispBuiltin):
            return func.func(*args.elements)
        raise EvalError("apply with procedures requires eval context")
    
    return builtins


# =============================================================================
# Lisp Interpreter
# =============================================================================

class Lisp:
    """
    Complete Lisp interpreter.
    
    Provides:
    - Parsing
    - Evaluation
    - REPL
    - Standard library
    """
    
    def __init__(self):
        self.global_env = Environment()
        
        # Install builtins
        for name, builtin in create_builtins().items():
            self.global_env.define(name, builtin)
        
        # Create evaluator
        self.evaluator = Evaluator(self.global_env)
        
        # Load standard library
        self._load_stdlib()
    
    def _load_stdlib(self):
        """Load Lisp-defined standard library."""
        stdlib = """
        ; Boolean helpers
        (define true #t)
        (define false #f)
        
        ; List helpers
        (define (cadr x) (car (cdr x)))
        (define (caddr x) (car (cdr (cdr x))))
        (define (cadddr x) (car (cdr (cdr (cdr x)))))
        (define (first x) (car x))
        (define (second x) (cadr x))
        (define (third x) (caddr x))
        (define (rest x) (cdr x))
        
        ; Functional helpers
        (define (identity x) x)
        (define (compose f g) (lambda (x) (f (g x))))
        
        ; Numeric helpers
        (define (zero? x) (= x 0))
        (define (positive? x) (> x 0))
        (define (negative? x) (< x 0))
        (define (even? x) (= (mod x 2) 0))
        (define (odd? x) (= (mod x 2) 1))
        (define (inc x) (+ x 1))
        (define (dec x) (- x 1))
        (define (square x) (* x x))
        (define (cube x) (* x x x))
        
        ; List predicates
        (define (empty? x) (null? x))
        
        ; Higher-order (implemented in Lisp for procedure support)
        (define (foldl f init lst)
          (if (null? lst)
              init
              (foldl f (f init (car lst)) (cdr lst))))
        
        (define (foldr f init lst)
          (if (null? lst)
              init
              (f (car lst) (foldr f init (cdr lst)))))
        
        (define (reduce f lst)
          (if (null? (cdr lst))
              (car lst)
              (f (car lst) (reduce f (cdr lst)))))
        
        ; Range
        (define (range start end)
          (if (>= start end)
              '()
              (cons start (range (+ start 1) end))))
        
        ; nth element
        (define (nth n lst)
          (if (= n 0)
              (car lst)
              (nth (- n 1) (cdr lst))))
        
        ; Take/Drop
        (define (take n lst)
          (if (or (= n 0) (null? lst))
              '()
              (cons (car lst) (take (- n 1) (cdr lst)))))
        
        (define (drop n lst)
          (if (or (= n 0) (null? lst))
              lst
              (drop (- n 1) (cdr lst))))
        """
        
        for expr in parse_all(stdlib):
            self.evaluator.eval(expr)
    
    def eval(self, source: str) -> LispValue:
        """Evaluate a Lisp expression."""
        expr = parse(source)
        return self.evaluator.eval(expr)
    
    def eval_all(self, source: str) -> List[LispValue]:
        """Evaluate multiple expressions, return all results."""
        exprs = parse_all(source)
        return [self.evaluator.eval(expr) for expr in exprs]
    
    def run(self, source: str) -> LispValue:
        """Run source, return last result."""
        results = self.eval_all(source)
        return results[-1] if results else NIL
    
    def define_macro(self, source: str) -> LispMacro:
        """Define a macro from source."""
        expr = parse(source)
        return self.evaluator.eval(expr)


# =============================================================================
# REPL
# =============================================================================

def repl(lisp: Optional[Lisp] = None) -> None:
    """
    Start an interactive REPL (Read-Eval-Print Loop).
    
    The original REPL from 1958!
    """
    if lisp is None:
        lisp = Lisp()
    
    print("λ Lisp REPL")
    print('Type "(help)" for help, "(quit)" to exit')
    print()
    
    # Define help
    lisp.eval("""
    (define (help)
      (display "Lisp Commands:")
      (newline)
      (display "  (+ 1 2 3)      ; Arithmetic")
      (newline)
      (display "  (define x 10)  ; Define variable")
      (newline)
      (display "  (lambda (x) (* x x)) ; Function")
      (newline)
      (display "  '(1 2 3)       ; Quoted list")
      (newline)
      (display "  (if test then else) ; Conditional")
      (newline)
      (display "  (quit)         ; Exit REPL")
      (newline)
      'ok)
    """)
    
    buffer = ""
    prompt = "λ> "
    
    while True:
        try:
            line = input(prompt)
            
            if line.strip() == "(quit)":
                print("Goodbye!")
                break
            
            buffer += line + "\n"
            
            # Check for balanced parens
            open_count = buffer.count('(')
            close_count = buffer.count(')')
            
            if open_count > close_count:
                prompt = ".. "
                continue
            
            prompt = "λ> "
            
            if buffer.strip():
                try:
                    results = lisp.eval_all(buffer)
                    for result in results:
                        print(f"=> {result.to_string()}")
                except (ParseError, EvalError) as e:
                    print(f"Error: {e}")
            
            buffer = ""
            
        except EOFError:
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\nInterrupted")
            buffer = ""
            prompt = "λ> "


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Values
    'LispValue',
    'LispNumber',
    'LispString',
    'LispSymbol',
    'LispBool',
    'LispNil',
    'LispList',
    'LispProcedure',
    'LispBuiltin',
    'LispMacro',
    'NIL',
    
    # Environment
    'Environment',
    
    # Errors
    'LispError',
    'ParseError',
    'EvalError',
    
    # Parsing
    'parse',
    'parse_all',
    
    # Evaluator
    'Evaluator',
    
    # Main class
    'Lisp',
    
    # REPL
    'repl',
]
