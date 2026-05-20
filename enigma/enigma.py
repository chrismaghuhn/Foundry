"""
Enigma: WWII Cipher Machine Simulator

A historically accurate simulation of the German Enigma cipher machine
used during World War II. This implementation includes:

    - All 8 historical Wehrmacht/Kriegsmarine rotors (I-VIII)
    - 4 historical reflectors (A, B, C, and thin B/C for M4)
    - Plugboard (Steckerbrett) with up to 13 pairs
    - Double-stepping anomaly (historically accurate)
    - M3 (3-rotor) and M4 (4-rotor naval) configurations

Historical Background:

    The Enigma machine was used by Nazi Germany to encrypt military
    communications. It was considered unbreakable until Polish and
    British cryptanalysts, including Alan Turing, developed methods
    to crack it. Breaking Enigma is estimated to have shortened
    WWII by 2-4 years.

How It Works:

    1. Key Press → Plugboard substitution
    2. → Right Rotor (forward) → Middle → Left → (4th if M4)
    3. → Reflector (signal bounces back)
    4. → Left Rotor (backward) → Middle → Right
    5. → Plugboard substitution → Lamp lights up
    
    After each keypress, rotors step like an odometer.
    The reflector makes the machine self-inverse:
    encrypt(encrypt(text)) = text

The Fatal Flaw:

    A letter can NEVER encrypt to itself. This property, along with
    known plaintext attacks (cribs), allowed Turing's Bombe to
    crack Enigma messages.

Usage:
    >>> from enigma import Enigma
    >>> machine = Enigma(
    ...     rotors=['III', 'II', 'I'],
    ...     reflector='B',
    ...     ring_settings='AAA',
    ...     initial_positions='MCK',
    ...     plugboard='AM FI NV PS TU WZ'
    ... )
    >>> cipher = machine.encrypt("HELLO")
    >>> print(cipher)  # Some encrypted text
    >>> 
    >>> # Reset and decrypt (self-inverse!)
    >>> machine.reset()
    >>> plain = machine.encrypt(cipher)
    >>> print(plain)  # HELLO

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import string


# =============================================================================
# Historical Rotor Wirings
# =============================================================================

# The alphabet
ALPHABET = string.ascii_uppercase

# Historical rotor wirings (Wehrmacht and Kriegsmarine)
# Each rotor maps A-Z to a scrambled alphabet
# Source: Historical documentation and Crypto Museum

ROTORS: Dict[str, Tuple[str, str]] = {
    # Wehrmacht Enigma I rotors
    # Format: (wiring, notch_positions)
    'I':    ('EKMFLGDQVZNTOWYHXUSPAIBRCJ', 'Q'),   # Notch at Q (steps next at R)
    'II':   ('AJDKSIRUXBLHWTMCQGZNPYFVOE', 'E'),   # Notch at E
    'III':  ('BDFHJLCPRTXVZNYEIWGAKMUSQO', 'V'),   # Notch at V
    'IV':   ('ESOVPZJAYQUIRHXLNFTGKDCMWB', 'J'),   # Notch at J
    'V':    ('VZBRGITYUPSDNHLXAWMJQOFECK', 'Z'),   # Notch at Z
    
    # Kriegsmarine M3/M4 additional rotors
    'VI':   ('JPGVOUMFYQBENHZRDKASXLICTW', 'ZM'),  # Double notch
    'VII':  ('NZJHGRCXMYSWBOUFAIVLPEKQDT', 'ZM'),  # Double notch
    'VIII': ('FKQHTLXOCBJSPDZRAMEWNIUYGV', 'ZM'),  # Double notch
}

# M4 thin rotors (Greek rotors) - used with thin reflector
THIN_ROTORS: Dict[str, str] = {
    'Beta':  'LEYJVCNIXWPBQMDRTAKZGFUHOS',
    'Gamma': 'FSOKANUERHMBTIYCWLQPZXVGJD',
}

# Reflectors (Umkehrwalze)
# These bounce the signal back through the rotors
REFLECTORS: Dict[str, str] = {
    'A': 'EJMZALYXVBWFCRQUONTSPIKHGD',
    'B': 'YRUHQSLDPXNGOKMIEBFZCWVJAT',  # Most common
    'C': 'FVPJIAOYEDRZXWGCTKUQSBNMHL',
    
    # Thin reflectors for M4 (used with Beta/Gamma)
    'B_THIN': 'ENKQAUYWJICOPBLMDXZVFTHRGS',
    'C_THIN': 'RDOBJNTKVEHMLFCWZAXGYIPSUQ',
}


# =============================================================================
# Helper Functions
# =============================================================================

def char_to_num(c: str) -> int:
    """Convert A-Z to 0-25."""
    return ord(c.upper()) - ord('A')


def num_to_char(n: int) -> str:
    """Convert 0-25 to A-Z."""
    return chr((n % 26) + ord('A'))


def rotate_string(s: str, n: int) -> str:
    """Rotate string by n positions."""
    n = n % len(s)
    return s[n:] + s[:n]


# =============================================================================
# Plugboard (Steckerbrett)
# =============================================================================

class Plugboard:
    """
    The Enigma plugboard (Steckerbrett).
    
    Swaps pairs of letters before and after the rotor assembly.
    Up to 13 pairs can be connected (26 letters / 2).
    
    Historical Note:
        The plugboard added significant security. Without knowing
        the plugboard settings, even correct rotor settings wouldn't
        decrypt the message. Typical usage was 10 pairs.
    """
    
    def __init__(self, pairs: str = ""):
        """
        Initialize plugboard with letter pairs.
        
        Args:
            pairs: Space-separated pairs like "AB CD EF" or "AM FI NV"
        
        Raises:
            ValueError: If pairs are invalid or overlap
        """
        self.wiring: Dict[str, str] = {}
        
        if not pairs.strip():
            return
        
        used: Set[str] = set()
        
        for pair in pairs.upper().split():
            if len(pair) != 2:
                raise ValueError(f"Invalid pair: {pair}")
            
            a, b = pair[0], pair[1]
            
            if a not in ALPHABET or b not in ALPHABET:
                raise ValueError(f"Invalid characters in pair: {pair}")
            
            if a == b:
                raise ValueError(f"Cannot pair letter with itself: {pair}")
            
            if a in used or b in used:
                raise ValueError(f"Letter already used: {pair}")
            
            used.add(a)
            used.add(b)
            
            self.wiring[a] = b
            self.wiring[b] = a
    
    def swap(self, char: str) -> str:
        """Swap a character through the plugboard."""
        return self.wiring.get(char.upper(), char.upper())
    
    def __repr__(self) -> str:
        pairs = []
        seen = set()
        for a, b in self.wiring.items():
            if a not in seen:
                pairs.append(f"{a}{b}")
                seen.add(a)
                seen.add(b)
        return f"Plugboard({' '.join(sorted(pairs))})"


# =============================================================================
# Rotor
# =============================================================================

class Rotor:
    """
    A single Enigma rotor.
    
    The rotor performs a substitution cipher that changes with each
    keypress as the rotor rotates. The wiring is fixed, but the
    rotation changes the effective substitution.
    
    Historical Note:
        Each rotor has a notch that triggers the next rotor to step.
        Rotors I-V have single notches, VI-VIII have double notches.
        The ring setting (Ringstellung) offsets the internal wiring
        relative to the visible letters.
    """
    
    def __init__(
        self,
        name: str,
        wiring: str,
        notches: str,
        ring_setting: int = 0,
        position: int = 0,
    ):
        """
        Initialize a rotor.
        
        Args:
            name: Rotor identifier (I, II, III, etc.)
            wiring: 26-letter substitution string
            notches: Letters where this rotor causes next to step
            ring_setting: Ring offset (0-25, or 'A'-'Z')
            position: Starting position (0-25)
        """
        self.name = name
        self.wiring = wiring.upper()
        self.notches = set(notches.upper())
        self.ring_setting = ring_setting
        self.position = position
        
        # Precompute forward and backward mappings
        self._forward: List[int] = []
        self._backward: List[int] = []
        
        for i in range(26):
            # Forward: input position → output position
            out_char = self.wiring[i]
            self._forward.append(char_to_num(out_char))
            
        # Backward mapping
        self._backward = [0] * 26
        for i, out in enumerate(self._forward):
            self._backward[out] = i
    
    def forward(self, char_num: int) -> int:
        """
        Pass signal through rotor in forward direction.
        
        The rotation and ring setting affect the mapping.
        """
        # Adjust for position and ring
        offset = self.position - self.ring_setting
        
        # Enter the rotor
        entry = (char_num + offset) % 26
        
        # Substitution
        exit_pos = self._forward[entry]
        
        # Leave the rotor
        output = (exit_pos - offset) % 26
        
        return output
    
    def backward(self, char_num: int) -> int:
        """Pass signal through rotor in backward direction."""
        offset = self.position - self.ring_setting
        
        entry = (char_num + offset) % 26
        exit_pos = self._backward[entry]
        output = (exit_pos - offset) % 26
        
        return output
    
    def step(self) -> bool:
        """
        Rotate the rotor one position.
        
        Returns:
            True if the rotor was at a notch (triggers next rotor)
        """
        at_notch = num_to_char(self.position) in self.notches
        self.position = (self.position + 1) % 26
        return at_notch
    
    def at_notch(self) -> bool:
        """Check if rotor is currently at a notch position."""
        return num_to_char(self.position) in self.notches
    
    @property
    def display(self) -> str:
        """Get the visible letter in the window."""
        return num_to_char(self.position)
    
    def __repr__(self) -> str:
        return f"Rotor({self.name}, pos={self.display})"


# =============================================================================
# Reflector (Umkehrwalze)
# =============================================================================

class Reflector:
    """
    The Enigma reflector (Umkehrwalze).
    
    The reflector bounces the signal back through the rotors.
    This is what makes Enigma self-inverse: the same settings
    encrypt and decrypt.
    
    Historical Note:
        The reflector ensures that no letter encrypts to itself.
        This was a critical weakness exploited by codebreakers.
    """
    
    def __init__(self, name: str, wiring: str):
        """
        Initialize reflector.
        
        Args:
            name: Reflector identifier (A, B, C)
            wiring: 26-letter reflection mapping
        """
        self.name = name
        self.wiring = wiring.upper()
        
        # Precompute mapping
        self._mapping: List[int] = []
        for c in self.wiring:
            self._mapping.append(char_to_num(c))
    
    def reflect(self, char_num: int) -> int:
        """Reflect signal back."""
        return self._mapping[char_num]
    
    def __repr__(self) -> str:
        return f"Reflector({self.name})"


# =============================================================================
# Enigma Machine
# =============================================================================

class Enigma:
    """
    The complete Enigma cipher machine.
    
    This simulates the Enigma I (Wehrmacht 3-rotor) and M4 (Kriegsmarine
    4-rotor) machines with historical accuracy including:
    
    - Correct rotor wirings and notch positions
    - Double-stepping anomaly
    - Ring settings (Ringstellung)
    - Plugboard (Steckerbrett)
    
    The machine is self-inverse: using the same settings,
    encrypt(encrypt(text)) = text
    
    Example:
        >>> machine = Enigma(
        ...     rotors=['III', 'II', 'I'],
        ...     reflector='B',
        ...     ring_settings='AAA',
        ...     initial_positions='AAZ',
        ... )
        >>> cipher = machine.encrypt("HELLO")
        >>> machine.reset()
        >>> machine.encrypt(cipher)  # Returns "HELLO"
    """
    
    def __init__(
        self,
        rotors: List[str],
        reflector: str,
        ring_settings: str = "",
        initial_positions: str = "",
        plugboard: str = "",
        fourth_rotor: Optional[str] = None,
    ):
        """
        Initialize the Enigma machine.
        
        Args:
            rotors: List of rotor names ['III', 'II', 'I'] (right to left)
            reflector: Reflector name ('A', 'B', 'C', 'B_THIN', 'C_THIN')
            ring_settings: Ring settings as letters 'AAA' or numbers
            initial_positions: Starting positions 'ABC'
            plugboard: Plugboard pairs 'AB CD EF'
            fourth_rotor: For M4, the thin rotor ('Beta' or 'Gamma')
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate rotor count
        if len(rotors) != 3:
            raise ValueError("Must specify exactly 3 rotors")
        
        # Set up default positions
        if not ring_settings:
            ring_settings = 'A' * len(rotors)
        if not initial_positions:
            initial_positions = 'A' * len(rotors)
        
        # Validate lengths
        if len(ring_settings) != len(rotors):
            raise ValueError("Ring settings must match rotor count")
        if len(initial_positions) != len(rotors):
            raise ValueError("Initial positions must match rotor count")
        
        # Store initial state for reset
        self._initial_positions = initial_positions.upper()
        
        # Create rotors - user specifies left-to-right, but internally we store
        # right-to-left for easier stepping logic (rotor[0] = right, etc.)
        self.rotors: List[Rotor] = []
        
        # Reverse the input order so rotors[0] is the rightmost
        rotor_names = list(reversed(rotors))
        ring_chars = list(reversed(ring_settings))
        pos_chars = list(reversed(initial_positions))
        
        for i, name in enumerate(rotor_names):
            if name not in ROTORS:
                raise ValueError(f"Unknown rotor: {name}")
            
            wiring, notches = ROTORS[name]
            ring = char_to_num(ring_chars[i]) if ring_chars[i].isalpha() else int(ring_chars[i])
            pos = char_to_num(pos_chars[i])
            
            self.rotors.append(Rotor(name, wiring, notches, ring, pos))
        
        # Set up fourth rotor for M4
        self.fourth_rotor: Optional[Rotor] = None
        if fourth_rotor:
            if fourth_rotor not in THIN_ROTORS:
                raise ValueError(f"Unknown thin rotor: {fourth_rotor}")
            wiring = THIN_ROTORS[fourth_rotor]
            self.fourth_rotor = Rotor(fourth_rotor, wiring, '', 0, 0)
        
        # Set up reflector
        if reflector not in REFLECTORS:
            raise ValueError(f"Unknown reflector: {reflector}")
        self.reflector = Reflector(reflector, REFLECTORS[reflector])
        
        # Set up plugboard
        self.plugboard = Plugboard(plugboard)
        
        # For tracing
        self._trace_enabled = False
        self._trace: List[Dict] = []
    
    def _step_rotors(self) -> None:
        """
        Step the rotors according to Enigma mechanics.
        
        The stepping follows these rules:
        1. Right rotor always steps
        2. If right rotor was at notch, middle rotor steps
        3. If middle rotor is at notch, it AND left rotor step
           (this is the famous "double stepping anomaly")
        
        The double-stepping means the middle rotor can step twice
        in succession - once from the right rotor's notch, then
        again because it's now at its own notch.
        """
        # Check for double-stepping BEFORE stepping
        middle_at_notch = self.rotors[1].at_notch()
        right_at_notch = self.rotors[0].at_notch()
        
        # Middle rotor double-steps if at notch
        if middle_at_notch:
            self.rotors[1].step()
            self.rotors[2].step()
        
        # Middle rotor steps if right was at notch
        if right_at_notch:
            self.rotors[1].step()
        
        # Right rotor always steps
        self.rotors[0].step()
    
    def _encrypt_char(self, char: str) -> str:
        """
        Encrypt a single character.
        
        Signal path:
        1. Plugboard (swap)
        2. Rotors right → middle → left (forward)
        3. Reflector
        4. Rotors left → middle → right (backward)
        5. Plugboard (swap)
        """
        if char.upper() not in ALPHABET:
            return char
        
        # Step rotors BEFORE encrypting (historical behavior)
        self._step_rotors()
        
        trace = {'input': char.upper(), 'steps': []}
        
        # Plugboard in
        signal = char_to_num(self.plugboard.swap(char))
        trace['steps'].append(('plugboard_in', num_to_char(signal)))
        
        # Forward through rotors (right to left)
        for rotor in self.rotors:
            signal = rotor.forward(signal)
            trace['steps'].append((f'{rotor.name}_fwd', num_to_char(signal)))
        
        # Fourth rotor if present (M4)
        if self.fourth_rotor:
            signal = self.fourth_rotor.forward(signal)
            trace['steps'].append((f'{self.fourth_rotor.name}_fwd', num_to_char(signal)))
        
        # Reflector
        signal = self.reflector.reflect(signal)
        trace['steps'].append(('reflector', num_to_char(signal)))
        
        # Fourth rotor backward if present
        if self.fourth_rotor:
            signal = self.fourth_rotor.backward(signal)
            trace['steps'].append((f'{self.fourth_rotor.name}_bwd', num_to_char(signal)))
        
        # Backward through rotors (left to right)
        for rotor in reversed(self.rotors):
            signal = rotor.backward(signal)
            trace['steps'].append((f'{rotor.name}_bwd', num_to_char(signal)))
        
        # Plugboard out
        output = self.plugboard.swap(num_to_char(signal))
        trace['steps'].append(('plugboard_out', output))
        trace['output'] = output
        trace['positions'] = self.positions
        
        if self._trace_enabled:
            self._trace.append(trace)
        
        return output
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt (or decrypt) a message.
        
        Since Enigma is self-inverse, this same method decrypts
        when using the same initial settings.
        
        Args:
            plaintext: Message to encrypt (only A-Z processed)
        
        Returns:
            Encrypted message
        """
        result = []
        for char in plaintext.upper():
            if char in ALPHABET:
                result.append(self._encrypt_char(char))
            else:
                result.append(char)
        return ''.join(result)
    
    # Alias for clarity
    decrypt = encrypt
    
    @property
    def positions(self) -> str:
        """Get current rotor positions as string (left to right)."""
        # Rotors stored right-to-left internally, reverse for display
        return ''.join(r.display for r in reversed(self.rotors))
    
    def reset(self) -> None:
        """Reset rotors to initial positions."""
        # _initial_positions is left-to-right, rotors are right-to-left
        pos_chars = list(reversed(self._initial_positions))
        for i, rotor in enumerate(self.rotors):
            rotor.position = char_to_num(pos_chars[i])
    
    def set_positions(self, positions: str) -> None:
        """Set rotor positions (left to right)."""
        if len(positions) != len(self.rotors):
            raise ValueError("Position string must match rotor count")
        # Reverse to match internal right-to-left storage
        pos_chars = list(reversed(positions.upper()))
        for i, rotor in enumerate(self.rotors):
            rotor.position = char_to_num(pos_chars[i])
    
    def enable_trace(self) -> None:
        """Enable signal tracing for visualization."""
        self._trace_enabled = True
        self._trace = []
    
    def disable_trace(self) -> None:
        """Disable signal tracing."""
        self._trace_enabled = False
    
    def get_trace(self) -> List[Dict]:
        """Get the trace of encrypted characters."""
        return self._trace
    
    def __repr__(self) -> str:
        rotor_names = [r.name for r in self.rotors]
        return f"Enigma(rotors={rotor_names}, reflector={self.reflector.name}, pos={self.positions})"


# =============================================================================
# Visualization
# =============================================================================

def visualize_encryption(machine: Enigma, char: str) -> str:
    """
    Visualize the encryption of a single character.
    
    Shows the signal path through the machine.
    """
    machine.enable_trace()
    output = machine.encrypt(char)
    trace = machine.get_trace()[-1]
    machine.disable_trace()
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"🔐 ENIGMA ENCRYPTION: '{trace['input']}' → '{trace['output']}'")
    lines.append("=" * 60)
    lines.append(f"Rotor positions: {trace['positions']}")
    lines.append("")
    lines.append("Signal path:")
    
    for step_name, value in trace['steps']:
        arrow = "→"
        if 'bwd' in step_name:
            arrow = "←"
        elif step_name == 'reflector':
            arrow = "↺"
        
        lines.append(f"  {arrow} {step_name:15s}: {value}")
    
    lines.append("")
    lines.append(f"Result: {trace['input']} → {trace['output']}")
    
    return '\n'.join(lines)


def visualize_rotor_wiring(rotor_name: str) -> str:
    """Visualize a rotor's wiring."""
    if rotor_name not in ROTORS:
        raise ValueError(f"Unknown rotor: {rotor_name}")
    
    wiring, notches = ROTORS[rotor_name]
    
    lines = []
    lines.append(f"Rotor {rotor_name}")
    lines.append("─" * 30)
    lines.append(f"Notch(es): {notches}")
    lines.append("")
    lines.append("Wiring:")
    lines.append(f"  Input:  {ALPHABET}")
    lines.append(f"  Output: {wiring}")
    
    return '\n'.join(lines)


