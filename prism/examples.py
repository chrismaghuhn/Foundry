#!/usr/bin/env python3
"""
Prism Usage Examples

Demonstrates real-world scenarios for the Prism query language.
"""

from prism import Prism, query


def example_basic_queries():
    """
    Example 1: Basic Property Access
    """
    print("=" * 60)
    print("Example 1: Basic Property Access")
    print("=" * 60)
    
    data = {
        "name": "Alice",
        "age": 30,
        "address": {
            "city": "New York",
            "zip": "10001"
        },
        "tags": ["developer", "python", "data"]
    }
    
    print(f"\nData: {data}\n")
    
    queries = [
        (".name", "Get name"),
        (".age", "Get age"),
        (".address.city", "Get nested city"),
        (".tags[0]", "Get first tag"),
        (".tags[-1]", "Get last tag"),
        (".tags | length", "Count tags"),
    ]
    
    for q, desc in queries:
        result = query(q, data)
        print(f"  {desc}")
        print(f"    Query: {q}")
        print(f"    Result: {result}\n")


def example_filtering():
    """
    Example 2: Filtering Collections
    """
    print("=" * 60)
    print("Example 2: Filtering Collections")
    print("=" * 60)
    
    users = [
        {"name": "Alice", "age": 30, "active": True, "role": "admin"},
        {"name": "Bob", "age": 17, "active": True, "role": "user"},
        {"name": "Charlie", "age": 25, "active": False, "role": "user"},
        {"name": "Diana", "age": 35, "active": True, "role": "admin"},
    ]
    
    print(f"\nUsers: {len(users)} records\n")
    
    queries = [
        (". | filter(.active)", "Active users"),
        (". | filter(.age >= 18)", "Adults only"),
        ('. | filter(.role == "admin")', "Admins only"),
        (". | filter(.active and .age >= 18)", "Active adults"),
    ]
    
    for q, desc in queries:
        result = query(q, users)
        names = [u["name"] for u in result]
        print(f"  {desc}")
        print(f"    Query: {q}")
        print(f"    Result: {names}\n")


def example_transformation():
    """
    Example 3: Data Transformation
    """
    print("=" * 60)
    print("Example 3: Data Transformation")
    print("=" * 60)
    
    products = [
        {"id": 1, "name": "Widget", "price": 9.99, "qty": 100},
        {"id": 2, "name": "Gadget", "price": 24.99, "qty": 50},
        {"id": 3, "name": "Gizmo", "price": 14.99, "qty": 75},
    ]
    
    print(f"\nProducts: {products}\n")
    
    # Extract just names
    result = query(". | map(.name)", products)
    print(f"  Extract names: {result}")
    
    # Calculate totals
    result = query(". | map(.price * .qty)", products)
    print(f"  Calculate values: {result}")
    
    # Select specific fields
    result = query(". | select(.name, .price)", products)
    print(f"  Select fields: {result}")
    
    # Transform structure
    result = query('. | map({product: .name, value: .price * .qty})', products)
    print(f"  Transform: {result}\n")


def example_aggregation():
    """
    Example 4: Aggregation Functions
    """
    print("=" * 60)
    print("Example 4: Aggregation Functions")
    print("=" * 60)
    
    sales = [
        {"region": "North", "amount": 1000},
        {"region": "South", "amount": 1500},
        {"region": "North", "amount": 800},
        {"region": "East", "amount": 2000},
        {"region": "South", "amount": 1200},
    ]
    
    print(f"\nSales data: {len(sales)} records\n")
    
    # Sum
    total = query(". | sum(.amount)", sales)
    print(f"  Total sales: ${total}")
    
    # Average
    avg = query(". | avg(.amount)", sales)
    print(f"  Average sale: ${avg:.2f}")
    
    # Min/Max
    min_sale = query(". | min(.amount)", sales)
    max_sale = query(". | max(.amount)", sales)
    print(f"  Range: ${min_sale} - ${max_sale}")
    
    # Group and count
    by_region = query(". | group(.region)", sales)
    print(f"\n  By region:")
    for region, items in by_region.items():
        region_total = sum(s["amount"] for s in items)
        print(f"    {region}: {len(items)} sales, ${region_total}")


def example_string_operations():
    """
    Example 5: String Operations
    """
    print("\n" + "=" * 60)
    print("Example 5: String Operations")
    print("=" * 60)
    
    data = {
        "title": "  Hello World  ",
        "tags": ["python", "data", "query"],
        "email": "USER@EXAMPLE.COM",
        "path": "/home/user/documents/file.txt"
    }
    
    print(f"\nData: {data}\n")
    
    queries = [
        (".title | trim", "Trim whitespace"),
        (".email | lower", "Lowercase email"),
        ('. | join(", ")', data["tags"]),
        ('.path | split("/")', "Split path"),
        ('.title | trim | upper', "Trim then uppercase"),
    ]
    
    print(f"  Trim: {query('.title | trim', data)!r}")
    print(f"  Lowercase: {query('.email | lower', data)}")
    print(f"  Join tags: {query('. | join(\", \")', data['tags'])}")
    print(f"  Split path: {query('. | split(\"/\")', data['path'])}")
    print(f"  Chain: {query('.title | trim | upper', data)}")


