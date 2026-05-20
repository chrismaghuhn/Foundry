"""Tests for rune."""

import pytest
import math
from rune import (
    Rune,
    CompiledExpression,
    RuType,
    TypeSignature,
    ExecutionLimits,
    RuneError,
    LexerError,
    ParseError,
    RuntimeError,
    FuelExhaustedError,
    DepthExceededError,
    Lexer,
    Parser,
    TokenType,
)


# =============================================================================
# Lexer Tests
# =============================================================================

class TestLexer:
    """Test tokenization."""
    
    def test_numbers(self):
        """Tokenize integers and floats."""
        tokens = Lexer("42 3.14 0 100.0").tokenize()
        
        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(numbers) == 4
        assert numbers[0].value == 42.0
        assert numbers[1].value == 3.14
    
    def test_strings(self):
        """Tokenize string literals."""
        tokens = Lexer('"hello" \'world\'').tokenize()
        
        strings = [t for t in tokens if t.type == TokenType.STRING]
        assert len(strings) == 2
        assert strings[0].value == "hello"
        assert strings[1].value == "world"
    
    def test_string_escapes(self):
        """Handle escape sequences."""
        tokens = Lexer(r'"hello\nworld\t!"').tokenize()
        
        assert tokens[0].value == "hello\nworld\t!"
    
    def test_keywords(self):
        """Recognize keywords."""
        tokens = Lexer("true false null and or not if then else").tokenize()
        
        types = [t.type for t in tokens[:-1]]  # Exclude EOF
        assert TokenType.TRUE in types
        assert TokenType.FALSE in types
        assert TokenType.NULL in types
        assert TokenType.AND in types
        assert TokenType.IF in types
    
    def test_operators(self):
        """Tokenize operators."""
        tokens = Lexer("+ - * / % ** == != < > <= >=").tokenize()
        
        types = [t.type for t in tokens[:-1]]
        assert TokenType.PLUS in types
        assert TokenType.POWER in types
        assert TokenType.EQ in types
        assert TokenType.LE in types
    
    def test_identifiers(self):
        """Tokenize identifiers."""
        tokens = Lexer("foo bar_baz _private x123").tokenize()
        
        idents = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        assert len(idents) == 4
        assert idents[0].value == "foo"
    
    def test_whitespace_handling(self):
        """Whitespace is ignored."""
        tokens1 = Lexer("1+2").tokenize()
        tokens2 = Lexer("  1  +  2  ").tokenize()
        
        assert len(tokens1) == len(tokens2)
    
    def test_unterminated_string(self):
        """Unterminated string raises error."""
        with pytest.raises(LexerError):
            Lexer('"hello').tokenize()
    
    def test_newline_in_string(self):
        """Newline in string raises error."""
        with pytest.raises(LexerError):
            Lexer('"hello\nworld"').tokenize()
    
    def test_unknown_escape(self):
        """Unknown escape sequence raises error."""
        with pytest.raises(LexerError):
            Lexer(r'"hello\x"').tokenize()


# =============================================================================
# Parser Tests
# =============================================================================

