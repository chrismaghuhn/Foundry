"""Tests for phantom."""

import pytest
from phantom import (
    # Main
    Regex,
    MatchResult,
    compile,
    match,
    search,
    fullmatch,
    trace,
    visualize,
    
    # AST
    Parser,
    ParseError,
    Literal,
    Concat,
    Alternate,
    Star,
    Plus,
    Question,
    
    # NFA
    NFABuilder,
    NFAVisualizer,
)


# =============================================================================
# Parser Tests
# =============================================================================

class TestParser:
    """Test regex parsing."""
    
    def test_literal(self):
        ast = Parser("a").parse()
        assert isinstance(ast, Literal)
        assert ast.char == 'a'
    
    def test_concatenation(self):
        ast = Parser("ab").parse()
        assert isinstance(ast, Concat)
    
    def test_alternation(self):
        ast = Parser("a|b").parse()
        assert isinstance(ast, Alternate)
    
    def test_star(self):
        ast = Parser("a*").parse()
        assert isinstance(ast, Star)
    
    def test_plus(self):
        ast = Parser("a+").parse()
        assert isinstance(ast, Plus)
    
    def test_question(self):
        ast = Parser("a?").parse()
        assert isinstance(ast, Question)
    
    def test_grouping(self):
        ast = Parser("(ab)").parse()
        assert isinstance(ast, Concat)
    
    def test_complex(self):
        # Should not raise
        Parser("(a|b)*c+d?").parse()
        Parser("[a-z]+").parse()
        Parser("\\d{2,4}").parse()
    
    def test_invalid_unmatched_paren(self):
        with pytest.raises(ParseError):
            Parser("(ab").parse()
    
    def test_invalid_unexpected_star(self):
        with pytest.raises(ParseError):
            Parser("*ab").parse()


# =============================================================================
# Literal Matching Tests
# =============================================================================

class TestLiteralMatching:
    """Test matching of literal characters."""
    
    def test_single_char(self):
        assert match("a", "a").matched
        assert not match("a", "b").matched
    
    def test_multiple_chars(self):
        assert match("abc", "abc").matched
        assert match("abc", "abcd").matched  # Prefix match
        assert not match("abc", "ab").matched
    
    def test_special_escaped(self):
        assert match(r"\.", ".").matched
        assert not match(r"\.", "a").matched
        assert match(r"\*", "*").matched


# =============================================================================
# Dot (Any Character) Tests
# =============================================================================

class TestDot:
    """Test the . metacharacter."""
    
    def test_matches_letter(self):
        assert match(".", "a").matched
    
    def test_matches_digit(self):
        assert match(".", "5").matched
    
    def test_matches_space(self):
        assert match(".", " ").matched
    
    def test_not_matches_newline(self):
        assert not match(".", "\n").matched
    
    def test_dot_in_pattern(self):
        assert match("a.c", "abc").matched
        assert match("a.c", "aXc").matched
        assert not match("a.c", "ac").matched


# =============================================================================
# Alternation Tests
# =============================================================================

class TestAlternation:
    """Test the | operator."""
    
    def test_simple_alternation(self):
        assert match("a|b", "a").matched
        assert match("a|b", "b").matched
        assert not match("a|b", "c").matched
    
    def test_multi_alternation(self):
        assert match("a|b|c", "c").matched
    
    def test_word_alternation(self):
        assert match("cat|dog", "cat").matched
        assert match("cat|dog", "dog").matched
        assert not match("cat|dog", "bird").matched


# =============================================================================
# Quantifier Tests
# =============================================================================

class TestQuantifiers:
    """Test *, +, ?, and {n,m}."""
    
    def test_star_zero(self):
        assert match("a*", "").matched
    
    def test_star_one(self):
        assert match("a*", "a").matched
    
    def test_star_many(self):
        assert match("a*", "aaaa").matched
    
    def test_plus_zero(self):
        assert not match("a+", "").matched
    
    def test_plus_one(self):
        assert match("a+", "a").matched
    
    def test_plus_many(self):
        assert match("a+", "aaaa").matched
    
    def test_question_zero(self):
        assert match("a?", "").matched
    
    def test_question_one(self):
        assert match("a?", "a").matched
    
    def test_question_not_two(self):
        # a? matches just one 'a', so "aa" matches at position 0-1
        result = match("a?", "aa")
        assert result.matched
        assert result.match_end == 1  # Only matches first 'a'
    
    def test_bounded_exact(self):
        assert fullmatch("a{3}", "aaa").matched
        assert not fullmatch("a{3}", "aa").matched
        assert not fullmatch("a{3}", "aaaa").matched
    
    def test_bounded_range(self):
        assert fullmatch("a{2,4}", "aa").matched
        assert fullmatch("a{2,4}", "aaa").matched
        assert fullmatch("a{2,4}", "aaaa").matched
        assert not fullmatch("a{2,4}", "a").matched
        assert not fullmatch("a{2,4}", "aaaaa").matched
    
    def test_bounded_minimum(self):
        assert fullmatch("a{2,}", "aa").matched
        assert fullmatch("a{2,}", "aaaaaaa").matched
        assert not fullmatch("a{2,}", "a").matched


# =============================================================================
# Character Class Tests
# =============================================================================

