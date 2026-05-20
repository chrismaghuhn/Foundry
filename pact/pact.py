#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ██████╗  █████╗  ██████╗████████╗                                            ║
║  ██╔══██╗██╔══██╗██╔════╝╚══██╔══╝                                            ║
║  ██████╔╝███████║██║        ██║                                               ║
║  ██╔═══╝ ██╔══██║██║        ██║                                               ║
║  ██║     ██║  ██║╚██████╗   ██║                                               ║
║  ╚═╝     ╚═╝  ╚═╝ ╚═════╝   ╚═╝                                               ║
║                                                                               ║
║     Immutable Agreement Protocol                                              ║
║                                                                               ║
║  "A contract that one party can change at will is not a contract —           ║
║   it's a demonstration of power dressed as consent."                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

PACT: A protocol where agreements require signatures from ALL parties,
and amendments require RE-SIGNATURE from all parties.

THE RULE THIS CHANGES:
    Previously: "We updated our Terms of Service. Continued use = acceptance."
    Now: No signature, no change. Period.

WHAT THIS MAKES OBSOLETE:
    - Unilateral contract modification
    - "Implied consent" through continued use
    - Terms of Service that can change without notice or agreement
    - The entire fiction that clicking "I Agree" to 50 pages is consent

WHAT THIS MAKES POSSIBLE:
    - Proving what terms you actually agreed to
    - Refusing amendments without losing your account
    - Holding platforms to their original promises
    - Third-party auditing of contract fairness

MORAL INVARIANTS:
    1. A Pact requires signatures from ALL named parties
    2. An unsigned Pact has NO legal or technical force
    3. Amendments are new Pacts that reference the old — both signatures required
    4. History is immutable — what you agreed to, when, is permanently recorded

THREAT MODEL:
    - Adversary can refuse to sign (result: no agreement, which is honest)
    - Adversary can propose bad terms (result: you can refuse)
    - Adversary CANNOT change terms you already signed
    - Adversary CANNOT claim you agreed to something you didn't sign

HONEST LIMITATIONS:
    - Cannot force anyone to use this system
    - Cannot prevent "sign or leave" ultimatums (but makes them VISIBLE)
    - Cannot make bad contracts good (but makes them provably what they are)
    - Real adoption requires social/regulatory pressure

DOMAINS INTEGRATED:
    1. Cryptography as social tool: Signatures create accountability
    2. Data structures encoding values: Hash chains make history immutable

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Set
import textwrap


# =============================================================================
# CRYPTOGRAPHIC PRIMITIVES
# =============================================================================

class Identity:
    """
    A party's cryptographic identity.
    
    MORAL INTENT:
        Identity is tied to a key pair. Your signature is YOUR commitment.
        If you sign, you agreed. If you didn't sign, you didn't agree.
        No ambiguity. No "implied consent."
    
    In production: Use Ed25519 or similar. This uses HMAC for simplicity.
    """
    
    def __init__(self, name: str, secret: Optional[bytes] = None):
        self.name = name
        self._secret = secret or secrets.token_bytes(32)
        self._public = hashlib.sha256(b"pact:public:" + self._secret).digest()
        
    @property
    def public_key(self) -> bytes:
        return self._public
    
    @property
    def public_key_hex(self) -> str:
        return self._public.hex()
    
    @property
    def fingerprint(self) -> str:
        """Short identifier for display."""
        return self._public.hex()[:16]
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message.
        
        MORAL INTENT:
            Signing is a COMMITMENT. Once signed, you cannot deny agreement.
            This replaces "click I Agree" with actual cryptographic proof.
        """
        sig = hmac.new(self._secret, message, hashlib.sha256).digest()
        _register_signature(self._public, message, sig)
        return sig
    
    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify a signature using only the public key."""
        return _verify_signature(public_key, message, signature)
    
    def __repr__(self) -> str:
        return f"Identity({self.name}, {self.fingerprint}...)"


# Signature registry (simulates public-key verification)
_SIGNATURES: Dict[Tuple[bytes, bytes], bytes] = {}

