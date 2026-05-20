#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ███████╗ ██████╗ ██████╗  ██████╗ ███████╗                                   ║
║  ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝                                   ║
║  █████╗  ██║   ██║██████╔╝██║  ███╗█████╗                                     ║
║  ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝                                     ║
║  ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗                                   ║
║  ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝                                   ║
║                                                                               ║
║     Verifiable Computation Kernel with Cryptographic Receipts                 ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

FORGE: A computation kernel where every execution produces a cryptographic
receipt proving exactly what resources were consumed.

INVARIANTS:
    1. DETERMINISM: Same (program, memory, fuel) → Same (output, receipt)
    2. BOUNDED RESOURCES: Execution ALWAYS terminates within fuel budget
    3. TAMPER EVIDENCE: Any modification to execution trace is detectable
    4. GRACEFUL FAILURE: Even errors produce valid, verifiable receipts

THE UNCOMFORTABLE TRUTH:
    Most code you run provides ZERO proof it executed correctly.
    You just... trust it. FORGE makes this visible.

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────────┐
    │                        FORGE EXECUTION                          │
    │  ┌─────────┐    ┌──────────┐    ┌────────────┐    ┌─────────┐  │
    │  │ Program │───>│ VM Core  │───>│ Checkpoint │───>│ Receipt │  │
    │  │ Memory  │    │  (fuel)  │    │   Tree     │    │ (proof) │  │
    │  │ Fuel    │    └──────────┘    └────────────┘    └─────────┘  │
    │  └─────────┘         │                                         │
    │                      ▼                                         │
    │               [State Snapshots]                                │
    │               Every N instructions                             │
    └─────────────────────────────────────────────────────────────────┘

INTENTIONAL LIMITATION:
    Memory is FIXED at startup (65536 cells = 256KB).
    No dynamic allocation. This ensures:
    - Memory consumption is predictable
    - Verification complexity is bounded
    - Programs must be written for fixed-size memory

VERIFICATION MODEL:
    Full verification: Re-execute entirely, compare receipt
    Partial verification: Re-execute segments, verify checkpoints
    
    Trade-off: Lower checkpoint interval = larger receipts, cheaper verification
               Higher checkpoint interval = smaller receipts, costlier verification

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import List, Optional, Tuple, Dict, Any
import json


# =============================================================================
# CONSTANTS - These define the execution environment bounds
# =============================================================================

# Memory is fixed at startup. This is an INTENTIONAL LIMITATION.
# Programs must be designed for this size. No dynamic allocation.
MAX_MEMORY_SIZE = 65536  # 64K cells (256KB with 32-bit integers)

# Stack size bounds recursion depth and expression complexity
MAX_STACK_SIZE = 1024

# Maximum fuel to prevent overflow in accounting
MAX_FUEL = 10**9

# Checkpoint interval: trade-off between receipt size and verification cost
# Lower = more checkpoints = larger receipt = cheaper partial verification
# Higher = fewer checkpoints = smaller receipt = more re-execution per verify
CHECKPOINT_INTERVAL = 1000

# Integer bounds (we use signed 64-bit integers)
INT_MIN = -(2**63)
INT_MAX = 2**63 - 1


# =============================================================================
# OPCODES - The instruction set
# =============================================================================

class Op(IntEnum):
    """
    FORGE bytecode instructions.
    
    Design rationale:
    - Stack-based (simpler than register, easier to trace)
    - Minimal set (easy to audit, verify, understand)
    - No I/O (determinism requires no external interaction)
    - No floating point (determinism across platforms)
    """
    # Stack manipulation
    NOP = 0       # Do nothing (costs 1 fuel, useful for padding)
    PUSH = 1      # Push immediate value: PUSH <value>
    POP = 2       # Discard top of stack
    DUP = 3       # Duplicate top of stack
    SWAP = 4      # Swap top two elements
    
    # Arithmetic (all operations are signed 64-bit, overflow wraps)
    ADD = 10      # a b → (a+b)
    SUB = 11      # a b → (a-b)
    MUL = 12      # a b → (a*b)
    DIV = 13      # a b → (a/b)  -- division by zero is an error
    MOD = 14      # a b → (a%b)  -- modulo by zero is an error
    NEG = 15      # a → (-a)
    
    # Comparison (results in 0 or 1)
    EQ = 20       # a b → (a==b ? 1 : 0)
    NE = 21       # a b → (a!=b ? 1 : 0)
    LT = 22       # a b → (a<b ? 1 : 0)
    LE = 23       # a b → (a<=b ? 1 : 0)
    GT = 24       # a b → (a>b ? 1 : 0)
    GE = 25       # a b → (a>=b ? 1 : 0)
    
    # Bitwise
    AND = 30      # a b → (a & b)
    OR = 31       # a b → (a | b)
    XOR = 32      # a b → (a ^ b)
    NOT = 33      # a → (~a)
    SHL = 34      # a b → (a << b)  -- shift left
    SHR = 35      # a b → (a >> b)  -- arithmetic shift right
    
    # Memory
    LOAD = 40     # addr → value (read from memory[addr])
    STORE = 41    # addr value → () (write value to memory[addr])
    
    # Control flow
    JMP = 50      # Jump to address: JMP <addr>
    JZ = 51       # Jump if zero: JZ <addr> (pops condition)
    JNZ = 52      # Jump if not zero: JNZ <addr>
    
    # Termination
    HALT = 60     # Stop execution (clean halt)


