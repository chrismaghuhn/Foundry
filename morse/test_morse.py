"""Tests for morse."""

import pytest
from collections import Counter
from morse import (
    # Core
    HuffmanNode,
    HuffmanTree,
    HuffmanBuilder,
    HuffmanCodec,
    CompressedData,
    
    # Utilities
    BitWriter,
    BitReader,
    
    # Functions
    compress,
    decompress,
    encode,
    decode,
    build_tree,
    visualize,
    visualize_encoding,
    visualize_tree_building,
    compare_compression,
)


# =============================================================================
# HuffmanNode Tests
# =============================================================================

class TestHuffmanNode:
    """Test Huffman tree nodes."""
    
    def test_leaf_node(self):
        node = HuffmanNode(frequency=5, symbol='A')
        assert node.is_leaf()
        assert node.frequency == 5
        assert node.symbol == 'A'
    
    def test_internal_node(self):
        left = HuffmanNode(frequency=2, symbol='A')
        right = HuffmanNode(frequency=3, symbol='B')
        internal = HuffmanNode(frequency=5, left=left, right=right)
        
        assert not internal.is_leaf()
        assert internal.left == left
        assert internal.right == right
    
    def test_node_comparison(self):
        node1 = HuffmanNode(frequency=2, symbol='A')
        node2 = HuffmanNode(frequency=5, symbol='B')
        
        assert node1 < node2  # Lower frequency comes first


# =============================================================================
# Tree Building Tests
# =============================================================================

class TestTreeBuilding:
    """Test Huffman tree construction."""
    
    def test_simple_tree(self):
        tree = HuffmanBuilder.from_text("AAABBC")
        assert tree.root is not None
        assert tree.root.frequency == 6
    
    def test_single_char(self):
        tree = HuffmanBuilder.from_text("AAAA")
        assert 'A' in tree.codes
        assert tree.codes['A'] == '0'  # Single char gets code '0'
    
    def test_two_chars(self):
        tree = HuffmanBuilder.from_text("AB")
        assert 'A' in tree.codes
        assert 'B' in tree.codes
        assert len(tree.codes['A']) == 1
        assert len(tree.codes['B']) == 1
    
    def test_from_frequencies(self):
        freq = {'A': 5, 'B': 2, 'C': 1}
        tree = HuffmanBuilder.from_frequencies(freq)
        
        # Most frequent should have shortest code
        assert len(tree.codes['A']) <= len(tree.codes['B'])
        assert len(tree.codes['A']) <= len(tree.codes['C'])
    
    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            HuffmanBuilder.from_text("")
    
    def test_empty_frequencies_raises(self):
        with pytest.raises(ValueError):
            HuffmanBuilder.from_frequencies({})


# =============================================================================
# Encoding/Decoding Tests
# =============================================================================

class TestEncodeDecode:
    """Test encoding and decoding."""
    
    def test_encode_simple(self):
        tree = HuffmanBuilder.from_text("AAABBC")
        encoded = tree.encode("AB")
        assert isinstance(encoded, str)
        assert all(c in '01' for c in encoded)
    
    def test_decode_simple(self):
        tree = HuffmanBuilder.from_text("AAABBC")
        encoded = tree.encode("ABC")
        decoded = tree.decode(encoded)
        assert decoded == "ABC"
    
    def test_roundtrip(self):
        text = "HELLO WORLD"
        tree = HuffmanBuilder.from_text(text)
        encoded = tree.encode(text)
        decoded = tree.decode(encoded)
        assert decoded == text
    
    def test_roundtrip_long_text(self):
        text = "The quick brown fox jumps over the lazy dog. " * 10
        tree = HuffmanBuilder.from_text(text)
        encoded = tree.encode(text)
        decoded = tree.decode(encoded)
        assert decoded == text
    
    def test_encode_unknown_symbol_raises(self):
        tree = HuffmanBuilder.from_text("ABC")
        with pytest.raises(ValueError):
            tree.encode("ABCD")  # D not in tree
    
    def test_decode_invalid_bits_raises(self):
        tree = HuffmanBuilder.from_text("AB")
        with pytest.raises(ValueError):
            tree.decode("012")  # Invalid bit


# =============================================================================
# Compression Tests
# =============================================================================

class TestCompression:
    """Test compression functionality."""
    
    def test_compress_decompress(self):
        text = "AAABBBCCCD"
        compressed = compress(text)
        decompressed = decompress(compressed)
        assert decompressed == text
    
    def test_compression_ratio(self):
        # Text with uneven distribution should compress well
        text = "A" * 100 + "B" * 10 + "C"
        tree = HuffmanBuilder.from_text(text)
        stats = tree.get_stats(text)
        
        # Should achieve compression
        assert stats['compression_ratio'] < 1.0
        assert stats['savings_percent'] > 0
    
    def test_compression_stats(self):
        text = "HELLO WORLD"
        compressed, stats = HuffmanCodec.compress_with_stats(text)
        
        assert 'original_bits' in stats
        assert 'encoded_bits' in stats
        assert 'compression_ratio' in stats
        assert 'savings_percent' in stats
    
    def test_compressed_data_attributes(self):
        text = "TEST"
        compressed = compress(text)
        
        assert isinstance(compressed.data, bytes)
        assert isinstance(compressed.padding, int)
        assert isinstance(compressed.tree, HuffmanTree)
        assert compressed.original_length == len(text)


