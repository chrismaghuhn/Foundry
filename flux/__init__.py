"""
Flux: Reactive Dataflow Computation Engine

Build computation graphs with automatic parallelization and caching.

Quick Start:
    >>> from flux import Flow
    >>> flow = Flow()
    >>> 
    >>> @flow.node()
    >>> async def fetch_a() -> int:
    ...     return 1
    >>> 
    >>> @flow.node()
    >>> async def fetch_b() -> int:
    ...     return 2
    >>> 
    >>> @flow.node()
    >>> async def combine(fetch_a: int, fetch_b: int) -> int:
    ...     return fetch_a + fetch_b  # Dependencies auto-detected!
    >>> 
    >>> result = await flow.execute()
    >>> print(result['combine'])  # 3
"""

from .flux import (
    # Core classes
    Flow,
    Node,
    NodeState,
    NodeResult,
    FlowResult,
    
    # Graph
    DependencyGraph,
    
    # Cache
    CacheBackend,
    InMemoryCache,
    compute_cache_key,
    
    # Exceptions
    FluxError,
    CycleDetectedError,
    NodeNotFoundError,
    ExecutionError,
    DuplicateNodeError,
    
    # Utilities
    create_flow,
    run_flow,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core
    'Flow',
    'Node',
    'NodeState',
    'NodeResult',
    'FlowResult',
    
    # Graph
    'DependencyGraph',
    
    # Cache
    'CacheBackend',
    'InMemoryCache',
    'compute_cache_key',
    
    # Exceptions
    'FluxError',
    'CycleDetectedError',
    'NodeNotFoundError',
    'ExecutionError',
    'DuplicateNodeError',
    
    # Utilities
    'create_flow',
    'run_flow',
]
