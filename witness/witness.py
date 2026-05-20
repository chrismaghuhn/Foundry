#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ██╗    ██╗██╗████████╗███╗   ██╗███████╗███████╗███████╗                     ║
║  ██║    ██║██║╚══██╔══╝████╗  ██║██╔════╝██╔════╝██╔════╝                     ║
║  ██║ █╗ ██║██║   ██║   ██╔██╗ ██║█████╗  ███████╗███████╗                     ║
║  ██║███╗██║██║   ██║   ██║╚██╗██║██╔══╝  ╚════██║╚════██║                     ║
║  ╚███╔███╔╝██║   ██║   ██║ ╚████║███████╗███████║███████║                     ║
║   ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═══╝╚══════╝╚══════╝╚══════╝                     ║
║                                                                               ║
║     Verifiable Decision Commitment Protocol                                   ║
║                                                                               ║
║  "If you won't let me verify your decision, you're not making a decision —   ║
║   you're exercising arbitrary power with plausible deniability."              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

WITNESS: A protocol for making algorithmic decisions VERIFIABLE.

THE PROBLEM:
    "The algorithm decided" is unfalsifiable.
    
    You're denied a loan, shown harmful content, rejected from a job.
    They say: "Our algorithm determined..."
    
    But you can never:
    - See the algorithm
    - Verify it ran on your data
    - Prove it treated you differently
    - Contest the decision with evidence
    
    The algorithm is a bureaucrat that cannot be questioned.

THE SOLUTION:
    Commitment-Before-Execution.
    
    1. COMMIT: Decision maker publishes hash of their logic BEFORE seeing your data
    2. EXECUTE: Logic runs on your data, producing a decision + execution trace
    3. REVEAL: Logic and trace are disclosed to you
    4. VERIFY: You can replay the execution and confirm the result
    
    If commitment doesn't match revealed logic → FRAUD
    If replay doesn't match claimed result → FRAUD
    
    "The algorithm decided" becomes a verifiable claim.

WHAT THIS CHANGES:
    - WHO MUST BE TRUSTED LESS: Decision makers. Their claims are now falsifiable.
    - WHO GAINS AGENCY: Anyone subject to algorithmic decisions. They can audit.
    - WHAT CAN NOW BE VERIFIED: That the stated logic produced the stated result.

MORAL INVARIANTS:
    1. You cannot claim an algorithm decided if you won't show the algorithm
    2. You cannot craft logic after seeing data to justify a predetermined outcome
    3. Every decision has a witness: the execution trace itself

INTENTIONAL LIMITATION:
    WITNESS proves that STATED logic produced STATED result.
    It does NOT prove the logic is fair, unbiased, or good.
    That requires human judgment on the revealed logic.
    But judgment requires evidence. WITNESS provides it.

DOMAINS INTEGRATED:
    1. Cryptography as social tool: Commitments create accountability
    2. Compiler/interpreter logic: Deterministic execution enables replay
    3. Data structures encoding values: The trace is a record of truth

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import json
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
)
import textwrap
import copy


# =============================================================================
# CORE TYPES
# =============================================================================

class VerificationResult(Enum):
    """Result of verifying a decision."""
    VALID = auto()           # Commitment matches, replay matches
    COMMITMENT_MISMATCH = auto()  # Revealed logic doesn't match commitment
    REPLAY_MISMATCH = auto()      # Replay produced different result
    INVALID_TRACE = auto()        # Trace is malformed or incomplete
    EXECUTION_ERROR = auto()      # Replay failed to execute


