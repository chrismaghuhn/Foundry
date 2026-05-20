#!/usr/bin/env python3
"""
Flux Usage Examples

Demonstrates real-world scenarios for the Flux dataflow computation engine.
"""

import asyncio
import random
import time
from flux import Flow, InMemoryCache


async def example_basic_flow():
    """
    Example 1: Basic Dataflow
    
    Simple computation graph with automatic dependency resolution.
    """
    print("=" * 60)
    print("Example 1: Basic Dataflow")
    print("=" * 60)
    
    flow = Flow()
    
    @flow.node()
    async def fetch_price() -> float:
        """Fetch stock price."""
        await asyncio.sleep(0.1)  # Simulate API call
        return 150.50
    
    @flow.node()
    async def fetch_quantity() -> int:
        """Fetch held quantity."""
        await asyncio.sleep(0.1)
        return 100
    
    @flow.node()
    async def calculate_value(fetch_price: float, fetch_quantity: int) -> float:
        """Calculate portfolio value. Dependencies auto-detected!"""
        return fetch_price * fetch_quantity
    
    print("\nExecution Plan:")
    print(flow.visualize())
    
    print("\nExecuting...")
    start = time.time()
    result = await flow.execute()
    elapsed = (time.time() - start) * 1000
    
    print(f"\nResults:")
    print(f"  Price: ${result['fetch_price']:.2f}")
    print(f"  Quantity: {result['fetch_quantity']}")
    print(f"  Total Value: ${result['calculate_value']:.2f}")
    print(f"  Execution Time: {elapsed:.0f}ms (parallel fetch!)")
    print(f"✓ Success!\n")


async def example_caching():
    """
    Example 2: Memoization with Caching
    
    Expensive computations are cached across runs.
    """
    print("=" * 60)
    print("Example 2: Memoization with Caching")
    print("=" * 60)
    
    flow = Flow()
    compute_count = 0
    
    @flow.node(cache_ttl=60)  # Cache for 60 seconds
    async def expensive_computation() -> int:
        """Simulates expensive work. Only runs once!"""
        nonlocal compute_count
        compute_count += 1
        print(f"  [Computing... (call #{compute_count})]")
        await asyncio.sleep(0.5)
        return 42
    
    @flow.node()
    async def use_result(expensive_computation: int) -> str:
        return f"The answer is {expensive_computation}"
    
    # First run - computes
    print("\nFirst run:")
    result1 = await flow.execute()
    print(f"  Result: {result1['use_result']}")
    print(f"  Cache hits: {result1.cache_hits}, misses: {result1.cache_misses}")
    
    # Second run - cached
    print("\nSecond run (cached):")
    result2 = await flow.execute()
    print(f"  Result: {result2['use_result']}")
    print(f"  Cache hits: {result2.cache_hits}, misses: {result2.cache_misses}")
    
    print(f"\nTotal compute calls: {compute_count} (only 1, despite 2 runs)")
    print("✓ Caching works!\n")


async def example_error_handling():
    """
    Example 3: Error Handling with Retries
    
    Automatic retry with exponential backoff.
    """
    print("=" * 60)
    print("Example 3: Error Handling with Retries")
    print("=" * 60)
    
    flow = Flow()
    attempt_count = 0
    
    @flow.node(retry_count=3, retry_delay=0.1)
    async def flaky_service() -> str:
        """Simulates a flaky API that fails sometimes."""
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count < 3:
            print(f"  Attempt {attempt_count}: Failed!")
            raise ConnectionError("Service unavailable")
        
        print(f"  Attempt {attempt_count}: Success!")
        return "Data retrieved"
    
    @flow.node()
    async def process(flaky_service: str) -> str:
        return f"Processed: {flaky_service}"
    
    print("\nExecuting with retries:")
    result = await flow.execute()
    
    print(f"\nFinal result: {result['process']}")
    print(f"Total attempts: {attempt_count}")
    print(f"Retry count in result: {result.results['flaky_service'].retry_count}")
    print("✓ Recovered from failures!\n")


