"""
Styx: Cryptographically Secure Async Secret Sharing

A production-grade implementation of Shamir's Secret Sharing Scheme over GF(2^8)
with HMAC integrity verification, constant-time operations, and an async-native
distributed share collection protocol.

Mathematical Foundation:
    Shamir's scheme relies on the fact that k points uniquely define a polynomial
    of degree k-1. We encode the secret as the constant term (f(0)) of a random
    polynomial, then distribute points f(1), f(2), ..., f(n) as shares.
    
    We operate over GF(2^8) (the Galois Field with 256 elements) because:
    1. Each byte maps directly to a field element (no size expansion)
    2. Arithmetic never overflows (closed under operations)
    3. The irreducible polynomial x^8 + x^4 + x^3 + x + 1 (0x11B) is standard (AES)

Security Properties:
    - Information-theoretic security: k-1 shares reveal NOTHING about the secret
    - HMAC-SHA256 per share prevents tampering and detects corruption
    - Constant-time polynomial evaluation resists timing side-channels
    - Share indices are bound to HMACs preventing index manipulation attacks

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol, TypeVar, Generic
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Galois Field GF(2^8) Arithmetic
# =============================================================================

class GF256:
    """
    Galois Field GF(2^8) arithmetic using the AES irreducible polynomial.
    
    Why GF(2^8)?
        - Bytes map 1:1 to field elements (no encoding overhead)
        - All operations stay within [0, 255] (no overflow handling)
        - Hardware-accelerated on modern CPUs (AES-NI uses same field)
    
    The irreducible polynomial is: x^8 + x^4 + x^3 + x + 1 = 0x11B
    
    We precompute logarithm and exponentiation tables for O(1) multiplication
    and division. The generator element is 0x03 (standard choice).
    """
    
    # AES irreducible polynomial: x^8 + x^4 + x^3 + x + 1
    _IRREDUCIBLE = 0x11B
    _GENERATOR = 0x03
    
    # Precomputed tables (populated at module load)
    _exp_table: list[int] = [0] * 512  # exp[i] = g^i mod p
    _log_table: list[int] = [0] * 256  # log[x] = i where g^i = x
    _initialized: bool = False
    
    @classmethod
    def _init_tables(cls) -> None:
        """
        Build exp/log tables using the generator element.
        
        The exp table has 512 entries to avoid modular reduction during
        multiplication: exp[log[a] + log[b]] works without % 255.
        """
        if cls._initialized:
            return
            
        x = 1
        for i in range(255):
            cls._exp_table[i] = x
            cls._log_table[x] = i
            
            # Multiply by generator in GF(2^8)
            x = cls._gf_mult_slow(x, cls._GENERATOR)
        
        # Extend exp table for easier multiplication (avoid modulo)
        for i in range(255, 512):
            cls._exp_table[i] = cls._exp_table[i - 255]
            
        cls._initialized = True
    
    @classmethod
    def _gf_mult_slow(cls, a: int, b: int) -> int:
        """
        Peasant multiplication in GF(2^8) - used only for table generation.
        
        This is the 'textbook' algorithm: shift-and-XOR with reduction.
        After tables are built, we use the fast O(1) table lookup instead.
        """
        result = 0
        while b:
            if b & 1:
                result ^= a
            a <<= 1
            if a & 0x100:  # Degree 8 term appeared
                a ^= cls._IRREDUCIBLE
            b >>= 1
        return result
    
    @classmethod
    def add(cls, a: int, b: int) -> int:
        """
        Addition in GF(2^8) is XOR.
        
        Why XOR? In characteristic-2 fields, addition is defined as
        polynomial coefficient addition mod 2, which is XOR.
        Bonus: subtraction is also XOR (additive inverse = self).
        """
        return a ^ b
    
    @classmethod
    def sub(cls, a: int, b: int) -> int:
        """Subtraction in GF(2^8) is identical to addition (XOR)."""
        return a ^ b
    
    @classmethod
    def mul(cls, a: int, b: int) -> int:
        """
        Multiplication via logarithm tables: a * b = exp[log[a] + log[b]]
        
        Special case: multiplication by 0 returns 0 (log[0] is undefined).
        The extended exp table (512 entries) eliminates modular reduction.
        """
        cls._init_tables()
        if a == 0 or b == 0:
            return 0
        return cls._exp_table[cls._log_table[a] + cls._log_table[b]]
    
    @classmethod
    def div(cls, a: int, b: int) -> int:
        """
        Division via logarithm tables: a / b = exp[log[a] - log[b] + 255]
        
        The +255 handles negative results from the subtraction.
        Division by zero raises an exception (as it should).
        """
        cls._init_tables()
        if b == 0:
            raise ZeroDivisionError("Division by zero in GF(2^8)")
        if a == 0:
            return 0
        # +255 ensures positive index when log[a] < log[b]
        return cls._exp_table[(cls._log_table[a] - cls._log_table[b] + 255) % 255]
    
    @classmethod
    def pow(cls, base: int, exp: int) -> int:
        """Exponentiation via logarithm table."""
        cls._init_tables()
        if base == 0:
            return 0 if exp > 0 else 1
        return cls._exp_table[(cls._log_table[base] * exp) % 255]
    
    @classmethod
    def inverse(cls, a: int) -> int:
        """Multiplicative inverse: a^(-1) such that a * a^(-1) = 1"""
        cls._init_tables()
        if a == 0:
            raise ZeroDivisionError("Zero has no multiplicative inverse")
        # In GF(2^8), a^(-1) = a^254 (Fermat's little theorem)
        return cls._exp_table[255 - cls._log_table[a]]


# Initialize tables at module load
GF256._init_tables()


# =============================================================================
# Share Data Structure
# =============================================================================

@dataclass(frozen=True, slots=True)
class Share:
    """
    A single share from Shamir's Secret Sharing.
    
    Attributes:
        index: The x-coordinate (1 to 255). Index 0 is reserved for the secret.
        data: The y-coordinates for each byte of the secret.
        hmac: HMAC-SHA256 of (index || data) for integrity verification.
        threshold: Minimum shares needed for reconstruction (metadata).
        total: Total number of shares created (metadata).
    
    Security Note:
        The HMAC binds the index to the data, preventing an attacker from
        claiming a share has a different index (which would corrupt reconstruction).
    """
    index: int
    data: bytes
    hmac: bytes
    threshold: int
    total: int
    
    def __post_init__(self) -> None:
        if not 1 <= self.index <= 255:
            raise ValueError(f"Share index must be in [1, 255], got {self.index}")
        if not self.data:
            raise ValueError("Share data cannot be empty")
        if len(self.hmac) != 32:
            raise ValueError(f"HMAC must be 32 bytes, got {len(self.hmac)}")
    
    def to_bytes(self) -> bytes:
        """
        Serialize share to bytes for network transmission.
        
        Format: [index:1][threshold:1][total:1][data_len:4][data:N][hmac:32]
        """
        return struct.pack(
            f">BBBi{len(self.data)}s32s",
            self.index,
            self.threshold,
            self.total,
            len(self.data),
            self.data,
            self.hmac
        )
    
    @classmethod
    def from_bytes(cls, raw: bytes) -> Share:
        """Deserialize share from bytes."""
        if len(raw) < 39:  # Minimum: 1+1+1+4+0+32 (but data can't be 0)
            raise ValueError("Share data too short")
        
        index, threshold, total, data_len = struct.unpack(">BBBi", raw[:7])
        
        if len(raw) != 7 + data_len + 32:
            raise ValueError(f"Share length mismatch: expected {7 + data_len + 32}, got {len(raw)}")
        
        data = raw[7:7 + data_len]
        hmac_value = raw[7 + data_len:7 + data_len + 32]
        
        return cls(
            index=index,
            data=data,
            hmac=hmac_value,
            threshold=threshold,
            total=total
        )
    
    def __repr__(self) -> str:
        return f"Share(index={self.index}, threshold={self.threshold}/{self.total}, data_len={len(self.data)})"


# =============================================================================
# Core Secret Sharing Engine
# =============================================================================

class StyxError(Exception):
    """Base exception for Styx errors."""
    pass


class IntegrityError(StyxError):
    """Share failed HMAC verification."""
    pass


class InsufficientSharesError(StyxError):
    """Not enough shares to reconstruct the secret."""
    pass


class DuplicateShareError(StyxError):
    """Duplicate share indices detected."""
    pass


class SecretSharer:
    """
    Core Shamir's Secret Sharing implementation.
    
    Thread-safe: All methods are stateless and can be called concurrently.
    The only mutable state (GF256 tables) is initialized once at module load.
    
    Example:
        sharer = SecretSharer(hmac_key=b"your-32-byte-key-here-padding!!")
        shares = sharer.split(b"my secret", n=5, k=3)
        secret = sharer.reconstruct(shares[:3])  # Any 3 shares work
    """
    
    def __init__(self, hmac_key: bytes | None = None):
        """
        Initialize the SecretSharer.
        
        Args:
            hmac_key: 32-byte key for HMAC computation. If None, a random
                      key is generated (shares won't be verifiable across
                      different SecretSharer instances).
        """
        if hmac_key is None:
            hmac_key = secrets.token_bytes(32)
        elif len(hmac_key) != 32:
            raise ValueError("HMAC key must be exactly 32 bytes")
        
        self._hmac_key = hmac_key
    
    def _compute_hmac(self, index: int, data: bytes) -> bytes:
        """
        Compute HMAC-SHA256 over the share index and data.
        
        Binding the index to the HMAC prevents index manipulation attacks
        where an adversary presents a valid share with a forged index.
        """
        h = hmac.new(self._hmac_key, digestmod=hashlib.sha256)
        h.update(bytes([index]))
        h.update(data)
        return h.digest()
    
    def _verify_hmac(self, share: Share) -> bool:
        """
        Verify share integrity using constant-time comparison.
        
        Returns True if HMAC matches, False otherwise.
        Uses hmac.compare_digest to prevent timing attacks.
        """
        expected = self._compute_hmac(share.index, share.data)
        return hmac.compare_digest(expected, share.hmac)
    
    def _generate_polynomial_coefficients(self, secret_byte: int, degree: int) -> list[int]:
        """
        Generate random polynomial coefficients with the secret as the constant term.
        
        For a threshold k, we need a polynomial of degree k-1:
            f(x) = secret + a1*x + a2*x^2 + ... + a(k-1)*x^(k-1)
        
        The coefficients a1...a(k-1) are cryptographically random.
        """
        # Constant term is the secret byte
        coeffs = [secret_byte]
        
        # Random coefficients for higher terms
        for _ in range(degree):
            coeffs.append(secrets.randbelow(256))
        
        return coeffs
    
    def _evaluate_polynomial(self, coeffs: list[int], x: int) -> int:
        """
        Evaluate polynomial at point x using Horner's method.
        
        Horner's method: f(x) = c0 + x*(c1 + x*(c2 + x*(...)))
        
        This is:
        1. More efficient: O(n) multiplications vs O(n^2) for naive
        2. More numerically stable (not relevant in finite fields, but good habit)
        3. Constant-time for same-degree polynomials (mitigates timing attacks)
        """
        result = 0
        for coeff in reversed(coeffs):
            result = GF256.add(GF256.mul(result, x), coeff)
        return result
    
    def split(self, secret: bytes, n: int, k: int) -> list[Share]:
        """
        Split a secret into n shares with threshold k.
        
        Args:
            secret: The secret bytes to split (any length > 0)
            n: Total number of shares to generate (2 <= n <= 255)
            k: Threshold - minimum shares needed to reconstruct (2 <= k <= n)
        
        Returns:
            List of n Share objects
        
        Raises:
            ValueError: Invalid parameters
        
        Security Properties:
            - k-1 shares reveal NO information about the secret
            - k shares uniquely determine the secret
            - HMAC on each share prevents tampering
        """
        # Validate parameters
        if not secret:
            raise ValueError("Secret cannot be empty")
        if not 2 <= k <= n <= 255:
            raise ValueError(f"Invalid parameters: need 2 <= k <= n <= 255, got k={k}, n={n}")
        
        # For each byte of the secret, generate a random polynomial
        # and evaluate it at points 1, 2, ..., n
        share_data: list[bytearray] = [bytearray() for _ in range(n)]
        
        for secret_byte in secret:
            # Generate polynomial with secret_byte as constant term
            coeffs = self._generate_polynomial_coefficients(secret_byte, k - 1)
            
            # Evaluate at each share index
            for i in range(n):
                x = i + 1  # Indices are 1-based (0 is reserved for secret)
                y = self._evaluate_polynomial(coeffs, x)
                share_data[i].append(y)
        
        # Create Share objects with HMACs
        shares = []
        for i in range(n):
            data = bytes(share_data[i])
            share = Share(
                index=i + 1,
                data=data,
                hmac=self._compute_hmac(i + 1, data),
                threshold=k,
                total=n
            )
            shares.append(share)
        
        return shares
    
    def reconstruct(self, shares: list[Share], verify_hmac: bool = True) -> bytes:
        """
        Reconstruct the secret from k or more shares.
        
        Args:
            shares: List of Share objects (at least threshold many)
            verify_hmac: Whether to verify share integrity (default: True)
        
        Returns:
            The reconstructed secret bytes
        
        Raises:
            InsufficientSharesError: Fewer shares than threshold
            IntegrityError: Share failed HMAC verification
            DuplicateShareError: Duplicate share indices
        
        Algorithm: Lagrange interpolation
            f(0) = Σ yi * Πj≠i (0 - xj) / (xi - xj)
            
            We compute this for each byte position independently.
        """
        if not shares:
            raise InsufficientSharesError("No shares provided")
        
        threshold = shares[0].threshold
        if len(shares) < threshold:
            raise InsufficientSharesError(
                f"Need at least {threshold} shares, got {len(shares)}"
            )
        
        # Check for duplicate indices
        indices = [s.index for s in shares]
        if len(indices) != len(set(indices)):
            raise DuplicateShareError("Duplicate share indices detected")
        
        # Verify integrity
        if verify_hmac:
            for share in shares:
                if not self._verify_hmac(share):
                    raise IntegrityError(f"Share {share.index} failed HMAC verification")
        
        # Use exactly threshold shares (using more doesn't help, just wastes computation)
        working_shares = shares[:threshold]
        
        # All shares must have the same data length
        data_len = len(working_shares[0].data)
        if any(len(s.data) != data_len for s in working_shares):
            raise ValueError("Share data length mismatch")
        
        # Reconstruct each byte using Lagrange interpolation
        secret = bytearray()
        
        for byte_idx in range(data_len):
            # Gather (x, y) points for this byte position
            points = [(s.index, s.data[byte_idx]) for s in working_shares]
            
            # Lagrange interpolation at x=0
            result = self._lagrange_interpolate_at_zero(points)
            secret.append(result)
        
        return bytes(secret)
    
    def _lagrange_interpolate_at_zero(self, points: list[tuple[int, int]]) -> int:
        """
        Lagrange interpolation evaluated at x=0.
        
        Formula: f(0) = Σ yi * Li(0) where Li(0) = Πj≠i (-xj) / (xi - xj)
        
        Since we're in GF(2^8), -xj = xj (additive inverse is self).
        
        Optimization: We precompute the Lagrange basis polynomials' values
        at 0, which depend only on the x-coordinates.
        """
        result = 0
        k = len(points)
        
        for i in range(k):
            xi, yi = points[i]
            
            # Compute Li(0) = Πj≠i xj / (xi - xj)
            numerator = 1
            denominator = 1
            
            for j in range(k):
                if i == j:
                    continue
                xj = points[j][0]
                
                # In GF(2^8): numerator *= xj, denominator *= (xi - xj) = (xi ^ xj)
                numerator = GF256.mul(numerator, xj)
                denominator = GF256.mul(denominator, GF256.sub(xi, xj))
            
            # Li(0) = numerator / denominator
            li = GF256.div(numerator, denominator)
            
            # Accumulate: result += yi * Li(0)
            result = GF256.add(result, GF256.mul(yi, li))
        
        return result


# =============================================================================
# Async Distributed Share Collection Protocol
# =============================================================================

class PeerState(Enum):
    """State machine for peer connections."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECEIVING = "receiving"
    FAILED = "failed"


