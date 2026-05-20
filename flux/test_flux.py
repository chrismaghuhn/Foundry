"""Tests for flux."""

import asyncio
import pytest
import time
from flux import (
    Flow,
    Node,
    NodeState,
    DependencyGraph,
    InMemoryCache,
    CycleDetectedError,
    NodeNotFoundError,
    ExecutionError,
    DuplicateNodeError,
    compute_cache_key,
)


# =============================================================================
# Graph Tests
# =============================================================================

class TestDependencyGraph:
    """Test dependency graph operations."""
    
    def test_add_nodes(self):
        """Basic node addition."""
        graph = DependencyGraph()
        graph.add_node("a", [])
        graph.add_node("b", ["a"])
        graph.add_node("c", ["a", "b"])
        
        assert graph.get_dependencies("a") == []
        assert graph.get_dependencies("b") == ["a"]
        assert set(graph.get_dependencies("c")) == {"a", "b"}
    
    def test_get_dependents(self):
        """Reverse dependency lookup."""
        graph = DependencyGraph()
        graph.add_node("a", [])
        graph.add_node("b", ["a"])
        graph.add_node("c", ["a"])
        
        dependents = graph.get_dependents("a")
        assert set(dependents) == {"b", "c"}
    
    def test_cycle_detection_simple(self):
        """Detect simple A -> B -> A cycle."""
        graph = DependencyGraph()
        graph.add_node("a", ["b"])
        graph.add_node("b", ["a"])
        
        cycle = graph.detect_cycle()
        assert cycle is not None
        assert set(cycle) == {"a", "b"}
    
    def test_cycle_detection_longer(self):
        """Detect A -> B -> C -> A cycle."""
        graph = DependencyGraph()
        graph.add_node("a", ["c"])
        graph.add_node("b", ["a"])
        graph.add_node("c", ["b"])
        
        cycle = graph.detect_cycle()
        assert cycle is not None
        assert len(cycle) == 3
    
    def test_no_cycle(self):
        """Verify no false positives for valid DAG."""
        graph = DependencyGraph()
        graph.add_node("a", [])
        graph.add_node("b", ["a"])
        graph.add_node("c", ["a"])
        graph.add_node("d", ["b", "c"])
        
        assert graph.detect_cycle() is None
    
    def test_topological_sort(self):
        """Verify topological ordering."""
        graph = DependencyGraph()
        graph.add_node("a", [])
        graph.add_node("b", ["a"])
        graph.add_node("c", ["b"])
        
        order = graph.topological_sort()
        
        # a must come before b, b must come before c
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")
    
    def test_execution_levels(self):
        """Verify parallel execution grouping."""
        graph = DependencyGraph()
        graph.add_node("a", [])
        graph.add_node("b", [])
        graph.add_node("c", ["a", "b"])
        graph.add_node("d", ["c"])
        
        levels = graph.get_execution_levels()
        
        assert len(levels) == 3
        assert set(levels[0]) == {"a", "b"}  # Independent, can run in parallel
        assert levels[1] == ["c"]  # Depends on a, b
        assert levels[2] == ["d"]  # Depends on c
    
    def test_validate_missing_dependency(self):
        """Detect references to non-existent nodes."""
        graph = DependencyGraph()
        graph.add_node("a", ["nonexistent"])
        
        with pytest.raises(NodeNotFoundError) as exc:
            graph.validate()
        
        assert exc.value.node_name == "nonexistent"
        assert exc.value.referenced_by == "a"
    
    def test_validate_cycle_raises(self):
        """Validation raises on cycle."""
        graph = DependencyGraph()
        graph.add_node("a", ["b"])
        graph.add_node("b", ["a"])
        
        with pytest.raises(CycleDetectedError):
            graph.validate()


# =============================================================================
# Cache Tests
# =============================================================================

