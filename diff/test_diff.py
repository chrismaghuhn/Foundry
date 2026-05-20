"""Tests for diff."""

import pytest
from diff import (
    # Types
    EditType,
    Edit,
    DiffResult,
    
    # Core
    MyersDiff,
    diff,
    diff_lines,
    edit_distance,
    similarity,
    
    # Visualization
    visualize_edit_graph,
    unified_diff,
    
    # Statistics
    diff_stats,
)


# =============================================================================
# Basic Diff Tests
# =============================================================================

class TestBasicDiff:
    """Test basic diff operations."""
    
    def test_identical(self):
        """Identical sequences have no edits."""
        result = diff("ABC", "ABC")
        assert result.edit_distance == 0
        assert all(e.type == EditType.EQUAL for e in result.edits)
    
    def test_empty_to_something(self):
        """Empty to non-empty is all insertions."""
        result = diff("", "ABC")
        assert result.edit_distance == 3
        assert all(e.type == EditType.INSERT for e in result.edits)
    
    def test_something_to_empty(self):
        """Non-empty to empty is all deletions."""
        result = diff("ABC", "")
        assert result.edit_distance == 3
        assert all(e.type == EditType.DELETE for e in result.edits)
    
    def test_both_empty(self):
        """Both empty has no edits."""
        result = diff("", "")
        assert result.edit_distance == 0
        assert len(result.edits) == 0
    
    def test_simple_insertion(self):
        """Single character insertion."""
        result = diff("AC", "ABC")
        assert result.edit_distance == 1
        
        types = [e.type for e in result.edits]
        assert types.count(EditType.INSERT) == 1
    
    def test_simple_deletion(self):
        """Single character deletion."""
        result = diff("ABC", "AC")
        assert result.edit_distance == 1
        
        types = [e.type for e in result.edits]
        assert types.count(EditType.DELETE) == 1
    
    def test_simple_substitution(self):
        """Single character substitution (delete + insert)."""
        result = diff("ABC", "AXC")
        assert result.edit_distance == 2
        
        types = [e.type for e in result.edits]
        assert types.count(EditType.DELETE) == 1
        assert types.count(EditType.INSERT) == 1
    
    def test_prefix_change(self):
        """Change at the beginning."""
        result = diff("XABC", "YABC")
        assert result.edit_distance == 2  # delete X, insert Y
    
    def test_suffix_change(self):
        """Change at the end."""
        result = diff("ABCX", "ABCY")
        assert result.edit_distance == 2  # delete X, insert Y


# =============================================================================
# Edit Distance Tests
# =============================================================================

class TestEditDistance:
    """Test edit distance calculations."""
    
    def test_identical(self):
        assert edit_distance("ABC", "ABC") == 0
    
    def test_empty(self):
        assert edit_distance("", "ABC") == 3
        assert edit_distance("ABC", "") == 3
    
    def test_known_distances(self):
        """Test known edit distances."""
        # kitten → sitting
        # k→s (delete k, insert s = 2), e→i (delete e, insert i = 2), +g (insert g = 1)
        # Total: 5 edits (using only insert/delete, not substitution)
        assert edit_distance("kitten", "sitting") == 5
        
        # Saturday → Sunday
        # Delete: a, t, u, r -> 4
        # Insert: u -> 1
        # Total depends on LCS
        assert edit_distance("Saturday", "Sunday") >= 3
    
    def test_symmetric(self):
        """Edit distance is symmetric."""
        assert edit_distance("ABC", "XYZ") == edit_distance("XYZ", "ABC")
    
    def test_single_char(self):
        assert edit_distance("A", "B") == 2  # delete A, insert B
        assert edit_distance("A", "A") == 0
        assert edit_distance("A", "") == 1
        assert edit_distance("", "A") == 1


# =============================================================================
# Similarity Tests
# =============================================================================

class TestSimilarity:
    """Test similarity calculations."""
    
    def test_identical(self):
        assert similarity("ABC", "ABC") == 1.0
    
    def test_empty_both(self):
        assert similarity("", "") == 1.0
    
    def test_completely_different(self):
        # "ABC" vs "XYZ" - no matches
        result = similarity("ABC", "XYZ")
        assert result == 0.0
    
    def test_partial_match(self):
        # "ABC" vs "AXC" - 2 matches, total length 6
        result = similarity("ABC", "AXC")
        assert 0 < result < 1
    
    def test_range(self):
        """Similarity is always between 0 and 1."""
        assert 0 <= similarity("hello", "world") <= 1
        assert 0 <= similarity("test", "testing") <= 1


# =============================================================================
# Line Diff Tests
# =============================================================================

