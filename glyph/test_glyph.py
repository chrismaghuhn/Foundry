"""Tests for glyph."""

import pytest
import asyncio
from glyph import (
    # Main
    GlyphCompiler,
    CompiledGlyph,
    glyph,
    parse,
    
    # Graph
    DataflowGraph,
    Node,
    
    # Parsing
    CharGrid,
    Box,
    Arrow,
    BoxDetector,
    ArrowTracer,
    
    # Execution
    Executor,
    ExecutionContext,
    NodeFunction,
    
    # Templates
    TEMPLATES,
)


# =============================================================================
# CharGrid Tests
# =============================================================================

class TestCharGrid:
    """Test the 2D character grid."""
    
    def test_basic_creation(self):
        grid = CharGrid("abc\ndef")
        assert grid.width == 3
        assert grid.height == 2
    
    def test_get_character(self):
        grid = CharGrid("ab\ncd")
        assert grid.get(0, 0) == 'a'
        assert grid.get(1, 0) == 'b'
        assert grid.get(0, 1) == 'c'
        assert grid.get(1, 1) == 'd'
    
    def test_out_of_bounds(self):
        grid = CharGrid("ab")
        assert grid.get(10, 10) == ' '
        assert grid.get(-1, 0) == ' '
    
    def test_claim_cell(self):
        grid = CharGrid("ab")
        assert not grid.is_claimed(0, 0)
        grid.claim(0, 0)
        assert grid.is_claimed(0, 0)
    
    def test_get_region(self):
        grid = CharGrid("abcd\nefgh\nijkl")
        region = grid.get_region(1, 0, 2, 2)
        assert region == ['bc', 'fg']


# =============================================================================
# Box Detection Tests
# =============================================================================

class TestBoxDetection:
    """Test box detection in various styles."""
    
    def test_unicode_box(self):
        source = '''
┌───────┐
│ hello │
└───────┘
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        assert len(boxes) == 1
        assert boxes[0].label == "hello"
    
    def test_double_line_box(self):
        source = '''
╔═══════╗
║ test  ║
╚═══════╝
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        assert len(boxes) == 1
        assert boxes[0].label == "test"
    
    def test_ascii_box(self):
        source = '''
+-------+
| ascii |
+-------+
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        assert len(boxes) == 1
        assert boxes[0].label == "ascii"
    
    def test_multiple_boxes(self):
        source = '''
┌───────┐     ┌───────┐
│  one  │     │  two  │
└───────┘     └───────┘
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        assert len(boxes) == 2
        labels = {b.label for b in boxes}
        assert labels == {"one", "two"}
    
    def test_box_position(self):
        source = '''
┌───┐
│ A │
└───┘
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        box = boxes[0]
        assert box.width == 5
        assert box.height == 3


# =============================================================================
# Arrow Tracing Tests
# =============================================================================

class TestArrowTracing:
    """Test arrow detection between boxes."""
    
    def test_simple_arrow(self):
        source = '''
┌───┐     ┌───┐
│ A │────>│ B │
└───┘     └───┘
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        tracer = ArrowTracer(grid, boxes)
        arrows = tracer.find_all()
        
        assert len(arrows) == 1
        assert arrows[0].source.label == "A"
        assert arrows[0].target.label == "B"
    
    def test_double_line_arrow(self):
        source = '''
╔═══╗      ╔═══╗
║ A ║═════>║ B ║
╚═══╝      ╚═══╝
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        tracer = ArrowTracer(grid, boxes)
        arrows = tracer.find_all()
        
        assert len(arrows) == 1
    
    def test_ascii_arrow(self):
        source = '''
+---+     +---+
| A |---->| B |
+---+     +---+
'''
        grid = CharGrid(source)
        detector = BoxDetector(grid)
        boxes = detector.find_all()
        
        tracer = ArrowTracer(grid, boxes)
        arrows = tracer.find_all()
        
        assert len(arrows) == 1


# =============================================================================
# Graph Construction Tests
# =============================================================================

class TestGraphConstruction:
    """Test dataflow graph building."""
    
    def test_simple_chain(self):
        source = '''
┌───┐     ┌───┐     ┌───┐
│ A │────>│ B │────>│ C │
└───┘     └───┘     └───┘
'''
        graph = parse(source)
        
        assert len(graph.nodes) == 3
        assert len(graph.sources) == 1
        assert len(graph.sinks) == 1
    
    def test_topological_order(self):
        source = '''
