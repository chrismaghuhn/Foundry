"""Tests for parsec."""

import pytest
from parsec import (
    # Core
    Parser,
    ParseState,
    ParseError,
    Position,
    Success,
    Failure,
    
    # Combinators
    pure,
    fail,
    lazy,
    sequence,
    choice,
    chainl,
    chainr,
    
    # Primitives
    satisfy,
    char,
    string,
    regex,
    
    # Character parsers
    any_char,
    digit,
    letter,
    alphanum,
    space,
    newline,
    eof,
    
    # Common
    spaces,
    spaces1,
    digits,
    word,
    
    # Numbers
    integer,
    floating,
    
    # Strings
    quoted_string,
    double_quoted,
    
    # Visualization
    visualize_parse,
)


# =============================================================================
# Position Tests
# =============================================================================

class TestPosition:
    """Test position tracking."""
    
    def test_start_position(self):
        pos = Position.start()
        assert pos.line == 1
        assert pos.column == 1
    
    def test_advance_column(self):
        pos = Position.start().advance('a')
        assert pos.line == 1
        assert pos.column == 2
    
    def test_advance_newline(self):
        pos = Position.start().advance('\n')
        assert pos.line == 2
        assert pos.column == 1


# =============================================================================
# Primitive Parser Tests
# =============================================================================

class TestPrimitives:
    """Test primitive parsers."""
    
    def test_char(self):
        p = char('a')
        assert p.parse("abc") == 'a'
    
    def test_char_fail(self):
        p = char('a')
        with pytest.raises(ValueError):
            p.parse("xyz")
    
    def test_string(self):
        p = string("hello")
        assert p.parse("hello world") == "hello"
    
    def test_string_fail(self):
        p = string("hello")
        with pytest.raises(ValueError):
            p.parse("world")
    
    def test_satisfy(self):
        p = satisfy(lambda c: c in 'aeiou', "vowel")
        assert p.parse("apple") == 'a'
    
    def test_digit(self):
        assert digit.parse("123") == '1'
    
    def test_letter(self):
        assert letter.parse("abc") == 'a'
    
    def test_any_char(self):
        assert any_char.parse("xyz") == 'x'
    
    def test_regex(self):
        p = regex(r'[a-z]+')
        assert p.parse("hello123") == "hello"
    
    def test_eof(self):
        p = string("end") << eof
        assert p.parse("end") == "end"
    
    def test_eof_fail(self):
        p = string("end") << eof
        with pytest.raises(ValueError):
            p.parse("end more")


# =============================================================================
# Combinator Tests
# =============================================================================

class TestCombinators:
    """Test parser combinators."""
    
    def test_sequence_operator(self):
        p = char('a') >> char('b')
        assert p.parse("ab") == 'b'
    
    def test_skip_operator(self):
        p = char('a') << char('b')
        assert p.parse("ab") == 'a'
    
    def test_choice_operator(self):
        p = char('a') | char('b')
        assert p.parse("abc") == 'a'
        assert p.parse("bcd") == 'b'
    
    def test_plus_operator(self):
        p = char('a') + char('b')
        assert p.parse("ab") == ('a', 'b')
    
    def test_pure(self):
        p = pure(42)
        assert p.parse("anything") == 42
    
    def test_fail(self):
        p = fail("expected something")
        with pytest.raises(ValueError):
            p.parse("anything")
    
    def test_sequence_function(self):
        p = sequence(char('a'), char('b'), char('c'))
        assert p.parse("abc") == ('a', 'b', 'c')
    
    def test_choice_function(self):
        p = choice(string("foo"), string("bar"), string("baz"))
        assert p.parse("bar") == "bar"


# =============================================================================
# Repetition Tests
# =============================================================================