@dataclass(frozen=True)
class Commitment:
    """
    A cryptographic commitment to decision logic.
    
    MORAL INTENT:
        This is published BEFORE the decision maker sees the subject's data.
        It locks in the logic. Post-hoc justification becomes detectable.
    
    INVARIANT:
        commitment_hash == SHA256(logic_source || salt)
        
        The salt prevents rainbow table attacks on the logic.
    """
    commitment_hash: str      # SHA256 of (logic + salt)
    timestamp: str            # ISO timestamp
    decision_maker_id: str    # Who made this commitment
    purpose: str              # What kind of decision (e.g., "loan_approval")
    version: str              # Version of the decision logic
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "commitment_hash": self.commitment_hash,
            "timestamp": self.timestamp,
            "decision_maker_id": self.decision_maker_id,
            "purpose": self.purpose,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Commitment':
        return cls(**d)


@dataclass(frozen=True)
class ExecutionStep:
    """
    A single step in the execution trace.
    
    MORAL INTENT:
        Every operation is recorded. Nothing is hidden.
        The trace is the WITNESS to what actually happened.
    """
    step_number: int
    operation: str           # What operation (e.g., "COMPARE", "LOAD", "BRANCH")
    operands: Tuple[Any, ...]  # Input values
    result: Any              # Output value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "op": self.operation,
            "operands": list(self.operands),
            "result": self.result,
        }


@dataclass
class ExecutionTrace:
    """
    Complete record of a decision execution.
    
    MORAL INTENT:
        This is the EVIDENCE. With logic + trace + input, anyone can verify.
        Lying about what the algorithm did becomes provably false.
    """
    input_hash: str           # Hash of input data (privacy: data not stored)
    steps: List[ExecutionStep]
    final_result: Any
    execution_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_hash": self.input_hash,
            "steps": [s.to_dict() for s in self.steps],
            "final_result": self.final_result,
            "execution_time_ms": self.execution_time_ms,
        }
    
    def hash(self) -> str:
        """Compute hash of the entire trace."""
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()


@dataclass
class Decision:
    """
    A complete verifiable decision.
    
    Contains everything needed to verify:
    - The commitment (what was promised)
    - The revealed logic (what was claimed to run)
    - The execution trace (evidence of what happened)
    - The result (what was decided)
    
    INVARIANT:
        A valid Decision satisfies:
        1. hash(revealed_logic + salt) == commitment.commitment_hash
        2. replay(revealed_logic, input_data) == result
    """
    commitment: Commitment
    revealed_logic: str       # The actual code
    salt: str                 # Random salt used in commitment
    input_data: Dict[str, Any]  # The subject's data
    trace: ExecutionTrace
    result: Any
    explanation: str          # Human-readable explanation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "commitment": self.commitment.to_dict(),
            "revealed_logic": self.revealed_logic,
            "salt": self.salt,
            "input_hash": hashlib.sha256(
                json.dumps(self.input_data, sort_keys=True).encode()
            ).hexdigest(),
            "trace": self.trace.to_dict(),
            "result": self.result,
            "explanation": self.explanation,
        }


# =============================================================================
# DECISION LOGIC DSL - A safe, deterministic language for decisions
# =============================================================================

class DecisionOp(Enum):
    """Operations in the decision logic DSL."""
    # Data access
    LOAD = "LOAD"           # Load a field from input
    CONST = "CONST"         # Load a constant
    
    # Arithmetic
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    
    # Comparison
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LE = "LE"
    GT = "GT"
    GE = "GE"
    
    # Logic
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    # Control
    IF = "IF"               # Conditional
    
    # Aggregation
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT = "COUNT"
    
    # Result
    APPROVE = "APPROVE"
    DENY = "DENY"
    SCORE = "SCORE"


@dataclass
class Instruction:
    """A single instruction in decision logic."""
    op: DecisionOp
    args: List[Any]
    target: str  # Variable to store result
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.op.value,
            "args": self.args,
            "target": self.target,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Instruction':
        return cls(
            op=DecisionOp(d["op"]),
            args=d["args"],
            target=d["target"],
        )


