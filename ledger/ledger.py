#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ██╗     ███████╗██████╗  ██████╗ ███████╗██████╗                             ║
║  ██║     ██╔════╝██╔══██╗██╔════╝ ██╔════╝██╔══██╗                            ║
║  ██║     █████╗  ██║  ██║██║  ███╗█████╗  ██████╔╝                            ║
║  ██║     ██╔══╝  ██║  ██║██║   ██║██╔══╝  ██╔══██╗                            ║
║  ███████╗███████╗██████╔╝╚██████╔╝███████╗██║  ██║                            ║
║  ╚══════╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝                            ║
║                                                                               ║
║     Mutual Reputation Protocol                                                ║
║                                                                               ║
║  "You cannot judge without being judged.                                      ║
║   You cannot see their review until you've committed yours."                  ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

LEDGER: A protocol where reputation is MUTUAL.

THE RULE THIS CHANGES:
    Previously: Your boss writes a reference about you. You never see it.
    Now: If they review you, you review them. Both revealed simultaneously.

THE PROBLEM THIS SOLVES:
    Reputation is asymmetric. Those with power judge those without.
    References are written behind closed doors.
    You never know what's said about you.
    You can't challenge what you can't see.

WHAT THIS MAKES IMPOSSIBLE:
    1. One-sided judgment (you can't review without being reviewed)
    2. Strategic adjustment (you can't see theirs before committing yours)
    3. Anonymous attacks (every review has a known author)
    4. Hidden reputation (both parties see both reviews)

WHAT THIS MAKES POSSIBLE:
    1. Symmetric accountability (managers get reviewed by reports)
    2. Honest feedback (can't retaliate against unknown content)
    3. Pattern detection (someone with 10 bad reviews has a problem)
    4. Informed decisions (see both sides of every relationship)

MORAL INVARIANTS:
    1. You cannot review someone without them reviewing you
    2. You cannot see their review until you've committed yours
    3. Both reviews are permanently linked
    4. Context is always visible (who reviewed whom, when, why)

THREAT MODEL:
    - Parties can collude ("you write good, I write good")
    - Parties can retaliate (but only symmetrically)
    - Adversary CANNOT see review before committing
    - Adversary CANNOT modify review after seeing the other

HONEST LIMITATIONS:
    - Cannot force honest reviews (collusion is possible)
    - Cannot prevent strategic behavior (but makes it symmetric)
    - Trust is not created, only made auditable

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
from typing import Any, Dict, List, Optional, Tuple
import uuid


# =============================================================================
# CRYPTOGRAPHIC PRIMITIVES
# =============================================================================

class Identity:
    """
    A person's cryptographic identity.
    
    MORAL INTENT: Your identity is tied to your reviews.
    You cannot hide behind anonymity when judging others.
    """
    
    def __init__(self, name: str, secret: Optional[bytes] = None):
        self.name = name
        self._secret = secret or secrets.token_bytes(32)
        self._public = hashlib.sha256(b"ledger:pk:" + self._secret).digest()
    
    @property
    def public_key(self) -> bytes:
        return self._public
    
    @property
    def public_key_hex(self) -> str:
        return self._public.hex()
    
    @property
    def fingerprint(self) -> str:
        return self._public.hex()[:16]
    
    def sign(self, message: bytes) -> bytes:
        sig = hmac.new(self._secret, message, hashlib.sha256).digest()
        _register_signature(self._public, message, sig)
        return sig
    
    def encrypt_for_reveal(self, plaintext: str) -> Tuple[str, str]:
        """
        Encrypt content with a random key. Return (ciphertext, key).
        The key is revealed later for simultaneous decryption.
        
        (Simplified: In production, use proper encryption)
        """
        key = secrets.token_hex(32)
        # Simple XOR-based encryption for demo (use AES in production)
        key_bytes = bytes.fromhex(key)
        plaintext_bytes = plaintext.encode('utf-8')
        
        # Pad plaintext to multiple of key length
        padded_len = ((len(plaintext_bytes) // 32) + 1) * 32
        padded = plaintext_bytes.ljust(padded_len, b'\x00')
        
        ciphertext = bytes(
            p ^ key_bytes[i % 32] 
            for i, p in enumerate(padded)
        )
        return ciphertext.hex(), key
    
    @staticmethod
    def decrypt(ciphertext_hex: str, key_hex: str) -> str:
        """Decrypt content with revealed key."""
        ciphertext = bytes.fromhex(ciphertext_hex)
        key_bytes = bytes.fromhex(key_hex)
        
        plaintext = bytes(
            c ^ key_bytes[i % 32]
            for i, c in enumerate(ciphertext)
        )
        return plaintext.rstrip(b'\x00').decode('utf-8')
    
    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        return _verify_signature(public_key, message, signature)
    
    def __repr__(self) -> str:
        return f"Identity({self.name})"


_SIGNATURES: Dict[Tuple[bytes, bytes], bytes] = {}

def _register_signature(pubkey: bytes, message: bytes, sig: bytes) -> None:
    _SIGNATURES[(pubkey, message)] = sig

def _verify_signature(pubkey: bytes, message: bytes, sig: bytes) -> bool:
    return _SIGNATURES.get((pubkey, message)) == sig


# =============================================================================
# REVIEW TYPES
# =============================================================================

class ReviewStatus(Enum):
    """Status of a mutual review."""
    INITIATED = auto()      # One party invited
    BOTH_COMMITTED = auto() # Both have sealed their reviews
    REVEALED = auto()       # Both reviews visible
    EXPIRED = auto()        # Timeout without completion
    DECLINED = auto()       # One party declined


class Rating(Enum):
    """Standardized rating scale."""
    EXCEPTIONAL = 5
    ABOVE_EXPECTATIONS = 4
    MEETS_EXPECTATIONS = 3
    BELOW_EXPECTATIONS = 2
    UNSATISFACTORY = 1


@dataclass
class ReviewContent:
    """
    The actual review content.
    
    MORAL INTENT: Reviews have structure to enable comparison
    and pattern detection. Free text alone enables gaming.
    """
    overall_rating: Rating
    
    # Specific dimensions
    competence: Rating
    reliability: Rating
    communication: Rating
    collaboration: Rating
    
    # Free text
    strengths: str
    areas_for_growth: str
    additional_comments: str
    
    # Would you work with them again?
    would_work_again: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_rating": self.overall_rating.value,
            "competence": self.competence.value,
            "reliability": self.reliability.value,
            "communication": self.communication.value,
            "collaboration": self.collaboration.value,
            "strengths": self.strengths,
            "areas_for_growth": self.areas_for_growth,
            "additional_comments": self.additional_comments,
            "would_work_again": self.would_work_again,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ReviewContent':
        return cls(
            overall_rating=Rating(d["overall_rating"]),
            competence=Rating(d["competence"]),
            reliability=Rating(d["reliability"]),
            communication=Rating(d["communication"]),
            collaboration=Rating(d["collaboration"]),
            strengths=d["strengths"],
            areas_for_growth=d["areas_for_growth"],
            additional_comments=d["additional_comments"],
            would_work_again=d["would_work_again"],
        )
    
    def summary(self) -> str:
        stars = "★" * self.overall_rating.value + "☆" * (5 - self.overall_rating.value)
        return f"{stars} | Would work again: {'Yes' if self.would_work_again else 'No'}"


# =============================================================================
# SEALED COMMITMENT
# =============================================================================

@dataclass
class SealedReview:
    """
    A review that has been committed but not yet revealed.
    
    MORAL INTENT: Once sealed, the content cannot change.
    This prevents adjusting your review after seeing theirs.
    """
    reviewer_id: str
    reviewer_pubkey: str
    subject_id: str
    
    # Encrypted content
    encrypted_content: str
    
    # Commitment (hash of plaintext + salt)
    commitment_hash: str
    
    # Signature over the commitment
    signature: str
    
    # Timestamp
    committed_at: str
    
    # The key is held by the reviewer until reveal
    _reveal_key: Optional[str] = field(default=None, repr=False)
    
    def verify_commitment(self, plaintext: str, salt: str) -> bool:
        """Verify that plaintext matches commitment."""
        expected = hashlib.sha256((plaintext + salt).encode()).hexdigest()
        return expected == self.commitment_hash


# =============================================================================
# MUTUAL REVIEW
# =============================================================================

@dataclass
class MutualReview:
    """
    A complete mutual review between two parties.
    
    INVARIANTS:
        1. Both parties must commit before either can see
        2. Reveal is simultaneous (neither sees first)
        3. Both reviews are permanently linked
        4. Context is always visible
    """
    review_id: str
    context: str  # "Project collaboration", "Employment 2022-2024", etc.
    
    # Participants
    party_a_id: str
    party_a_name: str
    party_a_pubkey: str
    
    party_b_id: str
    party_b_name: str
    party_b_pubkey: str
    
    # Sealed reviews (before reveal)
    sealed_a: Optional[SealedReview] = None
    sealed_b: Optional[SealedReview] = None
    
    # Revealed content (after reveal)
    review_a_of_b: Optional[ReviewContent] = None
    review_b_of_a: Optional[ReviewContent] = None
    
    # Metadata
    initiated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    revealed_at: Optional[str] = None
    status: ReviewStatus = ReviewStatus.INITIATED
    
    def is_ready_for_reveal(self) -> bool:
        """Both parties have committed."""
        return self.sealed_a is not None and self.sealed_b is not None
    
    def summary(self) -> str:
        """Human-readable summary."""
        status_emoji = {
            ReviewStatus.INITIATED: "⏳",
            ReviewStatus.BOTH_COMMITTED: "🔒",
            ReviewStatus.REVEALED: "✅",
            ReviewStatus.EXPIRED: "⏰",
            ReviewStatus.DECLINED: "❌",
        }
        
        lines = [
            f"╔══════════════════════════════════════════════════════════════════╗",
            f"║ MUTUAL REVIEW: {self.context[:45]:<45} ║",
            f"╠══════════════════════════════════════════════════════════════════╣",
            f"║ Status: {status_emoji.get(self.status, '?')} {self.status.name:<20}                          ║",
            f"║ Between: {self.party_a_name} ↔ {self.party_b_name:<30}       ║",
            f"╠══════════════════════════════════════════════════════════════════╣",
        ]
        
        if self.status == ReviewStatus.REVEALED:
            lines.append(f"║ {self.party_a_name}'s review of {self.party_b_name}:                              ║")
            lines.append(f"║   {self.review_a_of_b.summary():<60} ║")
            lines.append(f"║                                                                  ║")
            lines.append(f"║ {self.party_b_name}'s review of {self.party_a_name}:                              ║")
            lines.append(f"║   {self.review_b_of_a.summary():<60} ║")
        else:
            a_status = "✓ Committed" if self.sealed_a else "○ Pending"
            b_status = "✓ Committed" if self.sealed_b else "○ Pending"
            lines.append(f"║ {self.party_a_name}: {a_status:<20}                          ║")
            lines.append(f"║ {self.party_b_name}: {b_status:<20}                          ║")
        
        lines.append(f"╚══════════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# =============================================================================
# LEDGER PROTOCOL
# =============================================================================

class LedgerProtocol:
    """
    The complete LEDGER protocol for mutual reputation.
    
    FLOW:
        1. Party A initiates review with Party B
        2. Both write and seal their reviews (commit phase)
        3. Both reveal simultaneously (reveal phase)
        4. Reviews are permanently linked and visible
    
    MORAL GUARANTEES:
        - You cannot review without being reviewed
        - You cannot see theirs before committing yours
        - Both reviews are permanent and linked
    """
    
    def __init__(self):
        self._reviews: Dict[str, MutualReview] = {}
        self._by_person: Dict[str, List[str]] = {}  # person_id -> review_ids
        self._pending_keys: Dict[str, str] = {}  # sealed_id -> reveal_key
    
    def initiate(
        self,
        initiator: Identity,
        other: Identity,
        context: str
    ) -> MutualReview:
        """
        Initiate a mutual review.
        
        MORAL INTENT: Both parties must agree to be reviewed.
        Initiation is an invitation, not an imposition.
        """
        review_id = str(uuid.uuid4())
        
        review = MutualReview(
            review_id=review_id,
            context=context,
            party_a_id=initiator.name,
            party_a_name=initiator.name,
            party_a_pubkey=initiator.public_key_hex,
            party_b_id=other.name,
            party_b_name=other.name,
            party_b_pubkey=other.public_key_hex,
        )
        
        self._reviews[review_id] = review
        
        # Index by person
        for person_id in [initiator.name, other.name]:
            if person_id not in self._by_person:
                self._by_person[person_id] = []
            self._by_person[person_id].append(review_id)
        
        return review
    
    def commit_review(
        self,
        review_id: str,
        reviewer: Identity,
        content: ReviewContent
    ) -> bool:
        """
        Commit (seal) a review.
        
        MORAL INTENT: Once committed, you cannot change your review.
        You must decide what to write without knowing what they wrote.
        """
        review = self._reviews.get(review_id)
        if not review:
            return False
        
        # Determine which party this is
        if reviewer.name == review.party_a_name:
            if review.sealed_a is not None:
                return False  # Already committed
            is_party_a = True
            subject_id = review.party_b_id
        elif reviewer.name == review.party_b_name:
            if review.sealed_b is not None:
                return False  # Already committed
            is_party_a = False
            subject_id = review.party_a_id
        else:
            return False  # Not a party to this review
        
        # Serialize content
        plaintext = json.dumps(content.to_dict(), sort_keys=True)
        
        # Create commitment
        salt = secrets.token_hex(32)
        commitment_hash = hashlib.sha256((plaintext + salt).encode()).hexdigest()
        
        # Encrypt for later reveal
        encrypted, reveal_key = reviewer.encrypt_for_reveal(plaintext)
        
        # Sign the commitment
        sig_message = f"{review_id}:{commitment_hash}:{reviewer.name}".encode()
        signature = reviewer.sign(sig_message)
        
        # Create sealed review
        sealed = SealedReview(
            reviewer_id=reviewer.name,
            reviewer_pubkey=reviewer.public_key_hex,
            subject_id=subject_id,
            encrypted_content=encrypted,
            commitment_hash=commitment_hash,
            signature=signature.hex(),
            committed_at=datetime.now(timezone.utc).isoformat(),
            _reveal_key=reveal_key,
        )
        
        # Store the reveal key (held until both commit)
        sealed_id = f"{review_id}:{reviewer.name}"
        self._pending_keys[sealed_id] = reveal_key
        
        # Attach to review
        if is_party_a:
            review.sealed_a = sealed
        else:
            review.sealed_b = sealed
        
        # Check if both committed
        if review.is_ready_for_reveal():
            review.status = ReviewStatus.BOTH_COMMITTED
        
        return True
    
    def reveal(self, review_id: str) -> Optional[MutualReview]:
        """
        Reveal both reviews simultaneously.
        
        MORAL INTENT: Neither party sees the other's review first.
        This is the moment of truth.
        """
        review = self._reviews.get(review_id)
        if not review or not review.is_ready_for_reveal():
            return None
        
        if review.status == ReviewStatus.REVEALED:
            return review  # Already revealed
        
        # Get reveal keys
        key_a = self._pending_keys.get(f"{review_id}:{review.party_a_name}")
        key_b = self._pending_keys.get(f"{review_id}:{review.party_b_name}")
        
        if not key_a or not key_b:
            return None
        
        # Decrypt both reviews
        try:
            plaintext_a = Identity.decrypt(review.sealed_a.encrypted_content, key_a)
            plaintext_b = Identity.decrypt(review.sealed_b.encrypted_content, key_b)
            
            review.review_a_of_b = ReviewContent.from_dict(json.loads(plaintext_a))
            review.review_b_of_a = ReviewContent.from_dict(json.loads(plaintext_b))
            
            review.status = ReviewStatus.REVEALED
            review.revealed_at = datetime.now(timezone.utc).isoformat()
            
            # Clean up keys
            del self._pending_keys[f"{review_id}:{review.party_a_name}"]
            del self._pending_keys[f"{review_id}:{review.party_b_name}"]
            
            return review
            
        except Exception as e:
            return None
    
    def get_reviews_for(self, person_id: str) -> List[MutualReview]:
        """Get all reviews involving a person."""
        review_ids = self._by_person.get(person_id, [])
        return [self._reviews[rid] for rid in review_ids if rid in self._reviews]
    
    def get_revealed_reviews_for(self, person_id: str) -> List[MutualReview]:
        """Get only revealed reviews for a person."""
        return [
            r for r in self.get_reviews_for(person_id)
            if r.status == ReviewStatus.REVEALED
        ]
    
    def get_reputation_summary(self, person_id: str) -> Dict[str, Any]:
        """
        Compute reputation summary for a person.
        
        MORAL INTENT: Reputation is computed from MUTUAL reviews only.
        One-sided judgments don't exist in this system.
        """
        reviews = self.get_revealed_reviews_for(person_id)
        
        if not reviews:
            return {
                "person_id": person_id,
                "review_count": 0,
                "average_rating": None,
                "would_work_again_pct": None,
            }
        
        # Collect reviews OF this person
        ratings = []
        would_work_again = []
        
        for review in reviews:
            if review.party_a_id == person_id:
                # B reviewed A
                content = review.review_b_of_a
            else:
                # A reviewed B
                content = review.review_a_of_b
            
            if content:
                ratings.append(content.overall_rating.value)
                would_work_again.append(content.would_work_again)
        
        return {
            "person_id": person_id,
            "review_count": len(ratings),
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "would_work_again_pct": (
                sum(would_work_again) / len(would_work_again) * 100 
                if would_work_again else None
            ),
            "reviews_given": len(reviews),  # They also reviewed others
        }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'Identity',
    'Rating',
    'ReviewContent',
    'ReviewStatus',
    'SealedReview',
    'MutualReview',
    'LedgerProtocol',
]


# =============================================================================
# DEMONSTRATION
# =============================================================================

def demo():
    """Demonstrate the LEDGER protocol."""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  LEDGER: Mutual Reputation Protocol                                           ║
║                                                                               ║
║  "You cannot judge without being judged.                                      ║
║   You cannot see their review until you've committed yours."                  ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # =========================================================================
    # SCENARIO: Manager and Employee
    # =========================================================================
    print("=" * 75)
    print("SCENARIO: End of Employment — Mutual Review")
    print("=" * 75)
    
    print("""
    THE OLD WAY:
        Manager writes reference about Employee.
        Employee never sees it.
        Manager tells new employer: "Difficult to manage."
        Employee never knows why they don't get callbacks.
    
    THE LEDGER WAY:
        Manager and Employee both write reviews.
        Neither sees the other's until both commit.
        Both reviews are permanently linked.
        Anyone can see: What did each say about the other?
    """)
    
    # Create identities
    print("\n" + "-" * 75)
    print("STEP 1: ESTABLISH IDENTITIES")
    print("-" * 75)
    
    manager = Identity("Sarah Chen (Manager)")
    employee = Identity("Alex Kim (Employee)")
    
    print(f"\n  Manager: {manager}")
    print(f"  Employee: {employee}")
    
    # Initialize protocol
    protocol = LedgerProtocol()
    
    # =========================================================================
    # Initiate review
    # =========================================================================
    print("\n" + "-" * 75)
    print("STEP 2: INITIATE MUTUAL REVIEW")
    print("-" * 75)
    
    review = protocol.initiate(
        initiator=manager,
        other=employee,
        context="Employment at TechCorp (2022-2024)"
    )
    
    print(f"\n  Review initiated!")
    print(f"  Context: {review.context}")
    print(f"  Status: {review.status.name}")
    
    # =========================================================================
    # Both commit their reviews
    # =========================================================================
    print("\n" + "-" * 75)
    print("STEP 3: BOTH PARTIES COMMIT THEIR REVIEWS (sealed, not visible)")
    print("-" * 75)
    
    # Manager writes review of employee
    manager_review = ReviewContent(
        overall_rating=Rating.MEETS_EXPECTATIONS,
        competence=Rating.ABOVE_EXPECTATIONS,
        reliability=Rating.MEETS_EXPECTATIONS,
        communication=Rating.BELOW_EXPECTATIONS,
        collaboration=Rating.MEETS_EXPECTATIONS,
        strengths="Strong technical skills, quick learner, good problem solver.",
        areas_for_growth="Could improve communication with stakeholders. Sometimes misses meetings.",
        additional_comments="Talented but needs to work on soft skills.",
        would_work_again=True,  # Despite criticism, would hire again
    )
    
    # Employee writes review of manager
    employee_review = ReviewContent(
        overall_rating=Rating.BELOW_EXPECTATIONS,
        competence=Rating.MEETS_EXPECTATIONS,
        reliability=Rating.BELOW_EXPECTATIONS,
        communication=Rating.UNSATISFACTORY,
        collaboration=Rating.BELOW_EXPECTATIONS,
        strengths="Has deep domain knowledge. Well-connected in the industry.",
        areas_for_growth="Rarely available for 1:1s. Provides feedback only in annual reviews. Takes credit for team's work.",
        additional_comments="I learned a lot about the domain, but management style was frustrating.",
        would_work_again=False,
    )
    
    print("\n  Manager writing review of Employee...")
    print("  (Manager cannot see what Employee will write)")
    protocol.commit_review(review.review_id, manager, manager_review)
    print("  ✓ Manager committed")
    
    print("\n  Employee writing review of Manager...")
    print("  (Employee cannot see what Manager wrote)")
    protocol.commit_review(review.review_id, employee, employee_review)
    print("  ✓ Employee committed")
    
    print(f"\n  Status: {review.status.name}")
    print("  Both reviews are now sealed. Neither can change them.")
    
    # =========================================================================
    # Reveal
    # =========================================================================
    print("\n" + "-" * 75)
    print("STEP 4: SIMULTANEOUS REVEAL")
    print("-" * 75)
    
    print("\n  Revealing both reviews at the same time...")
    revealed = protocol.reveal(review.review_id)
    
    print(f"\n  Status: {revealed.status.name}")
    print("\n" + revealed.summary())
    
    # =========================================================================
    # Show full reviews
    # =========================================================================
    print("\n" + "-" * 75)
    print("STEP 5: THE FULL PICTURE")
    print("-" * 75)
    
    print(f"\n  MANAGER'S REVIEW OF EMPLOYEE:")
    print(f"    Overall: {revealed.review_a_of_b.overall_rating.name}")
    print(f"    Competence: {revealed.review_a_of_b.competence.name}")
    print(f"    Communication: {revealed.review_a_of_b.communication.name}")
    print(f"    Strengths: {revealed.review_a_of_b.strengths}")
    print(f"    Growth areas: {revealed.review_a_of_b.areas_for_growth}")
    print(f"    Would work again: {'Yes' if revealed.review_a_of_b.would_work_again else 'No'}")
    
    print(f"\n  EMPLOYEE'S REVIEW OF MANAGER:")
    print(f"    Overall: {revealed.review_b_of_a.overall_rating.name}")
    print(f"    Competence: {revealed.review_b_of_a.competence.name}")
    print(f"    Communication: {revealed.review_b_of_a.communication.name}")
    print(f"    Strengths: {revealed.review_b_of_a.strengths}")
    print(f"    Growth areas: {revealed.review_b_of_a.areas_for_growth}")
    print(f"    Would work again: {'Yes' if revealed.review_b_of_a.would_work_again else 'No'}")
    
    # =========================================================================
    # What this changes
    # =========================================================================
    print("\n" + "-" * 75)
    print("WHAT A FUTURE EMPLOYER NOW SEES")
    print("-" * 75)
    
    print("""
    When considering ALEX KIM:
    
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ MUTUAL REVIEW: Employment at TechCorp (2022-2024)                       │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │ Manager (Sarah Chen) said about Alex:                                   │
    │   ★★★☆☆ (Meets Expectations)                                            │
    │   "Strong technical skills... needs to work on soft skills"             │
    │   Would hire again: YES                                                 │
    │                                                                         │
    │ Alex said about Manager (Sarah Chen):                                   │
    │   ★★☆☆☆ (Below Expectations)                                            │
    │   "Rarely available... takes credit for team's work"                    │
    │   Would work for again: NO                                              │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘
    
    THE NEW EMPLOYER CAN NOW SEE:
    
    1. The criticism is MUTUAL, not one-sided
       → "Communication issues" might be the manager's fault
    
    2. Despite criticism, manager WOULD hire again
       → Technical skills must be genuinely strong
    
    3. The employee gave honest negative feedback
       → Shows integrity (or grievance — reader decides)
    
    4. Pattern recognition becomes possible
       → If Sarah Chen has 10 reports who all say "takes credit,"
         that's a pattern about HER, not about them.
    """)
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 75)
    print("WHAT LEDGER CHANGES")
    print("=" * 75)
    
    print("""
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         POWER SHIFT                                     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  BEFORE:                              AFTER:                            │
    │                                                                         │
    │  Manager judges Employee              Manager and Employee judge        │
    │  Employee never sees                  EACH OTHER                        │
    │                                                                         │
    │  Reference is one-sided               Both reviews linked               │
    │  Power flows downward                 Accountability is mutual          │
    │                                                                         │
    │  "Difficult to manage"                "Difficult to manage" + context   │
    │  (end of story)                       (was the manager available?)      │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘
    
    WHO MUST BE TRUSTED LESS:
        Reference writers. Their reviews now have context.
        Managers. Their reports review them back.
    
    WHO GAINS AGENCY:
        Anyone being judged. They judge back.
        Future employers. They see both sides.
    
    WHAT CAN NOW BE VERIFIED:
        - What each party ACTUALLY said (not just what they claim)
        - Whether negative reviews are mutual or one-sided
        - Patterns across multiple reviews
        - Whether criticism comes from credible sources
    
    HONEST LIMITATIONS:
        - Cannot prevent collusion ("you write good, I write good")
        - Cannot force honest reviews
        - Cannot prevent retaliation (but makes it symmetric)
        - Some relationships have genuine power imbalances
    
    WHO WOULD BE ANNOYED BY THIS:
        - HR departments that control the reference narrative
        - Bad managers protected by one-sided reviews
        - Anyone who benefits from asymmetric information
    """)


if __name__ == "__main__":
    demo()