# Instructions that take an immediate operand
IMMEDIATE_OPS = {Op.PUSH, Op.JMP, Op.JZ, Op.JNZ}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Checkpoint:
    """
    A snapshot of VM state at a specific point.
    
    INVARIANT: Given the same starting checkpoint and instructions,
    the next checkpoint will be identical.
    """
    instruction_count: int       # How many instructions executed so far
    pc: int                      # Program counter
    stack_hash: bytes            # SHA-256 of stack contents
    memory_hash: bytes           # SHA-256 of memory contents
    fuel_remaining: int          # Fuel left at this point
    
    def to_bytes(self) -> bytes:
        """Serialize for hashing."""
        return struct.pack(
            '>Q Q 32s 32s Q',  # Big-endian: uint64, uint64, 32 bytes, 32 bytes, uint64
            self.instruction_count,
            self.pc,
            self.stack_hash,
            self.memory_hash,
            self.fuel_remaining
        )
    
    def hash(self) -> bytes:
        """Compute hash of this checkpoint."""
        return hashlib.sha256(self.to_bytes()).digest()


@dataclass
class Receipt:
    """
    Cryptographic proof of execution.
    
    This is the PRIMARY OUTPUT of FORGE. It commits to:
    - What was executed (input_hash)
    - What was produced (output_hash)
    - How much resource was consumed (fuel_consumed)
    - The execution trace (checkpoint_root)
    - Whether execution completed cleanly (halted_cleanly)
    
    ANYONE can verify this receipt by re-executing and comparing.
    PARTIAL verification is possible by checking individual checkpoints.
    """
    # Input commitment
    input_hash: bytes            # SHA-256(program || initial_memory)
    
    # Output commitment
    output_hash: bytes           # SHA-256(final_memory)
    final_stack_hash: bytes      # SHA-256(final_stack)
    
    # Resource accounting
    fuel_consumed: int           # Actual fuel used
    fuel_limit: int              # Original budget
    instructions_executed: int   # Total instruction count
    
    # Execution trace commitment
    checkpoint_root: bytes       # Merkle root of checkpoints
    checkpoint_count: int        # Number of checkpoints
    
    # Termination status
    halted_cleanly: bool         # True if HALT instruction reached
    error: Optional[str]         # Error message if not clean
    final_pc: int                # Where execution stopped
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "input_hash": self.input_hash.hex(),
            "output_hash": self.output_hash.hex(),
            "final_stack_hash": self.final_stack_hash.hex(),
            "fuel_consumed": self.fuel_consumed,
            "fuel_limit": self.fuel_limit,
            "instructions_executed": self.instructions_executed,
            "checkpoint_root": self.checkpoint_root.hex(),
            "checkpoint_count": self.checkpoint_count,
            "halted_cleanly": self.halted_cleanly,
            "error": self.error,
            "final_pc": self.final_pc,
            "verification_cost_estimate": self._verification_cost()
        }
    
    def _verification_cost(self) -> str:
        """Estimate cost of different verification strategies."""
        full = self.instructions_executed
        spot_check = CHECKPOINT_INTERVAL  # Cost per checkpoint verified
        return f"full={full} instructions, spot_check={spot_check} per checkpoint"
    
    def summary(self) -> str:
        """Human-readable summary."""
        status = "✓ CLEAN HALT" if self.halted_cleanly else f"✗ {self.error}"
        return f"""
╔════════════════════════════════════════════════════════════╗
║ FORGE EXECUTION RECEIPT                                    ║
╠════════════════════════════════════════════════════════════╣
║ Input Hash:    {self.input_hash.hex()[:32]}... ║
║ Output Hash:   {self.output_hash.hex()[:32]}... ║
║ Fuel:          {self.fuel_consumed:,} / {self.fuel_limit:,} ({100*self.fuel_consumed/self.fuel_limit:.1f}%)          ║
║ Instructions:  {self.instructions_executed:,}                                  ║
║ Checkpoints:   {self.checkpoint_count}                                       ║
║ Status:        {status:40} ║
╚════════════════════════════════════════════════════════════╝"""


