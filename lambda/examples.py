#!/usr/bin/env python3
"""
Lambda Usage Examples

Pure Lambda Calculus Interpreter.
Everything is a function. Even numbers!
"""

from lambda_calc import (
    # Core
    parse,
    reduce,
    reduce_steps,
    
    # Church encoding
    Church,
    
    # Utilities
    evaluate,
    alpha_equivalent,
    
    # Visualization
    visualize_reduction,
    visualize_church_arithmetic,
    pretty_print,
    
    # Standard library
    STDLIB,
)


def example_basic():
    """
    Example 1: Basic Lambda Calculus
    """
    print("=" * 60)
    print("Example 1: Basic Lambda Calculus")
    print("=" * 60)
    
    # Identity function
    identity = parse("λx.x")
    print(f"\nIdentity: {identity}")
    
    # Apply identity to something
    app = parse("(λx.x) y")
    result = reduce(app)
    print(f"(λx.x) y → {result}")
    
    # Constant function
    const = parse("λx.λy.x")
    print(f"\nConstant (K): {const}")
    
    app2 = parse("(λx.λy.x) a b")
    result2 = reduce(app2)
    print(f"(λx.λy.x) a b → {result2}")
    print()


def example_church_numerals():
    """
    Example 2: Church Numerals - Numbers as Functions!
    """
    print("=" * 60)
    print("Example 2: 🔢 Church Numerals")
    print("=" * 60)
    
    print("""
Church numerals encode numbers as functions:
    
    0 = λf.λx.x           (apply f zero times)
    1 = λf.λx.f x         (apply f once)
    2 = λf.λx.f (f x)     (apply f twice)
    3 = λf.λx.f (f (f x)) (apply f three times)
    
The number n is "apply f n times to x".
""")
    
    for n in range(5):
        numeral = Church.numeral(n)
        print(f"{n} = {numeral}")
    print()


def example_church_arithmetic():
    """
    Example 3: Arithmetic with Pure Functions
    """
    print("=" * 60)
    print("Example 3: ➕ Church Arithmetic")
    print("=" * 60)
    
    print("\nNo numbers, no operators - just functions!")
    print("Yet we can add, multiply, even exponentiate.\n")
    
    # Addition
    print(visualize_church_arithmetic(2, 3, '+'))
    print()
    
    # Multiplication
    print(visualize_church_arithmetic(2, 3, '*'))
    print()


def example_church_booleans():
    """
    Example 4: Church Booleans
    """
    print("=" * 60)
    print("Example 4: ✓ Church Booleans")
    print("=" * 60)
    
    print("""
Booleans are also functions:

    TRUE  = λt.λf.t   (select first argument)
    FALSE = λt.λf.f   (select second argument)
    
This makes IF-THEN-ELSE trivial:
    IF cond THEN a ELSE b = cond a b
""")
    
    print(f"TRUE  = {Church.TRUE}")
    print(f"FALSE = {Church.FALSE}")
    
    # AND
    print("\nTRUE AND FALSE:")
    expr = parse("(λp.λq.p q p) (λt.λf.t) (λt.λf.f)")
    result = reduce(expr)
    print(f"  = {result}")
    print(f"  = {Church.to_bool(result)}")
    
    # NOT
    print("\nNOT TRUE:")
    not_true = reduce(parse("(λp.p (λt.λf.f) (λt.λf.t)) (λt.λf.t)"))
    print(f"  = {not_true}")
    print(f"  = {Church.to_bool(not_true)}")
    print()


def example_reduction_trace():
    """
    Example 5: Watch Reduction Step by Step
    """
    print("=" * 60)
    print("Example 5: 🔍 Reduction Trace")
    print("=" * 60)
    
    term = parse("(λx.λy.x) a b")
    print(f"\nTerm: {term}")
    print(visualize_reduction(term))
    print()


