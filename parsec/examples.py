#!/usr/bin/env python3
"""
Parsec Usage Examples

Parser Combinators: Build parsers like LEGO!
"""

from parsec import (
    # Primitives
    char,
    string,
    digit,
    letter,
    space,
    regex,
    eof,
    
    # Combinators
    pure,
    lazy,
    choice,
    chainl,
    chainr,
    
    # Common
    spaces,
    integer,
    floating,
    double_quoted,
    
    # Visualization
    visualize_parse,
)


def example_basic():
    """
    Example 1: Basic Parsers
    """
    print("=" * 60)
    print("Example 1: Basic Parsers")
    print("=" * 60)
    
    print("""
Parsers are functions that consume input:
    char('a')     : parse exactly 'a'
    string('hi')  : parse exactly "hi"
    digit         : parse one digit
    letter        : parse one letter
""")
    
    # Parse a character
    p = char('a')
    result = p.parse("abc")
    print(f"char('a').parse('abc') = {result!r}")
    
    # Parse a string
    p = string("hello")
    result = p.parse("hello world")
    print(f"string('hello').parse('hello world') = {result!r}")
    
    # Parse a digit
    result = digit.parse("123")
    print(f"digit.parse('123') = {result!r}")
    print()


def example_combinators():
    """
    Example 2: Combining Parsers
    """
    print("=" * 60)
    print("Example 2: 🧩 Combining Parsers")
    print("=" * 60)
    
    print("""
Combinators build complex parsers from simple ones:
    p1 >> p2  : sequence (keep right)
    p1 << p2  : sequence (keep left)  
    p1 | p2   : choice (try p1, then p2)
    p1 + p2   : sequence (tuple of both)
""")
    
    # Sequence: parse 'a' then 'b', keep 'b'
    p = char('a') >> char('b')
    result = p.parse("abc")
    print(f"char('a') >> char('b') = {result!r}")
    
    # Keep left
    p = char('a') << char('b')
    result = p.parse("abc")
    print(f"char('a') << char('b') = {result!r}")
    
    # Choice
    p = char('a') | char('b')
    print(f"char('a') | char('b') on 'abc' = {p.parse('abc')!r}")
    print(f"char('a') | char('b') on 'bcd' = {p.parse('bcd')!r}")
    
    # Tuple
    p = char('a') + char('b')
    result = p.parse("abc")
    print(f"char('a') + char('b') = {result!r}")
    print()


def example_repetition():
    """
    Example 3: Repetition
    """
    print("=" * 60)
    print("Example 3: 🔄 Repetition")
    print("=" * 60)
    
    print("""
Repeat parsers:
    p.many()   : zero or more
    p.many1()  : one or more
    p.optional(): zero or one
    p.sep_by(s): separated by s
""")
    
    # Many
    p = char('a').many()
    print(f"char('a').many().parse('aaab') = {p.parse('aaab')}")
    
    # Many1
    p = digit.many1().map(lambda ds: ''.join(ds))
    print(f"digit.many1() on '12345x' = {p.parse('12345x')!r}")
    
    # Sep by
    p = integer.sep_by(char(','))
    print(f"integer.sep_by(',') on '1,2,3' = {p.parse('1,2,3')}")
    print()


def example_transform():
    """
    Example 4: Transforming Results
    """
    print("=" * 60)
    print("Example 4: 🔄 Transforming Results")
    print("=" * 60)
    
    print("""
Transform parsed values:
    p.map(f) : apply function to result
""")
    
    # Parse number
    p = digit.many1().map(lambda ds: int(''.join(ds)))
    result = p.parse("42abc")
    print(f"Parse number: {result} (type: {type(result).__name__})")
    
    # Double it
    p = digit.many1().map(lambda ds: int(''.join(ds))).map(lambda n: n * 2)
    result = p.parse("21")
    print(f"Parse and double: {result}")
    print()


def example_arithmetic():
    """
    Example 5: Arithmetic Expression Parser
    """
    print("=" * 60)
    print("Example 5: 🔢 Arithmetic Expressions")
    print("=" * 60)
    
    print("""
Parse expressions like "1 + 2 * 3" with correct precedence!
    
    chainl(operand, operator) - left-associative
    chainr(operand, operator) - right-associative
""")
    
    # Simple addition
    add_op = string(" + ") >> pure(lambda a, b: a + b)
    sub_op = string(" - ") >> pure(lambda a, b: a - b)
    
    add_sub = add_op | sub_op
    expr = chainl(integer, add_sub)
    
    tests = ["1 + 2 + 3", "10 - 3 - 2", "10 + 5 - 3"]
    
    for test in tests:
        result = expr.parse(test)
        print(f"  {test} = {result}")
    
    # Right-associative (exponentiation)
    print("\nRight-associative (^):")
    pow_op = string(" ^ ") >> pure(lambda a, b: a ** b)
    power = chainr(integer, pow_op)
    
    result = power.parse("2 ^ 3 ^ 2")
    print(f"  2 ^ 3 ^ 2 = {result}  (= 2^(3^2) = 2^9 = 512)")
    print()