class TestCharacterClass:
    """Test [...] character classes."""
    
    def test_simple_class(self):
        assert match("[abc]", "a").matched
        assert match("[abc]", "b").matched
        assert match("[abc]", "c").matched
        assert not match("[abc]", "d").matched
    
    def test_range(self):
        assert match("[a-z]", "m").matched
        assert not match("[a-z]", "M").matched
        assert match("[0-9]", "5").matched
    
    def test_negated(self):
        assert not match("[^abc]", "a").matched
        assert match("[^abc]", "d").matched
    
    def test_shortcuts(self):
        assert match(r"\d", "5").matched
        assert not match(r"\d", "a").matched
        assert match(r"\w", "a").matched
        assert match(r"\w", "5").matched
        assert match(r"\w", "_").matched
        assert match(r"\s", " ").matched
        assert match(r"\s", "\t").matched


# =============================================================================
# Grouping Tests
# =============================================================================

class TestGrouping:
    """Test (...) grouping."""
    
    def test_simple_group(self):
        assert match("(ab)+", "abab").matched
    
    def test_alternation_in_group(self):
        assert match("(a|b)+", "abba").matched
    
    def test_nested_groups(self):
        assert match("((a|b)+c)+", "abcabc").matched


# =============================================================================
# Anchor Tests
# =============================================================================

class TestAnchors:
    """Test ^ and $ anchors."""
    
    def test_start_anchor(self):
        rx = Regex("^abc")
        assert rx.search("abc").matched
        assert not rx.search("xabc").matched
    
    def test_end_anchor(self):
        rx = Regex("abc$")
        result = rx.fullmatch("abc")
        assert result.matched


# =============================================================================
# Search Tests
# =============================================================================

class TestSearch:
    """Test searching within strings."""
    
    def test_search_at_start(self):
        result = search("abc", "abcdef")
        assert result.matched
        assert result.match_start == 0
    
    def test_search_in_middle(self):
        result = search("abc", "xxxabcyyy")
        assert result.matched
        assert result.match_start == 3
    
    def test_search_at_end(self):
        result = search("abc", "xxxabc")
        assert result.matched
        assert result.match_start == 3
    
    def test_search_not_found(self):
        result = search("abc", "xxxyyy")
        assert not result.matched


# =============================================================================
# Full Match Tests
# =============================================================================

class TestFullMatch:
    """Test matching entire strings."""
    
    def test_fullmatch_exact(self):
        assert fullmatch("abc", "abc").matched
    
    def test_fullmatch_too_short(self):
        assert not fullmatch("abc", "ab").matched
    
    def test_fullmatch_too_long(self):
        assert not fullmatch("abc", "abcd").matched
    
    def test_fullmatch_with_quantifiers(self):
        assert fullmatch("a+", "aaa").matched
        assert fullmatch("a*b+", "aaabbb").matched


# =============================================================================
# NFA Building Tests
# =============================================================================

class TestNFABuilding:
    """Test NFA construction."""
    
    def test_nfa_states_count(self):
        # Thompson's construction: at most 2n states
        rx = Regex("abc")
        assert len(rx.nfa.states) <= 6 * 2
    
    def test_nfa_has_start_and_accept(self):
        rx = Regex("a")
        assert rx.nfa.start is not None
        assert rx.nfa.accept is not None
        assert rx.nfa.accept.is_accept


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization output."""
    
    def test_ascii_visualization(self):
        rx = Regex("a|b")
        ascii_art = rx.visualize_nfa()
        assert "NFA:" in ascii_art
        assert "Start:" in ascii_art
        assert "Accept:" in ascii_art
    
    def test_dot_visualization(self):
        rx = Regex("ab")
        dot = rx.to_dot()
        assert "digraph NFA" in dot
        assert "__start__" in dot
    
    def test_trace(self):
        result = trace("ab", "ab")
        assert "PHANTOM" in result
        assert "MATCH" in result


# =============================================================================
# Complex Pattern Tests
# =============================================================================

class TestComplexPatterns:
    """Test realistic regex patterns."""
    
    def test_email_like(self):
        # Simplified email pattern
        pattern = r"\w+@\w+\.\w+"
        assert search(pattern, "test@example.com").matched
    
    def test_number_pattern(self):
        pattern = r"\d+"
        assert search(pattern, "abc123def").matched
        result = search(pattern, "abc123def")
        assert result.match_start == 3
    
    def test_word_boundary_like(self):
        pattern = r"cat"
        assert search(pattern, "the cat sat").matched


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_pattern(self):
        assert match("", "").matched
        assert match("", "abc").matched  # Empty matches anywhere
    
    def test_empty_string(self):
        assert match("a*", "").matched
        assert not match("a+", "").matched
    
    def test_single_char_class(self):
        assert match("[a]", "a").matched
    
    def test_escaped_brackets(self):
        assert match(r"\[", "[").matched
        assert match(r"\]", "]").matched


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Full integration tests."""
    
    def test_compile_and_reuse(self):
        rx = compile(r"\d+")
        assert rx.search("abc123").matched
        assert rx.search("456def").matched
        assert not rx.search("abcdef").matched
    
    def test_trace_shows_steps(self):
        rx = Regex("ab")
        result = rx.trace("ab", show_all=True)
        assert "Step" in result
        assert "Active:" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