def _register_signature(pubkey: bytes, message: bytes, sig: bytes) -> None:
    _SIGNATURES[(pubkey, message)] = sig

def _verify_signature(pubkey: bytes, message: bytes, sig: bytes) -> bool:
    return _SIGNATURES.get((pubkey, message)) == sig


def compute_hash(data: str) -> str:
    """Compute SHA-256 hash of string data."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


# =============================================================================
# PACT STATUS
# =============================================================================

class PactStatus(Enum):
    """Status of a Pact in its lifecycle."""
    DRAFT = auto()      # Proposed but not fully signed
    ACTIVE = auto()     # All parties have signed, in effect
    AMENDED = auto()    # Superseded by a newer Pact
    TERMINATED = auto() # Explicitly ended by mutual agreement


# =============================================================================
# SIGNATURE RECORD
# =============================================================================

@dataclass(frozen=True)
class SignatureRecord:
    """
    Record of a party's signature on a Pact.
    
    INVARIANT: A signature record is immutable proof that a specific
    party agreed to specific terms at a specific time.
    """
    party_name: str
    public_key_hex: str
    signature_hex: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "party": self.party_name,
            "public_key": self.public_key_hex,
            "signature": self.signature_hex,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'SignatureRecord':
        return cls(
            party_name=d["party"],
            public_key_hex=d["public_key"],
            signature_hex=d["signature"],
            timestamp=d["timestamp"],
        )


# =============================================================================
# THE PACT
# =============================================================================

@dataclass
class Pact:
    """
    An immutable agreement between parties.
    
    MORAL INVARIANTS:
        1. Terms cannot change after creation
        2. A Pact is only ACTIVE when ALL required parties have signed
        3. The hash of terms is computed ONCE at creation and never changes
        4. Amendments create NEW Pacts; they don't modify existing ones
    
    WHAT THIS ENCODES:
        - Agreement requires explicit consent (signatures)
        - History is permanent (hash chain)
        - No party has special power to modify (all signatures equal)
    """
    
    # Core identity
    pact_id: str
    version: int
    
    # The actual agreement
    title: str
    terms: str  # The full text of the agreement
    terms_hash: str  # SHA-256 of terms, computed once
    
    # Parties
    required_parties: List[str]  # Names of parties who must sign
    
    # Signatures
    signatures: Dict[str, SignatureRecord] = field(default_factory=dict)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Chain
    previous_pact_id: Optional[str] = None  # If this amends a previous Pact
    
    # Status
    status: PactStatus = PactStatus.DRAFT
    
    def __post_init__(self):
        # Ensure terms_hash matches terms
        if self.terms_hash != compute_hash(self.terms):
            raise ValueError("Terms hash does not match terms content")
    
    @classmethod
    def create(
        cls,
        title: str,
        terms: str,
        required_parties: List[str],
        previous_pact_id: Optional[str] = None
    ) -> 'Pact':
        """
        Create a new Pact (in DRAFT status).
        
        MORAL INTENT:
            Creation is just a PROPOSAL. It has no force until all sign.
            This is fundamentally different from "post terms, assume consent."
        """
        pact_id = hashlib.sha256(
            f"{time.time()}:{secrets.token_hex(16)}:{title}".encode()
        ).hexdigest()[:32]
        
        return cls(
            pact_id=pact_id,
            version=1 if previous_pact_id is None else 0,  # Set properly when signing
            title=title,
            terms=terms,
            terms_hash=compute_hash(terms),
            required_parties=required_parties,
            previous_pact_id=previous_pact_id,
        )
    
    def signing_message(self) -> bytes:
        """
        The canonical message that parties sign.
        
        INCLUDES: pact_id, terms_hash, required_parties, previous_pact_id
        
        This ensures parties are signing a SPECIFIC agreement, not just "something."
        """
        data = {
            "pact_id": self.pact_id,
            "terms_hash": self.terms_hash,
            "required_parties": sorted(self.required_parties),
            "previous_pact_id": self.previous_pact_id,
        }
        return json.dumps(data, sort_keys=True).encode('utf-8')
    
    def sign(self, identity: Identity) -> bool:
        """
        Sign the Pact as the given identity.
        
        MORAL INTENT:
            Signing is EXPLICIT. You see the terms, you sign.
            No "continued use implies consent." No ambiguity.
        
        Returns True if signature was added, False if already signed or not a party.
        """
        if identity.name not in self.required_parties:
            return False
        
        if identity.name in self.signatures:
            return False  # Already signed
        
        # Create signature
        message = self.signing_message()
        signature = identity.sign(message)
        
        # Record signature
        record = SignatureRecord(
            party_name=identity.name,
            public_key_hex=identity.public_key_hex,
            signature_hex=signature.hex(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self.signatures[identity.name] = record
        
        # Check if fully signed
        if self.is_fully_signed():
            self.status = PactStatus.ACTIVE
        
        return True
    
    def is_fully_signed(self) -> bool:
        """Check if all required parties have signed."""
        return all(party in self.signatures for party in self.required_parties)
    
    def missing_signatures(self) -> List[str]:
        """Get list of parties who haven't signed yet."""
        return [p for p in self.required_parties if p not in self.signatures]
    
    def verify_signature(self, party_name: str) -> bool:
        """
        Verify a specific party's signature.
        
        MORAL INTENT:
            ANYONE can verify. Trust is replaced by math.
            If verification fails, the Pact is invalid.
        """
        if party_name not in self.signatures:
            return False
        
        record = self.signatures[party_name]
        message = self.signing_message()
        
        return Identity.verify(
            bytes.fromhex(record.public_key_hex),
            message,
            bytes.fromhex(record.signature_hex)
        )
    
    def verify_all_signatures(self) -> Tuple[bool, List[str]]:
        """
        Verify all signatures.
        
        Returns (all_valid, list_of_invalid_parties).
        """
        invalid = []
        for party in self.signatures:
            if not self.verify_signature(party):
                invalid.append(party)
        return len(invalid) == 0, invalid
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pact_id": self.pact_id,
            "version": self.version,
            "title": self.title,
            "terms": self.terms,
            "terms_hash": self.terms_hash,
            "required_parties": self.required_parties,
            "signatures": {k: v.to_dict() for k, v in self.signatures.items()},
            "created_at": self.created_at,
            "previous_pact_id": self.previous_pact_id,
            "status": self.status.name,
        }
    
    def summary(self) -> str:
        """Human-readable summary."""
        sig_status = []
        for party in self.required_parties:
            if party in self.signatures:
                sig_status.append(f"    ✓ {party} (signed)")
            else:
                sig_status.append(f"    ○ {party} (pending)")
        
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║ PACT: {self.title[:54]:<54} ║
╠══════════════════════════════════════════════════════════════════╣
║ ID: {self.pact_id}                         ║
║ Status: {self.status.name:<10}                                       ║
║ Terms Hash: {self.terms_hash[:32]}...            ║
╠──────────────────────────────────────────────────────────────────╣
║ SIGNATURES:                                                      ║
{chr(10).join(f"║ {s:<64} ║" for s in sig_status)}
╚══════════════════════════════════════════════════════════════════╝"""


# =============================================================================
# PACT REGISTRY
# =============================================================================

class PactRegistry:
    """
    Registry of all Pacts.
    
    MORAL INTENT:
        History is public and immutable. What was agreed, when, and by whom
        is permanently recorded. No "we never said that."
    
    In production: This would be distributed/replicated.
    """
    
    def __init__(self):
        self._pacts: Dict[str, Pact] = {}
        self._by_party: Dict[str, Set[str]] = {}  # party_name -> pact_ids
        self._amendments: Dict[str, str] = {}  # old_pact_id -> new_pact_id
    
    def register(self, pact: Pact) -> None:
        """Register a Pact in the registry."""
        self._pacts[pact.pact_id] = pact
        
        for party in pact.required_parties:
            if party not in self._by_party:
                self._by_party[party] = set()
            self._by_party[party].add(pact.pact_id)
        
        if pact.previous_pact_id:
            self._amendments[pact.previous_pact_id] = pact.pact_id
    
    def get(self, pact_id: str) -> Optional[Pact]:
        """Get a Pact by ID."""
        return self._pacts.get(pact_id)
    
    def get_pacts_for_party(self, party_name: str) -> List[Pact]:
        """Get all Pacts involving a party."""
        pact_ids = self._by_party.get(party_name, set())
        return [self._pacts[pid] for pid in pact_ids]
    
    def get_active_pacts_for_party(self, party_name: str) -> List[Pact]:
        """Get all ACTIVE Pacts for a party."""
        return [p for p in self.get_pacts_for_party(party_name) 
                if p.status == PactStatus.ACTIVE]
    
    def get_amendment(self, pact_id: str) -> Optional[Pact]:
        """Get the amendment to a Pact, if any."""
        amendment_id = self._amendments.get(pact_id)
        return self._pacts.get(amendment_id) if amendment_id else None
    
    def get_history(self, pact_id: str) -> List[Pact]:
        """Get the full history chain of a Pact."""
        history = []
        current = self.get(pact_id)
        
        while current:
            history.append(current)
            if current.previous_pact_id:
                current = self.get(current.previous_pact_id)
            else:
                current = None
        
        return list(reversed(history))


# =============================================================================
# AMENDMENT PROTOCOL
# =============================================================================

def propose_amendment(
    original: Pact,
    new_terms: str,
    proposer: Identity,
    registry: PactRegistry
) -> Pact:
    """
    Propose an amendment to an existing Pact.
    
    MORAL INTENT:
        Amendments are NEW PACTS. The original remains valid until
        ALL parties sign the amendment. This means:
        - You can't change terms without consent
        - Refusing an amendment keeps the original in force
        - "Sign or leave" is still possible but now VISIBLE
    
    Returns the proposed amendment (in DRAFT status).
    """
    if original.status != PactStatus.ACTIVE:
        raise ValueError("Can only amend ACTIVE pacts")
    
    if proposer.name not in original.required_parties:
        raise ValueError("Only parties to the original can propose amendments")
    
    # Create amendment
    amendment = Pact.create(
        title=f"{original.title} (Amendment)",
        terms=new_terms,
        required_parties=original.required_parties,
        previous_pact_id=original.pact_id,
    )
    amendment.version = original.version + 1
    
    registry.register(amendment)
    return amendment


def accept_amendment(
    amendment: Pact,
    identity: Identity,
    registry: PactRegistry
) -> bool:
    """
    Accept (sign) a proposed amendment.
    
    MORAL INTENT:
        Acceptance is EXPLICIT. Each party must actively sign.
        When ALL sign, the original becomes AMENDED (superseded).
    
    Returns True if this signature activated the amendment.
    """
    if not amendment.sign(identity):
        return False
    
    # If now fully signed, mark original as amended
    if amendment.is_fully_signed() and amendment.previous_pact_id:
        original = registry.get(amendment.previous_pact_id)
        if original:
            original.status = PactStatus.AMENDED
        return True
    
    return False


def reject_amendment(
    amendment: Pact,
    identity: Identity
) -> str:
    """
    Explicitly reject an amendment.
    
    MORAL INTENT:
        Rejection is recorded. The original Pact remains in force.
        The platform CANNOT claim "you implicitly agreed by continuing to use."
    
    Returns a statement of rejection.
    """
    if identity.name not in amendment.required_parties:
        raise ValueError("Only parties to the amendment can reject")
    
    # In a full implementation, this would create a signed rejection record
    return f"{identity.name} explicitly rejected amendment {amendment.pact_id}. Original pact remains in force."


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'Identity',
    'Pact',
    'PactStatus',
    'PactRegistry',
    'SignatureRecord',
    'propose_amendment',
    'accept_amendment', 
    'reject_amendment',
    'compute_hash',
]


# =============================================================================
# DEMONSTRATION
# =============================================================================

def demo():
    """Demonstrate the PACT protocol."""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  PACT: Immutable Agreement Protocol                                           ║
║                                                                               ║
║  "A contract that one party can change at will is not a contract —           ║
║   it's a demonstration of power dressed as consent."                          ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # =========================================================================
    # SCENARIO: Platform Terms of Service
    # =========================================================================
    print("=" * 70)
    print("SCENARIO: Social Media Platform Terms of Service")
    print("=" * 70)
    
    print("""
    BEFORE PACT:
        Platform: "By using our service, you agree to our Terms."
        User: *clicks "I Agree" without reading*
        
        [6 months later]
        
        Platform: "We've updated our Terms. You now grant us perpetual
                  license to all your content. Continued use = acceptance."
        User: "I never agreed to that!"
        Platform: "You agreed to let us change the Terms whenever we want.
                  It was in paragraph 847."
        User: "..."
    
    AFTER PACT:
        Platform: "Here are our Terms. Please sign."
        User: *signs*
        
        [6 months later]
        
        Platform: "We'd like to update our Terms. Please sign the amendment."
        User: "No. I reject this amendment."
        Platform: "Then the original Terms remain in force."
        User: "Correct."
    """)
    
    # =========================================================================
    # Create identities
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 1: CREATE IDENTITIES")
    print("-" * 70)
    
    platform = Identity("MegaSocial Inc.")
    user = Identity("Alice")
    
    print(f"\n  Platform: {platform}")
    print(f"  User: {user}")
    
    # =========================================================================
    # Create and sign initial Pact
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 2: CREATE AND SIGN INITIAL AGREEMENT")
    print("-" * 70)
    
    terms_v1 = """