class DecisionLogic:
    """
    Decision logic program.
    
    This is a simple DSL that is:
    - DETERMINISTIC: Same inputs always produce same outputs
    - AUDITABLE: Every operation is recorded
    - SAFE: No side effects, no arbitrary code execution
    
    MORAL INTENT:
        This is NOT a general-purpose language.
        It is specifically designed so that:
        1. Logic can be committed to before seeing data
        2. Execution can be perfectly replayed
        3. Non-experts can read and understand decisions
    """
    
    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self.instructions: List[Instruction] = []
        self._var_counter = 0
    
    def _next_var(self) -> str:
        self._var_counter += 1
        return f"_v{self._var_counter}"
    
    # Builder methods for constructing logic
    
    def load(self, field_name: str) -> str:
        """Load a field from input data."""
        var = self._next_var()
        self.instructions.append(Instruction(
            op=DecisionOp.LOAD,
            args=[field_name],
            target=var
        ))
        return var
    
    def const(self, value: Any) -> str:
        """Load a constant value."""
        var = self._next_var()
        self.instructions.append(Instruction(
            op=DecisionOp.CONST,
            args=[value],
            target=var
        ))
        return var
    
    def add(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.ADD, [a, b], var))
        return var
    
    def sub(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.SUB, [a, b], var))
        return var
    
    def mul(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.MUL, [a, b], var))
        return var
    
    def div(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.DIV, [a, b], var))
        return var
    
    def eq(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.EQ, [a, b], var))
        return var
    
    def lt(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.LT, [a, b], var))
        return var
    
    def le(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.LE, [a, b], var))
        return var
    
    def gt(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.GT, [a, b], var))
        return var
    
    def ge(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.GE, [a, b], var))
        return var
    
    def and_(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.AND, [a, b], var))
        return var
    
    def or_(self, a: str, b: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.OR, [a, b], var))
        return var
    
    def not_(self, a: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(DecisionOp.NOT, [a], var))
        return var
    
    def if_(self, condition: str, then_val: str, else_val: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(
            DecisionOp.IF, [condition, then_val, else_val], var
        ))
        return var
    
    def approve(self, condition: str, reason: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(
            DecisionOp.APPROVE, [condition, reason], var
        ))
        return var
    
    def deny(self, condition: str, reason: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(
            DecisionOp.DENY, [condition, reason], var
        ))
        return var
    
    def score(self, value: str, explanation: str) -> str:
        var = self._next_var()
        self.instructions.append(Instruction(
            DecisionOp.SCORE, [value, explanation], var
        ))
        return var
    
    def to_source(self) -> str:
        """Serialize to a canonical string representation."""
        data = {
            "name": self.name,
            "version": self.version,
            "instructions": [i.to_dict() for i in self.instructions],
        }
        return json.dumps(data, sort_keys=True, indent=2)
    
    @classmethod
    def from_source(cls, source: str) -> 'DecisionLogic':
        """Deserialize from source string."""
        data = json.loads(source)
        logic = cls(data["name"], data["version"])
        logic.instructions = [
            Instruction.from_dict(i) for i in data["instructions"]
        ]
        logic._var_counter = len(logic.instructions)
        return logic
    
    def human_readable(self) -> str:
        """Generate human-readable description of the logic."""
        lines = [f"Decision Logic: {self.name} v{self.version}", "=" * 50]
        
        for i, inst in enumerate(self.instructions):
            if inst.op == DecisionOp.LOAD:
                lines.append(f"{inst.target} = input.{inst.args[0]}")
            elif inst.op == DecisionOp.CONST:
                lines.append(f"{inst.target} = {inst.args[0]}")
            elif inst.op == DecisionOp.ADD:
                lines.append(f"{inst.target} = {inst.args[0]} + {inst.args[1]}")
            elif inst.op == DecisionOp.SUB:
                lines.append(f"{inst.target} = {inst.args[0]} - {inst.args[1]}")
            elif inst.op == DecisionOp.MUL:
                lines.append(f"{inst.target} = {inst.args[0]} * {inst.args[1]}")
            elif inst.op == DecisionOp.DIV:
                lines.append(f"{inst.target} = {inst.args[0]} / {inst.args[1]}")
            elif inst.op == DecisionOp.LT:
                lines.append(f"{inst.target} = {inst.args[0]} < {inst.args[1]}")
            elif inst.op == DecisionOp.LE:
                lines.append(f"{inst.target} = {inst.args[0]} <= {inst.args[1]}")
            elif inst.op == DecisionOp.GT:
                lines.append(f"{inst.target} = {inst.args[0]} > {inst.args[1]}")
            elif inst.op == DecisionOp.GE:
                lines.append(f"{inst.target} = {inst.args[0]} >= {inst.args[1]}")
            elif inst.op == DecisionOp.AND:
                lines.append(f"{inst.target} = {inst.args[0]} AND {inst.args[1]}")
            elif inst.op == DecisionOp.OR:
                lines.append(f"{inst.target} = {inst.args[0]} OR {inst.args[1]}")
            elif inst.op == DecisionOp.NOT:
                lines.append(f"{inst.target} = NOT {inst.args[0]}")
            elif inst.op == DecisionOp.IF:
                lines.append(f"{inst.target} = IF {inst.args[0]} THEN {inst.args[1]} ELSE {inst.args[2]}")
            elif inst.op == DecisionOp.APPROVE:
                lines.append(f"{inst.target} = APPROVE IF {inst.args[0]} (reason: {inst.args[1]})")
            elif inst.op == DecisionOp.DENY:
                lines.append(f"{inst.target} = DENY IF {inst.args[0]} (reason: {inst.args[1]})")
            elif inst.op == DecisionOp.SCORE:
                lines.append(f"{inst.target} = SCORE {inst.args[0]} ({inst.args[1]})")
            else:
                lines.append(f"{inst.target} = {inst.op.value}({', '.join(map(str, inst.args))})")
        
        return "\n".join(lines)


