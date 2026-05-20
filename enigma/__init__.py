"""
Enigma: WWII Cipher Machine Simulator

A historically accurate simulation of the German Enigma cipher machine.
Encrypt messages like it's 1942. Understand how Turing cracked it.

Quick Start:
    >>> from enigma import Enigma
    >>> 
    >>> machine = Enigma(
    ...     rotors=['III', 'II', 'I'],
    ...     reflector='B',
    ...     initial_positions='AAA'
    ... )
    >>> 
    >>> cipher = machine.encrypt("HELLO")
    >>> machine.reset()
    >>> plain = machine.decrypt(cipher)  # HELLO

The Self-Inverse Property:
    Enigma's reflector makes it self-inverse:
        encrypt(encrypt(message)) = message
    
    This was convenient but also a weakness!

The Fatal Flaw:
    A letter can NEVER encrypt to itself.
    This property allowed Turing's Bombe to
    eliminate impossible rotor settings.

Historical Settings:
    >>> from enigma import create_historical_preset
    >>> machine = create_historical_preset('uboat')

Components:
    - Rotors I-VIII with historical wirings
    - Reflectors A, B, C (and thin B/C for M4)
    - Plugboard (Steckerbrett) with up to 13 pairs
    - Ring settings (Ringstellung)
    - Double-stepping anomaly (historically accurate)
"""

from .enigma import (
    # Main class
    Enigma,
    
    # Components
    Rotor,
    Reflector,
    Plugboard,
    
    # Visualization
    visualize_encryption,
    visualize_rotor_wiring,
    turing_mode_check,
    
    # Presets
    create_historical_preset,
    
    # Quick functions
    quick_encrypt,
    quick_decrypt,
    
    # Data
    ROTORS,
    REFLECTORS,
    THIN_ROTORS,
    ALPHABET,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Main
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
    'THIN_ROTORS',
    'ALPHABET',
]
