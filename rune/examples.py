#!/usr/bin/env python3
"""
Rune Usage Examples

Demonstrates real-world scenarios for the sandboxed expression evaluator.
"""

from rune import Rune, RuType, ExecutionLimits, FuelExhaustedError, RuntimeError


def example_basic_expressions():
    """
    Example 1: Basic Expression Evaluation
    """
    print("=" * 60)
    print("Example 1: Basic Expressions")
    print("=" * 60)
    
    engine = Rune()
    
    expressions = [
        ("2 + 2", {}),
        ("10 * 5 - 3", {}),
        ("2 ** 10", {}),
        ("'Hello' + ' ' + 'World'", {}),
        ("true and not false", {}),
        ("10 > 5 and 5 < 20", {}),
    ]
    
    for expr, vars in expressions:
        result = engine.evaluate(expr, vars)
        print(f"  {expr} = {result}")
    
    print()


def example_variables():
    """
    Example 2: Using Variables
    """
    print("=" * 60)
    print("Example 2: Variables from Context")
    print("=" * 60)
    
    engine = Rune()
    
    # Simple variable substitution
    result = engine.evaluate("x + y", {"x": 10, "y": 20})
    print(f"  x + y (x=10, y=20) = {result}")
    
    # Complex expression with multiple variables
    result = engine.evaluate(
        "base_price * quantity * (1 - discount)",
        {"base_price": 99.99, "quantity": 5, "discount": 0.15}
    )
    print(f"  Price calculation = ${result:.2f}")
    
    # Nested object access
    user = {"name": "Alice", "age": 30, "premium": True}
    result = engine.evaluate(
        "if user.premium then user.name + ' (VIP)' else user.name",
        {"user": user}
    )
    print(f"  User greeting = {result}")
    
    print()


def example_conditionals():
    """
    Example 3: Conditional Logic
    """
    print("=" * 60)
    print("Example 3: Conditional Logic")
    print("=" * 60)
    
    engine = Rune()
    
    # Ternary operator
    result = engine.evaluate("score >= 60 ? 'Pass' : 'Fail'", {"score": 75})
    print(f"  Grade (score=75): {result}")
    
    result = engine.evaluate("score >= 60 ? 'Pass' : 'Fail'", {"score": 45})
    print(f"  Grade (score=45): {result}")
    
    # If-then-else
    tier_expr = """
        if amount >= 1000 then 'Gold'
        else if amount >= 500 then 'Silver'
        else if amount >= 100 then 'Bronze'
        else 'Basic'
    """
    
    for amount in [1500, 750, 200, 50]:
        result = engine.evaluate(tier_expr, {"amount": amount})
        print(f"  Tier (amount={amount}): {result}")
    
    print()


def example_list_operations():
    """
    Example 4: List Operations
    """
    print("=" * 60)
    print("Example 4: List Operations")
    print("=" * 60)
    
    engine = Rune()
    
    # Basic list functions
    data = {"scores": [85, 92, 78, 95, 88]}
    
    print(f"  Data: {data['scores']}")
    print(f"  sum(scores) = {engine.evaluate('sum(scores)', data)}")
    print(f"  avg(scores) = {engine.evaluate('avg(scores)', data)}")
    print(f"  min(scores, scores) = {engine.evaluate('min(first(scores), last(scores))', data)}")
    print(f"  count(scores) = {engine.evaluate('count(scores)', data)}")
    print(f"  first(scores) = {engine.evaluate('first(scores)', data)}")
    print(f"  last(scores) = {engine.evaluate('last(scores)', data)}")
    
    # List literal and manipulation
    result = engine.evaluate("sort([3, 1, 4, 1, 5, 9, 2, 6])")
    print(f"  sort([3,1,4,1,5,9,2,6]) = {result}")
    
    result = engine.evaluate("unique([1, 2, 2, 3, 3, 3])")
    print(f"  unique([1,2,2,3,3,3]) = {result}")
    
    result = engine.evaluate("reverse([1, 2, 3, 4, 5])")
    print(f"  reverse([1,2,3,4,5]) = {result}")
    
    print()