# =============================================================================
# DECISION ENGINE - Executes logic with full trace
# =============================================================================

class DecisionEngine:
    """
    Executes decision logic with complete tracing.
    
    MORAL INTENT:
        Execution is DETERMINISTIC and TRANSPARENT.
        Every operation is recorded. Nothing is hidden.
        The trace allows perfect replay and verification.
    """
    
    def execute(
        self,
        logic: DecisionLogic,
        input_data: Dict[str, Any]
    ) -> Tuple[Any, ExecutionTrace]:
        """
        Execute decision logic on input data.
        
        Returns (result, execution_trace).
        
        GUARANTEE:
            Given the same logic and input_data, this will ALWAYS
            produce the same result and trace. Deterministic execution.
        """
        start_time = time.perf_counter()
        
        # Execution state
        variables: Dict[str, Any] = {}
        steps: List[ExecutionStep] = []
        step_number = 0
        result = None
        
        # Execute each instruction
        for inst in logic.instructions:
            step_number += 1
            operand_values = []
            
            # Resolve operands
            resolved_args = []
            for arg in inst.args:
                if isinstance(arg, str) and arg.startswith("_v"):
                    resolved_args.append(variables.get(arg))
                    operand_values.append(variables.get(arg))
                else:
                    resolved_args.append(arg)
                    operand_values.append(arg)
            
            # Execute operation
            if inst.op == DecisionOp.LOAD:
                field_name = resolved_args[0]
                value = input_data.get(field_name)
                variables[inst.target] = value
                result = value
                
            elif inst.op == DecisionOp.CONST:
                value = resolved_args[0]
                variables[inst.target] = value
                result = value
                
            elif inst.op == DecisionOp.ADD:
                result = resolved_args[0] + resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.SUB:
                result = resolved_args[0] - resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.MUL:
                result = resolved_args[0] * resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.DIV:
                if resolved_args[1] == 0:
                    result = float('inf')
                else:
                    result = resolved_args[0] / resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.EQ:
                result = resolved_args[0] == resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.LT:
                result = resolved_args[0] < resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.LE:
                result = resolved_args[0] <= resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.GT:
                result = resolved_args[0] > resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.GE:
                result = resolved_args[0] >= resolved_args[1]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.AND:
                result = bool(resolved_args[0]) and bool(resolved_args[1])
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.OR:
                result = bool(resolved_args[0]) or bool(resolved_args[1])
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.NOT:
                result = not bool(resolved_args[0])
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.IF:
                condition = bool(resolved_args[0])
                result = resolved_args[1] if condition else resolved_args[2]
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.APPROVE:
                condition = bool(resolved_args[0])
                reason = resolved_args[1]
                result = {"decision": "APPROVED" if condition else "PENDING", "reason": reason}
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.DENY:
                condition = bool(resolved_args[0])
                reason = resolved_args[1]
                result = {"decision": "DENIED" if condition else "PENDING", "reason": reason}
                variables[inst.target] = result
                
            elif inst.op == DecisionOp.SCORE:
                score_value = resolved_args[0]
                explanation = resolved_args[1]
                result = {"score": score_value, "explanation": explanation}
                variables[inst.target] = result
            
            # Record step
            steps.append(ExecutionStep(
                step_number=step_number,
                operation=inst.op.value,
                operands=tuple(operand_values),
                result=result
            ))
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        # Create trace
        trace = ExecutionTrace(
            input_hash=hashlib.sha256(
                json.dumps(input_data, sort_keys=True).encode()
            ).hexdigest(),
            steps=steps,
            final_result=result,
            execution_time_ms=execution_time
        )
        
        return result, trace