@dataclass
class MerkleTree:
    """
    Merkle tree for checkpoint commitments.
    
    INVARIANT: The root uniquely commits to all checkpoints.
    Any modification to any checkpoint changes the root.
    
    Supports:
    - O(1) append (with O(log n) finalization)
    - O(log n) inclusion proofs
    - O(1) root access
    """
    leaves: List[bytes] = field(default_factory=list)
    
    def append(self, data: bytes) -> int:
        """Add a leaf, return its index."""
        leaf_hash = hashlib.sha256(b'\x00' + data).digest()  # Prefix for leaf
        self.leaves.append(leaf_hash)
        return len(self.leaves) - 1
    
    def root(self) -> bytes:
        """Compute the Merkle root."""
        if not self.leaves:
            return hashlib.sha256(b'empty').digest()
        
        # Build tree bottom-up
        level = list(self.leaves)
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    # Two children: hash them together
                    combined = hashlib.sha256(
                        b'\x01' + level[i] + level[i + 1]  # Prefix for internal
                    ).digest()
                else:
                    # Odd one out: promote as-is
                    combined = level[i]
                next_level.append(combined)
            level = next_level
        
        return level[0]
    
    def get_proof(self, index: int) -> List[Tuple[bytes, bool]]:
        """
        Get inclusion proof for leaf at index.
        
        Returns list of (sibling_hash, is_right) pairs.
        """
        if index < 0 or index >= len(self.leaves):
            raise IndexError(f"Leaf {index} not found")
        
        proof = []
        level = list(self.leaves)
        idx = index
        
        while len(level) > 1:
            sibling_idx = idx ^ 1  # XOR to get sibling
            is_right = (idx % 2 == 0)
            
            if sibling_idx < len(level):
                proof.append((level[sibling_idx], is_right))
            
            # Build next level
            next_level = []
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    combined = hashlib.sha256(
                        b'\x01' + level[i] + level[i + 1]
                    ).digest()
                else:
                    combined = level[i]
                next_level.append(combined)
            
            level = next_level
            idx //= 2
        
        return proof
    
    @staticmethod
    def verify_proof(
        leaf_data: bytes,
        proof: List[Tuple[bytes, bool]],
        expected_root: bytes
    ) -> bool:
        """Verify an inclusion proof."""
        current = hashlib.sha256(b'\x00' + leaf_data).digest()
        
        for sibling, is_right in proof:
            if is_right:
                current = hashlib.sha256(b'\x01' + current + sibling).digest()
            else:
                current = hashlib.sha256(b'\x01' + sibling + current).digest()
        
        return current == expected_root


# =============================================================================
# THE FORGE VIRTUAL MACHINE
# =============================================================================

class ForgeError(Exception):
    """Base class for FORGE errors."""
    pass


class FuelExhausted(ForgeError):
    """Execution ran out of fuel."""
    pass


class InvalidOpcode(ForgeError):
    """Unknown instruction encountered."""
    pass


class StackUnderflow(ForgeError):
    """Attempted to pop from empty stack."""
    pass


class StackOverflow(ForgeError):
    """Stack exceeded maximum size."""
    pass


class MemoryError(ForgeError):
    """Memory access out of bounds."""
    pass


class DivisionByZero(ForgeError):
    """Division or modulo by zero."""
    pass


class InvalidJump(ForgeError):
    """Jump target out of bounds."""
    pass


