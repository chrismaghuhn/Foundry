"""
Prism: Embeddable Query Language for Structured Data

Query JSON, dicts, and lists with a powerful expression language.

Quick Start:
    >>> from prism import query
    >>> 
    >>> data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}]}
    >>> query(".users | filter(.age >= 18) | map(.name)", data)
    ['Alice']

For repeated queries, compile once:
    >>> from prism import Prism
    >>> p = Prism()
    >>> get_adults = p.compile(".users | filter(.age >= 18)")
    >>> get_adults(data1)
    >>> get_adults(data2)
"""

from .prism import (
    # Main interface
    Prism,
    query,
    
    # Components
    Lexer,
    Parser,
    Evaluator,
    Context,
    
    # Errors
    LexerError,
    LexError,
    ParseError,
    EvalError,
    TokenType,
    TT,
    
    # AST
    ASTNode,
    NumberLiteral,
    StringLiteral,
    BoolLiteral,
    NullLiteral,
    Identifier,
    CurrentValue,
    RootValue,
    ArrayLiteral,
    ObjectLiteral,
    BinaryOp,
    UnaryOp,
    PropertyAccess,
    IndexAccess,
    SliceAccess,
    FunctionCall,
    PipeExpr,
    ConditionalExpr,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Main
    'Prism',
    'query',
    
    # Components
    'Lexer',
    'Parser',
    'Evaluator',
    'Context',
    
    # Errors
    'LexerError',
    'ParseError',
    'EvalError',
    
    # AST
    'ASTNode',
    'NumberLiteral',
    'StringLiteral',
    'BoolLiteral',
    'NullLiteral',
    'Identifier',
    'CurrentValue',
    'RootValue',
    'ArrayLiteral',
    'ObjectLiteral',
    'BinaryOp',
    'UnaryOp',
    'PropertyAccess',
    'IndexAccess',
    'SliceAccess',
    'FunctionCall',
    'PipeExpr',
    'ConditionalExpr',
]
