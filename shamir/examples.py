#!/usr/bin/env python3
"""
Shamir Secret Sharing - Usage Examples

Split secrets into N shares where any K can reconstruct it.
"""

from shamir import (
    split,
    combine,
    split_string,
    combine_string,
    share_to_hex,
    share_from_hex,
    verify_shares,
    visualize_split,
    visualize_reconstruction,
    GF256,
)


def example_basic():
    """
    Example 1: Basic Secret Sharing
    """
    print("=" * 60)
    print("Example 1: 🔐 Basic Secret Sharing")
    print("=" * 60)
    
    print("""
Shamir's Secret Sharing (1979) splits a secret into N shares
where ANY K shares can reconstruct it, but K-1 shares reveal
NOTHING about the secret.

This is INFORMATION-THEORETICALLY secure - not just hard to
break, but mathematically impossible with fewer than K shares.
""")
    
    secret = b"my secret key"
    print(f"Secret: {secret}")
    print(f"Split into 5 shares, requiring 3 to reconstruct\n")
    
    shares = split(secret, n=5, k=3)
    
    print("Generated shares:")
    for i, share in enumerate(shares, 1):
        print(f"  Share {i}: x={share.x}, data={share.data.hex()[:20]}...")
    
    print(f"\nReconstruct using shares 1, 3, 5:")
    selected = [shares[0], shares[2], shares[4]]
    recovered = combine(selected)
    print(f"Recovered: {recovered}")
    print(f"Match: {recovered == secret} ✓")
    print()


def example_threshold():
    """
    Example 2: Different Thresholds
    """
    print("=" * 60)
    print("Example 2: 🎯 Different Thresholds")
    print("=" * 60)
    
    print("""
The threshold K determines security:
    - Higher K = more shares needed = harder to reconstruct
    - Lower K = fewer shares needed = easier access
""")
    
    secret = b"bitcoin seed phrase"
    
    # 2-of-3 (simple)
    print("2-of-3 scheme (any 2 can recover):")
    shares = split(secret, n=3, k=2)
    recovered = combine(shares[:2])
    print(f"  ✓ Recovered with 2 shares: {recovered == secret}")
    
    # 3-of-5 (balanced)
    print("\n3-of-5 scheme (any 3 can recover):")
    shares = split(secret, n=5, k=3)
    recovered = combine(shares[:3])
    print(f"  ✓ Recovered with 3 shares: {recovered == secret}")
    
    # 5-of-5 (all required)
    print("\n5-of-5 scheme (ALL shares required):")
    shares = split(secret, n=5, k=5)
    recovered = combine(shares)
    print(f"  ✓ Recovered with all 5 shares: {recovered == secret}")
    print()


def example_k_minus_1():
    """
    Example 3: K-1 Shares Reveal Nothing
    """
    print("=" * 60)
    print("Example 3: 🔒 K-1 Shares Reveal Nothing")
    print("=" * 60)
    
    print("""
The magic of Shamir's scheme:
    K-1 shares are consistent with ALL possible secrets.
    An attacker with K-1 shares learns ZERO information.
""")
    
    secret = b"SECRET"
    shares = split(secret, n=5, k=3)
    
    print(f"Secret: {secret}")
    print(f"Scheme: 3-of-5\n")
    
    print("With only 2 shares (K-1), trying to reconstruct:")
    wrong_result = combine(shares[:2])
    print(f"  Result: {wrong_result}")
    print(f"  Correct? {wrong_result == secret}")
    print(f"  This result is MEANINGLESS - it tells attacker nothing!")
    
    print("\nWith 3 shares (K), reconstruction works:")
    correct_result = combine(shares[:3])
    print(f"  Result: {correct_result}")
    print(f"  Correct? {correct_result == secret} ✓")
    print()


def example_string():
    """
    Example 4: String Secrets
    """
    print("=" * 60)
    print("Example 4: 📝 String Secrets")
    print("=" * 60)
    
    secret = "Hello, 世界! 🔐"
    print(f"Secret (unicode): {secret}\n")
    
    shares = split_string(secret, n=5, k=3)
    print(f"Split into {len(shares)} shares")
    
    recovered = combine_string(shares[:3])
    print(f"Recovered: {recovered}")
    print(f"Match: {recovered == secret} ✓")
    print()


def example_hex_storage():
    """
    Example 5: Hex Storage for Easy Sharing
    """
    print("=" * 60)
    print("Example 5: 💾 Hex Format for Storage")
    print("=" * 60)
    
    print("""
Shares can be converted to hex strings for easy storage,
transmission, or printing on paper.
""")
    
    secret = b"encryption key"
    shares = split(secret, n=3, k=2)
    
    print("Shares as hex strings (easy to copy/paste):")
    hex_shares = []
    for share in shares:
        hex_str = share_to_hex(share)
        hex_shares.append(hex_str)
        print(f"  {hex_str}")
    
    print("\nReconstructing from hex strings:")
    parsed = [share_from_hex(h) for h in hex_shares[:2]]
    recovered = combine(parsed)
    print(f"  Recovered: {recovered}")
    print()