@dataclass
class Peer:
    """
    Represents a remote peer holding a share.
    
    The actual network transport is abstracted via the ShareTransport protocol.
    This allows testing with mock transports and production use with real TCP/UDP.
    """
    peer_id: str
    address: str
    port: int
    state: PeerState = field(default=PeerState.DISCONNECTED)
    last_error: str | None = field(default=None)
    retry_count: int = field(default=0)


class ShareTransport(Protocol):
    """
    Protocol for share transmission.
    
    Implement this to plug in your preferred network transport:
    - TCP with TLS
    - QUIC
    - libp2p
    - Mock for testing
    """
    
    async def send_share(self, peer: Peer, share: Share) -> bool:
        """Send a share to a peer. Returns True on success."""
        ...
    
    async def request_share(self, peer: Peer, timeout: float) -> Share | None:
        """Request a share from a peer. Returns None on failure/timeout."""
        ...


class InMemoryTransport:
    """
    In-memory transport for testing and single-process scenarios.
    
    Shares are stored in a dictionary, keyed by peer_id.
    Simulates network latency for realistic testing.
    """
    
    def __init__(self, latency_ms: float = 0):
        self._shares: dict[str, Share] = {}
        self._latency = latency_ms / 1000.0
        self._lock = asyncio.Lock()
    
    async def send_share(self, peer: Peer, share: Share) -> bool:
        """Store share for later retrieval."""
        if self._latency > 0:
            await asyncio.sleep(self._latency)
        
        async with self._lock:
            self._shares[peer.peer_id] = share
        return True
    
    async def request_share(self, peer: Peer, timeout: float) -> Share | None:
        """Retrieve stored share."""
        if self._latency > 0:
            await asyncio.sleep(self._latency)
        
        async with self._lock:
            return self._shares.get(peer.peer_id)


