"""Tests for prism."""

import pytest
from prism import (
    Prism,
    query,
    Lexer,
    Parser,
    Evaluator,
    LexerError,
    ParseError,
    EvalError,
    TokenType,
)


# =============================================================================
# Lexer Tests
# =============================================================================

class TestLexer:
    """Test tokenization."""
    
    def test_numbers(self):
        """Tokenize integers and floats."""
        tokens = Lexer("42 3.14 0 -5").tokenize()
        
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[1].value == 3.14
    
    def test_strings(self):
        """Tokenize string literals."""
        tokens = Lexer('"hello" \'world\'').tokenize()
        
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "world"
    
    def test_string_escapes(self):
        """Handle escape sequences."""
        tokens = Lexer(r'"hello\nworld"').tokenize()
        
        assert tokens[0].value == "hello\nworld"
    
    def test_identifiers(self):
        """Tokenize identifiers."""
        tokens = Lexer("foo bar_baz _private").tokenize()
        
        assert tokens[0].type == TokenType.IDENT
        assert tokens[0].value == "foo"
        assert tokens[1].value == "bar_baz"
    
    def test_keywords(self):
        """Recognize keywords."""
        tokens = Lexer("true false null and or not").tokenize()
        
        assert tokens[0].type == TokenType.TRUE
        assert tokens[1].type == TokenType.FALSE
        assert tokens[2].type == TokenType.NULL
        assert tokens[3].type == TokenType.AND
    
    def test_operators(self):
        """Tokenize operators."""
        tokens = Lexer("+ - * / == != < > <= >=").tokenize()
        
        types = [t.type for t in tokens[:-1]]  # Exclude EOF
        assert TokenType.PLUS in types
        assert TokenType.EQ in types
        assert TokenType.LE in types
    
    def test_punctuation(self):
        """Tokenize punctuation."""
        tokens = Lexer(". | , : ? ( ) [ ] { }").tokenize()
        
        types = [t.type for t in tokens[:-1]]
        assert TokenType.DOT in types
        assert TokenType.PIPE in types
        assert TokenType.LPAREN in types
    
    def test_comments(self):
        """Ignore comments."""
        tokens = Lexer("42 # this is a comment\n43").tokenize()
        
        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(numbers) == 2
        assert numbers[0].value == 42
        assert numbers[1].value == 43
    
    def test_whitespace(self):
        """Handle whitespace."""
        tokens = Lexer("  foo  \n\t  bar  ").tokenize()
        
        idents = [t for t in tokens if t.type == TokenType.IDENT]
        assert len(idents) == 2
    
    def test_invalid_character(self):
        """Reject invalid characters."""
        with pytest.raises(LexerError):
            Lexer("foo ^ bar").tokenize()  # ^ is not a valid token


# =============================================================================
# Parser Tests
# =============================================================================

