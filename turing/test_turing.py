"""Tests for turing."""

import pytest
from turing import (
    # Core
    TuringMachine,
    Tape,
    Configuration,
    ExecutionResult,
    Direction,
    
    # Visualization
    visualize_execution,
    visualize_transition_table,
    
    # Built-in machines
    create_binary_increment,
    create_unary_addition,
    create_palindrome_checker,
    create_busy_beaver_3,
    create_binary_to_unary,
    
    # Convenience
    get_machine,
    run,
    visualize,
    trace,
    MACHINES,
)


# =============================================================================
# Tape Tests
# =============================================================================

class TestTape:
    """Test the infinite tape implementation."""
    
    def test_empty_tape(self):
        tape = Tape()
        assert tape.read(0) == '_'
    
    def test_initial_content(self):
        tape = Tape("abc")
        assert tape.read(0) == 'a'
        assert tape.read(1) == 'b'
        assert tape.read(2) == 'c'
    
    def test_write(self):
        tape = Tape()
        tape.write(0, 'X')
        assert tape.read(0) == 'X'
    
    def test_expand_right(self):
        tape = Tape("a")
        assert tape.read(10) == '_'  # Should expand
    
    def test_expand_left(self):
        tape = Tape("a")
        assert tape.read(-5) == '_'  # Should expand left
    
    def test_get_content(self):
        tape = Tape("hello")
        assert tape.get_content() == "hello"
    
    def test_get_window(self):
        tape = Tape("abcde")
        window, pos = tape.get_window(2, 2)
        assert 'c' in window
        assert pos == 2


# =============================================================================
# Direction Tests
# =============================================================================

class TestDirection:
    """Test direction parsing."""
    
    def test_left(self):
        assert Direction.from_str('L') == Direction.LEFT
        assert Direction.from_str('LEFT') == Direction.LEFT
    
    def test_right(self):
        assert Direction.from_str('R') == Direction.RIGHT
        assert Direction.from_str('right') == Direction.RIGHT
    
    def test_none(self):
        assert Direction.from_str('N') == Direction.NONE
        assert Direction.from_str('STAY') == Direction.NONE
    
    def test_invalid(self):
        with pytest.raises(ValueError):
            Direction.from_str('X')


# =============================================================================
# Basic Machine Tests
# =============================================================================

class TestBasicMachine:
    """Test basic Turing machine functionality."""
    
    def test_create_machine(self):
        tm = TuringMachine(
            states={'q0', 'halt'},
            alphabet={'a', 'b', '_'},
            transitions={
                ('q0', 'a'): ('halt', 'b', 'R'),
            },
            initial_state='q0',
            halt_states={'halt'}
        )
        assert tm is not None
    
    def test_simple_execution(self):
        tm = TuringMachine(
            states={'q0', 'halt'},
            alphabet={'0', '1', '_'},
            transitions={
                ('q0', '0'): ('q0', '0', 'R'),
                ('q0', '1'): ('q0', '1', 'R'),
                ('q0', '_'): ('halt', '_', 'N'),
            },
            initial_state='q0',
            halt_states={'halt'}
        )
        
        result = tm.run("101")
        assert result.halted
        assert result.final_state == 'halt'
    
    def test_write_symbol(self):
        tm = TuringMachine(
            states={'q0', 'halt'},
            alphabet={'a', 'b', '_'},
            transitions={
                ('q0', 'a'): ('halt', 'b', 'N'),
            },
            initial_state='q0',
            halt_states={'halt'}
        )
        
        result = tm.run("a")
        assert result.tape_content == "b"
    
    def test_move_left(self):
        tm = TuringMachine(
            states={'q0', 'q1', 'halt'},
            alphabet={'a', 'b', '_'},
            transitions={
                ('q0', 'a'): ('q1', 'a', 'R'),
                ('q1', 'b'): ('halt', 'b', 'L'),
            },
            initial_state='q0',
            halt_states={'halt'}
        )
        
        result = tm.run("ab")
        assert result.halted
    
    def test_stuck_no_transition(self):
        tm = TuringMachine(
            states={'q0', 'halt'},
            alphabet={'a', '_'},
            transitions={},  # No transitions!
            initial_state='q0',
            halt_states={'halt'}
        )
        
        result = tm.run("a")
        assert result.halted  # Halted because stuck
        assert "No transition" in result.halt_reason
    
    def test_timeout(self):
        # Infinite loop machine
        tm = TuringMachine(
            states={'q0'},
            alphabet={'a', '_'},
            transitions={
                ('q0', 'a'): ('q0', 'a', 'R'),
                ('q0', '_'): ('q0', 'a', 'R'),
            },
            initial_state='q0',
            halt_states=set()  # No halt states!
        )
        
        result = tm.run("a", max_steps=100)
        assert not result.halted or "Timeout" in result.halt_reason
    
    def test_invalid_state(self):
        with pytest.raises(ValueError):
            TuringMachine(
                states={'q0'},
                alphabet={'a'},
                transitions={
                    ('q0', 'a'): ('q1', 'a', 'R'),  # q1 doesn't exist
                },
                initial_state='q0',
                halt_states=set()
            )


# =============================================================================
# Binary Increment Tests
# =============================================================================

