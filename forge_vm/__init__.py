"""
FORGE: Verifiable Computation Kernel

Demonstration / reference implementation — not for production deployment.

Execute computation with hard resource bounds and get a cryptographic
RECEIPT proving what resources were consumed and what output was produced.

Features:
    - Deterministic execution (same inputs → same outputs)
    - Hard fuel bounds (execution ALWAYS terminates)
    - Cryptographic receipts (tamper-evident execution trace)
    - Checkpoint-based partial verification

Usage:
    from forge import ForgeVM, Assembler, Receipt, verify_receipt
    
    source = '''
        PUSH 10
        PUSH 20
        ADD
        HALT
    '''
    
    bytecode = Assembler.assemble(source)
    vm = ForgeVM(bytecode, fuel=1000)
    receipt = vm.run()
    
    # Verify the receipt
    is_valid, msg = verify_receipt(receipt, bytecode)

Author: chrismaghuhn
License: MIT
"""

from .forge import (
    # Core
    ForgeVM,
    Receipt,
    Checkpoint,
    Op,
    
    # Assembler
    Assembler,
    
    # Verification
    verify_receipt,
    verify_checkpoint,
    
    # Data structures
    MerkleTree,
    
    # Errors
    ForgeError,
    FuelExhausted,
    InvalidOpcode,
    StackUnderflow,
    StackOverflow,
    MemoryError,
    DivisionByZero,
    InvalidJump,
    
    # Constants
    MAX_MEMORY_SIZE,
    MAX_STACK_SIZE,
    MAX_FUEL,
    CHECKPOINT_INTERVAL,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    'ForgeVM', 'Receipt', 'Checkpoint', 'Op',
    'Assembler',
    'verify_receipt', 'verify_checkpoint',
    'MerkleTree',
    'ForgeError', 'FuelExhausted', 'InvalidOpcode',
    'StackUnderflow', 'StackOverflow', 'MemoryError',
    'DivisionByZero', 'InvalidJump',
    'MAX_MEMORY_SIZE', 'MAX_STACK_SIZE', 'MAX_FUEL', 'CHECKPOINT_INTERVAL',
]