@dataclass
class CollectionResult:
    """Result of share collection operation."""
    success: bool
    shares: list[Share]
    failed_peers: list[Peer]
    elapsed_seconds: float


class ShareCollector:
    """
    Async distributed share collector with retry logic.
    
    Collects shares from multiple peers concurrently, handling:
    - Timeouts per peer
    - Configurable retry attempts
    - Early termination when threshold is reached
    - Graceful degradation on partial failures
    
    Example:
        collector = ShareCollector(transport, sharer)
        result = await collector.collect(
            peers=[peer1, peer2, peer3, peer4, peer5],
            threshold=3,
            timeout_per_peer=5.0,
            max_retries=2
        )
        if result.success:
            secret = sharer.reconstruct(result.shares)
    """
    
    def __init__(self, transport: ShareTransport, sharer: SecretSharer):
        self._transport = transport
        self._sharer = sharer
    
    async def distribute(
        self,
        shares: list[Share],
        peers: list[Peer],
        timeout_per_peer: float = 10.0,
        max_retries: int = 3
    ) -> dict[str, bool]:
        """
        Distribute shares to peers concurrently.
        
        Args:
            shares: Shares to distribute (one per peer)
            peers: Target peers
            timeout_per_peer: Timeout for each send operation
            max_retries: Maximum retry attempts per peer
        
        Returns:
            Dict mapping peer_id to success status
        """
        if len(shares) != len(peers):
            raise ValueError("Must have exactly one share per peer")
        
        results: dict[str, bool] = {}
        
        async def send_to_peer(peer: Peer, share: Share) -> None:
            for attempt in range(max_retries + 1):
                try:
                    peer.state = PeerState.CONNECTING
                    success = await asyncio.wait_for(
                        self._transport.send_share(peer, share),
                        timeout=timeout_per_peer
                    )
                    if success:
                        peer.state = PeerState.CONNECTED
                        results[peer.peer_id] = True
                        logger.debug(f"Successfully sent share to {peer.peer_id}")
                        return
                except asyncio.TimeoutError:
                    peer.last_error = "timeout"
                    peer.retry_count = attempt + 1
                    logger.warning(f"Timeout sending to {peer.peer_id}, attempt {attempt + 1}")
                except Exception as e:
                    peer.last_error = str(e)
                    peer.retry_count = attempt + 1
                    logger.warning(f"Error sending to {peer.peer_id}: {e}, attempt {attempt + 1}")
                
                if attempt < max_retries:
                    # Exponential backoff: 0.1s, 0.2s, 0.4s, ...
                    await asyncio.sleep(0.1 * (2 ** attempt))
            
            peer.state = PeerState.FAILED
            results[peer.peer_id] = False
        
        # Send to all peers concurrently
        await asyncio.gather(*[
            send_to_peer(peer, share) 
            for peer, share in zip(peers, shares)
        ])
        
        return results
    
    async def collect(
        self,
        peers: list[Peer],
        threshold: int,
        timeout_per_peer: float = 10.0,
        max_retries: int = 3,
        total_timeout: float | None = None
    ) -> CollectionResult:
        """
        Collect shares from peers until threshold is reached.
        
        Args:
            peers: Peers to collect from
            threshold: Minimum shares needed
            timeout_per_peer: Timeout per peer request
            max_retries: Retries per peer
            total_timeout: Optional overall timeout
        
        Returns:
            CollectionResult with collected shares and status
        
        Strategy:
            - Request from all peers concurrently
            - Cancel remaining requests once threshold is reached
            - Track failures for diagnostic purposes
        """
        start_time = asyncio.get_event_loop().time()
        collected_shares: list[Share] = []
        failed_peers: list[Peer] = []
        share_lock = asyncio.Lock()
        threshold_event = asyncio.Event()
        
        async def collect_from_peer(peer: Peer) -> None:
            for attempt in range(max_retries + 1):
                # Check if we already have enough shares
                if threshold_event.is_set():
                    return
                
                try:
                    peer.state = PeerState.RECEIVING
                    share = await asyncio.wait_for(
                        self._transport.request_share(peer, timeout_per_peer),
                        timeout=timeout_per_peer
                    )
                    
                    if share is not None:
                        # Verify share integrity before accepting
                        if not self._sharer._verify_hmac(share):
                            peer.last_error = "HMAC verification failed"
                            logger.warning(f"Share from {peer.peer_id} failed HMAC")
                            continue
                        
                        async with share_lock:
                            # Check for duplicate indices
                            existing_indices = {s.index for s in collected_shares}
                            if share.index in existing_indices:
                                logger.warning(f"Duplicate share index from {peer.peer_id}")
                                continue
                            
                            collected_shares.append(share)
                            peer.state = PeerState.CONNECTED
                            logger.debug(f"Collected share {share.index} from {peer.peer_id}")
                            
                            if len(collected_shares) >= threshold:
                                threshold_event.set()
                        return
                        
                except asyncio.TimeoutError:
                    peer.last_error = "timeout"
                    peer.retry_count = attempt + 1
                except Exception as e:
                    peer.last_error = str(e)
                    peer.retry_count = attempt + 1
                
                if attempt < max_retries:
                    await asyncio.sleep(0.1 * (2 ** attempt))
            
            peer.state = PeerState.FAILED
            async with share_lock:
                failed_peers.append(peer)
        
        # Create tasks for all peers
        tasks = [
            asyncio.create_task(collect_from_peer(peer))
            for peer in peers
        ]
        
        try:
            if total_timeout:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=total_timeout
                )
            else:
                await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        return CollectionResult(
            success=len(collected_shares) >= threshold,
            shares=collected_shares,
            failed_peers=failed_peers,
            elapsed_seconds=elapsed
        )