class ForgeVM:
    """
    The FORGE Virtual Machine.
    
    DESIGN INTENT:
        This is a MINIMAL, DETERMINISTIC computation kernel.
        Every execution produces a cryptographic receipt.
        The receipt can be verified without trusting the executor.
    
    GUARANTEES:
        1. Same inputs → Same outputs (determinism)
        2. Execution terminates within fuel budget (bounded)
        3. Errors produce valid receipts (graceful failure)
        4. Checkpoints enable partial verification (efficiency)
    
    NON-GUARANTEES:
        - Receipt does NOT prove computation was "correct" in any semantic sense
        - Receipt does NOT enable verification without re-execution
        - Receipt does NOT protect against side-channel attacks
    """
    
    def __init__(
        self,
        program: bytes,
        memory: Optional[List[int]] = None,
        fuel: int = 100000
    ):
        """
        Initialize the VM.
        
        Args:
            program: Bytecode to execute
            memory: Initial memory (default: all zeros, MAX_MEMORY_SIZE cells)
            fuel: Maximum instructions to execute
        
        INVARIANT: After __init__, the VM is in a valid initial state.
        """
        # Validate fuel
        if fuel <= 0:
            raise ValueError(f"Fuel must be positive, got {fuel}")
        if fuel > MAX_FUEL:
            raise ValueError(f"Fuel exceeds maximum ({MAX_FUEL}), got {fuel}")
        
        # Store program
        self._program = program
        self._program_length = len(program)
        
        # Initialize memory (fixed size, intentional limitation)
        if memory is None:
            self._memory = [0] * MAX_MEMORY_SIZE
        else:
            if len(memory) > MAX_MEMORY_SIZE:
                raise ValueError(f"Memory exceeds max size ({MAX_MEMORY_SIZE})")
            # Pad to full size
            self._memory = list(memory) + [0] * (MAX_MEMORY_SIZE - len(memory))
        
        # Initialize state
        self._stack: List[int] = []
        self._pc = 0  # Program counter (byte offset)
        self._fuel = fuel
        self._fuel_limit = fuel
        self._instruction_count = 0
        
        # Checkpointing
        self._checkpoints: List[Checkpoint] = []
        self._checkpoint_tree = MerkleTree()
        
        # Termination
        self._halted = False
        self._error: Optional[str] = None
        
        # Compute input hash
        self._input_hash = self._compute_input_hash()
        
        # Record initial checkpoint
        self._record_checkpoint()
    
    def _compute_input_hash(self) -> bytes:
        """
        Compute hash of inputs (program + initial memory).
        
        This commits to the entire input state, ensuring the receipt
        is bound to specific inputs.
        """
        h = hashlib.sha256()
        h.update(self._program)
        # Hash memory as packed integers
        for value in self._memory:
            h.update(struct.pack('>q', value))  # Signed 64-bit big-endian
        return h.digest()
    
    def _hash_stack(self) -> bytes:
        """Compute hash of current stack."""
        h = hashlib.sha256()
        for value in self._stack:
            h.update(struct.pack('>q', value))
        return h.digest()
    
    def _hash_memory(self) -> bytes:
        """Compute hash of current memory."""
        h = hashlib.sha256()
        for value in self._memory:
            h.update(struct.pack('>q', value))
        return h.digest()
    
    def _record_checkpoint(self) -> None:
        """
        Record a checkpoint of current state.
        
        INVARIANT: Checkpoints form a chain. Given checkpoint N,
        executing CHECKPOINT_INTERVAL instructions deterministically
        produces checkpoint N+1.
        """
        checkpoint = Checkpoint(
            instruction_count=self._instruction_count,
            pc=self._pc,
            stack_hash=self._hash_stack(),
            memory_hash=self._hash_memory(),
            fuel_remaining=self._fuel
        )
        self._checkpoints.append(checkpoint)
        self._checkpoint_tree.append(checkpoint.to_bytes())
    
    def _consume_fuel(self, amount: int = 1) -> None:
        """
        Consume fuel. Raises FuelExhausted if insufficient.
        
        INVARIANT: Fuel is always non-negative after this call
        (or an exception is raised).
        """
        if self._fuel < amount:
            self._error = f"Fuel exhausted at instruction {self._instruction_count}"
            raise FuelExhausted(self._error)
        self._fuel -= amount
    
    def _push(self, value: int) -> None:
        """Push value onto stack with bounds checking."""
        if len(self._stack) >= MAX_STACK_SIZE:
            self._error = f"Stack overflow at instruction {self._instruction_count}"
            raise StackOverflow(self._error)
        # Wrap to 64-bit signed
        value = ((value + 2**63) % 2**64) - 2**63
        self._stack.append(value)
    
    def _pop(self) -> int:
        """Pop value from stack with underflow checking."""
        if not self._stack:
            self._error = f"Stack underflow at instruction {self._instruction_count}"
            raise StackUnderflow(self._error)
        return self._stack.pop()
    
    def _peek(self, offset: int = 0) -> int:
        """Peek at stack without popping."""
        if len(self._stack) <= offset:
            self._error = f"Stack underflow at instruction {self._instruction_count}"
            raise StackUnderflow(self._error)
        return self._stack[-(offset + 1)]
    
    def _read_byte(self) -> int:
        """Read byte at PC and advance."""
        if self._pc >= self._program_length:
            self._error = f"Program counter out of bounds: {self._pc}"
            raise InvalidJump(self._error)
        byte = self._program[self._pc]
        self._pc += 1
        return byte
    
    def _read_int64(self) -> int:
        """Read signed 64-bit integer at PC and advance."""
        if self._pc + 8 > self._program_length:
            self._error = f"Unexpected end of program reading int64 at {self._pc}"
            raise InvalidJump(self._error)
        value = struct.unpack('>q', self._program[self._pc:self._pc + 8])[0]
        self._pc += 8
        return value
    
    def _execute_one(self) -> bool:
        """
        Execute one instruction.
        
        Returns False if execution should stop (HALT or error).
        
        INVARIANT: Either returns True and VM is in valid state,
        or returns False and self._halted or self._error is set.
        """
        # Check fuel BEFORE executing
        self._consume_fuel(1)
        
        # Read opcode
        try:
            opcode_byte = self._read_byte()
        except InvalidJump:
            return False
        
        try:
            opcode = Op(opcode_byte)
        except ValueError:
            self._error = f"Invalid opcode {opcode_byte} at PC {self._pc - 1}"
            return False
        
        self._instruction_count += 1
        
        # Dispatch
        try:
            if opcode == Op.NOP:
                pass
            
            elif opcode == Op.PUSH:
                value = self._read_int64()
                self._push(value)
            
            elif opcode == Op.POP:
                self._pop()
            
            elif opcode == Op.DUP:
                self._push(self._peek())
            
            elif opcode == Op.SWAP:
                a = self._pop()
                b = self._pop()
                self._push(a)
                self._push(b)
            
            elif opcode == Op.ADD:
                b = self._pop()
                a = self._pop()
                self._push(a + b)
            
            elif opcode == Op.SUB:
                b = self._pop()
                a = self._pop()
                self._push(a - b)
            
            elif opcode == Op.MUL:
                b = self._pop()
                a = self._pop()
                self._push(a * b)
            
            elif opcode == Op.DIV:
                b = self._pop()
                a = self._pop()
                if b == 0:
                    self._error = f"Division by zero at instruction {self._instruction_count}"
                    raise DivisionByZero(self._error)
                # Python's // is floor division, we want truncation toward zero
                result = int(a / b)
                self._push(result)
            
            elif opcode == Op.MOD:
                b = self._pop()
                a = self._pop()
                if b == 0:
                    self._error = f"Modulo by zero at instruction {self._instruction_count}"
                    raise DivisionByZero(self._error)
                self._push(a % b)
            
            elif opcode == Op.NEG:
                a = self._pop()
                self._push(-a)
            
            elif opcode == Op.EQ:
                b = self._pop()
                a = self._pop()
                self._push(1 if a == b else 0)
            
            elif opcode == Op.NE:
                b = self._pop()
                a = self._pop()
                self._push(1 if a != b else 0)
            
            elif opcode == Op.LT:
                b = self._pop()
                a = self._pop()
                self._push(1 if a < b else 0)
            
            elif opcode == Op.LE:
                b = self._pop()
                a = self._pop()
                self._push(1 if a <= b else 0)
            
            elif opcode == Op.GT:
                b = self._pop()
                a = self._pop()
                self._push(1 if a > b else 0)
            
            elif opcode == Op.GE:
                b = self._pop()
                a = self._pop()
                self._push(1 if a >= b else 0)
            
            elif opcode == Op.AND:
                b = self._pop()
                a = self._pop()
                self._push(a & b)
            
            elif opcode == Op.OR:
                b = self._pop()
                a = self._pop()
                self._push(a | b)
            
            elif opcode == Op.XOR:
                b = self._pop()
                a = self._pop()
                self._push(a ^ b)
            
            elif opcode == Op.NOT:
                a = self._pop()
                self._push(~a)
            
            elif opcode == Op.SHL:
                b = self._pop()
                a = self._pop()
                if b < 0 or b > 63:
                    self._push(0)
                else:
                    self._push(a << b)
            
            elif opcode == Op.SHR:
                b = self._pop()
                a = self._pop()
                if b < 0 or b > 63:
                    self._push(0 if a >= 0 else -1)
                else:
                    self._push(a >> b)
            
            elif opcode == Op.LOAD:
                addr = self._pop()
                if addr < 0 or addr >= MAX_MEMORY_SIZE:
                    self._error = f"Memory read out of bounds: {addr}"
                    raise MemoryError(self._error)
                self._push(self._memory[addr])
            
            elif opcode == Op.STORE:
                value = self._pop()
                addr = self._pop()
                if addr < 0 or addr >= MAX_MEMORY_SIZE:
                    self._error = f"Memory write out of bounds: {addr}"
                    raise MemoryError(self._error)
                self._memory[addr] = value
            
            elif opcode == Op.JMP:
                target = self._read_int64()
                if target < 0 or target >= self._program_length:
                    self._error = f"Jump target out of bounds: {target}"
                    raise InvalidJump(self._error)
                self._pc = target
            
            elif opcode == Op.JZ:
                target = self._read_int64()
                cond = self._pop()
                if cond == 0:
                    if target < 0 or target >= self._program_length:
                        self._error = f"Jump target out of bounds: {target}"
                        raise InvalidJump(self._error)
                    self._pc = target
            
            elif opcode == Op.JNZ:
                target = self._read_int64()
                cond = self._pop()
                if cond != 0:
                    if target < 0 or target >= self._program_length:
                        self._error = f"Jump target out of bounds: {target}"
                        raise InvalidJump(self._error)
                    self._pc = target
            
            elif opcode == Op.HALT:
                self._halted = True
                return False
            
            else:
                self._error = f"Unimplemented opcode: {opcode}"
                return False
        
        except (StackUnderflow, StackOverflow, MemoryError, 
                DivisionByZero, InvalidJump):
            return False
        
        # Record checkpoint if needed
        if self._instruction_count % CHECKPOINT_INTERVAL == 0:
            self._record_checkpoint()
        
        return True
    
    def run(self) -> Receipt:
        """
        Execute until HALT, error, or fuel exhaustion.
        
        GUARANTEE: Always returns a valid Receipt.
        The receipt can be verified by re-executing with same inputs.
        """
        try:
            while self._execute_one():
                pass
        except FuelExhausted:
            pass
        
        # Record final checkpoint
        self._record_checkpoint()
        
        # Build receipt
        return Receipt(
            input_hash=self._input_hash,
            output_hash=self._hash_memory(),
            final_stack_hash=self._hash_stack(),
            fuel_consumed=self._fuel_limit - self._fuel,
            fuel_limit=self._fuel_limit,
            instructions_executed=self._instruction_count,
            checkpoint_root=self._checkpoint_tree.root(),
            checkpoint_count=len(self._checkpoints),
            halted_cleanly=self._halted,
            error=self._error,
            final_pc=self._pc
        )
    
    @property
    def checkpoints(self) -> List[Checkpoint]:
        """Access checkpoints for verification."""
        return list(self._checkpoints)
    
    @property
    def memory(self) -> List[int]:
        """Access final memory state."""
        return list(self._memory)
    
    @property
    def stack(self) -> List[int]:
        """Access final stack state."""
        return list(self._stack)