class TestParser:
    """Test parsing."""
    
    def parse(self, query_str: str):
        tokens = Lexer(query_str).tokenize()
        return Parser(tokens).parse()
    
    def test_number_literal(self):
        """Parse number literals."""
        from prism import NumberLiteral
        
        ast = self.parse("42")
        assert isinstance(ast, NumberLiteral)
        assert ast.value == 42
    
    def test_string_literal(self):
        """Parse string literals."""
        from prism import StringLiteral
        
        ast = self.parse('"hello"')
        assert isinstance(ast, StringLiteral)
        assert ast.value == "hello"
    
    def test_property_access(self):
        """Parse property access."""
        from prism import PropertyAccess, CurrentValue
        
        ast = self.parse(".name")
        assert isinstance(ast, PropertyAccess)
        assert isinstance(ast.obj, CurrentValue)
        assert ast.name == "name"
    
    def test_nested_property(self):
        """Parse nested property access."""
        ast = self.parse(".user.profile.name")
        # Should be PropertyAccess(PropertyAccess(PropertyAccess(...)))
        assert ast.name == "name"
    
    def test_index_access(self):
        """Parse index access."""
        from prism import IndexAccess
        
        ast = self.parse(".items[0]")
        assert isinstance(ast, IndexAccess)
    
    def test_binary_operators(self):
        """Parse binary operations."""
        from prism import BinaryOp
        
        ast = self.parse("1 + 2 * 3")
        # Should respect precedence: 1 + (2 * 3)
        assert isinstance(ast, BinaryOp)
        assert ast.op == "+"
        assert isinstance(ast.right, BinaryOp)
        assert ast.right.op == "*"
    
    def test_comparison(self):
        """Parse comparisons."""
        from prism import BinaryOp
        
        ast = self.parse(".age > 18")
        assert isinstance(ast, BinaryOp)
        assert ast.op == ">"
    
    def test_logical_operators(self):
        """Parse logical operators."""
        from prism import BinaryOp
        
        ast = self.parse(".a and .b or .c")
        assert isinstance(ast, BinaryOp)
        assert ast.op == "or"  # Lower precedence
    
    def test_pipe_expression(self):
        """Parse pipe expressions."""
        from prism import PipeExpr
        
        ast = self.parse(".users | filter(.active)")
        assert isinstance(ast, PipeExpr)
    
    def test_function_call(self):
        """Parse function calls."""
        from prism import FunctionCall
        
        ast = self.parse("map(.name)")
        assert isinstance(ast, FunctionCall)
        assert len(ast.args) == 1
    
    def test_array_literal(self):
        """Parse array literals."""
        from prism import ArrayLiteral
        
        ast = self.parse("[1, 2, 3]")
        assert isinstance(ast, ArrayLiteral)
        assert len(ast.elements) == 3
    
    def test_object_literal(self):
        """Parse object literals."""
        from prism import ObjectLiteral
        
        ast = self.parse('{name: "test", value: 42}')
        assert isinstance(ast, ObjectLiteral)
        assert len(ast.pairs) == 2
    
    def test_conditional(self):
        """Parse conditional expressions."""
        from prism import ConditionalExpr
        
        ast = self.parse(".x > 0 ? .x : 0")
        assert isinstance(ast, ConditionalExpr)
    
    def test_unary_operators(self):
        """Parse unary operators."""
        from prism import UnaryOp
        
        ast = self.parse("not .active")
        assert isinstance(ast, UnaryOp)
        assert ast.op == "not"
    
    def test_parentheses(self):
        """Parse parenthesized expressions."""
        from prism import BinaryOp
        
        ast = self.parse("(1 + 2) * 3")
        assert ast.op == "*"
        assert ast.left.op == "+"


# =============================================================================
# Evaluation Tests
# =============================================================================

class TestEvaluation:
    """Test query evaluation."""
    
    def test_literal_values(self):
        """Evaluate literals."""
        assert query("42", {}) == 42
        assert query('"hello"', {}) == "hello"
        assert query("true", {}) is True
        assert query("null", {}) is None
    
    def test_property_access(self):
        """Access object properties."""
        data = {"name": "Alice", "age": 30}
        
        assert query(".name", data) == "Alice"
        assert query(".age", data) == 30
        assert query(".missing", data) is None
    
    def test_nested_access(self):
        """Access nested properties."""
        data = {"user": {"profile": {"name": "Bob"}}}
        
        assert query(".user.profile.name", data) == "Bob"
    
    def test_index_access(self):
        """Access array elements."""
        data = {"items": ["a", "b", "c"]}
        
        assert query(".items[0]", data) == "a"
        assert query(".items[2]", data) == "c"
        assert query(".items[-1]", data) == "c"
    
    def test_slice_access(self):
        """Slice arrays."""
        data = [1, 2, 3, 4, 5]
        
        assert query(".[1:3]", data) == [2, 3]
        assert query(".[:2]", data) == [1, 2]
        assert query(".[3:]", data) == [4, 5]
    
    def test_arithmetic(self):
        """Evaluate arithmetic."""
        data = {"x": 10, "y": 3}
        
        assert query(".x + .y", data) == 13
        assert query(".x - .y", data) == 7
        assert query(".x * .y", data) == 30
        assert query(".x / .y", data) == pytest.approx(3.333, rel=0.01)
        assert query(".x % .y", data) == 1
    
    def test_comparison(self):
        """Evaluate comparisons."""
        data = {"age": 25}
        
        assert query(".age > 18", data) is True
        assert query(".age < 18", data) is False
        assert query(".age == 25", data) is True
        assert query(".age != 25", data) is False
    
    def test_logical_operators(self):
        """Evaluate logical operators."""
        data = {"a": True, "b": False}
        
        assert query(".a and .b", data) is False
        assert query(".a or .b", data) is True
        assert query("not .b", data) is True
    
    def test_pipe_expression(self):
        """Evaluate pipe expressions."""
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        
        result = query(".users | first", data)
        assert result == {"name": "Alice"}
    
    def test_conditional(self):
        """Evaluate conditionals."""
        assert query(".x > 0 ? .x : 0", {"x": 5}) == 5
        assert query(".x > 0 ? .x : 0", {"x": -5}) == 0
    
    def test_array_literal(self):
        """Evaluate array literals."""
        data = {"a": 1, "b": 2}
        
        assert query("[.a, .b, 3]", data) == [1, 2, 3]
    
    def test_object_literal(self):
        """Evaluate object literals."""
        data = {"name": "Alice"}
        
        result = query('{greeting: "Hello", user: .name}', data)
        assert result == {"greeting": "Hello", "user": "Alice"}