# =============================================================================
# WITNESS PROTOCOL - The complete verification system
# =============================================================================

class WitnessProtocol:
    """
    The complete WITNESS protocol for verifiable decisions.
    
    ROLES:
        - Decision Maker: Commits to logic, executes, reveals
        - Subject: Receives decision, can verify
        - Verifier: Anyone who can check the math
    
    FLOW:
        1. Decision Maker creates and commits to logic
        2. Subject provides their data
        3. Decision Maker executes, produces decision + trace
        4. Subject (or anyone) can verify the decision
    
    GUARANTEES:
        - If verification passes: The committed logic produced the claimed result
        - If verification fails: Fraud is detected
    """
    
    def __init__(self, decision_maker_id: str):
        self.decision_maker_id = decision_maker_id
        self._commitments: Dict[str, Tuple[Commitment, DecisionLogic, str]] = {}
        self._engine = DecisionEngine()
    
    # === DECISION MAKER OPERATIONS ===
    
    def commit(self, logic: DecisionLogic, purpose: str) -> Commitment:
        """
        Commit to decision logic BEFORE seeing subject data.
        
        MORAL INTENT:
            Once committed, the logic is locked.
            Changing it after seeing data would break the commitment.
            This prevents post-hoc justification.
        
        Returns the commitment that should be published/shared.
        """
        # Generate random salt
        salt = secrets.token_hex(32)
        
        # Compute commitment hash
        logic_source = logic.to_source()
        commitment_input = logic_source + salt
        commitment_hash = hashlib.sha256(commitment_input.encode()).hexdigest()
        
        # Create commitment
        commitment = Commitment(
            commitment_hash=commitment_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision_maker_id=self.decision_maker_id,
            purpose=purpose,
            version=logic.version
        )
        
        # Store for later revelation
        self._commitments[commitment_hash] = (commitment, logic, salt)
        
        return commitment
    
    def decide(
        self,
        commitment: Commitment,
        input_data: Dict[str, Any]
    ) -> Decision:
        """
        Execute committed logic on subject data.
        
        MORAL INTENT:
            This produces everything needed for verification:
            - The original commitment
            - The revealed logic
            - The execution trace
            - The result
            
            The subject receives complete evidence.
        """
        # Retrieve committed logic
        if commitment.commitment_hash not in self._commitments:
            raise ValueError("Unknown commitment")
        
        stored_commitment, logic, salt = self._commitments[commitment.commitment_hash]
        
        # Execute with tracing
        result, trace = self._engine.execute(logic, input_data)
        
        # Generate explanation
        explanation = self._generate_explanation(logic, trace)
        
        return Decision(
            commitment=commitment,
            revealed_logic=logic.to_source(),
            salt=salt,
            input_data=input_data,
            trace=trace,
            result=result,
            explanation=explanation
        )
    
    def _generate_explanation(
        self,
        logic: DecisionLogic,
        trace: ExecutionTrace
    ) -> str:
        """Generate human-readable explanation of the decision."""
        lines = [
            f"Decision made using: {logic.name} v{logic.version}",
            f"Total steps: {len(trace.steps)}",
            "",
            "Key computations:"
        ]
        
        # Highlight important steps
        for step in trace.steps:
            if step.operation in ["APPROVE", "DENY", "SCORE"]:
                lines.append(f"  → {step.operation}: {step.result}")
        
        return "\n".join(lines)
    
    # === VERIFICATION OPERATIONS ===
    
    @staticmethod
    def verify(decision: Decision) -> Tuple[VerificationResult, str]:
        """
        Verify a decision is valid.
        
        This can be called by ANYONE - the subject, a regulator, a journalist.
        
        CHECKS:
            1. Commitment matches: hash(revealed_logic + salt) == commitment_hash
            2. Replay matches: executing logic on data produces same result
        
        MORAL INTENT:
            Trust is replaced by verification.
            "The algorithm decided" becomes a falsifiable claim.
        """
        # Check 1: Commitment matches revealed logic
        logic_source = decision.revealed_logic
        commitment_input = logic_source + decision.salt
        computed_hash = hashlib.sha256(commitment_input.encode()).hexdigest()
        
        if computed_hash != decision.commitment.commitment_hash:
            return (
                VerificationResult.COMMITMENT_MISMATCH,
                f"Commitment mismatch: computed {computed_hash[:16]}... != stored {decision.commitment.commitment_hash[:16]}..."
            )
        
        # Check 2: Replay produces same result
        logic = DecisionLogic.from_source(decision.revealed_logic)
        engine = DecisionEngine()
        
        try:
            replay_result, replay_trace = engine.execute(logic, decision.input_data)
        except Exception as e:
            return (
                VerificationResult.EXECUTION_ERROR,
                f"Replay failed: {e}"
            )
        
        # Compare results
        if replay_result != decision.result:
            return (
                VerificationResult.REPLAY_MISMATCH,
                f"Replay mismatch: got {replay_result}, expected {decision.result}"
            )
        
        # Compare traces
        if len(replay_trace.steps) != len(decision.trace.steps):
            return (
                VerificationResult.INVALID_TRACE,
                f"Trace length mismatch: {len(replay_trace.steps)} vs {len(decision.trace.steps)}"
            )
        
        for i, (replay_step, original_step) in enumerate(
            zip(replay_trace.steps, decision.trace.steps)
        ):
            if replay_step.result != original_step.result:
                return (
                    VerificationResult.REPLAY_MISMATCH,
                    f"Step {i} mismatch: got {replay_step.result}, expected {original_step.result}"
                )
        
        return (VerificationResult.VALID, "Decision verified successfully")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Core types
    'Commitment', 'Decision', 'ExecutionTrace', 'ExecutionStep',
    'VerificationResult',
    
    # Logic DSL
    'DecisionLogic', 'DecisionOp', 'Instruction',
    
    # Engine
    'DecisionEngine',
    
    # Protocol
    'WitnessProtocol',
]


