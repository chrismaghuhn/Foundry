"""
Flux: Reactive Dataflow Computation Engine

A lightweight library for building and executing computation graphs with:
- Automatic dependency resolution from function signatures
- Parallel execution of independent nodes
- Content-addressable memoization
- Backpressure handling and retry logic
- Cycle detection and topological execution

Architecture:
    1. Users define nodes (computations) as decorated async functions
    2. Dependencies are inferred from parameter names matching other node names
    3. The engine builds a DAG and detects cycles
    4. Execution proceeds in topological order, parallelizing independent nodes
    5. Results are cached by input hash for memoization across runs

Key Data Structures:
    - Dependency Graph: Adjacency list for O(1) neighbor lookup
    - Execution Levels: Nodes grouped by topological depth for parallel batching
    - Cache: Content-addressable store keyed by (node_name, input_hash)

Thread Safety:
    All mutable state is protected by asyncio.Lock. The cache uses a 
    reader-writer pattern optimized for read-heavy workloads.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import pickle
import time
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import (
    Any, 
    Awaitable, 
    Callable, 
    Generic, 
    TypeVar, 
    ParamSpec,
    get_type_hints,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')


# =============================================================================
# Exceptions
# =============================================================================

class FluxError(Exception):
    """Base exception for Flux errors."""
    pass


class CycleDetectedError(FluxError):
    """Circular dependency detected in the computation graph."""
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle + [cycle[0]])
        super().__init__(f"Circular dependency detected: {cycle_str}")


class NodeNotFoundError(FluxError):
    """Referenced node does not exist."""
    def __init__(self, node_name: str, referenced_by: str | None = None):
        self.node_name = node_name
        self.referenced_by = referenced_by
        msg = f"Node '{node_name}' not found"
        if referenced_by:
            msg += f" (referenced by '{referenced_by}')"
        super().__init__(msg)


class ExecutionError(FluxError):
    """Error during node execution."""
    def __init__(self, node_name: str, original_error: Exception):
        self.node_name = node_name
        self.original_error = original_error
        super().__init__(f"Node '{node_name}' failed: {original_error}")


class DuplicateNodeError(FluxError):
    """Node with same name already registered."""
    def __init__(self, node_name: str):
        self.node_name = node_name
        super().__init__(f"Node '{node_name}' already exists in the flow")


# =============================================================================
# Node State Machine
# =============================================================================

class NodeState(Enum):
    """
    Execution state of a node.
    
    State transitions:
        PENDING -> RUNNING -> COMPLETED
                          -> FAILED -> (retry) -> RUNNING
                          -> SKIPPED (if upstream failed)
    """
    PENDING = auto()    # Not yet executed
    RUNNING = auto()    # Currently executing
    COMPLETED = auto()  # Successfully finished
    FAILED = auto()     # Execution failed
    SKIPPED = auto()    # Skipped due to upstream failure
    CACHED = auto()     # Result retrieved from cache


@dataclass
class NodeResult(Generic[T]):
    """
    Result of executing a single node.
    
    Captures both successful results and failures for debugging
    and downstream decision-making.
    """
    node_name: str
    state: NodeState
    value: T | None = None
    error: Exception | None = None
    execution_time_ms: float = 0.0
    cache_hit: bool = False
    retry_count: int = 0
    
    @property
    def success(self) -> bool:
        return self.state in (NodeState.COMPLETED, NodeState.CACHED)


# =============================================================================
# Cache System
# =============================================================================

class CacheBackend(ABC):
    """
    Abstract cache backend for memoization.
    
    Implement this to plug in Redis, disk, or other storage backends.
    """
    
    @abstractmethod
    async def get(self, key: str) -> tuple[bool, Any]:
        """
        Retrieve cached value.
        
        Returns:
            (hit, value) - hit is True if key exists, value is the cached data
        """
        ...
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store value in cache with optional TTL."""
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache. Returns True if key existed."""
        ...
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached values."""
        ...


class InMemoryCache(CacheBackend):
    """
    Thread-safe in-memory cache with optional LRU eviction.
    
    Uses asyncio.Lock for thread safety. In high-contention scenarios,
    consider using a sharded cache or reader-writer lock.
    """
    
    def __init__(self, max_size: int = 10000):
        self._cache: dict[str, tuple[Any, float | None]] = {}  # key -> (value, expiry)
        self._access_order: list[str] = []  # LRU tracking
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> tuple[bool, Any]:
        async with self._lock:
            if key not in self._cache:
                return (False, None)
            
            value, expiry = self._cache[key]
            
            # Check TTL
            if expiry is not None and time.time() > expiry:
                del self._cache[key]
                self._access_order.remove(key)
                return (False, None)
            
            # Update LRU order
            self._access_order.remove(key)
            self._access_order.append(key)
            
            return (True, value)
    
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        async with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self._max_size and self._access_order:
                oldest = self._access_order.pop(0)
                self._cache.pop(oldest, None)
            
            expiry = time.time() + ttl_seconds if ttl_seconds else None
            self._cache[key] = (value, expiry)
            
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)
                return True
            return False
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    @property
    def size(self) -> int:
        return len(self._cache)