async def example_etl_pipeline():
    """
    Example 4: ETL Pipeline
    
    Extract-Transform-Load with parallel extraction.
    """
    print("=" * 60)
    print("Example 4: ETL Pipeline")
    print("=" * 60)
    
    flow = Flow()
    
    # EXTRACT (parallel)
    @flow.node()
    async def extract_customers() -> list[dict]:
        """Extract customer data."""
        print("  Extracting customers...")
        await asyncio.sleep(0.1)
        return [
            {"id": 1, "name": "Alice", "tier": "gold"},
            {"id": 2, "name": "Bob", "tier": "silver"},
            {"id": 3, "name": "Charlie", "tier": "gold"},
        ]
    
    @flow.node()
    async def extract_orders() -> list[dict]:
        """Extract order data."""
        print("  Extracting orders...")
        await asyncio.sleep(0.1)
        return [
            {"customer_id": 1, "amount": 150.00},
            {"customer_id": 1, "amount": 75.50},
            {"customer_id": 2, "amount": 200.00},
            {"customer_id": 3, "amount": 50.00},
            {"customer_id": 3, "amount": 300.00},
        ]
    
    @flow.node()
    async def extract_products() -> list[dict]:
        """Extract product data."""
        print("  Extracting products...")
        await asyncio.sleep(0.1)
        return [{"id": 1, "name": "Widget", "price": 25.00}]
    
    # TRANSFORM
    @flow.node()
    async def transform_join(
        extract_customers: list[dict],
        extract_orders: list[dict]
    ) -> list[dict]:
        """Join customers with orders."""
        print("  Transforming: joining data...")
        customer_map = {c["id"]: c for c in extract_customers}
        return [
            {
                **order,
                "customer_name": customer_map[order["customer_id"]]["name"],
                "customer_tier": customer_map[order["customer_id"]]["tier"],
            }
            for order in extract_orders
        ]
    
    @flow.node()
    async def transform_aggregate(transform_join: list[dict]) -> dict:
        """Aggregate by customer tier."""
        print("  Transforming: aggregating...")
        totals = {}
        for record in transform_join:
            tier = record["customer_tier"]
            totals[tier] = totals.get(tier, 0) + record["amount"]
        return totals
    
    # LOAD
    @flow.node()
    async def load_report(
        transform_aggregate: dict,
        extract_products: list[dict]
    ) -> str:
        """Generate final report."""
        print("  Loading: generating report...")
        lines = ["=== Sales Report ==="]
        for tier, total in sorted(transform_aggregate.items()):
            lines.append(f"  {tier.upper()}: ${total:.2f}")
        lines.append(f"  Products in catalog: {len(extract_products)}")
        return "\n".join(lines)
    
    print("\nPipeline Structure:")
    print(flow.visualize())
    
    print("\nExecuting pipeline:")
    start = time.time()
    result = await flow.execute()
    elapsed = (time.time() - start) * 1000
    
    print(f"\n{result['load_report']}")
    print(f"\nExecution time: {elapsed:.0f}ms")
    print(f"Cache stats: {result.cache_hits} hits, {result.cache_misses} misses")
    print("✓ ETL pipeline complete!\n")


async def example_targeted_execution():
    """
    Example 5: Targeted Execution
    
    Execute only what's needed for specific targets.
    """
    print("=" * 60)
    print("Example 5: Targeted Execution")
    print("=" * 60)
    
    flow = Flow()
    executed = []
    
    @flow.node()
    async def compute_a() -> int:
        executed.append("a")
        return 1
    
    @flow.node()
    async def compute_b(compute_a: int) -> int:
        executed.append("b")
        return compute_a + 1
    
    @flow.node()
    async def compute_c() -> int:
        executed.append("c")
        return 100
    
    @flow.node()
    async def compute_d(compute_c: int) -> int:
        executed.append("d")
        return compute_c + 1
    
    @flow.node()
    async def final(compute_b: int, compute_d: int) -> int:
        executed.append("final")
        return compute_b + compute_d
    
    print("\nFull graph:")
    print(flow.visualize())
    
    # Execute only 'compute_b' and its dependencies
    print("\nExecuting only 'compute_b' and dependencies:")
    executed.clear()
    result = await flow.execute(targets=["compute_b"])
    
    print(f"  Executed: {executed}")
    print(f"  Result: compute_b = {result['compute_b']}")
    print(f"  Note: compute_c and compute_d were NOT executed!")
    print("✓ Targeted execution works!\n")