class TestBinaryIncrement:
    """Test the binary increment machine."""
    
    def test_zero_to_one(self):
        tm = create_binary_increment()
        result = tm.run("0")
        assert result.tape_content == "1"
    
    def test_one_to_two(self):
        tm = create_binary_increment()
        result = tm.run("1")
        assert result.tape_content == "10"
    
    def test_three_to_four(self):
        tm = create_binary_increment()
        result = tm.run("11")
        assert result.tape_content == "100"
    
    def test_seven_to_eight(self):
        tm = create_binary_increment()
        result = tm.run("111")
        assert result.tape_content == "1000"
    
    def test_eleven_to_twelve(self):
        tm = create_binary_increment()
        result = tm.run("1011")
        assert result.tape_content == "1100"


# =============================================================================
# Unary Addition Tests
# =============================================================================

class TestUnaryAddition:
    """Test the unary addition machine."""
    
    def test_one_plus_one(self):
        tm = create_unary_addition()
        result = tm.run("1+1")
        assert result.tape_content == "11"
    
    def test_two_plus_three(self):
        tm = create_unary_addition()
        result = tm.run("11+111")
        assert result.tape_content == "11111"
    
    def test_three_plus_two(self):
        tm = create_unary_addition()
        result = tm.run("111+11")
        assert result.tape_content == "11111"


# =============================================================================
# Palindrome Tests
# =============================================================================

class TestPalindrome:
    """Test the palindrome checker machine."""
    
    def test_empty_is_palindrome(self):
        tm = create_palindrome_checker()
        result = tm.run("")
        assert result.final_state == "accept"
    
    def test_single_char(self):
        tm = create_palindrome_checker()
        result = tm.run("1")
        assert result.final_state == "accept"
    
    def test_simple_palindrome(self):
        tm = create_palindrome_checker()
        result = tm.run("11")
        assert result.final_state == "accept"
    
    def test_longer_palindrome(self):
        tm = create_palindrome_checker()
        result = tm.run("1001")
        assert result.final_state == "accept"
    
    def test_not_palindrome(self):
        tm = create_palindrome_checker()
        result = tm.run("10")
        assert result.final_state == "reject"
    
    def test_another_non_palindrome(self):
        tm = create_palindrome_checker()
        result = tm.run("1010")
        assert result.final_state == "reject"


# =============================================================================
# Busy Beaver Tests
# =============================================================================

class TestBusyBeaver:
    """Test the 3-state Busy Beaver."""
    
    def test_busy_beaver_runs(self):
        tm = create_busy_beaver_3()
        result = tm.run("", max_steps=100)
        assert result.halted
    
    def test_busy_beaver_produces_ones(self):
        tm = create_busy_beaver_3()
        result = tm.run("", max_steps=100)
        # 3-state BB produces 6 ones
        ones = result.tape_content.count('1')
        assert ones == 6
    
    def test_busy_beaver_steps(self):
        tm = create_busy_beaver_3()
        result = tm.run("", max_steps=100)
        # 3-state BB takes 13 steps (some sources count 14 including initial)
        assert result.steps == 13


# =============================================================================
# History and Trace Tests
# =============================================================================

class TestHistory:
    """Test execution history recording."""
    
    def test_record_history(self):
        tm = create_binary_increment()
        result = tm.run("1", record_history=True)
        assert len(result.history) > 0
    
    def test_trace_generator(self):
        tm = create_binary_increment()
        configs = list(trace(tm, "1", max_steps=50))
        assert len(configs) > 0
        assert configs[0].step == 0


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization functions."""
    
    def test_visualize_execution(self):
        tm = create_binary_increment()
        result = visualize_execution(tm, "1")
        assert "TURING MACHINE" in result
        assert "Binary Increment" in result
    
    def test_visualize_transition_table(self):
        tm = create_binary_increment()
        result = visualize_transition_table(tm)
        assert "Transition Table" in result
    
    def test_configuration_string(self):
        tape = Tape("abc")
        config = Configuration(state="q0", head_position=1, tape=tape, step=0)
        result = config.to_string()
        assert "q0" in result


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenience:
    """Test convenience functions."""
    
    def test_get_machine(self):
        tm = get_machine('binary_increment')
        assert tm is not None
    
    def test_get_machine_invalid(self):
        with pytest.raises(ValueError):
            get_machine('nonexistent')
    
    def test_machines_dict(self):
        assert 'binary_increment' in MACHINES
        assert 'busy_beaver_3' in MACHINES
    
    def test_run_function(self):
        tm = create_binary_increment()
        result = run(tm, "1")
        assert result.halted
    
    def test_visualize_function(self):
        tm = create_binary_increment()
        result = visualize(tm, "1")
        assert isinstance(result, str)


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_input(self):
        tm = create_binary_increment()
        result = tm.run("")
        assert result.halted
    
    def test_very_long_input(self):
        tm = create_binary_increment()
        result = tm.run("1" * 20, max_steps=1000)
        # 20 ones should become 100000... (21 bits)
        assert result.halted
    
    def test_single_state_machine(self):
        tm = TuringMachine(
            states={'halt'},
            alphabet={'a', '_'},
            transitions={},
            initial_state='halt',
            halt_states={'halt'}
        )
        result = tm.run("a")
        assert result.halted
        assert result.steps == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
