"""
Lisp: A Lisp Interpreter from Scratch

A complete Lisp interpreter with REPL, macros, and tail call optimization.

Quick Start:
    >>> from lisp import Lisp
    >>> 
    >>> lisp = Lisp()
    >>> lisp.eval("(+ 1 2 3)")  # 6
    >>> 
    >>> lisp.eval("(define (square x) (* x x))")
    >>> lisp.eval("(square 5)")  # 25
    >>> 
    >>> # Start interactive REPL
    >>> from lisp import repl
    >>> repl()

Features:
    - Full S-expression parser
    - Lexical scoping with closures
    - Tail call optimization
    - Macros (defmacro, quasiquote)
    - Standard library (map, filter, fold, etc.)
    - Interactive REPL

Special Forms:
    (define name value)       Define variable
    (define (name args) body) Define function
    (lambda (args) body)      Anonymous function
    (if test then else)       Conditional
    (quote expr) or 'expr     Prevent evaluation
    (let ((x 1)) body)        Local bindings
    (set! name value)         Mutation
    (defmacro name (args) body) Define macro

The magic of Lisp: Code IS Data. This enables macros -
code that transforms code - Lisp's ultimate superpower.
"""

from .lisp import (
    # Values
    LispValue,
    LispNumber,
    LispString,
    LispSymbol,
    LispBool,
    LispNil,
    LispList,
    LispProcedure,
    LispBuiltin,
    LispMacro,
    NIL,
    
    # Environment
    Environment,
    
    # Errors
    LispError,
    ParseError,
    EvalError,
    
    # Parsing
    parse,
    parse_all,
    
    # Evaluator
    Evaluator,
    
    # Main class
    Lisp,
    
    # REPL
    repl,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Values
    'LispValue', 'LispNumber', 'LispString', 'LispSymbol',
    'LispBool', 'LispNil', 'LispList', 'LispProcedure',
    'LispBuiltin', 'LispMacro', 'NIL',
    
    # Environment
    'Environment',
    
    # Errors
    'LispError', 'ParseError', 'EvalError',
    
    # Parsing
    'parse', 'parse_all',
    
    # Evaluator
    'Evaluator',
    
    # Main class
    'Lisp',
    
    # REPL
    'repl',
]
