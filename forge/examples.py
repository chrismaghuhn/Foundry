#!/usr/bin/env python3
"""
Forge Usage Examples

Demonstrates real-world usage of validated finite state machines.
"""

import asyncio
from forge import (
    State,
    Event,
    StateMachine,
    analyze_machine,
    find_paths,
    state,
    event,
)


def example_basic_traffic_light():
    """
    Example 1: Basic Traffic Light
    """
    print("=" * 60)
    print("Example 1: Traffic Light")
    print("=" * 60)
    
    # Define states
    RED = State("red", initial=True)
    YELLOW = State("yellow")
    GREEN = State("green")
    
    # Define events
    TIMER = Event("timer")
    
    # Build machine (validation happens here)
    machine = (StateMachine.builder("traffic_light")
        .add_transition(RED, TIMER, GREEN)
        .add_transition(GREEN, TIMER, YELLOW)
        .add_transition(YELLOW, TIMER, RED)
        .build())
    
    print(f"\nMachine: {machine}")
    print(f"States: {[s.name for s in machine.states]}")
    
    # Create instance and run
    light = machine.create_instance()
    
    print(f"\nCycling through states:")
    for _ in range(6):
        print(f"  Current: {light.state.name}")
        light.send(TIMER)
    print()


def example_order_workflow():
    """
    Example 2: E-Commerce Order Workflow with Guards
    """
    print("=" * 60)
    print("Example 2: Order Workflow")
    print("=" * 60)
    
    # States
    PENDING = State("pending", initial=True)
    PAID = State("paid")
    SHIPPED = State("shipped")
    DELIVERED = State("delivered", final=True)
    CANCELLED = State("cancelled", final=True)
    
    # Events
    PAY = Event("pay")
    SHIP = Event("ship")
    DELIVER = Event("deliver")
    CANCEL = Event("cancel")
    
    # Guards
    def has_stock(ctx, payload):
        return ctx.get("stock", 0) > 0
    
    def payment_valid(ctx, payload):
        return payload and payload.get("amount", 0) >= ctx.get("price", 0)
    
    # Actions
    def reduce_stock(ctx, payload):
        ctx["stock"] -= 1
        print(f"    → Stock reduced to {ctx['stock']}")
    
    def log_cancellation(ctx, payload):
        print(f"    → Order cancelled, reason: {payload}")
    
    # Build machine
    machine = (StateMachine.builder("order")
        .add_transition(PENDING, PAY, PAID, 
                       guard=lambda c, p: has_stock(c, p) and payment_valid(c, p),
                       action=reduce_stock)
        .add_transition(PENDING, CANCEL, CANCELLED, action=log_cancellation)
        .add_transition(PAID, SHIP, SHIPPED)
        .add_transition(PAID, CANCEL, CANCELLED, action=log_cancellation)
        .add_transition(SHIPPED, DELIVER, DELIVERED)
        .build())
    
    # Successful order
    print("\n--- Order 1: Success ---")
    ctx1 = {"stock": 5, "price": 100}
    order1 = machine.create_instance(ctx1)
    
    print(f"  State: {order1.state.name}")
    order1.send(PAY, payload={"amount": 100})
    print(f"  State: {order1.state.name}")
    order1.send(SHIP)
    print(f"  State: {order1.state.name}")
    order1.send(DELIVER)
    print(f"  State: {order1.state.name} (final: {order1.is_final})")
    
    # Cancelled order
    print("\n--- Order 2: Cancelled ---")
    ctx2 = {"stock": 5, "price": 100}
    order2 = machine.create_instance(ctx2)
    
    print(f"  State: {order2.state.name}")
    order2.send(CANCEL, payload="Customer changed mind")
    print(f"  State: {order2.state.name} (final: {order2.is_final})")
    print()


