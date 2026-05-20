#!/usr/bin/env python3
"""
Lisp Usage Examples

A Lisp Interpreter from Scratch.
Everything is an S-expression. Code is data.
"""

from lisp import Lisp, parse


def example_basic():
    """
    Example 1: Basic Lisp
    """
    print("=" * 60)
    print("Example 1: Basic Lisp Syntax")
    print("=" * 60)
    
    print("""
Lisp syntax is simple - everything is an S-expression:
    
    Atoms: 42, "hello", x, #t, #f, nil
    Lists: (+ 1 2)
    
Function calls: (function arg1 arg2 ...)
""")
    
    lisp = Lisp()
    
    # Numbers
    print(f"42 → {lisp.eval('42')}")
    
    # Arithmetic
    print(f"(+ 1 2 3) → {lisp.eval('(+ 1 2 3)')}")
    print(f"(* 6 7) → {lisp.eval('(* 6 7)')}")
    print(f"(- 10 3) → {lisp.eval('(- 10 3)')}")
    print(f"(/ 100 4) → {lisp.eval('(/ 100 4)')}")
    print()


def example_homoiconicity():
    """
    Example 2: Code is Data (Homoiconicity)
    """
    print("=" * 60)
    print("Example 2: 🔮 Code is Data")
    print("=" * 60)
    
    print("""
The key insight of Lisp: Code and Data have the same form!

    '(+ 1 2) is a LIST containing: +, 1, 2
    (+ 1 2)  EXECUTES as: 1 + 2 = 3
    
The quote (') prevents evaluation, treating code as data.
""")
    
    lisp = Lisp()
    
    # Without quote: executes
    print(f"(+ 1 2) → {lisp.eval('(+ 1 2)')}")
    
    # With quote: data
    result = lisp.eval("'(+ 1 2)")
    print(f"'(+ 1 2) → {result}")
    
    # Manipulate code as data
    print(f"(car '(+ 1 2)) → {lisp.eval('(car (quote (+ 1 2)))')}")
    print(f"(cdr '(+ 1 2)) → {lisp.eval('(cdr (quote (+ 1 2)))')}")
    print()


def example_functions():
    """
    Example 3: Functions
    """
    print("=" * 60)
    print("Example 3: 📦 Functions")
    print("=" * 60)
    
    print("""
Define functions with (define (name args) body):
    
    (define (square x) (* x x))
    
Or with lambda:
    
    (lambda (x) (* x x))
""")
    
    lisp = Lisp()
    
    # Define a function
    lisp.eval("(define (square x) (* x x))")
    print(f"(define (square x) (* x x))")
    print(f"(square 5) → {lisp.eval('(square 5)')}")
    
    # Function with multiple args
    lisp.eval("(define (add3 a b c) (+ a b c))")
    print(f"\n(define (add3 a b c) (+ a b c))")
    print(f"(add3 1 2 3) → {lisp.eval('(add3 1 2 3)')}")
    
    # Lambda (anonymous function)
    result = lisp.eval("((lambda (x y) (+ x y)) 10 20)")
    print(f"\n((lambda (x y) (+ x y)) 10 20) → {result}")
    print()


def example_recursion():
    """
    Example 4: Recursion
    """
    print("=" * 60)
    print("Example 4: 🔄 Recursion")
    print("=" * 60)
    
    print("""
Recursion is the primary looping mechanism in Lisp.
""")
    
    lisp = Lisp()
    
    # Factorial
    lisp.eval("""
        (define (factorial n)
          (if (<= n 1)
              1
              (* n (factorial (- n 1)))))
    """)
    
    print("(define (factorial n)")
    print("  (if (<= n 1)")
    print("      1")
    print("      (* n (factorial (- n 1)))))")
    print()
    
    for n in [1, 5, 10]:
        result = lisp.eval(f"(factorial {n})")
        print(f"(factorial {n}) → {result}")
    
    # Fibonacci
    print()
    lisp.eval("""
        (define (fib n)
          (if (<= n 1)
              n
              (+ (fib (- n 1)) (fib (- n 2)))))
    """)
    
    print("(define (fib n) ...)")
    fibs = [lisp.eval(f"(fib {i})").value for i in range(10)]
    print(f"First 10 Fibonacci: {fibs}")
    print()


def example_higher_order():
    """
    Example 5: Higher-Order Functions
    """
    print("=" * 60)
    print("Example 5: 🚀 Higher-Order Functions")
    print("=" * 60)
    
    print("""
Functions that take or return functions!
""")
    
    lisp = Lisp()
    
    # Map-like operation using foldl
    print("Using foldl to sum a list:")
    result = lisp.eval("(foldl + 0 '(1 2 3 4 5))")
    print(f"(foldl + 0 '(1 2 3 4 5)) → {result}")
    
    # Function composition
    lisp.eval("(define (compose f g) (lambda (x) (f (g x))))")
    lisp.eval("(define (add1 x) (+ x 1))")
    lisp.eval("(define (double x) (* x 2))")
    lisp.eval("(define add1-then-double (compose double add1))")
    
    print("\n(define add1-then-double (compose double add1))")
    result = lisp.eval("(add1-then-double 5)")
    print(f"(add1-then-double 5) → {result}  ; (5+1)*2 = 12")
    print()


