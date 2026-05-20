#!/usr/bin/env python3
"""
Enigma Usage Examples

WWII Cipher Machine Simulator.
Encrypt messages like it's 1942!
"""

from enigma import (
    Enigma,
    visualize_encryption,
    visualize_rotor_wiring,
    turing_mode_check,
    create_historical_preset,
    quick_encrypt,
    quick_decrypt,
    ROTORS,
)


def example_basic():
    """
    Example 1: Basic Encryption/Decryption
    """
    print("=" * 60)
    print("Example 1: Basic Encryption/Decryption")
    print("=" * 60)
    
    machine = Enigma(
        rotors=['III', 'II', 'I'],
        reflector='B',
        initial_positions='AAA'
    )
    
    plaintext = "HELLO"
    print(f"\nPlaintext: {plaintext}")
    print(f"Settings: Rotors III-II-I, Reflector B, Position AAA")
    
    ciphertext = machine.encrypt(plaintext)
    print(f"Ciphertext: {ciphertext}")
    
    # The magic: same settings decrypt!
    machine.reset()
    decrypted = machine.encrypt(ciphertext)
    print(f"Decrypted: {decrypted}")
    print(f"\n✓ Self-inverse property verified!")
    print()


def example_plugboard():
    """
    Example 2: Using the Plugboard
    """
    print("=" * 60)
    print("Example 2: The Plugboard (Steckerbrett)")
    print("=" * 60)
    
    print("\nThe plugboard swaps letter pairs BEFORE and AFTER the rotors.")
    print("This added enormous complexity for codebreakers.")
    
    machine = Enigma(
        rotors=['III', 'II', 'I'],
        reflector='B',
        initial_positions='AAA',
        plugboard='AB CD EF'  # Swap A↔B, C↔D, E↔F
    )
    
    plaintext = "ABCDEF"
    print(f"\nPlugboard: AB CD EF")
    print(f"Plaintext: {plaintext}")
    
    ciphertext = machine.encrypt(plaintext)
    print(f"Ciphertext: {ciphertext}")
    
    machine.reset()
    decrypted = machine.decrypt(ciphertext)
    print(f"Decrypted: {decrypted}")
    print()


def example_self_inverse():
    """
    Example 3: The Self-Inverse Property
    """
    print("=" * 60)
    print("Example 3: 🔄 Self-Inverse Magic")
    print("=" * 60)
    
    print("""
The Enigma's reflector makes it self-inverse:
    encrypt(encrypt(message)) = message

This was convenient for operators but also a weakness!
Same machine, same settings → encrypts AND decrypts.
""")
    
    machine = Enigma(
        rotors=['III', 'II', 'I'],
        reflector='B',
        initial_positions='XYZ'
    )
    
    message = "SECRETMESSAGE"
    print(f"Original: {message}")
    
    # Encrypt
    cipher = machine.encrypt(message)
    print(f"Encrypted: {cipher}")
    
    # Reset and "encrypt" again = decrypt
    machine.reset()
    back = machine.encrypt(cipher)
    print(f"Encrypt again: {back}")
    
    print(f"\n✓ {message} → {cipher} → {back}")
    print()


def example_turing_mode():
    """
    Example 4: The Fatal Flaw (Turing Mode)
    """
    print("=" * 60)
    print("Example 4: 🧠 TURING MODE - The Fatal Flaw")
    print("=" * 60)
    
    print("""
Alan Turing exploited a critical weakness:
A letter can NEVER encrypt to itself!

This allowed codebreakers to eliminate impossible
rotor settings when they knew (or guessed) part
of the plaintext (called a "crib").
""")
    
    machine = Enigma(
        rotors=['III', 'II', 'I'],
        reflector='B',
        initial_positions='AAA'
    )
    
    print(turing_mode_check(machine, "AAAAA"))
    print()


def example_visualization():
    """
    Example 5: Visualize the Signal Path
    """
    print("=" * 60)
    print("Example 5: 🔌 Signal Path Visualization")
    print("=" * 60)
    
    machine = Enigma(
        rotors=['III', 'II', 'I'],
        reflector='B',
        initial_positions='AAA'
    )
    
    print(visualize_encryption(machine, 'A'))
    print()


def example_rotor_wiring():
    """
    Example 6: Historical Rotor Wirings
    """
    print("=" * 60)
    print("Example 6: 📜 Historical Rotor Wirings")
    print("=" * 60)
    
    print("\nThe Wehrmacht used 5 rotors (I-V).")
    print("The Kriegsmarine added rotors VI-VIII with double notches.\n")
    
    for rotor in ['I', 'III', 'VI']:
        print(visualize_rotor_wiring(rotor))
        print()