def example_vending_machine():
    """
    Example 3: Vending Machine with Context
    """
    print("=" * 60)
    print("Example 3: Vending Machine")
    print("=" * 60)
    
    # States
    IDLE = State("idle", initial=True)
    ACCEPTING = State("accepting_money")
    DISPENSING = State("dispensing")
    
    # Events
    INSERT_COIN = Event("insert_coin")
    SELECT_ITEM = Event("select_item")
    DISPENSE = Event("dispense")
    CANCEL = Event("cancel")
    
    # Context class
    class VendingContext:
        def __init__(self):
            self.balance = 0
            self.prices = {"soda": 150, "chips": 100, "candy": 75}
            self.selected_item = None
        
        def __repr__(self):
            return f"VendingContext(balance={self.balance}, selected={self.selected_item})"
    
    # Guards
    def enough_money(ctx, payload):
        if ctx.selected_item is None:
            return False
        return ctx.balance >= ctx.prices.get(ctx.selected_item, float('inf'))
    
    # Actions
    def add_money(ctx, payload):
        amount = payload.get("amount", 0)
        ctx.balance += amount
        print(f"    → Inserted {amount}¢, balance: {ctx.balance}¢")
    
    def select(ctx, payload):
        item = payload.get("item")
        ctx.selected_item = item
        price = ctx.prices.get(item, 0)
        print(f"    → Selected {item} (price: {price}¢)")
    
    def dispense_item(ctx, payload):
        price = ctx.prices[ctx.selected_item]
        ctx.balance -= price
        print(f"    → Dispensing {ctx.selected_item}")
        print(f"    → Change: {ctx.balance}¢")
        ctx.selected_item = None
    
    def refund(ctx, payload):
        print(f"    → Refunding {ctx.balance}¢")
        ctx.balance = 0
        ctx.selected_item = None
    
    # Build machine
    machine = (StateMachine.builder("vending")
        .add_transition(IDLE, INSERT_COIN, ACCEPTING, action=add_money)
        .add_transition(ACCEPTING, INSERT_COIN, ACCEPTING, action=add_money)
        .add_transition(ACCEPTING, SELECT_ITEM, ACCEPTING, action=select)
        .add_transition(ACCEPTING, DISPENSE, DISPENSING, guard=enough_money)
        .add_transition(ACCEPTING, CANCEL, IDLE, action=refund)
        .add_transition(DISPENSING, DISPENSE, IDLE, action=dispense_item)
        .build())
    
    # Use the machine
    print("\n--- Buying a soda ---")
    ctx = VendingContext()
    vm = machine.create_instance(ctx)
    
    print(f"  State: {vm.state.name}")
    vm.send(INSERT_COIN, {"amount": 100})
    print(f"  State: {vm.state.name}")
    vm.send(SELECT_ITEM, {"item": "soda"})
    vm.send(INSERT_COIN, {"amount": 100})
    print(f"  State: {vm.state.name}")
    vm.send(DISPENSE)
    print(f"  State: {vm.state.name}")
    vm.send(DISPENSE)
    print(f"  State: {vm.state.name}")
    print()


async def example_async_workflow():
    """
    Example 4: Async File Processing Workflow
    """
    print("=" * 60)
    print("Example 4: Async File Processing")
    print("=" * 60)
    
    # States
    IDLE = State("idle", initial=True)
    DOWNLOADING = State("downloading")
    PROCESSING = State("processing")
    UPLOADING = State("uploading")
    DONE = State("done", final=True)
    
    # Events
    START = Event("start")
    DOWNLOADED = Event("downloaded")
    PROCESSED = Event("processed")
    UPLOADED = Event("uploaded")
    
    # Async actions
    async def download_file(ctx, payload):
        print(f"    → Downloading {payload['file']}...")
        await asyncio.sleep(0.1)
        ctx["data"] = f"content of {payload['file']}"
        print(f"    → Downloaded!")
    
    async def process_file(ctx, payload):
        print(f"    → Processing...")
        await asyncio.sleep(0.1)
        ctx["processed_data"] = ctx["data"].upper()
        print(f"    → Processed: {ctx['processed_data']}")
    
    async def upload_file(ctx, payload):
        print(f"    → Uploading...")
        await asyncio.sleep(0.1)
        print(f"    → Uploaded successfully!")
    
    # Build machine
    machine = (StateMachine.builder("file_processor")
        .add_transition(IDLE, START, DOWNLOADING)
        .add_transition(DOWNLOADING, DOWNLOADED, PROCESSING)
        .add_transition(PROCESSING, PROCESSED, UPLOADING)
        .add_transition(UPLOADING, UPLOADED, DONE)
        .on_enter(DOWNLOADING, download_file)
        .on_enter(PROCESSING, process_file)
        .on_enter(UPLOADING, upload_file)
        .build())
    
    # Run async workflow
    print("\n--- Processing file ---")
    ctx = {}
    processor = machine.create_instance(ctx)
    
    print(f"  State: {processor.state.name}")
    await processor.send_async(START, {"file": "data.txt"})
    print(f"  State: {processor.state.name}")
    await processor.send_async(DOWNLOADED)
    print(f"  State: {processor.state.name}")
    await processor.send_async(PROCESSED)
    print(f"  State: {processor.state.name}")
    await processor.send_async(UPLOADED)
    print(f"  State: {processor.state.name} (final: {processor.is_final})")
    print()