class TestLineDiff:
    """Test line-based diffing."""
    
    def test_single_line_identical(self):
        result = diff_lines("hello", "hello")
        assert result.edit_distance == 0
    
    def test_single_line_different(self):
        result = diff_lines("hello", "world")
        assert result.edit_distance == 2  # delete + insert
    
    def test_multiline_identical(self):
        text = "line1\nline2\nline3"
        result = diff_lines(text, text)
        assert result.edit_distance == 0
    
    def test_multiline_insertion(self):
        old = "line1\nline3"
        new = "line1\nline2\nline3"
        result = diff_lines(old, new)
        assert result.edit_distance == 1
    
    def test_multiline_deletion(self):
        old = "line1\nline2\nline3"
        new = "line1\nline3"
        result = diff_lines(old, new)
        assert result.edit_distance == 1


# =============================================================================
# Edit Object Tests
# =============================================================================

class TestEditObject:
    """Test Edit dataclass."""
    
    def test_equal_str(self):
        edit = Edit(EditType.EQUAL, 0, 0, "test")
        assert str(edit) == "  test"
    
    def test_insert_str(self):
        edit = Edit(EditType.INSERT, None, 0, "test")
        assert str(edit) == "+ test"
    
    def test_delete_str(self):
        edit = Edit(EditType.DELETE, 0, None, "test")
        assert str(edit) == "- test"
    
    def test_colored(self):
        edit = Edit(EditType.INSERT, None, 0, "test")
        colored = edit.to_colored()
        assert "32m" in colored  # Green color code


# =============================================================================
# DiffResult Tests
# =============================================================================

class TestDiffResult:
    """Test DiffResult dataclass."""
    
    def test_iteration(self):
        result = diff("AB", "CB")
        edits = list(result)
        assert len(edits) > 0
    
    def test_similarity_method(self):
        result = diff("ABC", "ABC")
        assert result.similarity() == 1.0
    
    def test_to_string(self):
        result = diff("A", "B")
        s = result.to_string()
        assert "+" in s or "-" in s


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization functions."""
    
    def test_edit_graph_basic(self):
        graph = visualize_edit_graph("AB", "CAB")
        assert "A" in graph
        assert "B" in graph
        assert "C" in graph
        assert "+" in graph  # Grid character
    
    def test_edit_graph_with_path(self):
        graph = visualize_edit_graph("AB", "CB", show_path=True)
        assert "*" in graph  # Path marker
    
    def test_unified_diff(self):
        old = "line1\nline2"
        new = "line1\nline3"
        ud = unified_diff(old, new, colored=False)
        assert "---" in ud
        assert "+++" in ud
        assert "@@" in ud


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test diff statistics."""
    
    def test_stats_basic(self):
        stats = diff_stats("ABC", "AXC")
        
        assert 'edit_distance' in stats
        assert 'similarity' in stats
        assert 'insertions' in stats
        assert 'deletions' in stats
        assert 'matches' in stats
    
    def test_stats_values(self):
        stats = diff_stats("ABC", "ABC")
        
        assert stats['edit_distance'] == 0
        assert stats['similarity'] == 1.0
        assert stats['insertions'] == 0
        assert stats['deletions'] == 0
        # diff_stats uses line-based diff, so "ABC" is 1 line = 1 match
        assert stats['matches'] == 1


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_single_char_to_single_char(self):
        result = diff("A", "B")
        assert result.edit_distance == 2
    
    def test_repeated_chars(self):
        result = diff("AAAA", "AA")
        assert result.edit_distance == 2
    
    def test_long_strings(self):
        old = "A" * 100
        new = "A" * 100 + "B"
        result = diff(old, new)
        assert result.edit_distance == 1
    
    def test_completely_different(self):
        result = diff("ABC", "XYZ")
        assert result.edit_distance == 6  # 3 deletes + 3 inserts
    
    def test_list_diff(self):
        """Diff works on lists too."""
        result = diff([1, 2, 3], [1, 4, 3])
        assert result.edit_distance == 2


# =============================================================================
# Myers Algorithm Correctness
# =============================================================================

class TestMyersCorrectness:
    """Test that Myers algorithm finds optimal solutions."""
    
    def test_optimal_simple(self):
        """Should find the minimal edit sequence."""
        result = diff("ABCDEF", "ACDEF")
        # Remove B: 1 edit
        assert result.edit_distance == 1
    
    def test_optimal_complex(self):
        """Test a more complex case."""
        result = diff("ABCDEFG", "XBCDEFY")
        # A→X, G→Y: 4 edits (2 deletes, 2 inserts)
        assert result.edit_distance == 4
    
    def test_preserves_order(self):
        """Edits should preserve sequence order."""
        result = diff("ABC", "AXC")
        
        # Should be: A (equal), B (delete), X (insert), C (equal)
        values = [e.value for e in result.edits]
        assert "A" in values
        assert "C" in values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
