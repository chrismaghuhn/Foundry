"""Tests for lisp."""

import pytest
from lisp import (
    # Values
    LispValue,
    LispNumber,
    LispString,
    LispSymbol,
    LispBool,
    LispNil,
    LispList,
    LispProcedure,
    NIL,
    
    # Errors
    LispError,
    ParseError,
    EvalError,
    
    # Parsing
    parse,
    parse_all,
    
    # Main class
    Lisp,
)


# =============================================================================
# Parsing Tests
# =============================================================================

class TestParsing:
    """Test S-expression parsing."""
    
    def test_parse_number(self):
        result = parse("42")
        assert isinstance(result, LispNumber)
        assert result.value == 42
    
    def test_parse_negative_number(self):
        result = parse("-17")
        assert result.value == -17
    
    def test_parse_float(self):
        result = parse("3.14")
        assert abs(result.value - 3.14) < 0.001
    
    def test_parse_string(self):
        result = parse('"hello"')
        assert isinstance(result, LispString)
        assert result.value == "hello"
    
    def test_parse_string_escape(self):
        result = parse('"hello\\nworld"')
        assert result.value == "hello\nworld"
    
    def test_parse_symbol(self):
        result = parse("foo")
        assert isinstance(result, LispSymbol)
        assert result.name == "foo"
    
    def test_parse_boolean_true(self):
        result = parse("#t")
        assert isinstance(result, LispBool)
        assert result.value == True
    
    def test_parse_boolean_false(self):
        result = parse("#f")
        assert result.value == False
    
    def test_parse_nil(self):
        result = parse("nil")
        assert isinstance(result, LispNil)
    
    def test_parse_empty_list(self):
        result = parse("()")
        assert isinstance(result, LispList)
        assert len(result) == 0
    
    def test_parse_simple_list(self):
        result = parse("(+ 1 2)")
        assert isinstance(result, LispList)
        assert len(result) == 3
    
    def test_parse_nested_list(self):
        result = parse("(+ (* 2 3) 4)")
        assert len(result) == 3
        assert isinstance(result[1], LispList)
    
    def test_parse_quote(self):
        result = parse("'(1 2 3)")
        assert isinstance(result, LispList)
        assert isinstance(result[0], LispSymbol)
        assert result[0].name == "quote"
    
    def test_parse_multiple(self):
        results = parse_all("1 2 3")
        assert len(results) == 3
    
    def test_parse_comment(self):
        result = parse("42 ; this is a comment")
        assert result.value == 42


# =============================================================================
# Arithmetic Tests
# =============================================================================

class TestArithmetic:
    """Test arithmetic operations."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_add(self):
        assert self.lisp.eval("(+ 1 2)").value == 3
    
    def test_add_many(self):
        assert self.lisp.eval("(+ 1 2 3 4 5)").value == 15
    
    def test_subtract(self):
        assert self.lisp.eval("(- 10 3)").value == 7
    
    def test_subtract_unary(self):
        assert self.lisp.eval("(- 5)").value == -5
    
    def test_multiply(self):
        assert self.lisp.eval("(* 3 4)").value == 12
    
    def test_divide(self):
        assert self.lisp.eval("(/ 10 2)").value == 5
    
    def test_mod(self):
        assert self.lisp.eval("(mod 10 3)").value == 1
    
    def test_nested(self):
        assert self.lisp.eval("(+ (* 2 3) (- 10 5))").value == 11
    
    def test_sqrt(self):
        assert abs(self.lisp.eval("(sqrt 16)").value - 4.0) < 0.001
    
    def test_expt(self):
        assert self.lisp.eval("(expt 2 10)").value == 1024


# =============================================================================
# Comparison Tests
# =============================================================================

class TestComparison:
    """Test comparison operations."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_equal(self):
        assert self.lisp.eval("(= 1 1)").value == True
    
    def test_not_equal(self):
        assert self.lisp.eval("(= 1 2)").value == False
    
    def test_less_than(self):
        assert self.lisp.eval("(< 1 2)").value == True
    
    def test_greater_than(self):
        assert self.lisp.eval("(> 2 1)").value == True
    
    def test_less_equal(self):
        assert self.lisp.eval("(<= 1 1)").value == True
    
    def test_greater_equal(self):
        assert self.lisp.eval("(>= 2 2)").value == True


# =============================================================================
# List Operations Tests
# =============================================================================