class TestInMemoryCache:
    """Test in-memory cache implementation."""
    
    @pytest.mark.asyncio
    async def test_basic_get_set(self):
        """Basic cache operations."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1")
        hit, value = await cache.get("key1")
        
        assert hit is True
        assert value == "value1"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Cache miss returns (False, None)."""
        cache = InMemoryCache()
        
        hit, value = await cache.get("nonexistent")
        
        assert hit is False
        assert value is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        """TTL causes expiry."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1", ttl_seconds=1)
        
        # Should hit immediately
        hit, _ = await cache.get("key1")
        assert hit is True
        
        # Wait for expiry
        await asyncio.sleep(1.1)
        
        hit, _ = await cache.get("key1")
        assert hit is False
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """LRU eviction when at capacity."""
        cache = InMemoryCache(max_size=2)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Access key1 to make it more recent
        await cache.get("key1")
        
        # Add key3, should evict key2 (least recently used)
        await cache.set("key3", "value3")
        
        hit1, _ = await cache.get("key1")
        hit2, _ = await cache.get("key2")
        hit3, _ = await cache.get("key3")
        
        assert hit1 is True
        assert hit2 is False  # Evicted
        assert hit3 is True
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Delete removes key."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1")
        assert await cache.delete("key1") is True
        
        hit, _ = await cache.get("key1")
        assert hit is False
        
        # Delete non-existent key returns False
        assert await cache.delete("key1") is False
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Clear removes all keys."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        
        assert cache.size == 0


class TestCacheKey:
    """Test cache key computation."""
    
    def test_same_inputs_same_key(self):
        """Identical inputs produce same key."""
        key1 = compute_cache_key("node", {"a": 1, "b": 2})
        key2 = compute_cache_key("node", {"a": 1, "b": 2})
        
        assert key1 == key2
    
    def test_different_inputs_different_key(self):
        """Different inputs produce different keys."""
        key1 = compute_cache_key("node", {"a": 1})
        key2 = compute_cache_key("node", {"a": 2})
        
        assert key1 != key2
    
    def test_different_nodes_different_key(self):
        """Different node names produce different keys."""
        key1 = compute_cache_key("node1", {"a": 1})
        key2 = compute_cache_key("node2", {"a": 1})
        
        assert key1 != key2


# =============================================================================
# Node Tests
# =============================================================================

class TestNode:
    """Test individual node execution."""
    
    @pytest.mark.asyncio
    async def test_simple_execution(self):
        """Basic node execution."""
        async def my_func() -> int:
            return 42
        
        node = Node(name="test", func=my_func, dependencies=[])
        result = await node.execute({})
        
        assert result.success
        assert result.value == 42
        assert result.state == NodeState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_with_dependencies(self):
        """Node receives dependency values."""
        async def my_func(x: int, y: int) -> int:
            return x + y
        
        node = Node(name="test", func=my_func, dependencies=["x", "y"])
        result = await node.execute({"x": 10, "y": 20})
        
        assert result.success
        assert result.value == 30
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Node retries on failure."""
        attempts = []
        
        async def flaky_func() -> int:
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("Not yet!")
            return 42
        
        node = Node(
            name="test", 
            func=flaky_func, 
            dependencies=[],
            retry_count=3,
            retry_delay_seconds=0.01
        )
        result = await node.execute({})
        
        assert result.success
        assert result.value == 42
        assert len(attempts) == 3
    
    @pytest.mark.asyncio
    async def test_timeout(self):
        """Node respects timeout."""
        async def slow_func() -> int:
            await asyncio.sleep(10)
            return 42
        
        node = Node(
            name="test",
            func=slow_func,
            dependencies=[],
            timeout_seconds=0.1
        )
        result = await node.execute({})
        
        assert not result.success
        assert result.state == NodeState.FAILED
        assert isinstance(result.error, asyncio.TimeoutError)
    
    @pytest.mark.asyncio
    async def test_caching(self):
        """Node caches results."""
        call_count = 0
        
        async def my_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        cache = InMemoryCache()
        node = Node(name="test", func=my_func, dependencies=["x"])
        
        # First call
        result1 = await node.execute({"x": 5}, cache=cache)
        assert result1.success
        assert result1.value == 10
        assert not result1.cache_hit
        
        # Second call with same input - should hit cache
        result2 = await node.execute({"x": 5}, cache=cache)
        assert result2.success
        assert result2.value == 10
        assert result2.cache_hit
        
        # Function only called once
        assert call_count == 1


# =============================================================================
# Flow Tests
# =============================================================================