MEGASOCIAL TERMS OF SERVICE v1.0

1. CONTENT LICENSE
   You retain ownership of your content. You grant MegaSocial a 
   non-exclusive license to display your content on our platform.

2. DATA USAGE
   We collect usage data to improve our service. We do not sell
   your personal data to third parties.

3. ACCOUNT TERMINATION
   Either party may terminate this agreement with 30 days notice.
   Upon termination, your content will be deleted within 90 days.

4. MODIFICATIONS
   These terms may only be modified by mutual written agreement.
   [NOTE: In PACT, this is enforced cryptographically, not just promised]
"""
    
    pact = Pact.create(
        title="MegaSocial Terms of Service",
        terms=terms_v1,
        required_parties=["MegaSocial Inc.", "Alice"]
    )
    
    registry = PactRegistry()
    registry.register(pact)
    
    print(f"\n  Created Pact: {pact.pact_id}")
    print(f"  Terms Hash: {pact.terms_hash[:32]}...")
    print(f"  Status: {pact.status.name}")
    
    # Platform signs
    pact.sign(platform)
    print(f"\n  ✓ Platform signed")
    print(f"  Status: {pact.status.name}")
    
    # User signs
    pact.sign(user)
    print(f"  ✓ User signed")
    print(f"  Status: {pact.status.name}")
    
    print(pact.summary())
    
    # =========================================================================
    # Verify signatures
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 3: VERIFY SIGNATURES (anyone can do this)")
    print("-" * 70)
    
    all_valid, invalid = pact.verify_all_signatures()
    print(f"\n  All signatures valid: {all_valid}")
    
    for party in pact.required_parties:
        valid = pact.verify_signature(party)
        print(f"  {party}: {'✓ VALID' if valid else '✗ INVALID'}")
    
    # =========================================================================
    # Platform proposes amendment
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 4: PLATFORM PROPOSES AMENDMENT (wants more rights)")
    print("-" * 70)
    
    terms_v2 = """