class TestListOperations:
    """Test list operations."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_list(self):
        result = self.lisp.eval("(list 1 2 3)")
        assert isinstance(result, LispList)
        assert len(result) == 3
    
    def test_car(self):
        assert self.lisp.eval("(car '(1 2 3))").value == 1
    
    def test_cdr(self):
        result = self.lisp.eval("(cdr '(1 2 3))")
        assert len(result) == 2
    
    def test_cons(self):
        result = self.lisp.eval("(cons 1 '(2 3))")
        assert len(result) == 3
        assert result[0].value == 1
    
    def test_length(self):
        assert self.lisp.eval("(length '(1 2 3 4))").value == 4
    
    def test_append(self):
        result = self.lisp.eval("(append '(1 2) '(3 4))")
        assert len(result) == 4
    
    def test_reverse(self):
        result = self.lisp.eval("(reverse '(1 2 3))")
        assert result[0].value == 3
    
    def test_null_empty(self):
        assert self.lisp.eval("(null? '())").value == True
    
    def test_null_non_empty(self):
        assert self.lisp.eval("(null? '(1))").value == False


# =============================================================================
# Special Forms Tests
# =============================================================================

class TestSpecialForms:
    """Test special forms."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_quote(self):
        result = self.lisp.eval("(quote (1 2 3))")
        assert isinstance(result, LispList)
    
    def test_quote_shorthand(self):
        result = self.lisp.eval("'(1 2 3)")
        assert isinstance(result, LispList)
    
    def test_if_true(self):
        assert self.lisp.eval("(if #t 1 2)").value == 1
    
    def test_if_false(self):
        assert self.lisp.eval("(if #f 1 2)").value == 2
    
    def test_if_no_else(self):
        result = self.lisp.eval("(if #f 1)")
        assert isinstance(result, LispNil)
    
    def test_define_variable(self):
        self.lisp.eval("(define x 10)")
        assert self.lisp.eval("x").value == 10
    
    def test_define_function(self):
        self.lisp.eval("(define (double x) (* x 2))")
        assert self.lisp.eval("(double 5)").value == 10
    
    def test_lambda(self):
        self.lisp.eval("(define sqr (lambda (x) (* x x)))")
        assert self.lisp.eval("(sqr 4)").value == 16
    
    def test_let(self):
        result = self.lisp.eval("(let ((x 1) (y 2)) (+ x y))")
        assert result.value == 3
    
    def test_let_star(self):
        result = self.lisp.eval("(let* ((x 1) (y (+ x 1))) (+ x y))")
        assert result.value == 3
    
    def test_begin(self):
        result = self.lisp.eval("(begin 1 2 3)")
        assert result.value == 3
    
    def test_set(self):
        self.lisp.eval("(define x 1)")
        self.lisp.eval("(set! x 10)")
        assert self.lisp.eval("x").value == 10
    
    def test_cond(self):
        result = self.lisp.eval("""
            (cond
              ((= 1 2) 'nope)
              ((= 2 2) 'yes)
              (else 'default))
        """)
        assert result.name == "yes"
    
    def test_and(self):
        assert self.lisp.eval("(and #t #t)").value == True
        assert self.lisp.eval("(and #t #f)").value == False
    
    def test_or(self):
        assert self.lisp.eval("(or #f #t)").value == True
        assert self.lisp.eval("(or #f #f)").value == False


# =============================================================================
# Function Tests
# =============================================================================

