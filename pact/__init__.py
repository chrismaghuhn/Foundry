"""
PACT: Immutable Agreement Protocol

Demonstration / reference implementation — not for production deployment.

A protocol where agreements require signatures from ALL parties,
and amendments require RE-SIGNATURE from all parties.

"A contract that one party can change at will is not a contract —
 it's a demonstration of power dressed as consent."

Usage:
    from pact import Identity, Pact, PactRegistry
    
    # Create identities
    platform = Identity("MegaCorp")
    user = Identity("Alice")
    
    # Create agreement
    pact = Pact.create(
        title="Service Terms",
        terms="...",
        required_parties=["MegaCorp", "Alice"]
    )
    
    # Both must sign for it to be ACTIVE
    pact.sign(platform)
    pact.sign(user)
    
    # Now pact.status == PactStatus.ACTIVE
    
    # Amendments require BOTH signatures again
    # User can REJECT and original remains in force

Author: chrismaghuhn
License: MIT
"""

from .pact import (
    Identity,
    Pact,
    PactStatus,
    PactRegistry,
    SignatureRecord,
    propose_amendment,
    accept_amendment,
    reject_amendment,
    compute_hash,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

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
