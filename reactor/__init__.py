"""
REACTOR: Async Event-Sourcing Engine with Time-Travel Debugging

Demonstration / reference implementation — not for production deployment.

"Travel through time. See the butterfly effect. Ask what-if."

Core Features:
- Event Sourcing: All state changes are immutable events
- Automatic Snapshots: O(1) state reconstruction
- Time Travel: Jump to any point in history
- What-If Analysis: Simulate alternate timelines
- Async Native: Built on asyncio
- Lock-Free Reads: Immutable snapshots

Usage:
    from reactor import Reactor
    
    reactor = Reactor()
    
    @reactor.on("user_created")
    def handle(state, event):
        state["users"] = state.get("users", {})
        state["users"][event.payload["id"]] = event.payload
        return state
    
    await reactor.emit("user_created", {"id": "1", "name": "Alice"})
    
    # Time travel
    past = reactor.time_travel.travel_to(5)
    print(past.state)
    
    # What-if
    alt = reactor.what_if.simulate_without_event(3)
    print(alt)

Author: chrismaghuhn
License: MIT
"""

from .reactor import (
    Event,
    EventLog,
    Snapshot,
    SnapshotManager,
    StateProjector,
    TimeTravelController,
    WhatIfEngine,
    Reactor,
    ReactorVisualizer,
)

__version__ = "1.0.0"
__all__ = [
    'Event',
    'EventLog',
    'Snapshot',
    'SnapshotManager',
    'StateProjector',
    'TimeTravelController',
    'WhatIfEngine',
    'Reactor',
    'ReactorVisualizer',
]
