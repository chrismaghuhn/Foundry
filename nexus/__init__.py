"""
Nexus: Enterprise Integration Framework

Demonstration / reference implementation — not for production deployment.

Verifiable ETL Pipeline with Cryptographic Audit Trail.

Integrates:
    - Visual Pipeline Definition (Glyph-inspired)
    - Cryptographic Audit Logging (Malo-inspired)
    - Distributed Lock Coordination
    - Circuit Breaker Fault Tolerance
    - Real-time Metrics Collection

Usage:
    from nexus import (
        PipelineExecutor,
        VisualPipelineCompiler,
        CryptographicAuditLog,
        DistributedLockManager,
        MetricsCollector,
        CircuitBreaker
    )

Author: chrismaghuhn
License: MIT
"""

from .nexus_integration import (
    # Lock Management
    DistributedLockManager,
    LockInfo,
    LockState,
    
    # Circuit Breaker
    CircuitBreaker,
    CircuitState,
    CircuitStats,
    CircuitOpenError,
    
    # Metrics
    MetricsCollector,
    MetricPoint,
    
    # Audit Logging
    CryptographicAuditLog,
    AuditEntry,
    InclusionProof,
    hash_leaf,
    hash_nodes,
    
    # Pipeline
    VisualPipelineCompiler,
    CompiledPipeline,
    PipelineNode,
    PipelineEdge,
    PipelineExecutor,
    
    # Node Functions
    BUILTIN_FUNCTIONS,
    create_transform_function,
    create_filter_function,
    create_aggregation_function,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Lock Management
    'DistributedLockManager', 'LockInfo', 'LockState',
    
    # Circuit Breaker
    'CircuitBreaker', 'CircuitState', 'CircuitStats', 'CircuitOpenError',
    
    # Metrics
    'MetricsCollector', 'MetricPoint',
    
    # Audit Logging
    'CryptographicAuditLog', 'AuditEntry', 'InclusionProof',
    'hash_leaf', 'hash_nodes',
    
    # Pipeline
    'VisualPipelineCompiler', 'CompiledPipeline',
    'PipelineNode', 'PipelineEdge', 'PipelineExecutor',
    
    # Node Functions
    'BUILTIN_FUNCTIONS',
    'create_transform_function', 'create_filter_function',
    'create_aggregation_function',
]
