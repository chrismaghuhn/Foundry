"""
WITNESS: Verifiable Decision Commitment Protocol

Demonstration / reference implementation — not for production deployment.

A protocol for making algorithmic decisions VERIFIABLE.

"If you won't let me verify your decision, you're not making a decision —
 you're exercising arbitrary power with plausible deniability."

Usage:
    from witness import WitnessProtocol, DecisionLogic
    
    # Decision maker creates and commits to logic
    logic = DecisionLogic("MyDecision", "1.0")
    income = logic.load("income")
    threshold = logic.const(50000)
    approved = logic.ge(income, threshold)
    logic.approve(approved, "Income meets threshold")
    
    # Commit BEFORE seeing data
    protocol = WitnessProtocol("ACME_CORP")
    commitment = protocol.commit(logic, "approval")
    
    # Later: execute on subject's data
    decision = protocol.decide(commitment, {"income": 60000})
    
    # ANYONE can verify
    result, msg = WitnessProtocol.verify(decision)
    # result == VerificationResult.VALID

Author: chrismaghuhn
License: MIT
"""

from .witness import (
    # Core types
    Commitment, Decision, ExecutionTrace, ExecutionStep,
    VerificationResult,
    
    # Logic DSL
    DecisionLogic, DecisionOp, Instruction,
    
    # Engine
    DecisionEngine,
    
    # Protocol
    WitnessProtocol,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    'Commitment', 'Decision', 'ExecutionTrace', 'ExecutionStep',
    'VerificationResult',
    'DecisionLogic', 'DecisionOp', 'Instruction',
    'DecisionEngine',
    'WitnessProtocol',
]