def example_validation_errors():
    """
    Example 5: Validation Catches Errors at Build Time
    """
    print("=" * 60)
    print("Example 5: Validation Errors")
    print("=" * 60)
    
    from forge import (
        NoInitialStateError,
        UnreachableStatesError,
        DeadEndStatesError,
    )
    
    # Error 1: No initial state
    print("\n--- No Initial State ---")
    try:
        (StateMachine.builder("bad1")
            .add_state(State("a"))
            .add_state(State("b"))
            .add_transition(State("a"), Event("e"), State("b"))
            .build())
    except NoInitialStateError as e:
        print(f"  Caught: {e}")
    
    # Error 2: Unreachable state
    print("\n--- Unreachable State ---")
    try:
        (StateMachine.builder("bad2")
            .add_state(State("start", initial=True))
            .add_state(State("middle"))
            .add_state(State("orphan", final=True))  # Never reached!
            .add_transition(State("start"), Event("go"), State("middle"))
            .add_transition(State("middle"), Event("back"), State("start"))
            .build())
    except UnreachableStatesError as e:
        print(f"  Caught: {e}")
    
    # Error 3: Dead end (non-final with no outgoing)
    print("\n--- Dead End State ---")
    try:
        (StateMachine.builder("bad3")
            .add_state(State("start", initial=True))
            .add_state(State("trap"))  # Not final, no outgoing!
            .add_transition(State("start"), Event("go"), State("trap"))
            .build())
    except DeadEndStatesError as e:
        print(f"  Caught: {e}")
    
    print("\n  ✓ All errors caught at build time, not runtime!")
    print()


def example_analysis():
    """
    Example 6: Machine Analysis and Visualization
    """
    print("=" * 60)
    print("Example 6: Analysis & Visualization")
    print("=" * 60)
    
    # Build a more complex machine
    START = State("start", initial=True)
    AUTHENTICATING = State("authenticating")
    AUTHORIZED = State("authorized")
    LOADING = State("loading")
    READY = State("ready")
    ERROR = State("error", final=True)
    LOGGED_OUT = State("logged_out", final=True)
    
    LOGIN = Event("login")
    AUTH_SUCCESS = Event("auth_success")
    AUTH_FAIL = Event("auth_fail")
    LOAD = Event("load")
    LOADED = Event("loaded")
    LOGOUT = Event("logout")
    
    machine = (StateMachine.builder("app")
        .add_transition(START, LOGIN, AUTHENTICATING)
        .add_transition(AUTHENTICATING, AUTH_SUCCESS, AUTHORIZED)
        .add_transition(AUTHENTICATING, AUTH_FAIL, ERROR)
        .add_transition(AUTHORIZED, LOAD, LOADING)
        .add_transition(LOADING, LOADED, READY)
        .add_transition(READY, LOGOUT, LOGGED_OUT)
        .add_transition(AUTHORIZED, LOGOUT, LOGGED_OUT)
        .build())
    
    # Analyze
    analysis = analyze_machine(machine)
    
    print(f"\nMachine Analysis:")
    print(f"  States: {analysis['state_count']}")
    print(f"  Events: {analysis['event_count']}")
    print(f"  Transitions: {analysis['transition_count']}")
    print(f"  Final states: {analysis['final_states']}")
    print(f"  Has cycles: {analysis['has_cycles']}")
    print(f"  Avg outgoing: {analysis['average_outgoing']:.2f}")
    
    # Find paths
    paths = find_paths(machine, START, READY)
    print(f"\n  Paths from 'start' to 'ready': {len(paths)}")
    for i, path in enumerate(paths, 1):
        steps = " → ".join(f"{s.name}[{e.name}]" for s, e in path)
        print(f"    {i}. {steps} → ready")
    
    # Generate DOT
    print(f"\nGraphviz DOT output:")
    print("-" * 40)
    print(machine.to_dot())
    print("-" * 40)
    print()


def example_history_tracking():
    """
    Example 7: Transition History for Debugging
    """
    print("=" * 60)
    print("Example 7: History Tracking")
    print("=" * 60)
    
    # Simple workflow
    A = State("A", initial=True)
    B = State("B")
    C = State("C")
    D = State("D", final=True)
    
    TO_B = Event("to_b")
    TO_C = Event("to_c")
    TO_D = Event("to_d")
    
    machine = (StateMachine.builder("workflow")
        .add_transition(A, TO_B, B)
        .add_transition(B, TO_C, C)
        .add_transition(C, TO_D, D)
        .build())
    
    instance = machine.create_instance()
    
    instance.send(TO_B, payload={"step": 1})
    instance.send(TO_C, payload={"step": 2})
    instance.send(TO_D, payload={"step": 3})
    
    print(f"\nTransition History:")
    for i, info in enumerate(instance.history, 1):
        print(f"  {i}. {info.source.name} --{info.event.name}--> {info.target.name}")
        print(f"      payload: {info.payload}")
    print()


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  FORGE - VALIDATED STATE MACHINES EXAMPLES")
    print("=" * 60 + "\n")
    
    example_basic_traffic_light()
    example_order_workflow()
    example_vending_machine()
    await example_async_workflow()
    example_validation_errors()
    example_analysis()
    example_history_tracking()
    
    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