def example_conditional_logic():
    """
    Example 6: Conditional Logic
    """
    print("\n" + "=" * 60)
    print("Example 6: Conditional Logic")
    print("=" * 60)
    
    items = [
        {"name": "Item A", "stock": 100, "price": 10},
        {"name": "Item B", "stock": 0, "price": 20},
        {"name": "Item C", "stock": 5, "price": 15},
    ]
    
    print(f"\nItems: {items}\n")
    
    # Add status based on stock
    result = query(
        '. | map({name: .name, status: .stock > 0 ? "In Stock" : "Out of Stock"})',
        items
    )
    print(f"  With status: {result}")
    
    # Categorize by price
    result = query(
        '. | map({name: .name, tier: .price >= 15 ? "premium" : "standard"})',
        items
    )
    print(f"  With tier: {result}")


def example_complex_pipeline():
    """
    Example 7: Complex Pipeline
    """
    print("\n" + "=" * 60)
    print("Example 7: Complex Pipeline")
    print("=" * 60)
    
    orders = {
        "orders": [
            {"id": 1, "customer": "Alice", "items": [
                {"product": "Widget", "qty": 2, "price": 10},
                {"product": "Gadget", "qty": 1, "price": 25},
            ]},
            {"id": 2, "customer": "Bob", "items": [
                {"product": "Widget", "qty": 5, "price": 10},
            ]},
            {"id": 3, "customer": "Alice", "items": [
                {"product": "Gizmo", "qty": 3, "price": 15},
            ]},
        ]
    }
    
    print(f"\n{len(orders['orders'])} orders\n")
    
    # Get all products ordered
    products = query(
        ".orders | map(.items) | flatten | map(.product) | unique",
        orders
    )
    print(f"  Products ordered: {products}")
    
    # Orders by Alice
    alice_orders = query(
        '.orders | filter(.customer == "Alice") | length',
        orders
    )
    print(f"  Alice's orders: {alice_orders}")
    
    # Total items per order
    order_totals = query(
        ".orders | map({id: .id, total_items: .items | sum(.qty)})",
        orders
    )
    print(f"  Items per order: {order_totals}")


def example_config_extraction():
    """
    Example 8: Config File Extraction
    """
    print("\n" + "=" * 60)
    print("Example 8: Config File Extraction")
    print("=" * 60)
    
    config = {
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "debug": False
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "mydb",
            "pool": {"min": 5, "max": 20}
        },
        "features": {
            "auth": True,
            "cache": True,
            "logging": False
        }
    }
    
    print(f"\nConfig structure available\n")
    
    # Get specific values
    print(f"  App name: {query('.app.name', config)}")
    print(f"  DB connection: {query('.database.host', config)}:{query('.database.port', config)}")
    print(f"  Pool size: {query('.database.pool.min', config)}-{query('.database.pool.max', config)}")
    
    # Get enabled features
    enabled = query(
        ".features | entries | filter(.value) | map(.key)",
        config
    )
    print(f"  Enabled features: {enabled}")
    
    # With defaults
    timeout = query(".database.timeout | default(30)", config)
    print(f"  Timeout (with default): {timeout}")


def example_api_response():
    """
    Example 9: API Response Processing
    """
    print("\n" + "=" * 60)
    print("Example 9: API Response Processing")
    print("=" * 60)
    
    api_response = {
        "status": "success",
        "data": {
            "users": [
                {"id": 1, "username": "alice", "email": "alice@example.com", "verified": True},
                {"id": 2, "username": "bob", "email": "bob@example.com", "verified": False},
                {"id": 3, "username": "charlie", "email": "charlie@example.com", "verified": True},
            ],
            "pagination": {
                "page": 1,
                "per_page": 10,
                "total": 3
            }
        },
        "meta": {
            "request_id": "abc123",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
    
    print(f"\nAPI response received\n")
    
    # Check status
    print(f"  Status: {query('.status', api_response)}")
    
    # Get usernames
    usernames = query(".data.users | map(.username)", api_response)
    print(f"  Usernames: {usernames}")
    
    # Verified users only
    verified = query(
        ".data.users | filter(.verified) | map(.username)",
        api_response
    )
    print(f"  Verified users: {verified}")
    
    # Pagination info
    print(f"  Page {query('.data.pagination.page', api_response)} of {query('.data.pagination.total', api_response)} total")


def example_compiled_queries():
    """
    Example 10: Compiled Queries for Performance
    """
    print("\n" + "=" * 60)
    print("Example 10: Compiled Queries")
    print("=" * 60)
    
    prism = Prism()
    
    # Compile once, use many times
    get_name = prism.compile(".name")
    get_active_count = prism.compile(". | filter(.active) | length")
    
    datasets = [
        {"name": "Dataset A", "items": [{"active": True}, {"active": False}]},
        {"name": "Dataset B", "items": [{"active": True}, {"active": True}]},
        {"name": "Dataset C", "items": [{"active": False}]},
    ]
    
    print(f"\nProcessing {len(datasets)} datasets with compiled queries:\n")
    
    for ds in datasets:
        name = get_name(ds)
        active = get_active_count(ds["items"])
        print(f"  {name}: {active} active items")
    
    print("\n  (Compiled queries are cached and reused efficiently)")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  PRISM QUERY LANGUAGE - EXAMPLES")
    print("=" * 60 + "\n")
    
    example_basic_queries()
    example_filtering()
    example_transformation()
    example_aggregation()
    example_string_operations()
    example_conditional_logic()
    example_complex_pipeline()
    example_config_extraction()
    example_api_response()
    example_compiled_queries()
    
    print("\n" + "=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