class TestFlow:
    """Test flow execution."""
    
    @pytest.mark.asyncio
    async def test_simple_flow(self):
        """Basic flow with single node."""
        flow = Flow()
        
        @flow.node()
        async def compute() -> int:
            return 42
        
        result = await flow.execute()
        
        assert result.success
        assert result["compute"] == 42
    
    @pytest.mark.asyncio
    async def test_dependency_chain(self):
        """Nodes execute in dependency order."""
        flow = Flow()
        execution_order = []
        
        @flow.node()
        async def step1() -> int:
            execution_order.append("step1")
            return 1
        
        @flow.node()
        async def step2(step1: int) -> int:
            execution_order.append("step2")
            return step1 + 1
        
        @flow.node()
        async def step3(step2: int) -> int:
            execution_order.append("step3")
            return step2 + 1
        
        result = await flow.execute()
        
        assert result.success
        assert execution_order == ["step1", "step2", "step3"]
        assert result["step3"] == 3
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Independent nodes execute in parallel."""
        flow = Flow()
        start_times = {}
        
        @flow.node()
        async def slow1() -> int:
            start_times["slow1"] = time.time()
            await asyncio.sleep(0.1)
            return 1
        
        @flow.node()
        async def slow2() -> int:
            start_times["slow2"] = time.time()
            await asyncio.sleep(0.1)
            return 2
        
        @flow.node()
        async def combine(slow1: int, slow2: int) -> int:
            return slow1 + slow2
        
        start = time.time()
        result = await flow.execute()
        elapsed = time.time() - start
        
        assert result.success
        assert result["combine"] == 3
        
        # Should take ~0.1s (parallel) not ~0.2s (sequential)
        assert elapsed < 0.15
        
        # slow1 and slow2 should start at nearly the same time
        assert abs(start_times["slow1"] - start_times["slow2"]) < 0.05
    
    @pytest.mark.asyncio
    async def test_diamond_dependency(self):
        """Diamond-shaped dependency graph."""
        flow = Flow()
        
        @flow.node()
        async def root() -> int:
            return 1
        
        @flow.node()
        async def left(root: int) -> int:
            return root + 10
        
        @flow.node()
        async def right(root: int) -> int:
            return root + 100
        
        @flow.node()
        async def merge(left: int, right: int) -> int:
            return left + right
        
        result = await flow.execute()
        
        assert result.success
        assert result["root"] == 1
        assert result["left"] == 11
        assert result["right"] == 101
        assert result["merge"] == 112
    
    @pytest.mark.asyncio
    async def test_targeted_execution(self):
        """Execute only required nodes for targets."""
        flow = Flow()
        executed = set()
        
        @flow.node()
        async def a() -> int:
            executed.add("a")
            return 1
        
        @flow.node()
        async def b(a: int) -> int:
            executed.add("b")
            return a + 1
        
        @flow.node()
        async def c() -> int:
            executed.add("c")
            return 100
        
        # Only execute 'b' and its dependencies (not 'c')
        result = await flow.execute(targets=["b"])
        
        assert result.success
        assert "a" in executed
        assert "b" in executed
        assert "c" not in executed
    
    @pytest.mark.asyncio
    async def test_input_override(self):
        """Provided inputs bypass computation."""
        flow = Flow()
        computed = set()
        
        @flow.node()
        async def expensive() -> int:
            computed.add("expensive")
            await asyncio.sleep(1)  # Simulate expensive computation
            return 42
        
        @flow.node()
        async def use_it(expensive: int) -> int:
            return expensive * 2
        
        # Provide 'expensive' directly
        result = await flow.execute(inputs={"expensive": 10})
        
        assert result.success
        assert "expensive" not in computed  # Wasn't computed
        assert result["use_it"] == 20  # Used provided value
    
    @pytest.mark.asyncio
    async def test_caching_across_runs(self):
        """Results are cached across flow executions."""
        flow = Flow()
        call_count = 0
        
        @flow.node()
        async def expensive() -> int:
            nonlocal call_count
            call_count += 1
            return 42
        
        # First run
        result1 = await flow.execute()
        assert result1.success
        assert result1.cache_misses == 1
        
        # Second run - should hit cache
        result2 = await flow.execute()
        assert result2.success
        assert result2.cache_hits == 1
        
        # Function only called once
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_fail_fast(self):
        """Fail-fast stops on first error."""
        flow = Flow(fail_fast=True)
        executed = []
        
        @flow.node()
        async def ok1() -> int:
            executed.append("ok1")
            return 1
        
        @flow.node()
        async def fail_node(ok1: int) -> int:
            executed.append("fail_node")
            raise ValueError("Intentional failure")
        
        @flow.node()
        async def ok2(fail_node: int) -> int:
            executed.append("ok2")
            return 2
        
        result = await flow.execute()
        
        assert not result.success
        assert "fail_node" in result.failed_nodes
        assert "ok2" not in executed  # Skipped due to fail-fast
    
    @pytest.mark.asyncio
    async def test_skip_on_upstream_failure(self):
        """Downstream nodes are skipped when upstream fails."""
        flow = Flow()
        
        @flow.node()
        async def failing() -> int:
            raise ValueError("Oops")
        
        @flow.node()
        async def downstream(failing: int) -> int:
            return failing + 1
        
        result = await flow.execute()
        
        assert not result.success
        assert result.results["failing"].state == NodeState.FAILED
        assert result.results["downstream"].state == NodeState.SKIPPED
    
    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Max concurrency is respected."""
        flow = Flow(max_concurrency=2)
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def make_node():
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            async with lock:
                concurrent_count -= 1
            return 1
        
        # Add 5 independent nodes
        for i in range(5):
            flow.add_node(make_node, name=f"node{i}")
        
        await flow.execute()
        
        # Should never exceed 2 concurrent
        assert max_concurrent <= 2
    
    @pytest.mark.asyncio
    async def test_cycle_detection(self):
        """Cyclic dependencies are detected."""
        flow = Flow()
        
        @flow.node()
        async def a(b: int) -> int:
            return b + 1
        
        @flow.node()
        async def b(a: int) -> int:
            return a + 1
        
        with pytest.raises(CycleDetectedError):
            await flow.execute()
    
    @pytest.mark.asyncio
    async def test_duplicate_node_error(self):
        """Duplicate node names are rejected."""
        flow = Flow()
        
        @flow.node(name="my_node")
        async def first() -> int:
            return 1
        
        with pytest.raises(DuplicateNodeError):
            @flow.node(name="my_node")
            async def second() -> int:
                return 2
    
    def test_execution_plan(self):
        """Execution plan is correctly computed."""
        flow = Flow()
        
        @flow.node()
        async def a() -> int:
            return 1
        
        @flow.node()
        async def b() -> int:
            return 2
        
        @flow.node()
        async def c(a: int, b: int) -> int:
            return a + b
        
        plan = flow.get_execution_plan()
        
        assert len(plan) == 2
        assert set(plan[0]) == {"a", "b"}  # Level 0: independent
        assert plan[1] == ["c"]  # Level 1: depends on a, b
    
    def test_visualize(self):
        """Visualization produces output."""
        flow = Flow()
        
        @flow.node()
        async def a() -> int:
            return 1
        
        @flow.node()
        async def b(a: int) -> int:
            return a + 1
        
        viz = flow.visualize()
        
        assert "a" in viz
        assert "b" in viz
        assert "Level" in viz


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_etl_pipeline(self):
        """Simulate an ETL pipeline."""
        flow = Flow()
        
        # Extract
        @flow.node()
        async def extract_users() -> list[dict]:
            return [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        
        @flow.node()
        async def extract_orders() -> list[dict]:
            return [
                {"user_id": 1, "amount": 100},
                {"user_id": 1, "amount": 50},
                {"user_id": 2, "amount": 200},
            ]
        
        # Transform
        @flow.node()
        async def transform(
            extract_users: list[dict],
            extract_orders: list[dict]
        ) -> list[dict]:
            # Join users with orders
            user_map = {u["id"]: u for u in extract_users}
            return [
                {**order, "user_name": user_map[order["user_id"]]["name"]}
                for order in extract_orders
            ]
        
        # Load (aggregate)
        @flow.node()
        async def load(transform: list[dict]) -> dict:
            totals = {}
            for record in transform:
                name = record["user_name"]
                totals[name] = totals.get(name, 0) + record["amount"]
            return totals
        
        result = await flow.execute()
        
        assert result.success
        assert result["load"] == {"Alice": 150, "Bob": 200}
    
    @pytest.mark.asyncio
    async def test_api_aggregation(self):
        """Simulate parallel API calls with aggregation."""
        flow = Flow()
        
        # Simulate parallel API calls
        @flow.node()
        async def fetch_user_profile() -> dict:
            await asyncio.sleep(0.05)  # Simulate network delay
            return {"name": "Alice", "age": 30}
        
        @flow.node()
        async def fetch_user_orders() -> list[dict]:
            await asyncio.sleep(0.05)
            return [{"item": "Book", "price": 20}]
        
        @flow.node()
        async def fetch_user_preferences() -> dict:
            await asyncio.sleep(0.05)
            return {"theme": "dark"}
        
        # Aggregate
        @flow.node()
        async def build_response(
            fetch_user_profile: dict,
            fetch_user_orders: list[dict],
            fetch_user_preferences: dict
        ) -> dict:
            return {
                "profile": fetch_user_profile,
                "orders": fetch_user_orders,
                "preferences": fetch_user_preferences,
            }
        
        start = time.time()
        result = await flow.execute()
        elapsed = time.time() - start
        
        assert result.success
        
        # Should take ~0.05s (parallel) not ~0.15s (sequential)
        assert elapsed < 0.1
        
        response = result["build_response"]
        assert response["profile"]["name"] == "Alice"
        assert len(response["orders"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