┌───┐     ┌───┐     ┌───┐
│ A │────>│ B │────>│ C │
└───┘     └───┘     └───┘
'''
        graph = parse(source)
        order = graph.topological_order()
        
        labels = [n.label for n in order]
        # A must come before B, B before C
        assert labels.index('A') < labels.index('B')
        assert labels.index('B') < labels.index('C')
    
    def test_to_dot(self):
        source = '''
┌───┐     ┌───┐
│ A │────>│ B │
└───┘     └───┘
'''
        graph = parse(source)
        dot = graph.to_dot()
        
        assert 'digraph' in dot
        assert '"node_' in dot


# =============================================================================
# Execution Tests
# =============================================================================

class TestExecution:
    """Test dataflow execution."""
    
    def test_input_double_print(self):
        source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
'''
        result = glyph(source, input_data=[21])
        
        assert 42 in [int(x) for x in result.print_output]
    
    def test_chain_operations(self):
        source = '''
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  square  │────>│ output  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
'''
        result = glyph(source, input_data=[3])
        
        # (3 * 2)² = 36
        assert 36 in result.output_data
    
    def test_double_line_boxes(self):
        source = '''
╔═════════╗      ╔══════════╗      ╔═════════╗
║  input  ║═════>║  double  ║═════>║ output  ║
╚═════════╝      ╚══════════╝      ╚═════════╝
'''
        result = glyph(source, input_data=[10])
        
        assert 20 in result.output_data
    
    def test_ascii_boxes(self):
        source = '''
+----------+     +-----------+     +----------+
|  input   |---->|  double   |---->|  output  |
+----------+     +-----------+     +----------+
'''
        result = glyph(source, input_data=[5])
        
        assert 10 in result.output_data


# =============================================================================
# Built-in Operations Tests
# =============================================================================

class TestBuiltinOps:
    """Test built-in node operations."""
    
    def test_double(self):
        source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''
        result = glyph(source, input_data=[7])
        assert 14 in result.output_data
    
    def test_square(self):
        source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  square  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''
        result = glyph(source, input_data=[5])
        assert 25 in result.output_data
    
    def test_increment(self):
        source = '''
┌─────────┐     ┌─────┐     ┌─────────┐
│  input  │────>│  +1 │────>│ output  │
└─────────┘     └─────┘     └─────────┘
'''
        result = glyph(source, input_data=[99])
        assert 100 in result.output_data


# =============================================================================
# Template Tests
# =============================================================================

class TestTemplates:
    """Test pre-defined templates."""
    
    def test_simple_template(self):
        result = glyph(TEMPLATES['simple'], input_data=[10])
        assert '20' in result.print_output
    
    def test_chain_template(self):
        result = glyph(TEMPLATES['chain'], input_data=[2])
        # (2 * 2)² = 16
        assert '16' in result.print_output
    
    def test_fancy_template(self):
        result = glyph(TEMPLATES['fancy'], input_data=[5])
        assert '10' in result.print_output
    
    def test_ascii_template(self):
        result = glyph(TEMPLATES['ascii'], input_data=[3])
        assert '6' in result.print_output


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error cases."""
    
    def test_no_boxes(self):
        with pytest.raises(ValueError, match="No boxes found"):
            glyph("just some text")
    
    def test_empty_source(self):
        with pytest.raises(ValueError):
            glyph("")


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Full integration tests."""
    
    def test_realistic_pipeline(self):
        """Test a realistic data processing pipeline."""
        source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  +1     │────>│  print  │
└─────────┘     └──────────┘     └─────────┘     └─────────┘
'''
        # 10 * 2 + 1 = 21
        result = glyph(source, input_data=[10])
        assert '21' in result.print_output
    
    def test_compiled_reuse(self):
        """Test that compiled programs can be reused."""
        source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''
        compiler = GlyphCompiler()
        compiled = compiler.compile(source)
        
        # Run multiple times
        result1 = asyncio.run(compiled.execute([5]))
        result2 = asyncio.run(compiled.execute([10]))
        
        assert 10 in result1.output_data
        assert 20 in result2.output_data


# =============================================================================
# Custom Operations Tests
# =============================================================================

class TestCustomOperations:
    """Test custom node operations."""
    
    def test_custom_operation(self):
        class TripleNode(NodeFunction):
            async def execute(self, inputs, context):
                if inputs:
                    return inputs[0] * 3
                return None
        
        source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  triple  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''
        compiler = GlyphCompiler(custom_ops={'triple': TripleNode})
        compiled = compiler.compile(source)
        result = asyncio.run(compiled.execute([7]))
        
        assert 21 in result.output_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