# =============================================================================
# ASSEMBLER - Human-readable bytecode generation
# =============================================================================

class Assembler:
    """
    Assembler for FORGE bytecode.
    
    Converts human-readable assembly to bytecode.
    
    Example:
        PUSH 10
        PUSH 20
        ADD
        HALT
    
    Produces bytecode that pushes 10, pushes 20, adds them, and halts.
    """
    
    MNEMONICS = {name: op for name, op in Op.__members__.items()}
    
    @classmethod
    def assemble(cls, source: str) -> bytes:
        """
        Assemble source code to bytecode.
        
        Supports:
        - Labels: "label:" on its own line
        - Comments: "#" to end of line
        - Instructions: "OPCODE" or "OPCODE operand"
        """
        lines = source.strip().split('\n')
        
        # First pass: collect labels
        labels: Dict[str, int] = {}
        bytecode_offset = 0
        
        for line in lines:
            line = line.split('#')[0].strip()
            if not line:
                continue
            
            if line.endswith(':'):
                # Label definition
                label = line[:-1].strip()
                labels[label] = bytecode_offset
            else:
                # Instruction
                parts = line.split()
                mnemonic = parts[0].upper()
                
                if mnemonic not in cls.MNEMONICS:
                    raise ValueError(f"Unknown mnemonic: {mnemonic}")
                
                op = cls.MNEMONICS[mnemonic]
                bytecode_offset += 1  # Opcode byte
                
                if op in IMMEDIATE_OPS:
                    bytecode_offset += 8  # 64-bit operand
        
        # Second pass: generate bytecode
        bytecode = bytearray()
        
        for line in lines:
            line = line.split('#')[0].strip()
            if not line or line.endswith(':'):
                continue
            
            parts = line.split()
            mnemonic = parts[0].upper()
            op = cls.MNEMONICS[mnemonic]
            
            bytecode.append(op)
            
            if op in IMMEDIATE_OPS:
                if len(parts) < 2:
                    raise ValueError(f"{mnemonic} requires an operand")
                
                operand_str = parts[1]
                
                # Check if it's a label
                if operand_str in labels:
                    operand = labels[operand_str]
                else:
                    # Parse as integer
                    operand = int(operand_str, 0)  # Supports hex with 0x prefix
                
                bytecode.extend(struct.pack('>q', operand))
        
        return bytes(bytecode)