def example_string_functions():
    """
    Example 5: String Functions
    """
    print("=" * 60)
    print("Example 5: String Functions")
    print("=" * 60)
    
    engine = Rune()
    
    text = {"s": "  Hello, World!  "}
    
    print(f"  Original: {repr(text['s'])}")
    print(f"  trim(s) = {repr(engine.evaluate('trim(s)', text))}")
    print(f"  upper(s) = {repr(engine.evaluate('upper(s)', text))}")
    print(f"  lower(s) = {repr(engine.evaluate('lower(s)', text))}")
    print(f"  len(s) = {engine.evaluate('len(s)', text)}")
    
    print()
    
    # String predicates
    url = {"url": "https://example.com/page"}
    print(f"  URL: {url['url']}")
    print(f"  starts_with(url, 'https') = {engine.evaluate('starts_with(url, \"https\")', url)}")
    print(f"  ends_with(url, '.com') = {engine.evaluate('ends_with(url, \".com\")', url)}")
    print(f"  contains(url, 'example') = {engine.evaluate('contains(url, \"example\")', url)}")
    
    print()


def example_custom_functions():
    """
    Example 6: Custom Functions
    """
    print("=" * 60)
    print("Example 6: Custom Functions")
    print("=" * 60)
    
    engine = Rune()
    
    # Register custom functions
    engine.register_function(
        "double",
        lambda x: x * 2,
        [RuType.NUMBER],
        RuType.NUMBER
    )
    
    engine.register_function(
        "clamp",
        lambda x, lo, hi: max(lo, min(x, hi)),
        [RuType.NUMBER, RuType.NUMBER, RuType.NUMBER],
        RuType.NUMBER
    )
    
    engine.register_function(
        "greet",
        lambda name: f"Hello, {name}!",
        [RuType.STRING],
        RuType.STRING
    )
    
    print(f"  double(21) = {engine.evaluate('double(21)')}")
    print(f"  clamp(15, 0, 10) = {engine.evaluate('clamp(15, 0, 10)')}")
    print(f"  clamp(-5, 0, 10) = {engine.evaluate('clamp(-5, 0, 10)')}")
    print(f"  greet('Alice') = {engine.evaluate('greet(\"Alice\")')}")
    
    # Use custom functions in complex expressions
    result = engine.evaluate(
        "if score > 50 then greet(name) else 'Score too low'",
        {"score": 75, "name": "Bob"}
    )
    print(f"  Conditional greeting: {result}")
    
    print()


def example_compiled_expressions():
    """
    Example 7: Compiled Expressions for Performance
    """
    print("=" * 60)
    print("Example 7: Compiled Expressions")
    print("=" * 60)
    
    engine = Rune()
    
    # Compile once, use many times
    pricing = engine.compile("unit_price * quantity * (1 - discount)")
    
    orders = [
        {"unit_price": 10.00, "quantity": 100, "discount": 0.10},
        {"unit_price": 25.50, "quantity": 50, "discount": 0.15},
        {"unit_price": 5.00, "quantity": 200, "discount": 0.05},
    ]
    
    print("  Compiled expression: unit_price * quantity * (1 - discount)")
    print()
    
    for i, order in enumerate(orders, 1):
        total = pricing.evaluate(order)
        print(f"  Order {i}: ${total:.2f}")
    
    print()


