"""
Shamir: Secret Sharing Scheme

Split secrets into N shares where any K can reconstruct it,
but K-1 shares reveal absolutely nothing. Information-theoretically secure.

Background:

    Adi Shamir (the "S" in RSA) published this scheme in 1979.
    It's based on polynomial interpolation:
    
    - A polynomial of degree K-1 is uniquely determined by K points
    - But K-1 points define infinitely many such polynomials
    
    The secret is encoded as the constant term of a random polynomial.
    Shares are evaluations of the polynomial at different x values.

The Math:

    To share a secret S with threshold K:
    
    1. Create polynomial: f(x) = S + a₁x + a₂x² + ... + aₖ₋₁xᵏ⁻¹
       where a₁...aₖ₋₁ are random coefficients
    
    2. The secret is f(0) = S
    
    3. Generate N shares: (1, f(1)), (2, f(2)), ..., (N, f(N))
    
    To reconstruct from K shares:
    
    1. Use Lagrange interpolation to find the unique polynomial
       passing through the K points
    
    2. Evaluate at x=0 to get the secret

Finite Field GF(256):

    We work in GF(256) - the Galois Field with 256 elements.
    This allows all operations on bytes (0-255) without overflow.
    
    GF(256) uses polynomial arithmetic modulo x⁸ + x⁴ + x³ + x + 1.
    
    Key properties:
    - Addition is XOR
    - Multiplication uses log/exp tables
    - Division always possible (except by 0)

Security:

    This scheme is INFORMATION-THEORETICALLY secure:
    - Not just computationally hard to break
    - Mathematically impossible with fewer than K shares
    - K-1 shares reveal ZERO information about the secret
    
    This is proven: K-1 points are consistent with ALL possible
    secrets equally, giving perfect secrecy.

Usage:
    >>> from shamir import split, combine
    >>> 
    >>> # Split a secret into 5 shares, requiring 3 to reconstruct
    >>> secret = b"my secret key"
    >>> shares = split(secret, n=5, k=3)
    >>> 
    >>> # Any 3 shares can reconstruct
    >>> recovered = combine(shares[:3])
    >>> assert recovered == secret
    >>> 
    >>> # 2 shares reveal nothing!

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import os
import secrets


# =============================================================================
# Galois Field GF(256)
# =============================================================================

class GF256:
    """
    Galois Field with 256 elements.
    
    This is GF(2⁸) using the irreducible polynomial:
        x⁸ + x⁴ + x³ + x + 1  (0x11B in hex)
    
    All arithmetic operations work on bytes (0-255) and produce bytes.
    
    Key insight: In GF(256), addition is XOR and multiplication is
    defined by polynomial multiplication modulo the irreducible polynomial.
    
    We precompute log and exp tables for fast multiplication/division.
    """
    
    # Irreducible polynomial: x^8 + x^4 + x^3 + x + 1
    IRREDUCIBLE = 0x11B
    
    # Precomputed tables for fast operations
    _exp_table: List[int] = []  # exp_table[i] = g^i where g=3 is a generator
    _log_table: List[int] = []  # log_table[x] = i where g^i = x
    _initialized = False
    
    @classmethod
    def _init_tables(cls) -> None:
        """Initialize log and exp tables."""
        if cls._initialized:
            return
        
        cls._exp_table = [0] * 256
        cls._log_table = [0] * 256
        
        # Use 3 as the generator (primitive element)
        x = 1
        for i in range(255):
            cls._exp_table[i] = x
            cls._log_table[x] = i
            
            # Multiply by generator (3) in GF(256)
            x = cls._multiply_slow(x, 3)
        
        # exp[255] = exp[0] = 1 (wraps around)
        cls._exp_table[255] = cls._exp_table[0]
        
        cls._initialized = True
    
    @classmethod
    def _multiply_slow(cls, a: int, b: int) -> int:
        """
        Multiply two elements using polynomial multiplication.
        
        Used only during table initialization.
        """
        result = 0
        
        while b:
            if b & 1:
                result ^= a
            
            # Multiply a by x (shift left)
            a <<= 1
            
            # Reduce modulo irreducible polynomial if needed
            if a & 0x100:
                a ^= cls.IRREDUCIBLE
            
            b >>= 1
        
        return result
    
    @classmethod
    def add(cls, a: int, b: int) -> int:
        """
        Add two elements in GF(256).
        
        In GF(2^n), addition is XOR.
        """
        return a ^ b
    
    @classmethod
    def sub(cls, a: int, b: int) -> int:
        """
        Subtract in GF(256).
        
        In GF(2^n), subtraction equals addition (both are XOR).
        """
        return a ^ b
    
    @classmethod
    def mul(cls, a: int, b: int) -> int:
        """
        Multiply two elements in GF(256).
        
        Uses precomputed log/exp tables:
            a * b = exp(log(a) + log(b))
        """
        if a == 0 or b == 0:
            return 0
        
        cls._init_tables()
        
        log_sum = cls._log_table[a] + cls._log_table[b]
        if log_sum >= 255:
            log_sum -= 255
        
        return cls._exp_table[log_sum]
    
    @classmethod
    def div(cls, a: int, b: int) -> int:
        """
        Divide in GF(256).
        
        Uses precomputed tables:
            a / b = exp(log(a) - log(b))
        
        Raises:
            ZeroDivisionError: If b is 0
        """
        if b == 0:
            raise ZeroDivisionError("Division by zero in GF(256)")
        
        if a == 0:
            return 0
        
        cls._init_tables()
        
        log_diff = cls._log_table[a] - cls._log_table[b]
        if log_diff < 0:
            log_diff += 255
        
        return cls._exp_table[log_diff]
    
    @classmethod
    def pow(cls, base: int, exp: int) -> int:
        """
        Raise base to power exp in GF(256).
        """
        if exp == 0:
            return 1
        
        if base == 0:
            return 0
        
        cls._init_tables()
        
        log_result = (cls._log_table[base] * exp) % 255
        return cls._exp_table[log_result]
    
    @classmethod
    def inverse(cls, a: int) -> int:
        """
        Compute multiplicative inverse in GF(256).
        
        a * inverse(a) = 1
        """
        if a == 0:
            raise ZeroDivisionError("Zero has no inverse")
        
        cls._init_tables()
        
        # inverse(a) = exp(-log(a)) = exp(255 - log(a))
        return cls._exp_table[255 - cls._log_table[a]]


# =============================================================================
# Polynomial Operations
# =============================================================================

def _evaluate_polynomial(coefficients: List[int], x: int) -> int:
    """
    Evaluate a polynomial at point x in GF(256).
    
    coefficients[i] is the coefficient of x^i.
    
    Uses Horner's method for efficiency:
        f(x) = c₀ + x(c₁ + x(c₂ + ...))
    """
    if not coefficients:
        return 0
    
    # Horner's method (evaluate from highest degree down)
    result = coefficients[-1]
    
    for i in range(len(coefficients) - 2, -1, -1):
        result = GF256.add(GF256.mul(result, x), coefficients[i])
    
    return result


def _lagrange_interpolate(points: List[Tuple[int, int]], x: int) -> int:
    """
    Lagrange interpolation in GF(256).
    
    Given K points (x₁, y₁), ..., (xₖ, yₖ), finds the unique
    polynomial of degree K-1 passing through all points and
    evaluates it at x.
    
    The Lagrange formula:
        f(x) = Σᵢ yᵢ × Πⱼ≠ᵢ (x - xⱼ)/(xᵢ - xⱼ)
    
    This is the heart of secret reconstruction.
    """
    k = len(points)
    result = 0
    
    for i in range(k):
        xi, yi = points[i]
        
        # Compute Lagrange basis polynomial Lᵢ(x)
        # Lᵢ(x) = Πⱼ≠ᵢ (x - xⱼ)/(xᵢ - xⱼ)
        
        numerator = 1
        denominator = 1
        
        for j in range(k):
            if i != j:
                xj, _ = points[j]
                
                # (x - xⱼ)
                numerator = GF256.mul(numerator, GF256.sub(x, xj))
                
                # (xᵢ - xⱼ)
                denominator = GF256.mul(denominator, GF256.sub(xi, xj))
        
        # Lᵢ(x) = numerator / denominator
        basis = GF256.div(numerator, denominator)
        
        # Contribution: yᵢ × Lᵢ(x)
        term = GF256.mul(yi, basis)
        result = GF256.add(result, term)
    
    return result


# =============================================================================
# Share Data Structure
# =============================================================================

@dataclass
class Share:
    """
    A share of a secret.
    
    Attributes:
        x: The x-coordinate (share index, 1-255)
        data: The share data (same length as original secret)
    """
    x: int
    data: bytes
    
    def __post_init__(self):
        if not 1 <= self.x <= 255:
            raise ValueError(f"Share x must be 1-255, got {self.x}")
    
    def to_bytes(self) -> bytes:
        """
        Serialize share to bytes.
        
        Format: [x (1 byte)] [data]
        """
        return bytes([self.x]) + self.data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Share':
        """Deserialize share from bytes."""
        if len(data) < 2:
            raise ValueError("Share data too short")
        
        x = data[0]
        share_data = data[1:]
        
        return cls(x=x, data=share_data)
    
    def __repr__(self) -> str:
        return f"Share(x={self.x}, data={self.data.hex()[:16]}...)"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Share):
            return False
        return self.x == other.x and self.data == other.data
    
    def __hash__(self) -> int:
        return hash((self.x, self.data))


# =============================================================================
# Core Functions
# =============================================================================

def split(secret: bytes, n: int, k: int) -> List[Share]:
    """
    Split a secret into N shares, K required to reconstruct.
    
    This implements Shamir's Secret Sharing Scheme.
    
    Args:
        secret: The secret to split (any bytes)
        n: Number of shares to generate (2-255)
        k: Threshold - minimum shares needed to reconstruct (2-n)
    
    Returns:
        List of N shares
    
    Security Properties:
        - Any K shares can reconstruct the secret
        - K-1 shares reveal ZERO information about the secret
        - This is information-theoretically secure
    
    Example:
        >>> shares = split(b"my secret", n=5, k=3)
        >>> len(shares)
        5
        >>> combine(shares[:3]) == b"my secret"
        True
    """
    # Validate inputs
    if not isinstance(secret, bytes):
        raise TypeError("Secret must be bytes")
    
    if len(secret) == 0:
        raise ValueError("Secret cannot be empty")
    
    if not 2 <= k <= n <= 255:
        raise ValueError(f"Invalid parameters: need 2 <= k <= n <= 255, got k={k}, n={n}")
    
    # Initialize GF(256) tables
    GF256._init_tables()
    
    # Generate shares for each byte of the secret
    share_data = [bytearray() for _ in range(n)]
    
    for secret_byte in secret:
        # Create a random polynomial with secret_byte as the constant term
        # f(x) = secret_byte + a₁x + a₂x² + ... + aₖ₋₁xᵏ⁻¹
        
        coefficients = [secret_byte]
        
        # Generate k-1 random coefficients
        random_bytes = secrets.token_bytes(k - 1)
        coefficients.extend(random_bytes)
        
        # Evaluate polynomial at x = 1, 2, ..., n
        for i in range(n):
            x = i + 1  # x values are 1-indexed
            y = _evaluate_polynomial(coefficients, x)
            share_data[i].append(y)
    
    # Create Share objects
    shares = [
        Share(x=i + 1, data=bytes(share_data[i]))
        for i in range(n)
    ]
    
    return shares


def combine(shares: List[Share]) -> bytes:
    """
    Reconstruct a secret from K shares.
    
    Uses Lagrange interpolation to find the polynomial
    and evaluates it at x=0 to get the secret.
    
    Args:
        shares: List of K shares (or more)
    
    Returns:
        The reconstructed secret
    
    Raises:
        ValueError: If shares are invalid or inconsistent
    
    Example:
        >>> secret = b"hello"
        >>> shares = split(secret, n=5, k=3)
        >>> combine(shares[:3]) == secret
        True
    """
    if not shares:
        raise ValueError("No shares provided")
    
    # Validate shares
    share_length = len(shares[0].data)
    x_values = set()
    
    for share in shares:
        if len(share.data) != share_length:
            raise ValueError("All shares must have the same length")
        
        if share.x in x_values:
            raise ValueError(f"Duplicate share with x={share.x}")
        
        x_values.add(share.x)
    
    # Initialize GF(256) tables
    GF256._init_tables()
    
    # Reconstruct each byte of the secret
    secret_bytes = bytearray()
    
    for byte_index in range(share_length):
        # Collect (x, y) points for this byte position
        points = [(share.x, share.data[byte_index]) for share in shares]
        
        # Interpolate to find f(0) = secret byte
        secret_byte = _lagrange_interpolate(points, 0)
        secret_bytes.append(secret_byte)
    
    return bytes(secret_bytes)


def verify_shares(shares: List[Share], k: int) -> bool:
    """
    Verify that K shares are consistent (from the same split).
    
    Takes K shares and checks if they could have come from
    the same polynomial by verifying that any K-subset
    interpolates to the same values.
    
    Args:
        shares: List of shares to verify
        k: The threshold used in the original split
    
    Returns:
        True if shares are consistent, False otherwise
    """
    if len(shares) < k:
        raise ValueError(f"Need at least {k} shares for verification")
    
    # Use first k shares to reconstruct
    reference = combine(shares[:k])
    
    # Check all k-subsets give the same result
    # (For efficiency, we just check a few combinations)
    from itertools import combinations
    
    for combo in list(combinations(shares, k))[:10]:
        result = combine(list(combo))
        if result != reference:
            return False
    
    return True


# =============================================================================
# Utilities
# =============================================================================

def split_string(secret: str, n: int, k: int, encoding: str = 'utf-8') -> List[Share]:
    """
    Split a string secret into shares.
    
    Convenience function that handles encoding.
    """
    return split(secret.encode(encoding), n, k)


def combine_string(shares: List[Share], encoding: str = 'utf-8') -> str:
    """
    Combine shares and decode as string.
    
    Convenience function that handles decoding.
    """
    return combine(shares).decode(encoding)


def share_to_hex(share: Share) -> str:
    """Convert share to hex string for easy storage/display."""
    return f"{share.x:02x}:{share.data.hex()}"


def share_from_hex(hex_str: str) -> Share:
    """Parse share from hex string."""
    parts = hex_str.split(':')
    if len(parts) != 2:
        raise ValueError("Invalid share format")
    
    x = int(parts[0], 16)
    data = bytes.fromhex(parts[1])
    
    return Share(x=x, data=data)


# =============================================================================
# Visualization
# =============================================================================

def visualize_polynomial(coefficients: List[int], n: int = 5) -> str:
    """
    Visualize a polynomial and its evaluations.
    
    Shows the polynomial formula and share values.
    """
    lines = []
    
    # Build polynomial string
    terms = []
    for i, coef in enumerate(coefficients):
        if i == 0:
            terms.append(f"{coef}")
        elif i == 1:
            terms.append(f"{coef}x")
        else:
            terms.append(f"{coef}x^{i}")
    
    poly_str = " + ".join(terms)
    lines.append(f"Polynomial: f(x) = {poly_str}")
    lines.append(f"Secret = f(0) = {coefficients[0]}")
    lines.append("")
    lines.append("Shares:")
    
    for x in range(1, n + 1):
        y = _evaluate_polynomial(coefficients, x)
        lines.append(f"  Share {x}: ({x}, {y})")
    
    return '\n'.join(lines)


def visualize_split(secret: bytes, shares: List[Share]) -> str:
    """Visualize a secret split operation."""
    lines = []
    lines.append("=" * 50)
    lines.append("SHAMIR SECRET SHARING")
    lines.append("=" * 50)
    lines.append(f"Secret: {secret!r}")
    lines.append(f"Secret (hex): {secret.hex()}")
    lines.append(f"Number of shares: {len(shares)}")
    lines.append("")
    lines.append("Shares:")
    
    for share in shares:
        lines.append(f"  {share.x}: {share.data.hex()}")
    
    return '\n'.join(lines)


def visualize_reconstruction(shares: List[Share], secret: bytes) -> str:
    """Visualize secret reconstruction."""
    lines = []
    lines.append("=" * 50)
    lines.append("RECONSTRUCTION")
    lines.append("=" * 50)
    lines.append(f"Using {len(shares)} shares:")
    
    for share in shares:
        lines.append(f"  Share {share.x}")
    
    lines.append("")
    lines.append(f"Reconstructed: {secret!r}")
    lines.append(f"Reconstructed (hex): {secret.hex()}")
    
    return '\n'.join(lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core functions
    'split',
    'combine',
    'verify_shares',
    
    # Data structures
    'Share',
    
    # Utilities
    'split_string',
    'combine_string',
    'share_to_hex',
    'share_from_hex',
    
    # GF(256) for advanced users
    'GF256',
    
    # Visualization
    'visualize_polynomial',
    'visualize_split',
    'visualize_reconstruction',
]
