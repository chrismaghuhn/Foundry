"""Tests for automata."""

import pytest
from automata import (
    # Base
    CellularAutomaton,
    
    # Game of Life
    GameOfLife,
    Pattern,
    PATTERNS,
    
    # Elementary CA
    Elementary,
    FAMOUS_RULES,
    
    # Langton's Ant
    LangtonsAnt,
    Direction,
    
    # Utilities
    visualize_rule,
    analyze_life_pattern,
    compare_rules,
)


# =============================================================================
# Game of Life Tests
# =============================================================================

class TestGameOfLife:
    """Test Game of Life implementation."""
    
    def test_creation(self):
        """Test basic creation."""
        life = GameOfLife(width=10, height=10)
        assert life.width == 10
        assert life.height == 10
        assert life.population() == 0
    
    def test_set_cell(self):
        """Test setting cells."""
        life = GameOfLife(width=10, height=10)
        life.set_cell(5, 5, True)
        assert life.get_cell(5, 5) == True
        assert life.population() == 1
    
    def test_clear(self):
        """Test clearing grid."""
        life = GameOfLife(width=10, height=10)
        life.set_cell(5, 5, True)
        life.clear()
        assert life.population() == 0
    
    def test_toroidal(self):
        """Test toroidal wrapping."""
        life = GameOfLife(width=10, height=10)
        life.set_cell(15, 15, True)  # Should wrap to (5, 5)
        assert life.get_cell(5, 5) == True
    
    def test_neighbor_count(self):
        """Test neighbor counting."""
        life = GameOfLife(width=10, height=10)
        life.set_cell(5, 5, True)
        life.set_cell(4, 4, True)
        life.set_cell(6, 6, True)
        
        # Cell at (5,5) has neighbors at (4,4) and (6,6)
        assert life.count_neighbors(5, 5) == 2
    
    def test_blinker(self):
        """Test blinker oscillator (period 2)."""
        life = GameOfLife(width=10, height=10)
        life.add_pattern("blinker", 4, 4)
        
        initial_pop = life.population()
        assert initial_pop == 3
        
        # After one step, should still have 3 cells
        life.step()
        assert life.population() == 3
        
        # After two steps, should return to original
        life.step()
        assert life.population() == 3
    
    def test_block(self):
        """Test block still life."""
        life = GameOfLife(width=10, height=10)
        life.add_pattern("block", 4, 4)
        
        initial_hash = life.get_state_hash()
        life.step()
        assert life.get_state_hash() == initial_hash  # Unchanged
    
    def test_glider_moves(self):
        """Test that glider moves diagonally."""
        life = GameOfLife(width=20, height=20)
        life.add_pattern("glider", 2, 2)
        
        initial_pop = life.population()
        
        # Run for 4 generations (one glider cycle)
        for _ in range(4):
            life.step()
        
        assert life.population() == initial_pop  # Same population
        # Position should have changed
    
    def test_pattern_not_found(self):
        """Test error for unknown pattern."""
        life = GameOfLife(width=10, height=10)
        with pytest.raises(ValueError):
            life.add_pattern("nonexistent", 0, 0)
    
    def test_render(self):
        """Test rendering."""
        life = GameOfLife(width=10, height=5)
        life.set_cell(5, 2, True)
        
        rendered = life.render()
        assert "Generation: 0" in rendered
        assert "█" in rendered  # Alive cell


# =============================================================================
# Elementary CA Tests
# =============================================================================

class TestElementaryCA:
    """Test Elementary Cellular Automata."""
    
    def test_creation(self):
        """Test basic creation."""
        ca = Elementary(rule=110, width=20)
        assert ca.rule == 110
        assert ca.width == 20
    
    def test_invalid_rule(self):
        """Test error for invalid rule number."""
        with pytest.raises(ValueError):
            Elementary(rule=256, width=20)
        with pytest.raises(ValueError):
            Elementary(rule=-1, width=20)
    
    def test_single_cell(self):
        """Test single cell initialization."""
        ca = Elementary(rule=110, width=11)
        ca.set_single_cell()
        
        assert ca.cells[5] == 1  # Center cell
        assert sum(ca.cells) == 1  # Only one cell
    
    def test_step(self):
        """Test stepping the automaton."""
        ca = Elementary(rule=110, width=10)
        ca.set_single_cell()
        
        ca.step()
        assert ca.generation == 1
        assert len(ca.history) == 1
    
    def test_rule_30(self):
        """Test Rule 30 produces non-trivial patterns."""
        ca = Elementary(rule=30, width=40)
        ca.set_single_cell()
        ca.run(20)
        
        # Rule 30 should produce lots of 1s
        total_ones = sum(ca.cells)
        assert total_ones > 5  # Should have multiple 1s
    
    def test_rule_90(self):
        """Test Rule 90 (Sierpiński triangle)."""
        ca = Elementary(rule=90, width=21)
        ca.set_single_cell()
        ca.run(10)
        
        # Should still have structure
        assert sum(ca.cells) > 0
    
    def test_render(self):
        """Test rendering."""
        ca = Elementary(rule=110, width=10)
        ca.set_single_cell()
        
        rendered = ca.render()
        assert "█" in rendered
    
    def test_render_history(self):
        """Test history rendering."""
        ca = Elementary(rule=110, width=20)
        ca.set_single_cell()
        ca.run(5)
        
        history = ca.render_history()
        assert "Rule 110" in history


# =============================================================================
# Langton's Ant Tests
# =============================================================================