# =============================================================================
# BitWriter/BitReader Tests
# =============================================================================

class TestBitStream:
    """Test bit stream utilities."""
    
    def test_bit_writer(self):
        writer = BitWriter()
        writer.write_bits("10101010")
        data, padding = writer.flush()
        
        assert len(data) == 1
        assert data[0] == 0b10101010
        assert padding == 0
    
    def test_bit_writer_padding(self):
        writer = BitWriter()
        writer.write_bits("1010")  # 4 bits
        data, padding = writer.flush()
        
        assert len(data) == 1
        assert padding == 4
    
    def test_bit_reader(self):
        data = bytes([0b10101010])
        reader = BitReader(data)
        
        bits = reader.read_bits(8)
        assert bits == "10101010"
    
    def test_bit_reader_with_padding(self):
        data = bytes([0b10100000])  # Last 4 bits are padding
        reader = BitReader(data, padding=4)
        
        bits = reader.read_bits(4)
        assert bits == "1010"


# =============================================================================
# Code Properties Tests
# =============================================================================

class TestCodeProperties:
    """Test Huffman code properties."""
    
    def test_prefix_free(self):
        """Huffman codes are prefix-free (no code is prefix of another)."""
        text = "ABCDEFGHIJ" * 10
        tree = HuffmanBuilder.from_text(text)
        
        codes = list(tree.codes.values())
        for i, code1 in enumerate(codes):
            for code2 in codes[i+1:]:
                assert not code1.startswith(code2)
                assert not code2.startswith(code1)
    
    def test_optimal_length(self):
        """More frequent symbols should have shorter codes."""
        # Create text with known frequencies
        text = "A" * 100 + "B" * 50 + "C" * 25 + "D" * 10
        tree = HuffmanBuilder.from_text(text)
        
        # A is most frequent, should have shortest or equal code
        assert len(tree.codes['A']) <= len(tree.codes['B'])
        assert len(tree.codes['B']) <= len(tree.codes['C'])


# =============================================================================
# Visualization Tests
# =============================================================================

class TestVisualization:
    """Test visualization output."""
    
    def test_visualize_encoding(self):
        result = visualize_encoding("ABC")
        assert "HUFFMAN" in result
        assert "Code Table" in result
    
    def test_visualize_tree_building(self):
        result = visualize_tree_building("AABBC")
        assert "TREE CONSTRUCTION" in result
        assert "Frequency" in result
    
    def test_compare_compression(self):
        result = compare_compression("HELLO WORLD")
        assert "COMPRESSION" in result
        assert "Saved" in result
    
    def test_tree_visualize(self):
        tree = HuffmanBuilder.from_text("ABCD")
        viz = tree.visualize()
        assert "Huffman Tree" in viz
    
    def test_code_table(self):
        tree = HuffmanBuilder.from_text("ABC")
        table = tree.to_code_table()
        assert "Code Table" in table
        assert "Symbol" in table
    
    def test_to_dot(self):
        tree = HuffmanBuilder.from_text("AB")
        dot = tree.to_dot()
        assert "digraph" in dot


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_whitespace_text(self):
        text = "   \n\t  "
        tree = HuffmanBuilder.from_text(text)
        encoded = tree.encode(text)
        decoded = tree.decode(encoded)
        assert decoded == text
    
    def test_special_characters(self):
        text = "Hello, World! @#$%^&*()"
        tree = HuffmanBuilder.from_text(text)
        encoded = tree.encode(text)
        decoded = tree.decode(encoded)
        assert decoded == text
    
    def test_unicode_text(self):
        text = "Héllo Wörld 你好世界"
        tree = HuffmanBuilder.from_text(text)
        encoded = tree.encode(text)
        decoded = tree.decode(encoded)
        assert decoded == text
    
    def test_repeated_single_char(self):
        text = "X" * 1000
        compressed = compress(text)
        decompressed = decompress(compressed)
        assert decompressed == text


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Full integration tests."""
    
    def test_convenience_functions(self):
        text = "HELLO"
        bits, tree = encode(text)
        decoded = decode(bits, tree)
        assert decoded == text
    
    def test_build_tree_function(self):
        tree = build_tree("ABCD")
        assert isinstance(tree, HuffmanTree)
        assert len(tree.codes) == 4
    
    def test_visualize_function(self):
        result = visualize("TEST")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_full_workflow(self):
        # Complete workflow test
        text = "The Huffman algorithm is elegant!"
        
        # Build tree
        tree = build_tree(text)
        
        # Encode
        bits, _ = encode(text)
        
        # Check compression
        stats = tree.get_stats(text)
        
        # Decode
        decoded = decode(bits, tree)
        
        assert decoded == text
        assert stats['original_bits'] > stats['encoded_bits']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