# =============================================================================
# DEMONSTRATION
# =============================================================================

def demo():
    """Demonstrate the WITNESS protocol."""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  WITNESS: Verifiable Decision Commitment Protocol                             ║
║                                                                               ║
║  "If you won't let me verify your decision, you're not making a decision —   ║
║   you're exercising arbitrary power with plausible deniability."              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # =========================================================================
    # SCENARIO: Loan Application
    # =========================================================================
    print("=" * 70)
    print("SCENARIO: Loan Approval Decision")
    print("=" * 70)
    print("""
    BEFORE WITNESS:
        Bank: "Our algorithm denied your loan."
        You: "Why?"
        Bank: "Proprietary. Trust us, it's fair."
        You: "Can I verify it used my correct data?"
        Bank: "No."
        You: "Can I see the criteria?"
        Bank: "Trade secret."
        
    AFTER WITNESS:
        Bank: "Our algorithm denied your loan. Here's the commitment,
              the logic, and the execution trace."
        You: *verifies* "The logic says income must be > 3x debt.
             My income is $50k, debt is $20k. That's 2.5x. The denial is valid."
             
        OR
        
        You: *verifies* "FRAUD DETECTED: The revealed logic doesn't match
             the commitment hash. They changed the rules after seeing my data."
    """)
    
    # =========================================================================
    # Step 1: Bank creates and commits to decision logic
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 1: DECISION MAKER COMMITS TO LOGIC (before seeing applicant data)")
    print("-" * 70)
    
    # Create the decision logic
    logic = DecisionLogic("LoanApproval", "1.0")
    
    # Load applicant data
    income = logic.load("annual_income")
    debt = logic.load("total_debt")
    credit_score = logic.load("credit_score")
    
    # Define thresholds
    min_credit = logic.const(650)
    debt_ratio_threshold = logic.const(3.0)
    
    # Compute debt-to-income ratio
    debt_ratio = logic.div(income, debt)
    
    # Check conditions
    good_credit = logic.ge(credit_score, min_credit)
    good_debt_ratio = logic.ge(debt_ratio, debt_ratio_threshold)
    
    # Combined approval condition
    approved = logic.and_(good_credit, good_debt_ratio)
    
    # Final decision
    logic.approve(approved, "Meets credit and debt-to-income requirements")
    logic.deny(logic.not_(approved), "Does not meet minimum requirements")
    
    print("\n📜 DECISION LOGIC (human-readable):")
    print(logic.human_readable())
    
    # Create commitment
    protocol = WitnessProtocol("ACME_BANK")
    commitment = protocol.commit(logic, "loan_approval")
    
    print(f"\n🔒 COMMITMENT PUBLISHED:")
    print(f"   Hash: {commitment.commitment_hash[:32]}...")
    print(f"   Timestamp: {commitment.timestamp}")
    print(f"   Purpose: {commitment.purpose}")
    print("\n   (This commitment is published BEFORE the bank sees applicant data)")
    
    # =========================================================================
    # Step 2: Applicant provides data, bank makes decision
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 2: APPLICANT PROVIDES DATA, DECISION IS MADE")
    print("-" * 70)
    
    applicant_data = {
        "annual_income": 50000,
        "total_debt": 20000,
        "credit_score": 680,
    }
    
    print(f"\n👤 APPLICANT DATA:")
    for key, value in applicant_data.items():
        print(f"   {key}: {value}")
    
    # Make decision
    decision = protocol.decide(commitment, applicant_data)
    
    print(f"\n📋 DECISION:")
    print(f"   Result: {decision.result}")
    print(f"   Explanation: {decision.explanation}")
    
    # =========================================================================
    # Step 3: Applicant verifies the decision
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 3: APPLICANT VERIFIES THE DECISION")
    print("-" * 70)
    
    print("\n🔍 VERIFICATION (can be done by anyone):")
    
    result, message = WitnessProtocol.verify(decision)
    
    print(f"\n   Result: {result.name}")
    print(f"   Message: {message}")
    
    if result == VerificationResult.VALID:
        print("\n   ✅ The decision is VALID:")
        print("      - Committed logic matches revealed logic")
        print("      - Replay produces identical result")
        print("      - The bank cannot have lied about what algorithm was used")
    
    # =========================================================================
    # Step 4: Demonstrate fraud detection
    # =========================================================================
    print("\n" + "-" * 70)
    print("STEP 4: FRAUD DETECTION DEMONSTRATION")
    print("-" * 70)
    
    print("\n🚨 SIMULATING FRAUD: Bank tries to change logic after commitment...")
    
    # Create a different logic (more restrictive)
    fraud_logic = DecisionLogic("LoanApproval", "1.0")
    income_f = fraud_logic.load("annual_income")
    debt_f = fraud_logic.load("total_debt")
    credit_f = fraud_logic.load("credit_score")
    min_credit_f = fraud_logic.const(700)  # CHANGED: higher threshold
    debt_ratio_f = fraud_logic.const(4.0)  # CHANGED: stricter ratio
    ratio_f = fraud_logic.div(income_f, debt_f)
    good_credit_f = fraud_logic.ge(credit_f, min_credit_f)
    good_ratio_f = fraud_logic.ge(ratio_f, debt_ratio_f)
    approved_f = fraud_logic.and_(good_credit_f, good_ratio_f)
    fraud_logic.deny(fraud_logic.not_(approved_f), "Does not meet requirements")
    
    # Create fraudulent decision with wrong logic but same commitment
    engine = DecisionEngine()
    fraud_result, fraud_trace = engine.execute(fraud_logic, applicant_data)
    
    fraud_decision = Decision(
        commitment=commitment,  # Uses original commitment
        revealed_logic=fraud_logic.to_source(),  # But different logic!
        salt=decision.salt,
        input_data=applicant_data,
        trace=fraud_trace,
        result=fraud_result,
        explanation="Fraudulent decision"
    )
    
    print("\n   Fraudulent decision claims: DENIED (using stricter rules)")
    print("   But let's verify against the original commitment...")
    
    fraud_result, fraud_message = WitnessProtocol.verify(fraud_decision)
    
    print(f"\n   Verification Result: {fraud_result.name}")
    print(f"   Message: {fraud_message}")
    print("\n   ❌ FRAUD DETECTED! The revealed logic doesn't match the commitment.")
    print("      The bank CANNOT claim this denial came from the committed algorithm.")
    
    # =========================================================================
    # Summary: What Changed
    # =========================================================================
    print("\n" + "=" * 70)
    print("WHAT WITNESS CHANGES")
    print("=" * 70)
    print("""
    BEFORE WITNESS:
        ┌─────────────────┐
        │  DECISION MAKER │ "Trust me, the algorithm is fair"
        └────────┬────────┘
                 │ (opaque)
                 ▼
        ┌─────────────────┐
        │    SUBJECT      │ "I have no way to verify"
        └─────────────────┘
    
    AFTER WITNESS:
        ┌─────────────────┐
        │  DECISION MAKER │ Commits to logic BEFORE seeing data
        └────────┬────────┘
                 │ (commitment published)
                 ▼
        ┌─────────────────┐
        │    SUBJECT      │ Provides data
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  DECISION MAKER │ Executes, reveals logic + trace
        └────────┬────────┘
                 │ (evidence provided)
                 ▼
        ┌─────────────────┐
        │ ANYONE (subject,│ VERIFIES: commitment matches?
        │ regulator, etc.)│ VERIFIES: replay matches?
        └─────────────────┘
    
    WHO MUST BE TRUSTED LESS:
        Decision makers. Their claims are now falsifiable.
    
    WHO GAINS AGENCY:
        Anyone subject to algorithmic decisions. They can audit.
    
    WHAT CAN NOW BE VERIFIED:
        That the stated logic produced the stated result on the stated data.
        
    WHAT THIS DOES NOT DO:
        Guarantee the logic is fair. That's a human judgment.
        But you can't make that judgment without seeing the logic.
        WITNESS provides the evidence. You provide the judgment.
    """)


if __name__ == "__main__":
    demo()