def example_real_world():
    """
    Example 6: Real-World Use Case
    """
    print("=" * 60)
    print("Example 6: 🌍 Real-World Use Case")
    print("=" * 60)
    
    print("""
SCENARIO: You have a Bitcoin wallet seed phrase.
    - You want 5 trusted people to each hold a share
    - Any 3 together can recover the seed if you die
    - 2 colluding attackers cannot steal your Bitcoin
""")
    
    seed_phrase = b"abandon ability able about above absent absorb abstract absurd abuse"
    
    shares = split(seed_phrase, n=5, k=3)
    
    print("Distribution plan:")
    people = ["Spouse", "Lawyer", "Parent", "Sibling", "Friend"]
    
    for person, share in zip(people, shares):
        hex_share = share_to_hex(share)
        print(f"  {person}: {hex_share[:30]}...")
    
    print("\nRecovery scenarios:")
    
    # Scenario 1: Death
    print("\n  If you die, Spouse + Lawyer + Parent can recover:")
    recovered = combine([shares[0], shares[1], shares[2]])
    print(f"    ✓ Seed recovered: {recovered == seed_phrase}")
    
    # Scenario 2: Attack
    print("\n  If Sibling + Friend collude (only 2 shares):")
    wrong = combine([shares[3], shares[4]])
    print(f"    ✗ They get garbage: {wrong[:20]}...")
    print(f"    They learn NOTHING about the real seed!")
    print()


def example_verification():
    """
    Example 7: Share Verification
    """
    print("=" * 60)
    print("Example 7: ✅ Share Verification")
    print("=" * 60)
    
    print("""
You can verify that shares are consistent (from the same split)
without revealing the secret.
""")
    
    secret = b"verify me"
    shares = split(secret, n=5, k=3)
    
    print("Verifying shares are consistent...")
    is_valid = verify_shares(shares, k=3)
    print(f"  All shares consistent: {is_valid} ✓")
    print()


def example_gf256():
    """
    Example 8: The Math - GF(256)
    """
    print("=" * 60)
    print("Example 8: 🧮 The Math - Galois Field GF(256)")
    print("=" * 60)
    
    print("""
Shamir's scheme works in GF(256) - a finite field with 256 elements.
This allows all operations on bytes (0-255) without overflow.

Key properties:
    - Addition is XOR: a + b = a ⊕ b
    - Every non-zero element has an inverse
    - No rounding or overflow issues
""")
    
    a, b = 42, 73
    
    print(f"Examples with a={a}, b={b}:")
    print(f"  a + b = {GF256.add(a, b)} (XOR)")
    print(f"  a × b = {GF256.mul(a, b)}")
    print(f"  a ÷ b = {GF256.div(a, b)}")
    print(f"  a⁻¹   = {GF256.inverse(a)}")
    
    print(f"\nVerification:")
    print(f"  a × a⁻¹ = {GF256.mul(a, GF256.inverse(a))} (should be 1)")
    print(f"  (a × b) ÷ b = {GF256.div(GF256.mul(a, b), b)} (should be {a})")
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ███████╗██╗  ██╗ █████╗ ███╗   ███╗██╗██████╗                ║
║  ██╔════╝██║  ██║██╔══██╗████╗ ████║██║██╔══██╗               ║
║  ███████╗███████║███████║██╔████╔██║██║██████╔╝               ║
║  ╚════██║██╔══██║██╔══██║██║╚██╔╝██║██║██╔══██╗               ║
║  ███████║██║  ██║██║  ██║██║ ╚═╝ ██║██║██║  ██║               ║
║  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═╝               ║
║                                                               ║
║     🔐 Secret Sharing Scheme (1979) 🔐                        ║
║                                                               ║
║  Split secrets. K-of-N threshold. Information-theoretic.      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_threshold()
    example_k_minus_1()
    example_string()
    example_hex_storage()
    example_real_world()
    example_verification()
    example_gf256()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)
    print("""
Key Takeaways:

    1. Shamir's Secret Sharing splits secrets into N shares
    
    2. Any K shares can reconstruct the secret
    
    3. K-1 shares reveal ZERO information (provably!)
    
    4. Based on polynomial interpolation over finite fields
    
    5. Invented by Adi Shamir (the "S" in RSA) in 1979

Use cases:
    - Backup encryption keys across multiple locations
    - Corporate secrets shared among executives  
    - Cryptocurrency seed phrase protection
    - Dead man's switch / estate planning
""")


if __name__ == "__main__":
    main()
