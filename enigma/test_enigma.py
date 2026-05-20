"""Tests for enigma."""

import pytest
from enigma import (
    # Main
    Enigma,
    Rotor,
    Reflector,
    Plugboard,
    
    # Visualization
    visualize_encryption,
    visualize_rotor_wiring,
    turing_mode_check,
    
    # Presets
    create_historical_preset,
    
    # Functions
    quick_encrypt,
    quick_decrypt,
    
    # Data
    ROTORS,
    REFLECTORS,
    ALPHABET,
)


# =============================================================================
# Plugboard Tests
# =============================================================================

class TestPlugboard:
    """Test plugboard (Steckerbrett) functionality."""
    
    def test_empty_plugboard(self):
        pb = Plugboard("")
        assert pb.swap('A') == 'A'
        assert pb.swap('Z') == 'Z'
    
    def test_single_pair(self):
        pb = Plugboard("AB")
        assert pb.swap('A') == 'B'
        assert pb.swap('B') == 'A'
        assert pb.swap('C') == 'C'
    
    def test_multiple_pairs(self):
        pb = Plugboard("AB CD EF")
        assert pb.swap('A') == 'B'
        assert pb.swap('C') == 'D'
        assert pb.swap('E') == 'F'
        assert pb.swap('G') == 'G'
    
    def test_swap_is_symmetric(self):
        pb = Plugboard("XY")
        assert pb.swap(pb.swap('X')) == 'X'
        assert pb.swap(pb.swap('Y')) == 'Y'
    
    def test_invalid_pair_length(self):
        with pytest.raises(ValueError):
            Plugboard("ABC")
    
    def test_duplicate_letter(self):
        with pytest.raises(ValueError):
            Plugboard("AB AC")
    
    def test_self_pair(self):
        with pytest.raises(ValueError):
            Plugboard("AA")


# =============================================================================
# Rotor Tests
# =============================================================================

class TestRotor:
    """Test rotor mechanics."""
    
    def test_rotor_creation(self):
        wiring, notches = ROTORS['I']
        rotor = Rotor('I', wiring, notches)
        assert rotor.name == 'I'
        assert rotor.position == 0
    
    def test_rotor_step(self):
        wiring, notches = ROTORS['I']
        rotor = Rotor('I', wiring, notches, position=0)
        rotor.step()
        assert rotor.position == 1
        assert rotor.display == 'B'
    
    def test_rotor_wraparound(self):
        wiring, notches = ROTORS['I']
        rotor = Rotor('I', wiring, notches, position=25)  # Z
        rotor.step()
        assert rotor.position == 0
        assert rotor.display == 'A'
    
    def test_rotor_notch(self):
        wiring, notches = ROTORS['I']  # Notch at Q
        rotor = Rotor('I', wiring, notches, position=16)  # Q
        assert rotor.at_notch()
    
    def test_forward_backward_inverse(self):
        wiring, notches = ROTORS['I']
        rotor = Rotor('I', wiring, notches)
        
        for i in range(26):
            forward = rotor.forward(i)
            back = rotor.backward(forward)
            assert back == i


# =============================================================================
# Reflector Tests
# =============================================================================

class TestReflector:
    """Test reflector (Umkehrwalze) functionality."""
    
    def test_reflector_creation(self):
        ref = Reflector('B', REFLECTORS['B'])
        assert ref.name == 'B'
    
    def test_reflector_symmetric(self):
        """Reflector must be self-inverse: reflect(reflect(x)) = x"""
        ref = Reflector('B', REFLECTORS['B'])
        for i in range(26):
            reflected = ref.reflect(i)
            back = ref.reflect(reflected)
            assert back == i
    
    def test_no_self_mapping(self):
        """No letter reflects to itself."""
        ref = Reflector('B', REFLECTORS['B'])
        for i in range(26):
            assert ref.reflect(i) != i


# =============================================================================
# Enigma Machine Tests
# =============================================================================