# =============================================================================
# Builtin Function Tests
# =============================================================================

class TestBuiltinFunctions:
    """Test builtin functions."""
    
    def test_map(self):
        """Test map function."""
        data = [{"x": 1}, {"x": 2}, {"x": 3}]
        
        result = query(". | map(.x)", data)
        assert result == [1, 2, 3]
    
    def test_filter(self):
        """Test filter function."""
        data = [1, 2, 3, 4, 5]
        
        result = query(". | filter(. > 2)", data)
        assert result == [3, 4, 5]
    
    def test_select(self):
        """Test select function."""
        data = [{"name": "Alice", "age": 30, "city": "NYC"}]
        
        result = query(". | select(.name, .age)", data)
        assert result == [{"name": "Alice", "age": 30}]
    
    def test_sort(self):
        """Test sort function."""
        data = [3, 1, 4, 1, 5]
        
        assert query(". | sort", data) == [1, 1, 3, 4, 5]
    
    def test_sort_by_key(self):
        """Test sort with key."""
        data = [{"name": "Bob"}, {"name": "Alice"}]
        
        result = query(". | sort(.name)", data)
        assert result[0]["name"] == "Alice"
    
    def test_reverse(self):
        """Test reverse function."""
        assert query(". | reverse", [1, 2, 3]) == [3, 2, 1]
        assert query(". | reverse", "hello") == "olleh"
    
    def test_unique(self):
        """Test unique function."""
        data = [1, 2, 2, 3, 3, 3]
        
        assert query(". | unique", data) == [1, 2, 3]
    
    def test_flatten(self):
        """Test flatten function."""
        data = [[1, 2], [3, 4], [5]]
        
        assert query(". | flatten", data) == [1, 2, 3, 4, 5]
    
    def test_group(self):
        """Test group function."""
        data = [
            {"type": "a", "val": 1},
            {"type": "b", "val": 2},
            {"type": "a", "val": 3},
        ]
        
        result = query(". | group(.type)", data)
        assert len(result["a"]) == 2
        assert len(result["b"]) == 1
    
    def test_first_last(self):
        """Test first and last functions."""
        data = [1, 2, 3]
        
        assert query(". | first", data) == 1
        assert query(". | last", data) == 3
    
    def test_take_drop(self):
        """Test take and drop functions."""
        data = [1, 2, 3, 4, 5]
        
        assert query(". | take(3)", data) == [1, 2, 3]
        assert query(". | drop(3)", data) == [4, 5]
    
    def test_length(self):
        """Test length function."""
        assert query(". | length", [1, 2, 3]) == 3
        assert query(". | length", "hello") == 5
        assert query(". | length", {"a": 1}) == 1
    
    def test_count(self):
        """Test count function."""
        data = [1, 2, 3, 4, 5]
        
        assert query(". | count", data) == 5
        assert query(". | count(. > 2)", data) == 3
    
    def test_sum_avg(self):
        """Test sum and avg functions."""
        data = [1, 2, 3, 4, 5]
        
        assert query(". | sum", data) == 15
        assert query(". | avg", data) == 3.0
    
    def test_min_max(self):
        """Test min and max functions."""
        data = [3, 1, 4, 1, 5]
        
        assert query(". | min", data) == 1
        assert query(". | max", data) == 5
    
    def test_join_split(self):
        """Test join and split functions."""
        assert query('. | join("-")', ["a", "b", "c"]) == "a-b-c"
        assert query('. | split("-")', "a-b-c") == ["a", "b", "c"]
    
    def test_string_functions(self):
        """Test string functions."""
        assert query(". | trim", "  hello  ") == "hello"
        assert query(". | upper", "hello") == "HELLO"
        assert query(". | lower", "HELLO") == "hello"
    
    def test_contains(self):
        """Test contains function."""
        assert query('. | contains("ll")', "hello") is True
        assert query(". | contains(2)", [1, 2, 3]) is True
    
    def test_starts_ends_with(self):
        """Test starts_with and ends_with."""
        assert query('. | starts_with("he")', "hello") is True
        assert query('. | ends_with("lo")', "hello") is True
    
    def test_replace(self):
        """Test replace function."""
        assert query('. | replace("l", "L")', "hello") == "heLLo"
    
    def test_type(self):
        """Test type function."""
        assert query(". | type", 42) == "integer"
        assert query(". | type", 3.14) == "number"
        assert query(". | type", "hi") == "string"
        assert query(". | type", []) == "array"
        assert query(". | type", {}) == "object"
        assert query(". | type", None) == "null"
    
    def test_keys_values(self):
        """Test keys and values functions."""
        data = {"a": 1, "b": 2}
        
        assert set(query(". | keys", data)) == {"a", "b"}
        assert set(query(". | values", data)) == {1, 2}
    
    def test_entries_from_entries(self):
        """Test entries and from_entries."""
        data = {"a": 1, "b": 2}
        
        entries = query(". | entries", data)
        assert len(entries) == 2
        
        restored = query(". | from_entries", entries)
        assert restored == data
    
    def test_default(self):
        """Test default function."""
        assert query(". | default(42)", None) == 42
        assert query(". | default(42)", 10) == 10


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_complex_query(self):
        """Complex real-world query."""
        data = {
            "users": [
                {"name": "Alice", "age": 30, "active": True},
                {"name": "Bob", "age": 17, "active": True},
                {"name": "Charlie", "age": 25, "active": False},
            ]
        }
        
        # Get names of active users over 18
        result = query(
            ".users | filter(.active and .age > 18) | map(.name)",
            data
        )
        
        assert result == ["Alice"]
    
    def test_data_transformation(self):
        """Transform data structure."""
        data = {"items": [{"id": 1, "val": 10}, {"id": 2, "val": 20}]}
        
        result = query(
            '.items | map({key: .id, value: .val}) | from_entries',
            data
        )
        
        assert result == {1: 10, 2: 20}
    
    def test_aggregation_pipeline(self):
        """Aggregation pipeline."""
        data = {
            "orders": [
                {"product": "A", "qty": 5, "price": 10},
                {"product": "B", "qty": 3, "price": 20},
                {"product": "A", "qty": 2, "price": 10},
            ]
        }
        
        # Group by product and sum quantities
        result = query(
            ".orders | group(.product)",
            data
        )
        
        assert len(result["A"]) == 2
        assert len(result["B"]) == 1
    
    def test_compiled_query(self):
        """Test compiled query reuse."""
        prism = Prism()
        
        q = prism.compile(".x + .y")
        
        assert q({"x": 1, "y": 2}) == 3
        assert q({"x": 10, "y": 20}) == 30
    
    def test_variables(self):
        """Test query with variables."""
        data = {"values": [1, 2, 3, 4, 5]}
        
        # Note: Variable access would need to be implemented
        # For now, test basic query
        result = query(".values | filter(. > 2)", data)
        assert result == [3, 4, 5]


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""
    
    def test_lexer_error(self):
        """Lexer reports errors."""
        with pytest.raises(LexerError):
            Lexer('"unterminated').tokenize()
    
    def test_parser_error(self):
        """Parser reports errors."""
        with pytest.raises(ParseError):
            tokens = Lexer("1 +").tokenize()
            Parser(tokens).parse()
    
    def test_eval_error(self):
        """Evaluator reports errors."""
        with pytest.raises(EvalError):
            query(". | map(.x, .y)", [1, 2, 3])  # map takes 1 arg
    
    def test_null_propagation(self):
        """Null propagates gracefully."""
        data = {"a": None}
        
        # Should not crash, return None
        assert query(".a.b.c", data) is None
        assert query(".missing.nested", data) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