def example_closures():
    """
    Example 6: Closures
    """
    print("=" * 60)
    print("Example 6: 🔒 Closures")
    print("=" * 60)
    
    print("""
Functions can capture their environment (lexical scoping).
""")
    
    lisp = Lisp()
    
    # Counter using closure
    lisp.eval("""
        (define (make-counter)
          (let ((count 0))
            (lambda ()
              (set! count (+ count 1))
              count)))
    """)
    
    print("(define (make-counter)")
    print("  (let ((count 0))")
    print("    (lambda ()")
    print("      (set! count (+ count 1))")
    print("      count)))")
    print()
    
    lisp.eval("(define counter (make-counter))")
    print("(define counter (make-counter))")
    
    for _ in range(5):
        result = lisp.eval("(counter)")
        print(f"(counter) → {result}")
    print()


def example_macros():
    """
    Example 7: Macros - Code that Writes Code!
    """
    print("=" * 60)
    print("Example 7: 🪄 Macros - Code that Writes Code!")
    print("=" * 60)
    
    print("""
Macros transform code before execution.
This is Lisp's superpower - extend the language itself!

The magic: since code is data, you can manipulate it
with regular list operations.
""")
    
    lisp = Lisp()
    
    # Define 'unless' macro
    lisp.eval("""
        (defmacro unless (test body)
          `(if (not ,test) ,body nil))
    """)
    
    print("(defmacro unless (test body)")
    print("  `(if (not ,test) ,body nil))")
    print()
    print("'unless' is not built into Lisp - we just created it!")
    print()
    
    result = lisp.eval("(unless #f 'it-worked)")
    print(f"(unless #f 'it-worked) → {result}")
    
    result = lisp.eval("(unless #t 'it-worked)")
    print(f"(unless #t 'it-worked) → {result}")
    
    # More macro magic
    print()
    lisp.eval("""
        (defmacro when (test body)
          `(if ,test ,body nil))
    """)
    
    result = lisp.eval("(when (> 5 3) 'yes)")
    print(f"(when (> 5 3) 'yes) → {result}")
    print()


def example_list_processing():
    """
    Example 8: List Processing
    """
    print("=" * 60)
    print("Example 8: 📋 List Processing")
    print("=" * 60)
    
    print("""
Lisp was originally "LISt Processing"!
""")
    
    lisp = Lisp()
    
    # List operations
    print("List operations:")
    print(f"  (list 1 2 3) → {lisp.eval('(list 1 2 3)')}")
    print(f"  (car '(a b c)) → {lisp.eval('(car (quote (a b c)))')}")
    print(f"  (cdr '(a b c)) → {lisp.eval('(cdr (quote (a b c)))')}")
    print(f"  (cons 'x '(y z)) → {lisp.eval('(cons (quote x) (quote (y z)))')}")
    print(f"  (append '(1 2) '(3 4)) → {lisp.eval('(append (quote (1 2)) (quote (3 4)))')}")
    print(f"  (reverse '(1 2 3)) → {lisp.eval('(reverse (quote (1 2 3)))')}")
    print(f"  (length '(a b c d)) → {lisp.eval('(length (quote (a b c d)))')}")
    
    # Using standard library
    print("\nStandard library functions:")
    print(f"  (range 0 5) → {lisp.eval('(range 0 5)')}")
    print(f"  (take 3 '(a b c d e)) → {lisp.eval('(take 3 (quote (a b c d e)))')}")
    print(f"  (drop 2 '(1 2 3 4 5)) → {lisp.eval('(drop 2 (quote (1 2 3 4 5)))')}")
    print()


def example_classic_lisp():
    """
    Example 9: Classic Lisp Programs
    """
    print("=" * 60)
    print("Example 9: 📚 Classic Lisp Programs")
    print("=" * 60)
    
    lisp = Lisp()
    
    # Quicksort
    print("Quicksort in Lisp:")
    lisp.eval("""
        (define (filter pred lst)
          (if (null? lst)
              '()
              (if (pred (car lst))
                  (cons (car lst) (filter pred (cdr lst)))
                  (filter pred (cdr lst)))))
    """)
    
    lisp.eval("""
        (define (quicksort lst)
          (if (null? lst)
              '()
              (let ((pivot (car lst))
                    (rest (cdr lst)))
                (append
                  (quicksort (filter (lambda (x) (< x pivot)) rest))
                  (list pivot)
                  (quicksort (filter (lambda (x) (>= x pivot)) rest))))))
    """)
    
    result = lisp.eval("(quicksort '(5 2 8 1 9 3))")
    print(f"(quicksort '(5 2 8 1 9 3)) → {result}")
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ██╗     ██╗███████╗██████╗                                   ║
║  ██║     ██║██╔════╝██╔══██╗                                  ║
║  ██║     ██║███████╗██████╔╝                                  ║
║  ██║     ██║╚════██║██╔═══╝                                   ║
║  ███████╗██║███████║██║                                       ║
║  ╚══════╝╚═╝╚══════╝╚═╝                                       ║
║                                                               ║
║     λ A Lisp Interpreter from Scratch λ                       ║
║                                                               ║
║   "Lisp is worth learning for the profound                    ║
║    enlightenment experience you will have."                   ║
║                        - Eric S. Raymond                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_homoiconicity()
    example_functions()
    example_recursion()
    example_higher_order()
    example_closures()
    example_macros()
    example_list_processing()
    example_classic_lisp()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Historical Note:

    Lisp was invented by John McCarthy in 1958.
    It introduced:
        - Garbage collection
        - Tree data structures  
        - Recursion
        - Higher-order functions
        - REPL (interactive development)
    
    The key insight: Code and data have the same form
    (S-expressions). This enables macros - code that
    transforms code - Lisp's ultimate superpower.
    
    Start the REPL with: from lisp import repl; repl()
""")


if __name__ == "__main__":
    main()