class TestLangtonsAnt:
    """Test Langton's Ant."""
    
    def test_creation(self):
        """Test basic creation."""
        ant = LangtonsAnt(width=20, height=20)
        assert ant.width == 20
        assert ant.height == 20
        assert ant.ant_x == 10
        assert ant.ant_y == 10
    
    def test_initial_state(self):
        """Test initial state."""
        ant = LangtonsAnt(width=20, height=20)
        assert len(ant.black_cells) == 0
        assert ant.generation == 0
    
    def test_first_step(self):
        """Test first step from white cell."""
        ant = LangtonsAnt(width=20, height=20)
        initial_x, initial_y = ant.ant_x, ant.ant_y
        
        ant.step()
        
        # Should have turned right and moved
        assert ant.generation == 1
        # Original cell should now be black
        assert (initial_x, initial_y) in ant.black_cells
    
    def test_direction_turn_right(self):
        """Test turning right."""
        assert Direction.UP.turn_right() == Direction.RIGHT
        assert Direction.RIGHT.turn_right() == Direction.DOWN
        assert Direction.DOWN.turn_right() == Direction.LEFT
        assert Direction.LEFT.turn_right() == Direction.UP
    
    def test_direction_turn_left(self):
        """Test turning left."""
        assert Direction.UP.turn_left() == Direction.LEFT
        assert Direction.LEFT.turn_left() == Direction.DOWN
        assert Direction.DOWN.turn_left() == Direction.RIGHT
        assert Direction.RIGHT.turn_left() == Direction.UP
    
    def test_multiple_steps(self):
        """Test running multiple steps."""
        ant = LangtonsAnt(width=40, height=40)
        ant.run(100)
        
        assert ant.generation == 100
        assert len(ant.black_cells) > 0
    
    def test_render(self):
        """Test rendering."""
        ant = LangtonsAnt(width=20, height=10)
        ant.run(10)
        
        rendered = ant.render()
        assert "◆" in rendered  # Ant
        assert "Step: 10" in rendered
    
    def test_clear(self):
        """Test clearing."""
        ant = LangtonsAnt(width=20, height=20)
        ant.run(50)
        ant.clear()
        
        assert ant.generation == 0
        assert len(ant.black_cells) == 0


# =============================================================================
# Pattern Tests
# =============================================================================

class TestPatterns:
    """Test Life patterns."""
    
    def test_patterns_exist(self):
        """Test that patterns are defined."""
        assert "glider" in PATTERNS
        assert "blinker" in PATTERNS
        assert "block" in PATTERNS
    
    def test_pattern_has_cells(self):
        """Test that patterns have cells."""
        for name, pattern in PATTERNS.items():
            assert len(pattern.cells) > 0, f"Pattern {name} has no cells"
    
    def test_glider_gun_exists(self):
        """Test Gosper Glider Gun is defined."""
        assert "glider_gun" in PATTERNS
        gun = PATTERNS["glider_gun"]
        assert len(gun.cells) > 30  # Gun has many cells


# =============================================================================
# Utility Tests
# =============================================================================

class TestUtilities:
    """Test utility functions."""
    
    def test_visualize_rule(self):
        """Test rule visualization."""
        viz = visualize_rule(110, width=40, generations=10)
        assert "Rule 110" in viz
    
    def test_analyze_pattern(self):
        """Test pattern analysis."""
        life = GameOfLife(width=20, height=20)
        life.add_pattern("blinker", 5, 5)
        
        analysis = analyze_life_pattern(life, max_gen=10)
        
        assert 'initial_population' in analysis
        assert 'period' in analysis
        assert analysis['period'] == 2  # Blinker is period 2
    
    def test_analyze_still_life(self):
        """Test still life analysis."""
        life = GameOfLife(width=20, height=20)
        life.add_pattern("block", 5, 5)
        
        analysis = analyze_life_pattern(life, max_gen=10)
        
        assert analysis['period'] == 1  # Still life
        assert analysis['is_still_life'] == True


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_life(self):
        """Test empty Game of Life."""
        life = GameOfLife(width=10, height=10)
        life.step()
        
        assert life.population() == 0
    
    def test_single_cell_dies(self):
        """Test single cell dies (no neighbors)."""
        life = GameOfLife(width=10, height=10)
        life.set_cell(5, 5, True)
        life.step()
        
        assert life.population() == 0
    
    def test_small_grid(self):
        """Test very small grid."""
        life = GameOfLife(width=3, height=3)
        life.set_cell(1, 1, True)
        life.render()  # Should not crash
    
    def test_elementary_all_zeros(self):
        """Test elementary CA with all zeros."""
        ca = Elementary(rule=0, width=10)
        ca.cells = [1] * 10
        ca.step()
        
        # Rule 0 maps everything to 0
        assert sum(ca.cells) == 0


# =============================================================================
# Rule 110 Turing Completeness
# =============================================================================

class TestRule110:
    """Test Rule 110 special properties."""
    
    def test_rule_110_description(self):
        """Test Rule 110 has Turing complete description."""
        desc = Elementary.rule_description(110)
        assert "TURING" in desc.upper()
    
    def test_rule_110_complex_behavior(self):
        """Test Rule 110 produces complex behavior."""
        ca = Elementary(rule=110, width=80)
        ca.set_single_cell()
        ca.run(50)
        
        # Should have non-trivial pattern
        ones = sum(ca.cells)
        assert ones > 10  # Multiple active cells
        assert ones < ca.width - 10  # Not all ones


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