class TestParser:
    """Test parsing."""
    
    def parse(self, expr: str):
        tokens = Lexer(expr).tokenize()
        return Parser(tokens).parse()
    
    def test_number_literal(self):
        """Parse number literals."""
        from rune import NumberLiteral
        
        ast = self.parse("42")
        assert isinstance(ast, NumberLiteral)
        assert ast.value == 42.0
    
    def test_string_literal(self):
        """Parse string literals."""
        from rune import StringLiteral
        
        ast = self.parse('"hello"')
        assert isinstance(ast, StringLiteral)
        assert ast.value == "hello"
    
    def test_binary_ops(self):
        """Parse binary operations."""
        from rune import BinaryOp
        
        ast = self.parse("1 + 2")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "+"
    
    def test_operator_precedence(self):
        """Respect operator precedence."""
        from rune import BinaryOp
        
        # Multiplication before addition
        ast = self.parse("1 + 2 * 3")
        assert ast.op == "+"
        assert ast.right.op == "*"
    
    def test_power_right_associative(self):
        """Power is right-associative."""
        from rune import BinaryOp
        
        # 2 ** 3 ** 2 should be 2 ** (3 ** 2) = 512
        ast = self.parse("2 ** 3 ** 2")
        assert ast.op == "**"
        assert ast.right.op == "**"  # Right side is also power
    
    def test_parentheses(self):
        """Parentheses override precedence."""
        from rune import BinaryOp
        
        ast = self.parse("(1 + 2) * 3")
        assert ast.op == "*"
        assert ast.left.op == "+"
    
    def test_unary_minus(self):
        """Parse unary minus."""
        from rune import UnaryOp
        
        ast = self.parse("-42")
        assert isinstance(ast, UnaryOp)
        assert ast.op == "-"
    
    def test_conditional(self):
        """Parse if-then-else."""
        from rune import Conditional
        
        ast = self.parse("if true then 1 else 2")
        assert isinstance(ast, Conditional)
    
    def test_ternary(self):
        """Parse ternary operator."""
        from rune import TernaryOp
        
        ast = self.parse("x > 0 ? x : -x")
        assert isinstance(ast, TernaryOp)
    
    def test_function_call(self):
        """Parse function call."""
        from rune import FunctionCall
        
        ast = self.parse("max(1, 2, 3)")
        assert isinstance(ast, FunctionCall)
        assert ast.name == "max"
        assert len(ast.arguments) == 3
    
    def test_list_literal(self):
        """Parse list literal."""
        from rune import ListLiteral
        
        ast = self.parse("[1, 2, 3]")
        assert isinstance(ast, ListLiteral)
        assert len(ast.elements) == 3
    
    def test_index_access(self):
        """Parse index access."""
        from rune import IndexAccess
        
        ast = self.parse("items[0]")
        assert isinstance(ast, IndexAccess)
    
    def test_property_access(self):
        """Parse property access."""
        from rune import PropertyAccess
        
        ast = self.parse("obj.name")
        assert isinstance(ast, PropertyAccess)
        assert ast.property == "name"
    
    def test_trailing_tokens(self):
        """Trailing tokens raise error."""
        with pytest.raises(ParseError):
            self.parse("1 + 2 3")


# =============================================================================
# Evaluation Tests
# =============================================================================

class TestEvaluation:
    """Test expression evaluation."""
    
    def setup_method(self):
        self.engine = Rune()
    
    def test_literals(self):
        """Evaluate literals."""
        assert self.engine.evaluate("42") == 42
        assert self.engine.evaluate("3.14") == 3.14
        assert self.engine.evaluate('"hello"') == "hello"
        assert self.engine.evaluate("true") is True
        assert self.engine.evaluate("false") is False
        assert self.engine.evaluate("null") is None
    
    def test_arithmetic(self):
        """Evaluate arithmetic expressions."""
        assert self.engine.evaluate("1 + 2") == 3
        assert self.engine.evaluate("5 - 3") == 2
        assert self.engine.evaluate("4 * 3") == 12
        assert self.engine.evaluate("10 / 4") == 2.5
        assert self.engine.evaluate("10 % 3") == 1
        assert self.engine.evaluate("2 ** 10") == 1024
    
    def test_comparison(self):
        """Evaluate comparisons."""
        assert self.engine.evaluate("1 < 2") is True
        assert self.engine.evaluate("2 > 1") is True
        assert self.engine.evaluate("1 <= 1") is True
        assert self.engine.evaluate("1 >= 1") is True
        assert self.engine.evaluate("1 == 1") is True
        assert self.engine.evaluate("1 != 2") is True
    
    def test_logical(self):
        """Evaluate logical operations."""
        assert self.engine.evaluate("true and true") is True
        assert self.engine.evaluate("true and false") is False
        assert self.engine.evaluate("true or false") is True
        assert self.engine.evaluate("not true") is False
    
    def test_short_circuit_and(self):
        """AND short-circuits on false."""
        # If AND didn't short-circuit, division by zero would fail
        result = self.engine.evaluate("false and (1/0 > 0)")
        assert result is False
    
    def test_short_circuit_or(self):
        """OR short-circuits on true."""
        result = self.engine.evaluate("true or (1/0 > 0)")
        assert result is True
    
    def test_string_concatenation(self):
        """Strings concatenate with +."""
        assert self.engine.evaluate('"hello" + " " + "world"') == "hello world"
    
    def test_variables(self):
        """Access variables from context."""
        result = self.engine.evaluate("x + y", {"x": 10, "y": 20})
        assert result == 30
    
    def test_unknown_variable(self):
        """Unknown variables are null."""
        assert self.engine.evaluate("unknown") is None
    
    def test_conditional(self):
        """Evaluate if-then-else."""
        assert self.engine.evaluate("if true then 1 else 2") == 1
        assert self.engine.evaluate("if false then 1 else 2") == 2
    
    def test_ternary(self):
        """Evaluate ternary operator."""
        assert self.engine.evaluate("true ? 1 : 2") == 1
        assert self.engine.evaluate("false ? 1 : 2") == 2
    
    def test_list_literal(self):
        """Evaluate list literal."""
        result = self.engine.evaluate("[1, 2, 3]")
        assert result == [1, 2, 3]
    
    def test_index_access(self):
        """Access list elements."""
        result = self.engine.evaluate("items[0]", {"items": [10, 20, 30]})
        assert result == 10
    
    def test_index_out_of_bounds(self):
        """Out of bounds index returns null."""
        result = self.engine.evaluate("items[100]", {"items": [1, 2, 3]})
        assert result is None
    
    def test_property_access(self):
        """Access object properties."""
        result = self.engine.evaluate("user.name", {"user": {"name": "Alice"}})
        assert result == "Alice"
    
    def test_length_property(self):
        """Access .length property."""
        assert self.engine.evaluate('"hello".length') == 5
        assert self.engine.evaluate("items.length", {"items": [1, 2, 3]}) == 3
    
    def test_division_by_zero(self):
        """Division by zero raises error."""
        with pytest.raises(RuntimeError):
            self.engine.evaluate("1 / 0")
    
    def test_numeric_overflow(self):
        """Numeric overflow raises error."""
        with pytest.raises(RuntimeError):
            self.engine.evaluate("10 ** 1000")