def example_json_value():
    """
    Example 6: JSON-like Value Parser
    """
    print("=" * 60)
    print("Example 6: 📋 JSON-like Parser")
    print("=" * 60)
    
    print("""
Build a simple JSON value parser with combinators!
""")
    
    # JSON value
    def json_value():
        return (
            double_quoted.map(lambda s: ('string', s)) |
            integer.map(lambda n: ('number', n)) |
            string("true").map(lambda _: ('bool', True)) |
            string("false").map(lambda _: ('bool', False)) |
            string("null").map(lambda _: ('null', None)) |
            lazy(json_array)
        )
    
    def json_array():
        sep = spaces >> char(',') << spaces
        elements = lazy(json_value).sep_by(sep)
        return elements.between(
            char('[') << spaces,
            spaces >> char(']')
        ).map(lambda items: ('array', items))
    
    parser = lazy(json_value)
    
    tests = [
        '"hello"',
        '42',
        'true',
        '[1, 2, 3]',
        '["a", "b", "c"]',
    ]
    
    for test in tests:
        result = parser.parse(test)
        print(f"  {test:20} → {result}")
    print()


def example_recursive():
    """
    Example 7: Recursive Grammar (S-expressions)
    """
    print("=" * 60)
    print("Example 7: 🌳 Recursive Grammar")
    print("=" * 60)
    
    print("""
Parse S-expressions (the basis of Lisp!)
    atom    : number or symbol
    sexpr   : atom | (sexpr*)
""")
    
    # S-expression parser
    symbol = letter.many1().map(lambda cs: ('symbol', ''.join(cs)))
    number = integer.map(lambda n: ('number', n))
    atom = number | symbol
    
    def sexpr():
        lparen = char('(') << spaces
        rparen = spaces >> char(')')
        ws = space.many1()
        
        list_expr = lazy(sexpr).sep_by(ws).between(lparen, rparen).map(
            lambda items: ('list', items)
        )
        
        return atom | list_expr
    
    parser = lazy(sexpr)
    
    tests = [
        "42",
        "hello",
        "(+ 1 2)",
        "(define x 10)",
        "(if (> x 0) (print x) nil)",
    ]
    
    for test in tests:
        result = parser.parse(test)
        print(f"  {test:30} → {result[0]}")
    print()


def example_key_value():
    """
    Example 8: Key-Value Parser
    """
    print("=" * 60)
    print("Example 8: 🔑 Key-Value Config Parser")
    print("=" * 60)
    
    # Identifier
    ident = letter.many1().map(lambda cs: ''.join(cs))
    
    # Value (string or number)
    value = double_quoted | integer.map(str)
    
    # Key: value
    pair = (ident << spaces << char(':') << spaces) + value
    
    # Multiple pairs
    pairs = pair.sep_by(char(',') << spaces)
    
    input_text = 'name: "Alice", age: 30, city: "NYC"'
    result = pairs.parse(input_text)
    
    print(f"Input: {input_text}")
    print(f"Parsed: {dict(result)}")
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ██████╗  █████╗ ██████╗ ███████╗███████╗ ██████╗             ║
║  ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝             ║
║  ██████╔╝███████║██████╔╝███████╗█████╗  ██║                  ║
║  ██╔═══╝ ██╔══██║██╔══██╗╚════██║██╔══╝  ██║                  ║
║  ██║     ██║  ██║██║  ██║███████║███████╗╚██████╗             ║
║  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝             ║
║                                                               ║
║     🧩 Parser Combinator Library 🧩                           ║
║                                                               ║
║   Build parsers like LEGO bricks.                             ║
║   Compose small parsers into complex grammars.                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_combinators()
    example_repetition()
    example_transform()
    example_arithmetic()
    example_json_value()
    example_recursive()
    example_key_value()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
The elegance of parser combinators:
    - Small parsers compose into complex grammars
    - Code reads like the grammar it parses
    - No separate lexer/parser phases needed
    - Easy to test, extend, and maintain
    
Inspired by Haskell's Parsec library.
""")


if __name__ == "__main__":
    main()