async def example_input_override():
    """
    Example 6: Input Overrides
    
    Bypass expensive computation by providing inputs directly.
    """
    print("=" * 60)
    print("Example 6: Input Overrides")
    print("=" * 60)
    
    flow = Flow()
    
    @flow.node()
    async def train_model() -> dict:
        """Expensive: train ML model (simulated)."""
        print("  Training model... (this takes a while)")
        await asyncio.sleep(1.0)
        return {"weights": [0.1, 0.2, 0.3], "accuracy": 0.95}
    
    @flow.node()
    async def predict(train_model: dict) -> list:
        """Make predictions using the trained model."""
        weights = train_model["weights"]
        return [sum(weights)] * 5  # Dummy prediction
    
    @flow.node()
    async def evaluate(predict: list) -> float:
        """Evaluate predictions."""
        return sum(predict) / len(predict)
    
    # Without override - slow
    print("\nWithout override:")
    start = time.time()
    result1 = await flow.execute()
    print(f"  Time: {(time.time() - start) * 1000:.0f}ms")
    print(f"  Evaluation: {result1['evaluate']}")
    
    # With override - fast (skip training!)
    print("\nWith model override (skip training):")
    await flow.clear_cache()  # Clear cache to ensure fair comparison
    
    pretrained_model = {"weights": [0.5, 0.5, 0.5], "accuracy": 0.99}
    
    start = time.time()
    result2 = await flow.execute(inputs={"train_model": pretrained_model})
    print(f"  Time: {(time.time() - start) * 1000:.0f}ms")
    print(f"  Evaluation: {result2['evaluate']}")
    
    print("✓ Input override allows using pre-computed results!\n")


async def example_concurrency_control():
    """
    Example 7: Concurrency Control
    
    Limit parallel executions to avoid overwhelming resources.
    """
    print("=" * 60)
    print("Example 7: Concurrency Control")
    print("=" * 60)
    
    concurrent_count = 0
    max_concurrent = 0
    lock = asyncio.Lock()
    
    async def make_api_call(name: str) -> str:
        nonlocal concurrent_count, max_concurrent
        async with lock:
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            print(f"  {name}: Starting (concurrent: {concurrent_count})")
        
        await asyncio.sleep(0.1)  # Simulate API call
        
        async with lock:
            concurrent_count -= 1
            print(f"  {name}: Done")
        
        return f"{name}_result"
    
    # Flow with concurrency limit
    flow = Flow(max_concurrency=2)
    
    # Create node functions with proper closure binding
    def create_node_func(idx):
        async def node_func() -> str:
            return await make_api_call(f"api_{idx}")
        return node_func
    
    for i in range(5):
        flow.add_node(create_node_func(i), name=f"api_{i}")
    
    print(f"\n5 independent API calls with max_concurrency=2:")
    await flow.execute()
    
    print(f"\nMax concurrent calls: {max_concurrent}")
    print(f"Expected: 2 (our limit)")
    print("✓ Concurrency control works!\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  FLUX DATAFLOW ENGINE - EXAMPLES")
    print("=" * 60 + "\n")
    
    await example_basic_flow()
    await example_caching()
    await example_error_handling()
    await example_etl_pipeline()
    await example_targeted_execution()
    await example_input_override()
    await example_concurrency_control()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