# =============================================================================
# Built-in Function Tests
# =============================================================================

class TestBuiltinFunctions:
    """Test built-in functions."""
    
    def setup_method(self):
        self.engine = Rune()
    
    def test_math_functions(self):
        """Test math functions."""
        assert self.engine.evaluate("abs(-5)") == 5
        assert self.engine.evaluate("floor(3.7)") == 3
        assert self.engine.evaluate("ceil(3.2)") == 4
        assert self.engine.evaluate("round(3.5)") == 4
        assert self.engine.evaluate("sqrt(16)") == 4
    
    def test_min_max(self):
        """Test min/max functions."""
        assert self.engine.evaluate("min(3, 1, 2)") == 1
        assert self.engine.evaluate("max(3, 1, 2)") == 3
    
    def test_string_functions(self):
        """Test string functions."""
        assert self.engine.evaluate("len('hello')") == 5
        assert self.engine.evaluate("upper('hello')") == "HELLO"
        assert self.engine.evaluate("lower('HELLO')") == "hello"
        assert self.engine.evaluate("trim('  hi  ')") == "hi"
    
    def test_string_predicates(self):
        """Test string predicate functions."""
        assert self.engine.evaluate('contains("hello", "ell")') is True
        assert self.engine.evaluate('starts_with("hello", "he")') is True
        assert self.engine.evaluate('ends_with("hello", "lo")') is True
    
    def test_list_functions(self):
        """Test list functions."""
        assert self.engine.evaluate("first([1, 2, 3])") == 1
        assert self.engine.evaluate("last([1, 2, 3])") == 3
        assert self.engine.evaluate("sum([1, 2, 3])") == 6
        assert self.engine.evaluate("avg([1, 2, 3, 4])") == 2.5
        assert self.engine.evaluate("count([1, 2, 3])") == 3
    
    def test_sort_reverse(self):
        """Test sort and reverse."""
        assert self.engine.evaluate("sort([3, 1, 2])") == [1, 2, 3]
        assert self.engine.evaluate("reverse([1, 2, 3])") == [3, 2, 1]
    
    def test_unique(self):
        """Test unique function."""
        assert self.engine.evaluate("unique([1, 2, 2, 3, 1])") == [1, 2, 3]
    
    def test_slice(self):
        """Test slice function."""
        assert self.engine.evaluate("slice([1, 2, 3, 4], 1, 3)") == [2, 3]
    
    def test_includes(self):
        """Test includes function."""
        assert self.engine.evaluate("includes([1, 2, 3], 2)") is True
        assert self.engine.evaluate("includes([1, 2, 3], 5)") is False
    
    def test_type_conversion(self):
        """Test type conversion functions."""
        assert self.engine.evaluate("str(42)") == "42"
        assert self.engine.evaluate('num("42")') == 42.0
        assert self.engine.evaluate("bool(1)") is True
        assert self.engine.evaluate("bool(0)") is False
    
    def test_default(self):
        """Test default function."""
        assert self.engine.evaluate("default(null, 42)") == 42
        assert self.engine.evaluate("default(10, 42)") == 10
    
    def test_coalesce(self):
        """Test coalesce function."""
        assert self.engine.evaluate("coalesce(null, null, 5)") == 5
        assert self.engine.evaluate("coalesce(1, 2, 3)") == 1
    
    def test_unknown_function(self):
        """Unknown function raises error."""
        with pytest.raises(RuntimeError):
            self.engine.evaluate("unknown_func()")


