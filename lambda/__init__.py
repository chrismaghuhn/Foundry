"""
Lambda: Pure Lambda Calculus Interpreter

An interpreter for the pure untyped lambda calculus with
Church encoding, step-by-step reduction, and visualization.

Quick Start:
    >>> from lambda_calc import parse, reduce, Church
    >>> 
    >>> # Parse and reduce
    >>> term = parse("(λx.x) y")
    >>> result = reduce(term)  # Var(y)
    >>> 
    >>> # Church numerals - numbers as functions!
    >>> two = Church.numeral(2)
    >>> three = Church.numeral(3)
    >>> 
    >>> # 2 + 3 = 5, using only functions!
    >>> from lambda_calc import evaluate
    >>> result = evaluate("add 2 3")
    >>> Church.to_int(result)  # 5

Church Encoding:
    Numbers:
        0 = λf.λx.x
        1 = λf.λx.f x
        2 = λf.λx.f (f x)
    
    Booleans:
        TRUE  = λt.λf.t
        FALSE = λt.λf.f
    
    Arithmetic:
        SUCC = λn.λf.λx.f (n f x)
        ADD  = λm.λn.λf.λx.m f (n f x)

The magic: Everything is a function. No numbers, no booleans,
no if-else - just λ. Yet it can compute anything computable.
"""

from .lambda_calc import (
    # AST
    Term,
    Var,
    Abs,
    App,
    
    # Parsing
    parse,
    ParseError,
    
    # Reduction
    Reducer,
    ReductionStrategy,
    ReductionStep,
    reduce,
    reduce_steps,
    
    # Church encoding
    Church,
    
    # Utilities
    alpha_equivalent,
    fresh_variable,
    expand_stdlib,
    evaluate,
    
    # Visualization
    visualize_reduction,
    visualize_church_arithmetic,
    pretty_print,
    
    # Standard library
    STDLIB,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # AST
    'Term', 'Var', 'Abs', 'App',
    
    # Parsing
    'parse', 'ParseError',
    
    # Reduction
    'Reducer', 'ReductionStrategy', 'ReductionStep',
    'reduce', 'reduce_steps',
    
    # Church encoding
    'Church',
    
    # Utilities
    'alpha_equivalent', 'fresh_variable',
    'expand_stdlib', 'evaluate',
    
    # Visualization
    'visualize_reduction', 'visualize_church_arithmetic',
    'pretty_print',
    
    # Standard library
    'STDLIB',
]