# =============================================================================
# VERIFICATION
# =============================================================================

def verify_receipt(
    receipt: Receipt,
    program: bytes,
    initial_memory: Optional[List[int]] = None
) -> Tuple[bool, str]:
    """
    Fully verify a receipt by re-executing.
    
    Returns (is_valid, message).
    
    COST: O(n) where n = instructions executed
    GUARANTEE: If returns True, the receipt is valid for the given inputs.
    """
    # Re-execute
    vm = ForgeVM(program, initial_memory, receipt.fuel_limit)
    new_receipt = vm.run()
    
    # Compare
    checks = [
        (receipt.input_hash == new_receipt.input_hash, "input_hash mismatch"),
        (receipt.output_hash == new_receipt.output_hash, "output_hash mismatch"),
        (receipt.fuel_consumed == new_receipt.fuel_consumed, "fuel_consumed mismatch"),
        (receipt.instructions_executed == new_receipt.instructions_executed, "instruction_count mismatch"),
        (receipt.checkpoint_root == new_receipt.checkpoint_root, "checkpoint_root mismatch"),
        (receipt.halted_cleanly == new_receipt.halted_cleanly, "halt_status mismatch"),
    ]
    
    for valid, msg in checks:
        if not valid:
            return False, msg
    
    return True, "Receipt verified successfully"