def example_presets():
    """
    Example 7: Historical Presets
    """
    print("=" * 60)
    print("Example 7: 🏛️ Historical Settings")
    print("=" * 60)
    
    print("\nUsing actual WWII Enigma configurations:\n")
    
    # Wehrmacht
    print("--- Wehrmacht Standard ---")
    machine = create_historical_preset('wehrmacht')
    cipher = machine.encrypt("PANZER")
    machine.reset()
    print(f"PANZER → {cipher} → {machine.decrypt(cipher)}")
    
    # U-boat
    print("\n--- Kriegsmarine U-Boot ---")
    machine = create_historical_preset('uboat')
    cipher = machine.encrypt("TORPEDO")
    machine.reset()
    print(f"TORPEDO → {cipher} → {machine.decrypt(cipher)}")
    
    # Barbarossa
    print("\n--- Operation Barbarossa ---")
    machine = create_historical_preset('barbarossa')
    cipher = machine.encrypt("ANGRIFF")
    machine.reset()
    print(f"ANGRIFF → {cipher} → {machine.decrypt(cipher)}")
    print()


def example_quick():
    """
    Example 8: Quick Functions
    """
    print("=" * 60)
    print("Example 8: ⚡ Quick Encryption")
    print("=" * 60)
    
    print("\nFor simple encryption with minimal setup:\n")
    
    message = "QUICKTEST"
    key = "XYZ"
    
    cipher = quick_encrypt(message, key)
    decrypted = quick_decrypt(cipher, key)
    
    print(f"Message: {message}")
    print(f"Key: {key}")
    print(f"Encrypted: {cipher}")
    print(f"Decrypted: {decrypted}")
    print()


def example_message():
    """
    Example 9: A Complete Message
    """
    print("=" * 60)
    print("Example 9: 📨 Complete Message Exchange")
    print("=" * 60)
    
    print("""
Scenario: Berlin sends a message to a U-boat.
Both sides have the same daily key settings.
""")
    
    # Daily settings (from codebook)
    settings = {
        'rotors': ['IV', 'II', 'V'],
        'reflector': 'B',
        'ring_settings': 'BUL',
        'plugboard': 'AV BS CG DL FU HZ IN KM OW RX',
    }
    
    # Message indicator (random starting position)
    message_key = 'QWE'
    
    print(f"Daily Settings: Rotors {settings['rotors']}")
    print(f"Ring Settings: {settings['ring_settings']}")
    print(f"Plugboard: {settings['plugboard']}")
    print(f"Message Key: {message_key}")
    
    # Sender
    sender = Enigma(**settings, initial_positions=message_key)
    plaintext = "ANGRIFF AUF KONVOI UM ACHT UHR"
    plaintext_clean = plaintext.replace(' ', 'X')  # Historical convention
    
    print(f"\nPlaintext: {plaintext}")
    print(f"(Spaces as X: {plaintext_clean})")
    
    ciphertext = sender.encrypt(plaintext_clean)
    print(f"Ciphertext: {ciphertext}")
    
    # Receiver
    receiver = Enigma(**settings, initial_positions=message_key)
    decrypted = receiver.decrypt(ciphertext)
    
    print(f"\n--- At U-boat ---")
    print(f"Received: {ciphertext}")
    print(f"Decrypted: {decrypted}")
    print(f"Message: {decrypted.replace('X', ' ')}")
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ███████╗███╗   ██╗██╗ ██████╗ ███╗   ███╗ █████╗             ║
║  ██╔════╝████╗  ██║██║██╔════╝ ████╗ ████║██╔══██╗            ║
║  █████╗  ██╔██╗ ██║██║██║  ███╗██╔████╔██║███████║            ║
║  ██╔══╝  ██║╚██╗██║██║██║   ██║██║╚██╔╝██║██╔══██║            ║
║  ███████╗██║ ╚████║██║╚██████╔╝██║ ╚═╝ ██║██║  ██║            ║
║  ╚══════╝╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝            ║
║                                                               ║
║         🔐 WWII Cipher Machine Simulator 🔐                   ║
║                                                               ║
║   Encrypt messages like it's 1942.                            ║
║   Understand how Turing cracked it.                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_plugboard()
    example_self_inverse()
    example_turing_mode()
    example_visualization()
    example_rotor_wiring()
    example_presets()
    example_quick()
    example_message()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Historical Note:
    Breaking Enigma shortened WWII by an estimated 2-4 years
    and saved countless lives. Alan Turing's work at Bletchley
    Park laid the foundation for modern computer science.
""")


if __name__ == "__main__":
    main()