def compute_cache_key(node_name: str, inputs: dict[str, Any]) -> str:
    """
    Compute content-addressable cache key.
    
    The key is a hash of the node name and serialized inputs, ensuring
    that identical computations map to the same cache entry.
    
    We use pickle for serialization as it handles more types than JSON,
    but this means cached values may not be portable across Python versions.
    """
    try:
        # Try pickle first (handles more types)
        input_bytes = pickle.dumps(inputs, protocol=pickle.HIGHEST_PROTOCOL)
    except (pickle.PicklingError, TypeError):
        # Fall back to JSON for unpickleable objects
        input_bytes = json.dumps(inputs, sort_keys=True, default=str).encode()
    
    content = f"{node_name}:".encode() + input_bytes
    return hashlib.sha256(content).hexdigest()[:32]


# =============================================================================
# Node Definition
# =============================================================================

@dataclass
class Node:
    """
    A computation node in the dataflow graph.
    
    Nodes are defined by an async function and metadata about execution:
    - Dependencies are inferred from parameter names
    - Retry policy controls failure handling
    - Cache TTL determines memoization behavior
    """
    name: str
    func: Callable[..., Awaitable[Any]]
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 0
    retry_delay_seconds: float = 1.0
    cache_ttl_seconds: int | None = None
    timeout_seconds: float | None = None
    
    def __post_init__(self):
        # Validate the function is async
        if not asyncio.iscoroutinefunction(self.func):
            raise FluxError(f"Node '{self.name}' function must be async")
    
    async def execute(
        self, 
        inputs: dict[str, Any],
        cache: CacheBackend | None = None
    ) -> NodeResult:
        """
        Execute this node with the given inputs.
        
        Handles:
        - Cache lookup and storage
        - Retry logic with exponential backoff
        - Timeout enforcement
        - Error capture
        """
        start_time = time.time()
        
        # Check cache first
        if cache is not None:
            cache_key = compute_cache_key(self.name, inputs)
            hit, cached_value = await cache.get(cache_key)
            if hit:
                logger.debug(f"Cache hit for node '{self.name}'")
                return NodeResult(
                    node_name=self.name,
                    state=NodeState.CACHED,
                    value=cached_value,
                    cache_hit=True,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
        
        # Execute with retries
        last_error: Exception | None = None
        for attempt in range(self.retry_count + 1):
            try:
                # Build kwargs from inputs
                kwargs = {k: v for k, v in inputs.items() if k in self.dependencies}
                
                # Execute with optional timeout
                if self.timeout_seconds:
                    result = await asyncio.wait_for(
                        self.func(**kwargs),
                        timeout=self.timeout_seconds
                    )
                else:
                    result = await self.func(**kwargs)
                
                # Store in cache
                if cache is not None:
                    await cache.set(cache_key, result, self.cache_ttl_seconds)
                
                return NodeResult(
                    node_name=self.name,
                    state=NodeState.COMPLETED,
                    value=result,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    retry_count=attempt
                )
                
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"Node '{self.name}' timed out (attempt {attempt + 1})")
            except Exception as e:
                last_error = e
                logger.warning(f"Node '{self.name}' failed (attempt {attempt + 1}): {e}")
            
            # Exponential backoff before retry
            if attempt < self.retry_count:
                delay = self.retry_delay_seconds * (2 ** attempt)
                await asyncio.sleep(delay)
        
        return NodeResult(
            node_name=self.name,
            state=NodeState.FAILED,
            error=last_error,
            execution_time_ms=(time.time() - start_time) * 1000,
            retry_count=self.retry_count
        )


# =============================================================================
# Graph Analysis
# =============================================================================