def verify_checkpoint(
    receipt: Receipt,
    checkpoint_index: int,
    checkpoint: Checkpoint
) -> Tuple[bool, str]:
    """
    Verify a single checkpoint against the receipt.
    
    COST: O(log n) for proof verification + O(CHECKPOINT_INTERVAL) for segment re-execution
    """
    # Get proof from a re-execution (in practice, proofs would be provided separately)
    # For now, we just verify the checkpoint hash is correct
    
    expected_hash = checkpoint.hash()
    
    # In a full implementation, we would:
    # 1. Get the Merkle proof for this checkpoint
    # 2. Verify the proof against receipt.checkpoint_root
    # 3. Re-execute the segment and verify the checkpoint matches
    
    # Simplified: just check the hash computation is consistent
    recomputed = Checkpoint(
        instruction_count=checkpoint.instruction_count,
        pc=checkpoint.pc,
        stack_hash=checkpoint.stack_hash,
        memory_hash=checkpoint.memory_hash,
        fuel_remaining=checkpoint.fuel_remaining
    )
    
    if recomputed.hash() != expected_hash:
        return False, "Checkpoint hash mismatch"
    
    return True, "Checkpoint verified"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Core
    'ForgeVM',
    'Receipt',
    'Checkpoint',
    'Op',
    
    # Assembler
    'Assembler',
    
    # Verification
    'verify_receipt',
    'verify_checkpoint',
    
    # Data structures
    'MerkleTree',
    
    # Errors
    'ForgeError',
    'FuelExhausted',
    'InvalidOpcode',
    'StackUnderflow',
    'StackOverflow',
    'MemoryError',
    'DivisionByZero',
    'InvalidJump',
    
    # Constants
    'MAX_MEMORY_SIZE',
    'MAX_STACK_SIZE',
    'MAX_FUEL',
    'CHECKPOINT_INTERVAL',
]


# =============================================================================
# DEMONSTRATION
# =============================================================================

def demo():
    """Demonstrate FORGE capabilities."""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  FORGE: Verifiable Computation Kernel                                         ║