# =============================================================================
# Resource Limit Tests
# =============================================================================

class TestResourceLimits:
    """Test resource limiting."""
    
    def test_fuel_exhaustion(self):
        """Expression exceeding fuel limit fails."""
        # Very low fuel limit
        engine = Rune(limits=ExecutionLimits(max_fuel=10))
        
        # This needs more than 10 operations
        with pytest.raises(FuelExhaustedError):
            engine.evaluate("1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9 + 10")
    
    def test_depth_exceeded(self):
        """Deep nesting exceeds depth limit."""
        engine = Rune(limits=ExecutionLimits(max_depth=1))
        
        # Register function
        engine.register_function("f", lambda x: x, [RuType.NUMBER], RuType.NUMBER)
        
        # f(f(1)) needs depth 2, should exceed limit of 1
        with pytest.raises(DepthExceededError):
            engine.evaluate("f(f(1))")
    
    def test_string_length_limit(self):
        """String exceeding length limit fails."""
        engine = Rune(limits=ExecutionLimits(max_string_length=20))
        
        # This should fail - 30 chars > 20 limit
        with pytest.raises(RuntimeError):
            engine.evaluate(
                'a + a + a',
                {"a": "0123456789"}  # 10 chars * 3 = 30
            )
    
    def test_list_length_limit(self):
        """List exceeding length limit fails."""
        engine = Rune(limits=ExecutionLimits(max_list_length=10))
        
        with pytest.raises(RuntimeError):
            engine.evaluate("[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]")


# =============================================================================
# Compiled Expression Tests
# =============================================================================

class TestCompiledExpression:
    """Test pre-compiled expressions."""
    
    def test_reuse_compiled(self):
        """Compiled expression can be reused."""
        engine = Rune()
        compiled = engine.compile("x * 2")
        
        assert compiled.evaluate({"x": 5}) == 10
        assert compiled.evaluate({"x": 10}) == 20
        assert compiled.evaluate({"x": -3}) == -6
    
    def test_different_variables(self):
        """Same expression with different variables."""
        engine = Rune()
        compiled = engine.compile("price * quantity * (1 - discount)")
        
        result1 = compiled.evaluate({
            "price": 100,
            "quantity": 5,
            "discount": 0.1
        })
        
        result2 = compiled.evaluate({
            "price": 50,
            "quantity": 10,
            "discount": 0.2
        })
        
        assert result1 == 450  # 100 * 5 * 0.9
        assert result2 == 400  # 50 * 10 * 0.8


# =============================================================================
# Custom Function Tests
# =============================================================================