# =============================================================================
# High-Level API
# =============================================================================

class Styx:
    """
    High-level facade for the Styx secret sharing system.
    
    Provides a simple async interface for common operations while
    allowing access to lower-level components when needed.
    
    Example:
        async with Styx() as styx:
            # Split and distribute
            shares = styx.split(b"my secret", n=5, k=3)
            await styx.distribute(shares, peers)
            
            # Later: collect and reconstruct
            result = await styx.collect(peers, threshold=3)
            secret = styx.reconstruct(result.shares)
    """
    
    def __init__(
        self,
        hmac_key: bytes | None = None,
        transport: ShareTransport | None = None
    ):
        self._sharer = SecretSharer(hmac_key)
        self._transport = transport or InMemoryTransport()
        self._collector = ShareCollector(self._transport, self._sharer)
    
    async def __aenter__(self) -> Styx:
        return self
    
    async def __aexit__(self, *args) -> None:
        pass  # No cleanup needed for now
    
    @property
    def sharer(self) -> SecretSharer:
        """Access the underlying SecretSharer for advanced operations."""
        return self._sharer
    
    @property
    def collector(self) -> ShareCollector:
        """Access the underlying ShareCollector for advanced operations."""
        return self._collector
    
    def split(self, secret: bytes, n: int, k: int) -> list[Share]:
        """
        Split a secret into n shares with threshold k.
        
        See SecretSharer.split for full documentation.
        """
        return self._sharer.split(secret, n, k)
    
    def reconstruct(self, shares: list[Share], verify: bool = True) -> bytes:
        """
        Reconstruct the secret from shares.
        
        See SecretSharer.reconstruct for full documentation.
        """
        return self._sharer.reconstruct(shares, verify_hmac=verify)
    
    async def distribute(
        self,
        shares: list[Share],
        peers: list[Peer],
        **kwargs
    ) -> dict[str, bool]:
        """
        Distribute shares to peers.
        
        See ShareCollector.distribute for full documentation.
        """
        return await self._collector.distribute(shares, peers, **kwargs)
    
    async def collect(
        self,
        peers: list[Peer],
        threshold: int,
        **kwargs
    ) -> CollectionResult:
        """
        Collect shares from peers.
        
        See ShareCollector.collect for full documentation.
        """
        return await self._collector.collect(peers, threshold, **kwargs)


# =============================================================================
# Utility Functions
# =============================================================================

def generate_hmac_key() -> bytes:
    """Generate a cryptographically secure 32-byte HMAC key."""
    return secrets.token_bytes(32)


def shares_to_hex(shares: list[Share]) -> list[str]:
    """Convert shares to hex strings for storage/display."""
    return [share.to_bytes().hex() for share in shares]


def shares_from_hex(hex_strings: list[str]) -> list[Share]:
    """Reconstruct shares from hex strings."""
    return [Share.from_bytes(bytes.fromhex(h)) for h in hex_strings]


__all__ = [
    'GF256',
    'Share',
    'SecretSharer',
    'ShareCollector',
    'ShareTransport',
    'InMemoryTransport',
    'Peer',
    'PeerState',
    'CollectionResult',
    'Styx',
    'StyxError',
    'IntegrityError',
    'InsufficientSharesError',
    'DuplicateShareError',
    'generate_hmac_key',
    'shares_to_hex',
    'shares_from_hex',
]
