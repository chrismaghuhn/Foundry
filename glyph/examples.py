#!/usr/bin/env python3
"""
Glyph Usage Examples

ASCII Art → Executable Code

The diagram IS the program!
"""

from glyph import (
    glyph,
    GlyphCompiler,
    NodeFunction,
    TEMPLATES,
)


def example_basic():
    """
    Example 1: The Simplest Glyph Program
    """
    print("=" * 60)
    print("Example 1: Hello Glyph!")
    print("=" * 60)
    
    # This ASCII art IS the program:
    source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
'''
    
    print("\nSource code (ASCII art):")
    print(source)
    
    print("Running with input [21]:")
    result = glyph(source, input_data=[21])
    
    print(f"\nOutput: {result.print_output}")
    print()


def example_chain():
    """
    Example 2: Chained Operations
    """
    print("=" * 60)
    print("Example 2: Data Pipeline")
    print("=" * 60)
    
    source = '''
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  square  │────>│  print  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
'''
    
    print("\nPipeline: input → double → square → print")
    print(source)
    
    print("Running with input [3]:")
    print("  Expected: (3 × 2)² = 36")
    result = glyph(source, input_data=[3])
    print()


def example_different_styles():
    """
    Example 3: Multiple Box Styles
    """
    print("=" * 60)
    print("Example 3: Box Styles")
    print("=" * 60)
    
    print("\n--- Unicode Single Line ---")
    glyph(TEMPLATES['simple'], input_data=[5])
    
    print("\n--- Unicode Double Line ---")
    glyph(TEMPLATES['fancy'], input_data=[5])
    
    print("\n--- ASCII Style ---")
    glyph(TEMPLATES['ascii'], input_data=[5])
    print()


def example_custom_operation():
    """
    Example 4: Custom Operations
    """
    print("=" * 60)
    print("Example 4: Custom Operations")
    print("=" * 60)
    
    # Define a custom operation
    class CubeNode(NodeFunction):
        async def execute(self, inputs, context):
            if inputs:
                return inputs[0] ** 3
            return None
    
    class GreetNode(NodeFunction):
        async def execute(self, inputs, context):
            if inputs:
                return f"Hello, {inputs[0]}!"
            return None
    
    source = '''
┌─────────┐     ┌────────┐     ┌─────────┐
│  input  │────>│  cube  │────>│  print  │
└─────────┘     └────────┘     └─────────┘
'''
    
    print("\nCustom 'cube' operation:")
    print(source)
    
    compiler = GlyphCompiler(custom_ops={'cube': CubeNode})
    compiled = compiler.compile(source)
    
    import asyncio
    result = asyncio.run(compiled.execute([4]))
    
    print(f"\n  4³ = 64 ✓" if '64' in result.print_output else "  Error!")
    print()


def example_visualization():
    """
    Example 5: Graphviz Export
    """
    print("=" * 60)
    print("Example 5: Graphviz Visualization")
    print("=" * 60)
    
    source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''
    
    compiler = GlyphCompiler()
    compiled = compiler.compile(source)
    
    print("\nGraphviz DOT output:")
    print("-" * 40)
    print(compiled.to_dot())
    print("-" * 40)
    print("\n(Paste into https://dreampuf.github.io/GraphvizOnline/)")
    print()


def example_art():
    """
    Example 6: ASCII Art as Documentation
    """
    print("=" * 60)
    print("Example 6: Self-Documenting Code")
    print("=" * 60)
    
    print("""
The magic of Glyph: your documentation IS your code!

In a README.md file, you can write:

    ## Data Processing Pipeline
    
    Our ETL process works like this:
    
    ```
    ┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
    │  input  │────>│  double  │────>│  square  │────>│ output  │
    └─────────┘     └──────────┘     └──────────┘     └─────────┘
    ```
    
And that diagram is EXECUTABLE! No more "code doesn't match docs" bugs!
""")


def example_emoji_banner():
    """
    Print a fun banner showing what Glyph does.
    """
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗ ██╗  ██╗   ██╗██████╗ ██╗  ██╗                 ║
║  ██╔════╝ ██║  ╚██╗ ██╔╝██╔══██╗██║  ██║                 ║
║  ██║  ███╗██║   ╚████╔╝ ██████╔╝███████║                 ║
║  ██║   ██║██║    ╚██╔╝  ██╔═══╝ ██╔══██║                 ║
║  ╚██████╔╝███████╗██║   ██║     ██║  ██║                 ║
║   ╚═════╝ ╚══════╝╚═╝   ╚═╝     ╚═╝  ╚═╝                 ║
║                                                           ║
║        🎨 ASCII Art → 🔮 Executable Code                  ║
║                                                           ║
║   The diagram IS the program.                             ║
║   Draw boxes. Connect with arrows. Run!                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_emoji_banner()
    
    example_basic()
    example_chain()
    example_different_styles()
    example_custom_operation()
    example_visualization()
    example_art()
    
    print("=" * 60)
    print("  All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