def example_validation_rules():
    """
    Example 8: Validation Rules
    """
    print("=" * 60)
    print("Example 8: Validation Rules")
    print("=" * 60)
    
    engine = Rune()
    
    # Define validation rules as expressions
    rules = {
        "age_valid": "age >= 18 and age <= 120",
        "email_valid": "contains(email, '@') and contains(email, '.')",
        "password_strong": "len(password) >= 8",
        "username_valid": "len(username) >= 3 and len(username) <= 20",
    }
    
    # Compile rules for reuse
    compiled_rules = {name: engine.compile(rule) for name, rule in rules.items()}
    
    # Test data
    users = [
        {"username": "alice", "email": "alice@example.com", "password": "secret123", "age": 25},
        {"username": "bo", "email": "invalid-email", "password": "short", "age": 15},
        {"username": "charlie_long_name", "email": "charlie@test.org", "password": "verysecure!", "age": 30},
    ]
    
    for user in users:
        print(f"\n  User: {user['username']}")
        for rule_name, rule in compiled_rules.items():
            result = rule.evaluate(user)
            status = "✓" if result else "✗"
            print(f"    {status} {rule_name}")
    
    print()


def example_resource_limits():
    """
    Example 9: Resource Limits (Safety)
    """
    print("=" * 60)
    print("Example 9: Resource Limits")
    print("=" * 60)
    
    # Create engine with strict limits
    strict_engine = Rune(limits=ExecutionLimits(
        max_fuel=100,
        max_string_length=50,
        max_list_length=10
    ))
    
    # Fuel exhaustion
    print("  Testing fuel exhaustion:")
    try:
        # This uses too much fuel
        strict_engine.evaluate("1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1")
    except FuelExhaustedError as e:
        print(f"    Caught: {e}")
    
    # String length limit
    print("  Testing string length limit:")
    try:
        strict_engine.evaluate("'x' + 'x' + 'x' + 'x' + 'x'" * 20)
    except Exception as e:
        print(f"    Caught: {type(e).__name__}")
    
    # Normal engine handles complex expressions fine
    normal_engine = Rune()
    result = normal_engine.evaluate("sum([1,2,3,4,5,6,7,8,9,10])")
    print(f"  Normal engine: sum([1..10]) = {result}")
    
    print()


def example_real_world_pricing():
    """
    Example 10: Real-World Pricing Engine
    """
    print("=" * 60)
    print("Example 10: Real-World Pricing Engine")
    print("=" * 60)
    
    engine = Rune()
    
    # Register domain-specific functions
    import math
    engine.register_function(
        "shipping_cost",
        lambda weight, distance: 5.0 + (weight * 0.1) + (distance * 0.01),
        [RuType.NUMBER, RuType.NUMBER],
        RuType.NUMBER
    )
    
    engine.register_function(
        "tax_rate",
        lambda state: {"CA": 0.0725, "NY": 0.08, "TX": 0.0625}.get(state, 0.05),
        [RuType.STRING],
        RuType.NUMBER
    )
    
    # Complex pricing formula
    pricing_formula = """
        if quantity >= 100 then
            base_price * quantity * 0.85
        else if quantity >= 50 then
            base_price * quantity * 0.90
        else if quantity >= 10 then
            base_price * quantity * 0.95
        else
            base_price * quantity
    """
    
    total_formula = """
        subtotal + (subtotal * tax_rate(state)) + shipping_cost(weight, distance)
    """
    
    # Calculate order
    order = {
        "base_price": 29.99,
        "quantity": 75,
        "state": "CA",
        "weight": 50,
        "distance": 500
    }
    
    subtotal = engine.evaluate(pricing_formula, order)
    order["subtotal"] = subtotal
    
    total = engine.evaluate(total_formula, order)
    
    print(f"  Order: {order['quantity']} items @ ${order['base_price']}")
    print(f"  Subtotal (with bulk discount): ${subtotal:.2f}")
    print(f"  Tax ({order['state']}): ${subtotal * engine.evaluate('tax_rate(state)', order):.2f}")
    print(f"  Shipping: ${engine.evaluate('shipping_cost(weight, distance)', order):.2f}")
    print(f"  Total: ${total:.2f}")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  RUNE EXPRESSION ENGINE - EXAMPLES")
    print("=" * 60 + "\n")
    
    example_basic_expressions()
    example_variables()
    example_conditionals()
    example_list_operations()
    example_string_functions()
    example_custom_functions()
    example_compiled_expressions()
    example_validation_rules()
    example_resource_limits()
    example_real_world_pricing()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