class TestFunctions:
    """Test function definition and calling."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_simple_function(self):
        self.lisp.eval("(define (add a b) (+ a b))")
        assert self.lisp.eval("(add 3 4)").value == 7
    
    def test_recursive_function(self):
        self.lisp.eval("""
            (define (factorial n)
              (if (<= n 1)
                  1
                  (* n (factorial (- n 1)))))
        """)
        assert self.lisp.eval("(factorial 5)").value == 120
    
    def test_closure(self):
        self.lisp.eval("""
            (define (make-counter)
              (let ((count 0))
                (lambda ()
                  (set! count (+ count 1))
                  count)))
        """)
        self.lisp.eval("(define counter (make-counter))")
        assert self.lisp.eval("(counter)").value == 1
        assert self.lisp.eval("(counter)").value == 2
    
    def test_higher_order(self):
        self.lisp.eval("(define (apply-twice f x) (f (f x)))")
        self.lisp.eval("(define (inc x) (+ x 1))")
        assert self.lisp.eval("(apply-twice inc 5)").value == 7
    
    def test_anonymous_lambda(self):
        result = self.lisp.eval("((lambda (x) (* x x)) 5)")
        assert result.value == 25


# =============================================================================
# Standard Library Tests
# =============================================================================

class TestStdlib:
    """Test standard library functions."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_cadr(self):
        assert self.lisp.eval("(cadr '(1 2 3))").value == 2
    
    def test_first(self):
        assert self.lisp.eval("(first '(1 2 3))").value == 1
    
    def test_rest(self):
        result = self.lisp.eval("(rest '(1 2 3))")
        assert len(result) == 2
    
    def test_zero(self):
        assert self.lisp.eval("(zero? 0)").value == True
    
    def test_even(self):
        assert self.lisp.eval("(even? 4)").value == True
    
    def test_odd(self):
        assert self.lisp.eval("(odd? 3)").value == True
    
    def test_inc(self):
        assert self.lisp.eval("(inc 5)").value == 6
    
    def test_dec(self):
        assert self.lisp.eval("(dec 5)").value == 4
    
    def test_square(self):
        assert self.lisp.eval("(square 4)").value == 16
    
    def test_range(self):
        result = self.lisp.eval("(range 0 5)")
        assert len(result) == 5
    
    def test_nth(self):
        assert self.lisp.eval("(nth 2 '(a b c d))").name == "c"
    
    def test_take(self):
        result = self.lisp.eval("(take 2 '(1 2 3 4))")
        assert len(result) == 2
    
    def test_drop(self):
        result = self.lisp.eval("(drop 2 '(1 2 3 4))")
        assert len(result) == 2
    
    def test_foldl(self):
        result = self.lisp.eval("(foldl + 0 '(1 2 3 4 5))")
        assert result.value == 15
    
    def test_foldr(self):
        result = self.lisp.eval("(foldr cons '() '(1 2 3))")
        assert len(result) == 3


# =============================================================================
# Type Predicate Tests
# =============================================================================

class TestTypePredicates:
    """Test type predicates."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_number(self):
        assert self.lisp.eval("(number? 42)").value == True
        assert self.lisp.eval("(number? 'x)").value == False
    
    def test_string(self):
        assert self.lisp.eval('(string? "hello")').value == True
    
    def test_symbol(self):
        assert self.lisp.eval("(symbol? 'x)").value == True
    
    def test_list(self):
        assert self.lisp.eval("(list? '(1 2))").value == True
    
    def test_procedure(self):
        self.lisp.eval("(define (f x) x)")
        assert self.lisp.eval("(procedure? f)").value == True
    
    def test_boolean(self):
        assert self.lisp.eval("(boolean? #t)").value == True


# =============================================================================
# Macro Tests
# =============================================================================

class TestMacros:
    """Test macro definition and expansion."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_simple_macro(self):
        self.lisp.eval("(defmacro my-if (test then) `(if ,test ,then nil))")
        assert self.lisp.eval("(my-if #t 42)").value == 42
    
    def test_unless_macro(self):
        self.lisp.eval("""
            (defmacro unless (test body)
              `(if (not ,test) ,body nil))
        """)
        assert self.lisp.eval("(unless #f 'success)").name == "success"
    
    def test_quasiquote(self):
        self.lisp.eval("(define x 10)")
        result = self.lisp.eval("`(1 ,x 3)")
        assert result[1].value == 10


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_empty_list_eval(self):
        result = self.lisp.eval("'()")
        assert isinstance(result, LispList)
        assert len(result) == 0
    
    def test_undefined_variable(self):
        with pytest.raises(LispError):
            self.lisp.eval("undefined_var")
    
    def test_division_by_zero(self):
        with pytest.raises(EvalError):
            self.lisp.eval("(/ 1 0)")
    
    def test_car_empty_list(self):
        with pytest.raises(EvalError):
            self.lisp.eval("(car '())")
    
    def test_nested_quotes(self):
        result = self.lisp.eval("''x")
        assert isinstance(result, LispList)


# =============================================================================
# Tail Call Optimization Tests
# =============================================================================

class TestTailCallOptimization:
    """Test that tail calls don't overflow stack."""
    
    def setup_method(self):
        self.lisp = Lisp()
    
    def test_tail_recursive_sum(self):
        self.lisp.eval("""
            (define (sum-tail n acc)
              (if (<= n 0)
                  acc
                  (sum-tail (- n 1) (+ acc n))))
        """)
        # This would overflow without TCO
        result = self.lisp.eval("(sum-tail 100 0)")
        assert result.value == 5050


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