class TestCustomFunctions:
    """Test user-registered functions."""
    
    def test_register_simple_function(self):
        """Register and use simple function."""
        engine = Rune()
        engine.register_function("double", lambda x: x * 2, [RuType.NUMBER], RuType.NUMBER)
        
        assert engine.evaluate("double(21)") == 42
    
    def test_register_multi_param_function(self):
        """Register function with multiple parameters."""
        engine = Rune()
        engine.register_function(
            "clamp", 
            lambda x, lo, hi: max(lo, min(x, hi)),
            [RuType.NUMBER, RuType.NUMBER, RuType.NUMBER],
            RuType.NUMBER
        )
        
        assert engine.evaluate("clamp(5, 0, 10)") == 5
        assert engine.evaluate("clamp(-5, 0, 10)") == 0
        assert engine.evaluate("clamp(15, 0, 10)") == 10
    
    def test_wrong_arity(self):
        """Wrong number of arguments raises error."""
        engine = Rune()
        engine.register_function("double", lambda x: x * 2, [RuType.NUMBER], RuType.NUMBER)
        
        with pytest.raises(RuntimeError):
            engine.evaluate("double(1, 2)")  # Too many args
    
    def test_function_exception(self):
        """Function exception is caught."""
        engine = Rune()
        engine.register_function(
            "fail",
            lambda: (_ for _ in ()).throw(ValueError("oops")),
            [],
            RuType.ANY
        )
        
        # Actually let's use a simpler failing function
        def always_fail():
            raise ValueError("intentional failure")
        
        engine.register_function("fail", always_fail, [], RuType.ANY)
        
        with pytest.raises(RuntimeError) as exc_info:
            engine.evaluate("fail()")
        
        assert "intentional failure" in str(exc_info.value)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_pricing_formula(self):
        """Complex pricing formula."""
        engine = Rune()
        
        result = engine.evaluate(
            "base_price * quantity * (1 - discount) + if quantity > 100 then 0 else shipping",
            {
                "base_price": 10.0,
                "quantity": 50,
                "discount": 0.15,
                "shipping": 5.0
            }
        )
        
        # 10 * 50 * 0.85 + 5 = 430
        assert result == 430.0
    
    def test_validation_rule(self):
        """Validation rule expression."""
        engine = Rune()
        
        rule = 'age >= 18 and country == "US" and not banned'
        
        assert engine.evaluate(rule, {"age": 25, "country": "US", "banned": False}) is True
        assert engine.evaluate(rule, {"age": 16, "country": "US", "banned": False}) is False
        assert engine.evaluate(rule, {"age": 25, "country": "CA", "banned": False}) is False
    
    def test_list_processing(self):
        """Process list of data."""
        engine = Rune()
        
        # Calculate total from list of items
        result = engine.evaluate(
            "sum([10, 20, 30]) * (1 - discount)",
            {"discount": 0.1}
        )
        
        assert result == 54.0  # 60 * 0.9
    
    def test_nested_data_access(self):
        """Access nested data structures."""
        engine = Rune()
        
        data = {
            "user": {
                "name": "Alice",
                "scores": [85, 90, 95]
            }
        }
        
        assert engine.evaluate("user.name", data) == "Alice"
        assert engine.evaluate("user.scores[1]", data) == 90
        assert engine.evaluate("avg(user.scores)", data) == 90.0
    
    def test_complex_conditional(self):
        """Complex conditional logic."""
        engine = Rune()
        
        expr = """
            if status == "premium" then 
                base * 0.8
            else if status == "member" then
                base * 0.9
            else
                base
        """
        
        assert engine.evaluate(expr, {"status": "premium", "base": 100}) == 80.0
        assert engine.evaluate(expr, {"status": "member", "base": 100}) == 90.0
        assert engine.evaluate(expr, {"status": "guest", "base": 100}) == 100.0


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        self.engine = Rune()
    
    def test_empty_list(self):
        """Handle empty list."""
        assert self.engine.evaluate("[]") == []
        assert self.engine.evaluate("first([])") is None
        assert self.engine.evaluate("sum([])") == 0
    
    def test_empty_string(self):
        """Handle empty string."""
        assert self.engine.evaluate('""') == ""
        assert self.engine.evaluate('"".length') == 0
    
    def test_null_handling(self):
        """Null values handled gracefully."""
        assert self.engine.evaluate("null == null") is True
        assert self.engine.evaluate("default(null, 0)") == 0
        
        # null arithmetic should fail
        with pytest.raises(RuntimeError):
            self.engine.evaluate("null + 1")
    
    def test_boolean_truthiness(self):
        """Test truthiness of various values."""
        # Truthy
        assert self.engine.evaluate("if 1 then true else false") is True
        assert self.engine.evaluate('if "x" then true else false') is True
        assert self.engine.evaluate("if [1] then true else false") is True
        
        # Falsy
        assert self.engine.evaluate("if 0 then true else false") is False
        assert self.engine.evaluate('if "" then true else false') is False
        assert self.engine.evaluate("if [] then true else false") is False
        assert self.engine.evaluate("if null then true else false") is False
    
    def test_comparison_different_types(self):
        """Comparing different types."""
        # Equality of different types is false (type-safe comparison)
        assert self.engine.evaluate("1 == '1'") is False
        assert self.engine.evaluate("true == 1") is False  # Boolean != number
        assert self.engine.evaluate("1.0 == 1") is True  # Float and int can compare
    
    def test_very_long_expression(self):
        """Handle long expressions."""
        # Build expression: 1 + 1 + 1 + ... (100 times)
        expr = " + ".join(["1"] * 100)
        result = self.engine.evaluate(expr)
        assert result == 100
    
    def test_deeply_nested_parens(self):
        """Handle deeply nested parentheses."""
        expr = "(" * 20 + "1 + 2" + ")" * 20
        assert self.engine.evaluate(expr) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