class TestRepetition:
    """Test repetition combinators."""
    
    def test_many(self):
        p = char('a').many()
        assert p.parse("aaab") == ['a', 'a', 'a']
    
    def test_many_empty(self):
        p = char('a').many()
        assert p.parse("bbb") == []
    
    def test_many1(self):
        p = char('a').many1()
        assert p.parse("aaab") == ['a', 'a', 'a']
    
    def test_many1_fail(self):
        p = char('a').many1()
        with pytest.raises(ValueError):
            p.parse("bbb")
    
    def test_optional(self):
        p = char('a').optional()
        assert p.parse("abc") == 'a'
    
    def test_optional_missing(self):
        p = char('a').optional()
        assert p.parse("bcd") is None
    
    def test_sep_by(self):
        p = digit.sep_by(char(','))
        assert p.parse("1,2,3") == ['1', '2', '3']
    
    def test_sep_by_single(self):
        p = digit.sep_by(char(','))
        assert p.parse("1") == ['1']
    
    def test_sep_by_empty(self):
        p = digit.sep_by(char(','))
        assert p.parse("abc") == []
    
    def test_sep_by1(self):
        p = digit.sep_by1(char(','))
        assert p.parse("1,2,3") == ['1', '2', '3']


# =============================================================================
# Map and Transform Tests
# =============================================================================

class TestTransform:
    """Test result transformation."""
    
    def test_map(self):
        p = digit.map(int)
        assert p.parse("5") == 5
    
    def test_map_chain(self):
        p = digits.map(int).map(lambda x: x * 2)
        assert p.parse("10") == 20
    
    def test_flatmap(self):
        p = digit.flatmap(lambda d: string(d * int(d)))
        assert p.parse("3333") == "333"


# =============================================================================
# Expression Parsing Tests
# =============================================================================

class TestExpressions:
    """Test expression parsing with chainl/chainr."""
    
    def test_chainl_addition(self):
        add_op = char('+') >> pure(lambda a, b: a + b)
        expr = chainl(integer, add_op)
        assert expr.parse("1+2+3") == 6
    
    def test_chainl_subtraction(self):
        sub_op = char('-') >> pure(lambda a, b: a - b)
        expr = chainl(integer, sub_op)
        # Left associative: ((10-3)-2) = 5
        assert expr.parse("10-3-2") == 5
    
    def test_chainl_mixed(self):
        ops = (
            (char('+') >> pure(lambda a, b: a + b)) |
            (char('-') >> pure(lambda a, b: a - b))
        )
        expr = chainl(integer, ops)
        assert expr.parse("10+5-3") == 12
    
    def test_chainr_power(self):
        pow_op = char('^') >> pure(lambda a, b: a ** b)
        expr = chainr(integer, pow_op)
        # Right associative: 2^(3^2) = 2^9 = 512
        assert expr.parse("2^3^2") == 512
    
    def test_chainl_single(self):
        add_op = char('+') >> pure(lambda a, b: a + b)
        expr = chainl(integer, add_op)
        assert expr.parse("42") == 42


# =============================================================================
# Numeric Parser Tests
# =============================================================================

class TestNumeric:
    """Test numeric parsers."""
    
    def test_integer_positive(self):
        assert integer.parse("123") == 123
    
    def test_integer_negative(self):
        assert integer.parse("-456") == -456
    
    def test_floating(self):
        assert floating.parse("3.14") == pytest.approx(3.14)
    
    def test_floating_scientific(self):
        assert floating.parse("1.5e10") == pytest.approx(1.5e10)


# =============================================================================
# String Parser Tests
# =============================================================================

class TestStrings:
    """Test string parsers."""
    
    def test_double_quoted(self):
        assert double_quoted.parse('"hello"') == "hello"
    
    def test_double_quoted_escaped(self):
        assert double_quoted.parse('"hello\\nworld"') == "hello\nworld"
    
    def test_double_quoted_escaped_quote(self):
        assert double_quoted.parse('"say \\"hi\\""') == 'say "hi"'
    
    def test_single_quoted(self):
        from parsec import single_quoted
        assert single_quoted.parse("'hello'") == "hello"


# =============================================================================
# Between Tests
# =============================================================================

class TestBetween:
    """Test between combinator."""
    
    def test_between(self):
        p = word.between(char('('), char(')'))
        assert p.parse("(hello)") == "hello"
    
    def test_between_nested(self):
        # Parse nested brackets
        def expr():
            return word | lazy(expr).between(char('('), char(')'))
        
        p = lazy(expr)
        assert p.parse("hello") == "hello"
        assert p.parse("(hello)") == "hello"
        assert p.parse("((hello))") == "hello"