class DependencyGraph:
    """
    Directed acyclic graph for dependency tracking.
    
    Provides:
    - O(1) dependency lookup
    - Cycle detection via DFS
    - Topological sorting for execution order
    - Level grouping for parallel execution batching
    """
    
    def __init__(self):
        # node -> list of nodes it depends on
        self._dependencies: dict[str, list[str]] = defaultdict(list)
        # node -> list of nodes that depend on it
        self._dependents: dict[str, list[str]] = defaultdict(list)
        self._nodes: set[str] = set()
    
    def add_node(self, name: str, dependencies: list[str]) -> None:
        """Add a node with its dependencies."""
        self._nodes.add(name)
        self._dependencies[name] = list(dependencies)
        
        for dep in dependencies:
            self._dependents[dep].append(name)
    
    def get_dependencies(self, name: str) -> list[str]:
        """Get direct dependencies of a node."""
        return self._dependencies.get(name, [])
    
    def get_dependents(self, name: str) -> list[str]:
        """Get nodes that depend on this node."""
        return self._dependents.get(name, [])
    
    def detect_cycle(self) -> list[str] | None:
        """
        Detect cycles using DFS with coloring.
        
        Returns the cycle path if found, None otherwise.
        
        Colors:
        - WHITE (0): Not visited
        - GRAY (1): Currently in recursion stack
        - BLACK (2): Fully processed
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self._nodes}
        parent = {node: None for node in self._nodes}
        
        def dfs(node: str) -> str | None:
            color[node] = GRAY
            
            for dep in self._dependencies[node]:
                if dep not in self._nodes:
                    continue
                    
                if color[dep] == GRAY:
                    # Found cycle - reconstruct path
                    cycle = [dep]
                    current = node
                    while current != dep:
                        cycle.append(current)
                        current = parent.get(current)
                        if current is None:
                            break
                    return cycle[::-1]
                
                if color[dep] == WHITE:
                    parent[dep] = node
                    result = dfs(dep)
                    if result:
                        return result
            
            color[node] = BLACK
            return None
        
        for node in self._nodes:
            if color[node] == WHITE:
                cycle = dfs(node)
                if cycle:
                    return cycle
        
        return None
    
    def topological_sort(self) -> list[str]:
        """
        Return nodes in topological order using Kahn's algorithm.
        
        Nodes with no dependencies come first, followed by nodes
        whose dependencies have all been processed.
        """
        # Compute in-degrees
        in_degree = {node: 0 for node in self._nodes}
        for node in self._nodes:
            for dep in self._dependencies[node]:
                if dep in self._nodes:
                    in_degree[node] += 1
        
        # Start with nodes having no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for dependent in self._dependents[node]:
                if dependent in self._nodes:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        return result
    
    def get_execution_levels(self) -> list[list[str]]:
        """
        Group nodes into levels for parallel execution.
        
        Nodes at the same level have no dependencies on each other
        and can be executed concurrently.
        
        Level 0: Nodes with no dependencies
        Level N: Nodes whose dependencies are all in levels < N
        """
        # Compute node levels
        levels: dict[str, int] = {}
        
        def compute_level(node: str, visited: set[str]) -> int:
            if node in levels:
                return levels[node]
            
            if node in visited:
                return 0  # Cycle handling (shouldn't happen after validation)
            
            visited.add(node)
            
            deps = [d for d in self._dependencies[node] if d in self._nodes]
            if not deps:
                levels[node] = 0
            else:
                levels[node] = 1 + max(compute_level(d, visited) for d in deps)
            
            return levels[node]
        
        for node in self._nodes:
            compute_level(node, set())
        
        # Group by level
        max_level = max(levels.values()) if levels else 0
        result = [[] for _ in range(max_level + 1)]
        
        for node, level in levels.items():
            result[level].append(node)
        
        return result
    
    def validate(self) -> None:
        """
        Validate the graph structure.
        
        Raises:
            CycleDetectedError: If circular dependencies exist
            NodeNotFoundError: If a dependency references a non-existent node
        """
        # Check for missing dependencies
        for node in self._nodes:
            for dep in self._dependencies[node]:
                if dep not in self._nodes:
                    raise NodeNotFoundError(dep, referenced_by=node)
        
        # Check for cycles
        cycle = self.detect_cycle()
        if cycle:
            raise CycleDetectedError(cycle)


# =============================================================================
# Flow Engine
# =============================================================================

@dataclass
class FlowResult:
    """
    Complete result of executing a flow.
    
    Contains results for all nodes, timing information, and aggregate status.
    """
    results: dict[str, NodeResult]
    total_time_ms: float
    cache_hits: int
    cache_misses: int
    
    @property
    def success(self) -> bool:
        return all(r.success for r in self.results.values())
    
    @property
    def failed_nodes(self) -> list[str]:
        return [name for name, r in self.results.items() if not r.success]
    
    def get(self, node_name: str) -> Any:
        """Get the result value of a specific node."""
        if node_name not in self.results:
            raise NodeNotFoundError(node_name)
        result = self.results[node_name]
        if not result.success:
            raise ExecutionError(node_name, result.error or Exception("Unknown error"))
        return result.value
    
    def __getitem__(self, node_name: str) -> Any:
        return self.get(node_name)


class Flow:
    """
    Main entry point for building and executing dataflow graphs.
    
    Usage:
        flow = Flow()
        
        @flow.node()
        async def fetch_data() -> list[dict]:
            return await api.get_data()
        
        @flow.node()
        async def process(fetch_data: list[dict]) -> Result:
            # Automatically depends on fetch_data
            return transform(fetch_data)
        
        result = await flow.execute()
        processed = result['process']
    
    The flow automatically:
    1. Infers dependencies from parameter names
    2. Builds and validates the dependency graph
    3. Executes nodes in parallel where possible
    4. Caches results for subsequent runs
    """
    
    def __init__(
        self,
        cache: CacheBackend | None = None,
        max_concurrency: int | None = None,
        fail_fast: bool = False
    ):
        """
        Initialize a new Flow.
        
        Args:
            cache: Optional cache backend for memoization
            max_concurrency: Limit parallel executions (None = unlimited)
            fail_fast: Stop execution on first failure
        """
        self._nodes: dict[str, Node] = {}
        self._graph = DependencyGraph()
        self._cache = cache or InMemoryCache()
        self._max_concurrency = max_concurrency
        self._fail_fast = fail_fast
        self._semaphore: asyncio.Semaphore | None = None
        self._validated = False
    
    def node(
        self,
        name: str | None = None,
        *,
        dependencies: list[str] | None = None,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        cache_ttl: int | None = None,
        timeout: float | None = None
    ) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
        """
        Decorator to register a node in the flow.
        
        Args:
            name: Node name (defaults to function name)
            dependencies: Explicit dependencies (auto-inferred if None)
            retry_count: Number of retry attempts on failure
            retry_delay: Base delay between retries (exponential backoff)
            cache_ttl: Cache TTL in seconds (None = forever)
            timeout: Execution timeout in seconds
        
        Returns:
            Decorated function (unchanged, but registered)
        """
        def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
            node_name = name or func.__name__
            
            if node_name in self._nodes:
                raise DuplicateNodeError(node_name)
            
            # Infer dependencies from function signature
            if dependencies is None:
                sig = inspect.signature(func)
                inferred_deps = list(sig.parameters.keys())
            else:
                inferred_deps = list(dependencies)
            
            # Create and register node
            node = Node(
                name=node_name,
                func=func,
                dependencies=inferred_deps,
                retry_count=retry_count,
                retry_delay_seconds=retry_delay,
                cache_ttl_seconds=cache_ttl,
                timeout_seconds=timeout
            )
            
            self._nodes[node_name] = node
            self._graph.add_node(node_name, inferred_deps)
            self._validated = False
            
            # Return original function unchanged
            return func
        
        return decorator
    
    def add_node(
        self,
        func: Callable[..., Awaitable[Any]],
        name: str | None = None,
        **kwargs
    ) -> None:
        """
        Programmatically add a node (alternative to decorator).
        
        Useful for dynamic flow construction.
        """
        self.node(name, **kwargs)(func)
    
    def validate(self) -> None:
        """
        Validate the flow graph.
        
        Called automatically before execution, but can be called
        manually for early error detection.
        """
        if self._validated:
            return
        
        self._graph.validate()
        self._validated = True
    
    async def execute(
        self,
        targets: list[str] | None = None,
        inputs: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Execute the flow.
        
        Args:
            targets: Specific nodes to execute (and their dependencies).
                     If None, executes all nodes.
            inputs: Override inputs for specific nodes (bypasses computation)
        
        Returns:
            FlowResult with all node results
        
        Raises:
            CycleDetectedError: If circular dependencies exist
            NodeNotFoundError: If a target or dependency doesn't exist
            ExecutionError: If fail_fast is True and a node fails
        """
        self.validate()
        
        start_time = time.time()
        results: dict[str, NodeResult] = {}
        inputs = inputs or {}
        
        # Pre-populate results with provided inputs
        for node_name, value in inputs.items():
            results[node_name] = NodeResult(
                node_name=node_name,
                state=NodeState.COMPLETED,
                value=value
            )
        
        # Determine which nodes to execute
        if targets:
            nodes_to_execute = self._get_required_nodes(targets)
        else:
            nodes_to_execute = set(self._nodes.keys())
        
        # Remove nodes with pre-provided inputs
        nodes_to_execute -= set(inputs.keys())
        
        # Set up concurrency limit
        if self._max_concurrency:
            self._semaphore = asyncio.Semaphore(self._max_concurrency)
        
        # Get execution levels
        levels = self._graph.get_execution_levels()
        
        # Track failures for fail-fast and skip logic
        failed = False
        failed_nodes: set[str] = set()
        
        # Execute level by level
        for level in levels:
            if failed and self._fail_fast:
                break
            
            # Filter to nodes we need to execute
            level_nodes = [n for n in level if n in nodes_to_execute and n not in results]
            
            if not level_nodes:
                continue
            
            # Execute level in parallel
            tasks = []
            for node_name in level_nodes:
                # Check if any dependency failed
                deps = self._graph.get_dependencies(node_name)
                dep_failed = any(d in failed_nodes for d in deps)
                
                if dep_failed:
                    # Skip this node
                    results[node_name] = NodeResult(
                        node_name=node_name,
                        state=NodeState.SKIPPED
                    )
                    failed_nodes.add(node_name)
                    continue
                
                # Gather inputs from completed dependencies
                node_inputs = {}
                for dep in deps:
                    if dep in results and results[dep].success:
                        node_inputs[dep] = results[dep].value
                    elif dep in self._nodes:
                        # Dependency exists but wasn't executed - shouldn't happen
                        logger.error(f"Dependency '{dep}' not ready for '{node_name}'")
                
                tasks.append(self._execute_node(node_name, node_inputs))
            
            # Await all tasks in this level
            level_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in level_results:
                if isinstance(result, Exception):
                    logger.error(f"Unexpected error: {result}")
                    continue
                
                results[result.node_name] = result
                
                if not result.success:
                    failed = True
                    failed_nodes.add(result.node_name)
                    
                    if self._fail_fast:
                        break
        
        # Compute cache statistics
        cache_hits = sum(1 for r in results.values() if r.cache_hit)
        cache_misses = sum(1 for r in results.values() if r.success and not r.cache_hit)
        
        return FlowResult(
            results=results,
            total_time_ms=(time.time() - start_time) * 1000,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
    
    async def _execute_node(self, node_name: str, inputs: dict[str, Any]) -> NodeResult:
        """Execute a single node with optional concurrency limiting."""
        node = self._nodes[node_name]
        
        if self._semaphore:
            async with self._semaphore:
                return await node.execute(inputs, self._cache)
        else:
            return await node.execute(inputs, self._cache)
    
    def _get_required_nodes(self, targets: list[str]) -> set[str]:
        """
        Get all nodes required to compute the targets.
        
        Performs a DFS from each target to collect all dependencies.
        """
        required: set[str] = set()
        
        def collect(node_name: str) -> None:
            if node_name in required:
                return
            if node_name not in self._nodes:
                raise NodeNotFoundError(node_name)
            
            required.add(node_name)
            
            for dep in self._graph.get_dependencies(node_name):
                if dep in self._nodes:
                    collect(dep)
        
        for target in targets:
            collect(target)
        
        return required
    
    async def clear_cache(self) -> None:
        """Clear all cached results."""
        await self._cache.clear()
    
    def get_execution_plan(self) -> list[list[str]]:
        """
        Get the execution plan (for debugging/visualization).
        
        Returns levels of nodes that will be executed in parallel.
        """
        self.validate()
        return self._graph.get_execution_levels()
    
    def visualize(self) -> str:
        """
        Generate a simple ASCII visualization of the flow.
        
        Returns a string representation of the dependency graph.
        """
        lines = ["Flow Execution Plan:", "=" * 40]
        
        for i, level in enumerate(self.get_execution_plan()):
            lines.append(f"Level {i}: {', '.join(sorted(level))}")
            
            for node_name in sorted(level):
                deps = self._graph.get_dependencies(node_name)
                if deps:
                    dep_str = ", ".join(sorted(deps))
                    lines.append(f"  └─ {node_name} <- [{dep_str}]")
                else:
                    lines.append(f"  └─ {node_name} (no dependencies)")
        
        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_flow(**kwargs) -> Flow:
    """Create a new Flow with the given configuration."""
    return Flow(**kwargs)


async def run_flow(flow: Flow, **kwargs) -> FlowResult:
    """Execute a flow and return results."""
    return await flow.execute(**kwargs)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core classes
    'Flow',
    'Node',
    'NodeResult',
    'NodeState',
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