MEGASOCIAL TERMS OF SERVICE v2.0

1. CONTENT LICENSE
   You retain ownership of your content. You grant MegaSocial a 
   PERPETUAL, IRREVOCABLE, WORLDWIDE license to use, modify, and
   sublicense your content for any purpose.  [CHANGED]

2. DATA USAGE
   We collect usage data and may share it with advertising partners
   and other third parties.  [CHANGED]

3. ACCOUNT TERMINATION
   MegaSocial may terminate your account at any time for any reason.
   You may not terminate without forfeiting all content.  [CHANGED]

4. MODIFICATIONS
   These terms may only be modified by mutual written agreement.
"""
    
    amendment = propose_amendment(pact, terms_v2, platform, registry)
    
    print(f"\n  Amendment proposed: {amendment.pact_id}")
    print(f"  New Terms Hash: {amendment.terms_hash[:32]}...")
    print(f"  Status: {amendment.status.name}")
    
    # Platform signs their own amendment
    amendment.sign(platform)
    print(f"\n  ✓ Platform signed amendment")
    print(f"  Waiting for: {amendment.missing_signatures()}")
    
    # =========================================================================
    # User REJECTS amendment
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 5: USER REJECTS AMENDMENT")
    print("-" * 70)
    
    print(f"\n  Alice reviews the changes and sees:")
    print(f"    - Content license changed from 'non-exclusive' to 'perpetual, irrevocable'")
    print(f"    - Data can now be shared with third parties")
    print(f"    - Termination rights removed")
    
    rejection = reject_amendment(amendment, user)
    print(f"\n  {rejection}")
    
    # =========================================================================
    # Verify original pact still active
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 6: VERIFY ORIGINAL AGREEMENT STILL IN FORCE")
    print("-" * 70)
    
    original = registry.get(pact.pact_id)
    
    print(f"\n  Original Pact Status: {original.status.name}")
    print(f"  Amendment Status: {amendment.status.name}")
    print(f"\n  ✓ Original terms remain in force!")
    print(f"  ✓ Platform CANNOT claim user agreed to new terms")
    print(f"  ✓ User's content remains under original license")
    
    # =========================================================================
    # CONTRAST: What would happen without PACT
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 7: WHAT WOULD HAPPEN WITHOUT PACT")
    print("-" * 70)
    
    print("""
    WITHOUT PACT:
        Platform emails: "We've updated our Terms. Review at megasocial.com/tos"
        User: *doesn't read email*
        Platform: "Continued use after Feb 1 constitutes acceptance."
        User: *continues using, unaware*
        
        [Later]
        
        Platform: "We're licensing your photos to advertisers."
        User: "I never agreed to that!"
        Platform: "You did. You kept using the service after we changed the terms."
        User: "I didn't know!"
        Platform: "Ignorance is not a defense. You agreed to receive notices by email."
        
    WITH PACT:
        Platform cannot change terms without user's explicit signature.
        If user doesn't sign, original terms apply.
        "Continued use" is not consent.
        History proves what was actually agreed.
    """)
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 70)
    print("WHAT PACT CHANGES")
    print("=" * 70)
    
    print("""
    ┌────────────────────────────────────────────────────────────────────┐
    │                    POWER SHIFT                                     │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  BEFORE:                         AFTER:                            │
    │                                                                    │
    │  Platform → "Take it or leave"   Platform → "Please sign"          │
    │  User → "I have no choice"       User → "No. Original stands."     │
    │                                                                    │
    │  Platform → "We changed terms"   Platform → "We'd like to change"  │
    │  User → "I never agreed!"        User → "I don't agree."           │
    │  Platform → "Yes you did"        Platform → "...okay."             │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘
    
    WHO MUST BE TRUSTED LESS:
        Platforms. They can't change contracts without consent.
    
    WHO GAINS AGENCY:
        Users. Refusal is meaningful. History is provable.
    
    WHAT CAN NOW BE VERIFIED:
        - Exactly what terms you agreed to
        - When you agreed
        - That no changes occurred without your signature
        - That rejection was recorded
    
    HONEST LIMITATIONS:
        - Platforms can still say "sign the bad terms or don't use us"
        - But now that's VISIBLE, not hidden in updates
        - And you can prove what you actually agreed to
    """)


if __name__ == "__main__":
    demo()