# =============================================================================
# Try/Backtracking Tests
# =============================================================================

class TestBacktracking:
    """Test backtracking with try_."""
    
    def test_try_allows_backtrack(self):
        # Without try_, choice fails after consuming 'hel'
        # With try_(), it backtracks
        p = string("hello").try_() | string("help")
        assert p.parse("help") == "help"
    
    def test_without_try_fails(self):
        # This demonstrates the issue try_() solves
        p1 = string("hel") >> string("lo")
        p2 = string("hel") >> string("p")
        
        # First parser will consume 'hel' then fail on 'p'
        # Without try_(), second parser won't be tried
        combined = p1 | p2
        
        # This might fail depending on implementation
        # The test documents expected behavior


# =============================================================================
# Label/Description Tests
# =============================================================================

class TestLabels:
    """Test error message customization."""
    
    def test_label(self):
        p = digit.many1().label("number")
        try:
            p.parse("abc")
            assert False, "Should have raised"
        except ValueError as e:
            assert "number" in str(e)
    
    def test_desc(self):
        p = letter.desc("letter")
        try:
            p.parse("123")
            assert False, "Should have raised"
        except ValueError as e:
            assert "letter" in str(e)


# =============================================================================
# Lazy Tests
# =============================================================================

class TestLazy:
    """Test lazy evaluation for recursive grammars."""
    
    def test_lazy_simple(self):
        p = lazy(lambda: char('a'))
        assert p.parse("abc") == 'a'
    
    def test_lazy_recursive(self):
        # expr = number | '(' expr ')'
        def make_expr():
            return integer | lazy(make_expr).between(char('('), char(')'))
        
        expr = lazy(make_expr)
        
        assert expr.parse("42") == 42
        assert expr.parse("(42)") == 42
        assert expr.parse("((42))") == 42


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_input(self):
        p = char('a').optional()
        assert p.parse("") is None
    
    def test_parse_all_leaves_nothing(self):
        p = string("hello")
        assert p.parse_all("hello") == "hello"
    
    def test_parse_all_fails_with_remaining(self):
        p = string("hello")
        with pytest.raises(ValueError):
            p.parse_all("hello world")
    
    def test_try_parse_returns_none(self):
        p = string("hello")
        assert p.try_parse("world") is None
    
    def test_try_parse_returns_value(self):
        p = string("hello")
        assert p.try_parse("hello") == "hello"


# =============================================================================
# Complex Grammar Tests
# =============================================================================

class TestComplexGrammars:
    """Test complex grammar compositions."""
    
    def test_json_like_array(self):
        # Parse [1, 2, 3]
        num = integer
        sep = spaces >> char(',') << spaces
        arr = num.sep_by(sep).between(
            char('[') << spaces,
            spaces >> char(']')
        )
        
        assert arr.parse("[1,2,3]") == [1, 2, 3]
        assert arr.parse("[ 1 , 2 , 3 ]") == [1, 2, 3]
    
    def test_key_value_pairs(self):
        # Parse "key: value"
        key = word
        value = word
        pair = (key << spaces << char(':') << spaces) + value
        
        assert pair.parse("name: John") == ("name", "John")
    
    def test_simple_s_expression(self):
        # Parse (+ 1 2)
        lparen = char('(') << spaces
        rparen = spaces >> char(')')
        symbol = word
        num = integer
        
        atom = symbol.map(str) | num.map(str)
        
        def sexp():
            return atom | lazy(sexp).sep_by(spaces1).between(lparen, rparen).map(tuple)
        
        expr = lazy(sexp)
        
        assert expr.parse("42") == "42"
        assert expr.parse("hello") == "hello"


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization functions."""
    
    def test_visualize_success(self):
        result = visualize_parse(integer, "123")
        assert "Success" in result
        assert "123" in result
    
    def test_visualize_failure(self):
        result = visualize_parse(integer, "abc")
        assert "Failure" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
