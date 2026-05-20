"""Tests for lambda."""

import pytest
from lambda_calc import (
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
    
    # Standard library
    STDLIB,
)


# =============================================================================
# Parsing Tests
# =============================================================================

class TestParsing:
    """Test lambda calculus parser."""
    
    def test_variable(self):
        term = parse("x")
        assert isinstance(term, Var)
        assert term.name == "x"
    
    def test_abstraction(self):
        term = parse("λx.x")
        assert isinstance(term, Abs)
        assert term.param == "x"
        assert isinstance(term.body, Var)
    
    def test_abstraction_backslash(self):
        term = parse("\\x.x")
        assert isinstance(term, Abs)
    
    def test_application(self):
        term = parse("f x")
        assert isinstance(term, App)
        assert isinstance(term.func, Var)
        assert isinstance(term.arg, Var)
    
    def test_application_left_associative(self):
        term = parse("f x y")
        # Should be ((f x) y)
        assert isinstance(term, App)
        assert isinstance(term.func, App)
        assert isinstance(term.arg, Var)
    
    def test_parentheses(self):
        term = parse("(λx.x)")
        assert isinstance(term, Abs)
    
    def test_complex_term(self):
        term = parse("(λx.λy.x y) a b")
        assert isinstance(term, App)
    
    def test_multi_param_lambda(self):
        term = parse("λx y z.x")
        # Should expand to λx.λy.λz.x
        assert isinstance(term, Abs)
        assert isinstance(term.body, Abs)
        assert isinstance(term.body.body, Abs)
    
    def test_empty_raises(self):
        with pytest.raises(ParseError):
            parse("")
    
    def test_unmatched_paren(self):
        with pytest.raises(ParseError):
            parse("(λx.x")


# =============================================================================
# Free Variables Tests
# =============================================================================

class TestFreeVariables:
    """Test free variable computation."""
    
    def test_var_is_free(self):
        term = parse("x")
        assert term.free_variables() == {"x"}
    
    def test_bound_not_free(self):
        term = parse("λx.x")
        assert term.free_variables() == set()
    
    def test_mixed(self):
        term = parse("λx.y")
        assert term.free_variables() == {"y"}
    
    def test_application(self):
        term = parse("x y")
        assert term.free_variables() == {"x", "y"}
    
    def test_complex(self):
        term = parse("λx.x y z")
        assert term.free_variables() == {"y", "z"}


# =============================================================================
# Substitution Tests
# =============================================================================

class TestSubstitution:
    """Test capture-avoiding substitution."""
    
    def test_simple_substitution(self):
        term = parse("x")
        result = term.substitute("x", parse("y"))
        assert str(result) == "y"
    
    def test_no_substitution(self):
        term = parse("y")
        result = term.substitute("x", parse("z"))
        assert str(result) == "y"
    
    def test_bound_not_substituted(self):
        term = parse("λx.x")
        result = term.substitute("x", parse("y"))
        # x is bound, should not be substituted
        assert isinstance(result, Abs)
        assert str(result.body) == "x"
    
    def test_capture_avoidance(self):
        term = parse("λx.y")
        result = term.substitute("y", parse("x"))
        # Should rename x to avoid capture
        assert isinstance(result, Abs)
        assert result.param != "x"  # Renamed


# =============================================================================
# Alpha Equivalence Tests
# =============================================================================

class TestAlphaEquivalence:
    """Test α-equivalence checking."""
    
    def test_same_term(self):
        t1 = parse("λx.x")
        t2 = parse("λx.x")
        assert alpha_equivalent(t1, t2)
    
    def test_renamed_bound(self):
        t1 = parse("λx.x")
        t2 = parse("λy.y")
        assert alpha_equivalent(t1, t2)
    
    def test_different_structure(self):
        t1 = parse("λx.x")
        t2 = parse("λx.y")
        assert not alpha_equivalent(t1, t2)
    
    def test_complex_equivalent(self):
        t1 = parse("λx.λy.x y")
        t2 = parse("λa.λb.a b")
        assert alpha_equivalent(t1, t2)


# =============================================================================
# Reduction Tests
# =============================================================================

class TestReduction:
    """Test β-reduction."""
    
    def test_simple_reduction(self):
        term = parse("(λx.x) y")
        result = reduce(term)
        assert str(result) == "y"
    
    def test_identity(self):
        term = parse("(λx.x) (λy.y)")
        result = reduce(term)
        assert alpha_equivalent(result, parse("λy.y"))
    
    def test_constant(self):
        term = parse("(λx.λy.x) a b")
        result = reduce(term)
        assert str(result) == "a"
    
    def test_already_normal(self):
        term = parse("λx.x")
        result = reduce(term)
        assert alpha_equivalent(result, term)
    
    def test_nested_reduction(self):
        term = parse("(λx.x x) (λy.y)")
        result = reduce(term)
        assert alpha_equivalent(result, parse("λy.y"))
    
    def test_reduction_steps(self):
        term = parse("(λx.x) y")
        steps = reduce_steps(term)
        assert len(steps) == 1


# =============================================================================
# Church Numeral Tests
# =============================================================================

