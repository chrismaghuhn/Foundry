"""
Rune: Sandboxed Expression Evaluator

Safely evaluate user-defined expressions with resource limits and no I/O.

Quick Start:
    >>> from rune import Rune
    >>> 
    >>> engine = Rune()
    >>> result = engine.evaluate("price * quantity * (1 - discount)", {
    ...     "price": 100,
    ...     "quantity": 5,
    ...     "discount": 0.1
    ... })
    >>> print(result)  # 450.0

For repeated evaluations, compile once:
    >>> compiled = engine.compile("x * 2 + y")
    >>> compiled.evaluate({"x": 5, "y": 10})  # 20.0
    >>> compiled.evaluate({"x": 10, "y": 5})  # 25.0

Custom functions:
    >>> engine.register_function("double", lambda x: x*2, [RuType.NUMBER], RuType.NUMBER)
    >>> engine.evaluate("double(21)")  # 42.0
"""

from .rune import (
    # Main interface
    Rune,
    CompiledExpression,
    
    # Types
    RuType,
    TypeSignature,
    ExecutionLimits,
    
    # Errors
    RuneError,
    LexerError,
    ParseError,
    TypeError,
    RuntimeError,
    FuelExhaustedError,
    DepthExceededError,
    
    # For advanced use
    Lexer,
    Parser,
    Evaluator,
    ExecutionContext,
    TokenType,
    NumberLiteral,
    StringLiteral,
    BoolLiteral,
    NullLiteral,
    ListLiteral,
    PropertyAccess,
    BinaryOp,
    UnaryOp,
    Conditional,
    TernaryOp,
    FunctionCall,
    IndexAccess,
    Identifier,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

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
    
    # Advanced
    'Lexer',
    'Parser',
    'Evaluator',
    'ExecutionContext',
    'TokenType',
    'NumberLiteral',
    'StringLiteral',
    'BoolLiteral',
    'NullLiteral',
    'ListLiteral',
    'PropertyAccess',
    'BinaryOp',
    'UnaryOp',
    'Conditional',
    'TernaryOp',
    'FunctionCall',
    'IndexAccess',
    'Identifier',
]