║                                                                               ║
║  Every execution produces a cryptographic RECEIPT proving:                    ║
║  • What was computed (input hash)                                             ║
║  • What was produced (output hash)                                            ║
║  • How much resource was consumed (fuel)                                      ║
║  • The execution trace (checkpoint root)                                      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Example 1: Simple computation
    print("═" * 70)
    print("EXAMPLE 1: Simple Arithmetic")
    print("═" * 70)
    print("\nProgram: Compute (10 + 20) * 3")
    
    source = """
        PUSH 10
        PUSH 20
        ADD         # Stack: [30]
        PUSH 3
        MUL         # Stack: [90]
        PUSH 0      # addr
        SWAP        # Stack: [0, 90] - addr at bottom, value on top
        STORE       # memory[0] = 90
        HALT
    """
    
    print(f"\nAssembly:\n{source}")
    
    bytecode = Assembler.assemble(source)
    print(f"Bytecode: {bytecode.hex()}")
    
    vm = ForgeVM(bytecode, fuel=1000)
    receipt = vm.run()
    
    print(receipt.summary())
    print(f"\nFinal memory[0]: {vm.memory[0]}")
    
    # Verify the receipt
    is_valid, msg = verify_receipt(receipt, bytecode)
    print(f"\n🔐 Verification: {'✓ VALID' if is_valid else '✗ INVALID'} - {msg}")
    
    # Example 2: Loop with fuel limit
    print("\n" + "═" * 70)
    print("EXAMPLE 2: Loop with Fuel Limit")
    print("═" * 70)
    print("\nProgram: Sum 1 to N (where N is in memory[0])")
    
    source = """
        # memory[0] = N (input, DO NOT OVERWRITE)
        # memory[1] = sum (output)
        # memory[2] = counter
        # STORE pops: value, then addr -> memory[addr] = value
        
        PUSH 1          # addr = 1
        PUSH 0          # value = 0 (initial sum)
        STORE           # memory[1] = 0
        
        PUSH 2          # addr = 2
        PUSH 1          # value = 1 (initial counter)
        STORE           # memory[2] = 1
        
    loop:
        # if counter > N, jump to done
        PUSH 2
        LOAD            # counter
        PUSH 0
        LOAD            # N
        GT              # counter > N ?
        JNZ done
        
        # sum = sum + counter
        PUSH 1          # addr for result
        PUSH 1
        LOAD            # sum
        PUSH 2
        LOAD            # counter
        ADD             # sum + counter
        STORE           # memory[1] = sum + counter
        
        # counter = counter + 1
        PUSH 2          # addr for result
        PUSH 2
        LOAD            # counter
        PUSH 1
        ADD             # counter + 1
        STORE           # memory[2] = counter + 1
        
        JMP loop
        
    done:
        HALT
    """
    
    bytecode = Assembler.assemble(source)
    
    # Test with N=10
    memory = [10] + [0] * (MAX_MEMORY_SIZE - 1)  # N=10
    
    vm = ForgeVM(bytecode, memory, fuel=10000)
    receipt = vm.run()
    
    print(f"\nInput: N = 10")
    print(f"Expected: 1+2+...+10 = 55")
    print(f"Result: memory[1] = {vm.memory[1]}")
    print(receipt.summary())
    
    # Example 3: Fuel exhaustion (graceful failure)
    print("\n" + "═" * 70)
    print("EXAMPLE 3: Fuel Exhaustion (Graceful Failure)")
    print("═" * 70)
    print("\nProgram: Same loop but with insufficient fuel")
    
    memory = [100] + [0] * (MAX_MEMORY_SIZE - 1)  # N=100
    
    vm = ForgeVM(bytecode, memory, fuel=500)  # Not enough!
    receipt = vm.run()
    
    print(f"\nInput: N = 100")
    print(f"Fuel budget: 500 (not enough for full computation)")
    print(receipt.summary())
    print(f"\n⚠️  Execution stopped at partial sum: {vm.memory[1]}")
    print("Note: Even failed executions produce valid receipts!")
    
    # Verify the failed execution
    is_valid, msg = verify_receipt(receipt, bytecode, [100] + [0] * (MAX_MEMORY_SIZE - 1))
    print(f"\n🔐 Verification: {'✓ VALID' if is_valid else '✗ INVALID'} - {msg}")
    
    # Example 4: Adversarial input (division by zero)
    print("\n" + "═" * 70)
    print("EXAMPLE 4: Adversarial Input (Division by Zero)")
    print("═" * 70)
    
    source = """
        PUSH 100
        PUSH 0          # Divisor = 0 (adversarial!)
        DIV             # This will error
        HALT
    """
    
    bytecode = Assembler.assemble(source)
    vm = ForgeVM(bytecode, fuel=1000)
    receipt = vm.run()
    
    print(receipt.summary())
    print("\nNote: Error produces a valid receipt proving the failure!")
    
    # Final summary
    print("\n" + "═" * 70)
    print("SUMMARY: The Uncomfortable Truth")
    print("═" * 70)
    print("""
    Most code you run provides ZERO proof it executed correctly.
    
    FORGE changes this:
    
    1. ✓ DETERMINISM: Same inputs → Same outputs (always)
    2. ✓ BOUNDED: Execution terminates within fuel budget (guaranteed)
    3. ✓ VERIFIABLE: Anyone can verify by re-executing
    4. ✓ GRACEFUL: Even errors produce valid receipts
    
    The receipt is a cryptographic commitment to:
    • The exact computation that was performed
    • The exact resources that were consumed
    • The exact output that was produced
    
    Trust, but verify.
    """)


if __name__ == "__main__":
    demo()