class TestChurchNumerals:
    """Test Church encoding of numbers."""
    
    def test_zero(self):
        zero = Church.numeral(0)
        assert Church.to_int(zero) == 0
    
    def test_one(self):
        one = Church.numeral(1)
        assert Church.to_int(one) == 1
    
    def test_five(self):
        five = Church.numeral(5)
        assert Church.to_int(five) == 5
    
    def test_successor(self):
        two = Church.numeral(2)
        succ_two = App(Church.SUCC, two)
        result = reduce(succ_two)
        assert Church.to_int(result) == 3
    
    def test_addition(self):
        two = Church.numeral(2)
        three = Church.numeral(3)
        add_expr = App(App(Church.ADD, two), three)
        result = reduce(add_expr)
        assert Church.to_int(result) == 5
    
    def test_multiplication(self):
        two = Church.numeral(2)
        three = Church.numeral(3)
        mul_expr = App(App(Church.MUL, two), three)
        result = reduce(mul_expr)
        assert Church.to_int(result) == 6
    
    def test_negative_raises(self):
        with pytest.raises(ValueError):
            Church.numeral(-1)


# =============================================================================
# Church Boolean Tests
# =============================================================================

class TestChurchBooleans:
    """Test Church encoding of booleans."""
    
    def test_true(self):
        assert Church.to_bool(Church.TRUE) == True
    
    def test_false(self):
        assert Church.to_bool(Church.FALSE) == False
    
    def test_and_true_true(self):
        expr = App(App(Church.AND, Church.TRUE), Church.TRUE)
        result = reduce(expr)
        assert Church.to_bool(result) == True
    
    def test_and_true_false(self):
        expr = App(App(Church.AND, Church.TRUE), Church.FALSE)
        result = reduce(expr)
        assert Church.to_bool(result) == False
    
    def test_or_false_true(self):
        expr = App(App(Church.OR, Church.FALSE), Church.TRUE)
        result = reduce(expr)
        assert Church.to_bool(result) == True
    
    def test_not_true(self):
        expr = App(Church.NOT, Church.TRUE)
        result = reduce(expr)
        assert Church.to_bool(result) == False
    
    def test_iszero_zero(self):
        expr = App(Church.ISZERO, Church.ZERO)
        result = reduce(expr)
        assert Church.to_bool(result) == True
    
    def test_iszero_one(self):
        expr = App(Church.ISZERO, Church.ONE)
        result = reduce(expr)
        assert Church.to_bool(result) == False


# =============================================================================
# Church Pairs Tests
# =============================================================================

class TestChurchPairs:
    """Test Church encoding of pairs."""
    
    def test_fst(self):
        # (fst (pair a b)) = a
        a = Var('a')
        b = Var('b')
        pair_ab = App(App(Church.PAIR, a), b)
        fst_pair = App(Church.FST, pair_ab)
        result = reduce(fst_pair)
        assert str(result) == "a"
    
    def test_snd(self):
        # (snd (pair a b)) = b
        a = Var('a')
        b = Var('b')
        pair_ab = App(App(Church.PAIR, a), b)
        snd_pair = App(Church.SND, pair_ab)
        result = reduce(snd_pair)
        assert str(result) == "b"


# =============================================================================
# Standard Library Tests
# =============================================================================

class TestStdlib:
    """Test standard library expansion."""
    
    def test_identity_combinator(self):
        term = parse("I x")
        expanded = expand_stdlib(term)
        result = reduce(expanded)
        assert str(result) == "x"
    
    def test_constant_combinator(self):
        term = parse("K a b")
        expanded = expand_stdlib(term)
        result = reduce(expanded)
        assert str(result) == "a"
    
    def test_evaluate(self):
        result = evaluate("add 2 3")
        assert Church.to_int(result) == 5


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization functions."""
    
    def test_reduction_visualization(self):
        result = visualize_reduction(parse("(λx.x) y"))
        assert "REDUCTION" in result
        assert "Normal form" in result
    
    def test_church_arithmetic_visualization(self):
        result = visualize_church_arithmetic(2, 3, '+')
        assert "CHURCH ARITHMETIC" in result
        assert "2 + 3 = 5" in result


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_single_variable(self):
        term = parse("x")
        result = reduce(term)
        assert str(result) == "x"
    
    def test_deeply_nested(self):
        term = parse("λa.λb.λc.λd.a b c d")
        result = reduce(term)
        # Should be unchanged (already normal form)
        assert isinstance(result, Abs)
    
    def test_long_application(self):
        term = parse("(λx.x) (λy.y) z")
        result = reduce(term)
        assert str(result) == "z"
    
    def test_fresh_variable(self):
        used = {"x", "x'", "x''"}
        fresh = fresh_variable("x", used)
        assert fresh not in used


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Full integration tests."""
    
    def test_factorial_concept(self):
        # Test that iszero and pred work together
        zero = Church.ZERO
        one = Church.ONE
        
        # iszero 0 = true
        is_zero = App(Church.ISZERO, zero)
        assert Church.to_bool(reduce(is_zero)) == True
        
        # iszero 1 = false
        is_one = App(Church.ISZERO, one)
        assert Church.to_bool(reduce(is_one)) == False
    
    def test_power(self):
        # 2^3 = 8
        two = Church.numeral(2)
        three = Church.numeral(3)
        pow_expr = App(App(Church.POW, two), three)
        result = reduce(pow_expr, max_steps=200)
        assert Church.to_int(result) == 8
    
    def test_complex_expression(self):
        # (succ (add 1 2)) = 4
        result = evaluate("succ (add 1 2)")
        assert Church.to_int(result) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