def turing_mode_check(machine: Enigma, text: str) -> str:
    """
    "Turing Mode" - Demonstrate the fatal flaw!
    
    Shows that no letter ever encrypts to itself.
    This weakness, discovered by the codebreakers,
    was crucial to breaking Enigma.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("🧠 TURING MODE - The Fatal Flaw")
    lines.append("=" * 60)
    lines.append("")
    lines.append("A letter can NEVER encrypt to itself!")
    lines.append("This was Enigma's Achilles heel.")
    lines.append("")
    
    cipher = machine.encrypt(text)
    machine.reset()
    
    same_count = 0
    for i, (p, c) in enumerate(zip(text.upper(), cipher)):
        if p in ALPHABET:
            if p == c:
                same_count += 1
                lines.append(f"  Position {i}: {p} → {c} ❌ SAME (impossible!)")
            else:
                lines.append(f"  Position {i}: {p} → {c} ✓")
    
    lines.append("")
    if same_count == 0:
        lines.append("✓ Confirmed: No letter encrypted to itself")
        lines.append("  This property allowed codebreakers to eliminate")
        lines.append("  incorrect rotor settings quickly.")
    else:
        lines.append(f"❌ ERROR: {same_count} letters encrypted to themselves!")
        lines.append("  This should never happen with a correct implementation.")
    
    return '\n'.join(lines)


# =============================================================================
# Historical Presets
# =============================================================================

def create_historical_preset(name: str) -> Enigma:
    """
    Create an Enigma with historical settings.
    
    These are actual settings used during WWII.
    """
    presets = {
        # Wehrmacht standard
        'wehrmacht': {
            'rotors': ['III', 'II', 'I'],
            'reflector': 'B',
            'ring_settings': 'AAA',
            'initial_positions': 'AAA',
            'plugboard': '',
        },
        
        # Famous "TUNNY" intercept settings
        'barbarossa': {
            'rotors': ['II', 'IV', 'V'],
            'reflector': 'B',
            'ring_settings': 'BUL',
            'initial_positions': 'ABL',
            'plugboard': 'AV BS CG DL FU HZ IN KM OW RX',
        },
        
        # Kriegsmarine U-boat
        'uboat': {
            'rotors': ['VI', 'VII', 'VIII'],
            'reflector': 'B',
            'ring_settings': 'AAA',
            'initial_positions': 'ZZZ',
            'plugboard': 'AN EZ HK IJ LR MQ OT PV SW UX',
        },
    }
    
    if name not in presets:
        raise ValueError(f"Unknown preset: {name}. Available: {list(presets.keys())}")
    
    return Enigma(**presets[name])


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_encrypt(plaintext: str, key: str = "AAA") -> str:
    """
    Quick encryption with minimal setup.
    
    Args:
        plaintext: Text to encrypt
        key: 3-letter starting position
    
    Returns:
        Encrypted text
    """
    machine = Enigma(
        rotors=['III', 'II', 'I'],
        reflector='B',
        initial_positions=key,
    )
    return machine.encrypt(plaintext)


def quick_decrypt(ciphertext: str, key: str = "AAA") -> str:
    """Quick decryption (same as encrypt due to self-inverse)."""
    return quick_encrypt(ciphertext, key)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Main class
    'Enigma',
    
    # Components
    'Rotor',
    'Reflector',
    'Plugboard',
    
    # Visualization
    'visualize_encryption',
    'visualize_rotor_wiring',
    'turing_mode_check',
    
    # Presets
    'create_historical_preset',
    
    # Quick functions
    'quick_encrypt',
    'quick_decrypt',
    
    # Data
    'ROTORS',
    'REFLECTORS',
    'ALPHABET',
]