def example_combinators():
    """
    Example 6: Famous Combinators
    """
    print("=" * 60)
    print("Example 6: 🎭 Famous Combinators")
    print("=" * 60)
    
    combinators = [
        ('I', 'λx.x', 'Identity'),
        ('K', 'λx.λy.x', 'Constant'),
        ('S', 'λx.λy.λz.x z (y z)', 'Substitution'),
        ('B', 'λf.λg.λx.f (g x)', 'Composition'),
        ('C', 'λf.λx.λy.f y x', 'Flip'),
        ('W', 'λf.λx.f x x', 'Duplicate'),
    ]
    
    print("\nThe SKI combinators are Turing-complete!")
    print("Any computation can be expressed with just S, K, and I.\n")
    
    for name, expr, desc in combinators:
        print(f"{name} = {expr}")
        print(f"   {desc}")
    print()
    
    # Demonstrate S K K = I
    print("\nFun fact: S K K = I")
    skk = parse("(λx.λy.λz.x z (y z)) (λx.λy.x) (λx.λy.x)")
    result = reduce(skk)
    print(f"S K K reduces to: {result}")
    print(f"Which is α-equivalent to I: {alpha_equivalent(result, parse('λx.x'))}")
    print()


def example_y_combinator():
    """
    Example 7: The Y Combinator - Recursion!
    """
    print("=" * 60)
    print("Example 7: 🔄 The Y Combinator")
    print("=" * 60)
    
    print("""
The Y combinator enables recursion in pure lambda calculus!

    Y = λf.(λx.f (x x)) (λx.f (x x))
    
Property: Y f = f (Y f)

This means f gets passed "itself" as an argument,
enabling recursive definitions without explicit recursion.
""")
    
    print(f"Y = {Church.Y}")
    
    # Note: Actually running Y diverges without lazy evaluation
    print("\n(Note: Y requires lazy evaluation to not diverge)")
    print()


def example_stdlib():
    """
    Example 8: Using the Standard Library
    """
    print("=" * 60)
    print("Example 8: 📚 Standard Library")
    print("=" * 60)
    
    print("\nThe stdlib provides named constants for common terms.\n")
    
    print("Available definitions:")
    for name in sorted(STDLIB.keys()):
        print(f"  {name}")
    
    print("\n\nExamples using stdlib:")
    
    # succ 2 = 3
    result = evaluate("succ 2")
    print(f"succ 2 = {Church.to_int(result)}")
    
    # add 2 3 = 5
    result = evaluate("add 2 3")
    print(f"add 2 3 = {Church.to_int(result)}")
    
    # mul 2 3 = 6
    result = evaluate("mul 2 3")
    print(f"mul 2 3 = {Church.to_int(result)}")
    
    # iszero 0 = true
    result = evaluate("iszero 0")
    print(f"iszero 0 = {Church.to_bool(result)}")
    
    # I x = x
    result = evaluate("I x")
    print(f"I x = {result}")
    
    # K a b = a
    result = evaluate("K a b")
    print(f"K a b = {result}")
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ██╗      █████╗ ███╗   ███╗██████╗ ██████╗  █████╗           ║
║  ██║     ██╔══██╗████╗ ████║██╔══██╗██╔══██╗██╔══██╗          ║
║  ██║     ███████║██╔████╔██║██████╔╝██║  ██║███████║          ║
║  ██║     ██╔══██║██║╚██╔╝██║██╔══██╗██║  ██║██╔══██║          ║
║  ███████╗██║  ██║██║ ╚═╝ ██║██████╔╝██████╔╝██║  ██║          ║
║  ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ ╚═════╝ ╚═╝  ╚═╝          ║
║                                                               ║
║         λ Pure Lambda Calculus Interpreter λ                  ║
║                                                               ║
║   Everything is a function. Even numbers.                     ║
║   The foundation of all computation.                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_church_numerals()
    example_church_arithmetic()
    example_church_booleans()
    example_reduction_trace()
    example_combinators()
    example_y_combinator()
    example_stdlib()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Historical Note:
    Alonzo Church invented the lambda calculus in the 1930s
    to formalize the concept of computation. It was proven
    equivalent to Turing machines (Church-Turing thesis).
    
    Every functional programming language (Lisp, Haskell,
    ML, Scheme) is directly descended from this formalism.
""")


if __name__ == "__main__":
    main()