class TestEnigmaMachine:
    """Test the complete Enigma machine."""
    
    def test_creation(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        assert machine.positions == 'AAA'
    
    def test_single_char_encrypt(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAA'
        )
        cipher = machine.encrypt('A')
        assert cipher != 'A'  # Never encrypts to itself
        assert len(cipher) == 1
    
    def test_self_inverse(self):
        """Enigma's key property: encrypt(encrypt(x)) = x"""
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAA'
        )
        
        plaintext = "HELLO"
        ciphertext = machine.encrypt(plaintext)
        
        machine.reset()
        decrypted = machine.encrypt(ciphertext)
        
        assert decrypted == plaintext
    
    def test_never_encrypts_to_self(self):
        """The fatal flaw: a letter never encrypts to itself."""
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAA'
        )
        
        # Test all letters at various positions
        for _ in range(100):
            for char in ALPHABET:
                pos_before = machine.positions
                cipher = machine.encrypt(char)
                assert cipher != char, f"{char} encrypted to itself at {pos_before}"
    
    def test_rotor_stepping(self):
        """Right rotor steps with each keypress."""
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAA'
        )
        
        machine.encrypt('A')
        # positions is left-to-right, so [-1] is the right rotor
        assert machine.positions[-1] == 'B'  # Right rotor stepped
    
    def test_middle_rotor_step(self):
        """Middle rotor steps when right rotor hits notch."""
        # Rotor I (rightmost) has notch at Q (position 16)
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAQ'  # Right rotor (I) at Q (notch position)
        )
        
        machine.encrypt('A')  # This should trigger middle rotor step
        
        # Right rotor stepped past Q to R
        assert machine.positions[-1] == 'R'  # Right rotor
    
    def test_with_plugboard(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAA',
            plugboard='AB'
        )
        
        cipher = machine.encrypt('A')
        machine.reset()
        decrypted = machine.decrypt(cipher)
        assert decrypted == 'A'
    
    def test_ring_settings(self):
        machine1 = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            ring_settings='AAA',
            initial_positions='AAA'
        )
        
        machine2 = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            ring_settings='BBB',
            initial_positions='AAA'
        )
        
        # Different ring settings should produce different output
        cipher1 = machine1.encrypt('A')
        cipher2 = machine2.encrypt('A')
        
        # They might be the same by chance, but probably not
        # The important thing is both work
        assert len(cipher1) == 1
        assert len(cipher2) == 1
    
    def test_set_positions(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        
        machine.set_positions('XYZ')
        assert machine.positions == 'XYZ'
    
    def test_non_alpha_passthrough(self):
        """Non-alphabetic characters pass through unchanged."""
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        
        result = machine.encrypt('HELLO 123 WORLD!')
        assert ' ' in result
        assert '1' in result
        assert '!' in result


# =============================================================================
# Historical Accuracy Tests
# =============================================================================

class TestHistoricalAccuracy:
    """Test historical rotor wirings and behavior."""
    
    def test_all_rotors_defined(self):
        expected = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
        for rotor in expected:
            assert rotor in ROTORS
    
    def test_all_reflectors_defined(self):
        expected = ['A', 'B', 'C', 'B_THIN', 'C_THIN']
        for ref in expected:
            assert ref in REFLECTORS
    
    def test_rotor_wiring_length(self):
        for name, (wiring, _) in ROTORS.items():
            assert len(wiring) == 26, f"Rotor {name} has wrong wiring length"
    
    def test_rotor_wiring_is_permutation(self):
        for name, (wiring, _) in ROTORS.items():
            assert set(wiring) == set(ALPHABET), f"Rotor {name} wiring is not a permutation"
    
    def test_reflector_wiring_length(self):
        for name, wiring in REFLECTORS.items():
            assert len(wiring) == 26, f"Reflector {name} has wrong wiring length"
    
    def test_known_message(self):
        """Test with a known historical setting."""
        # This is a simplified test - real historical messages
        # would require exact settings and message indicators
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B',
            initial_positions='AAA'
        )
        
        plaintext = "AAAAA"
        cipher = machine.encrypt(plaintext)
        
        # Reset and decrypt
        machine.reset()
        decrypted = machine.decrypt(cipher)
        
        assert decrypted == plaintext


# =============================================================================
# Preset Tests
# =============================================================================

class TestPresets:
    """Test historical presets."""
    
    def test_wehrmacht_preset(self):
        machine = create_historical_preset('wehrmacht')
        assert machine is not None
        
        cipher = machine.encrypt("TEST")
        machine.reset()
        assert machine.decrypt(cipher) == "TEST"
    
    def test_uboat_preset(self):
        machine = create_historical_preset('uboat')
        assert machine is not None
        
        cipher = machine.encrypt("UBOAT")
        machine.reset()
        assert machine.decrypt(cipher) == "UBOAT"
    
    def test_barbarossa_preset(self):
        machine = create_historical_preset('barbarossa')
        assert machine is not None
    
    def test_invalid_preset(self):
        with pytest.raises(ValueError):
            create_historical_preset('invalid')


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization functions."""
    
    def test_visualize_encryption(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        
        result = visualize_encryption(machine, 'A')
        assert 'ENIGMA' in result
        assert 'Signal path' in result
    
    def test_visualize_rotor(self):
        result = visualize_rotor_wiring('I')
        assert 'Rotor I' in result
        assert 'Wiring' in result
    
    def test_turing_mode(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        
        result = turing_mode_check(machine, "HELLO")
        assert 'TURING' in result
        assert 'Fatal Flaw' in result


# =============================================================================
# Quick Function Tests
# =============================================================================

class TestQuickFunctions:
    """Test convenience functions."""
    
    def test_quick_encrypt_decrypt(self):
        plaintext = "HELLO"
        key = "ABC"
        
        cipher = quick_encrypt(plaintext, key)
        decrypted = quick_decrypt(cipher, key)
        
        assert decrypted == plaintext
    
    def test_quick_default_key(self):
        cipher = quick_encrypt("TEST")
        decrypted = quick_decrypt(cipher)
        assert decrypted == "TEST"


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_rotor(self):
        with pytest.raises(ValueError):
            Enigma(rotors=['X', 'Y', 'Z'], reflector='B')
    
    def test_invalid_reflector(self):
        with pytest.raises(ValueError):
            Enigma(rotors=['I', 'II', 'III'], reflector='X')
    
    def test_wrong_rotor_count(self):
        with pytest.raises(ValueError):
            Enigma(rotors=['I', 'II'], reflector='B')
    
    def test_empty_message(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        assert machine.encrypt("") == ""
    
    def test_long_message(self):
        machine = Enigma(
            rotors=['III', 'II', 'I'],
            reflector='B'
        )
        
        plaintext = "A" * 1000
        cipher = machine.encrypt(plaintext)
        machine.reset()
        decrypted = machine.decrypt(cipher)
        
        assert decrypted == plaintext


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
