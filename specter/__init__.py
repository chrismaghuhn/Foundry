"""
SPECTER: Phantom Type State Machine

Demonstration / reference implementation — not for production deployment.

State machines where invalid transitions are IMPOSSIBLE TO WRITE.

The type checker (mypy/pyright) catches invalid transitions at compile time,
not runtime. Zero runtime overhead - it's just types.

Usage:
    from specter import SpecterBuilder, SpecterCodeGen, StateMarker
    
    # Define states
    class Off(StateMarker): pass
    class On(StateMarker): pass
    
    # Build state machine
    definition = (SpecterBuilder("LightSwitch")
        .initial(Off)
        .transition("turn_on", Off, On)
        .transition("turn_off", On, Off)
        .build())
    
    # Generate type-safe code
    code = SpecterCodeGen(definition).generate()
    print(code)  # Copy this into your project!

Author: chrismaghuhn
License: MIT
"""

from .specter import (
    # Core types
    StateMarker,
    StateMachine,
    Transition,
    StateDefinition,
    
    # Builder
    SpecterBuilder,
    
    # Code generation
    SpecterCodeGen,
    
    # Runtime machine
    RuntimeMachine,
    
    # Visualization
    generate_mermaid,
    generate_ascii_diagram,
    
    # Example states
    Idle, Starting, Running, Paused, Stopping, Stopped, Error,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    'StateMarker', 'StateMachine', 'Transition', 'StateDefinition',
    'SpecterBuilder', 'SpecterCodeGen', 'RuntimeMachine',
    'generate_mermaid', 'generate_ascii_diagram',
    'Idle', 'Starting', 'Running', 'Paused', 'Stopping', 'Stopped', 'Error',
]
