#!/usr/bin/env python3
"""
Morse Usage Examples

Huffman Coding Engine with Visualization.
Watch your text flow through the tree!
"""

from morse import (
    # Core
    HuffmanBuilder,
    HuffmanCodec,
    
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


def example_basic():
    """
    Example 1: Basic Encoding/Decoding
    """
    print("=" * 60)
    print("Example 1: Basic Encoding/Decoding")
    print("=" * 60)
    
    text = "HELLO WORLD"
    print(f"\nOriginal: \"{text}\"")
    
    # Build tree and encode
    tree = build_tree(text)
    bits, _ = encode(text)
    
    print(f"Encoded:  {bits}")
    print(f"Bits: {len(bits)} (vs {len(text) * 8} for ASCII)")
    
    # Decode
    decoded = decode(bits, tree)
    print(f"Decoded:  \"{decoded}\"")
    print()


def example_code_table():
    """
    Example 2: View the Code Table
    """
    print("=" * 60)
    print("Example 2: The Huffman Code Table")
    print("=" * 60)
    
    text = "ABRACADABRA"
    tree = build_tree(text)
    
    print(f"\nText: \"{text}\"")
    print()
    print(tree.to_code_table())
    print()


def example_tree_visualization():
    """
    Example 3: Visualize the Huffman Tree
    """
    print("=" * 60)
    print("Example 3: 🌲 The Huffman Tree")
    print("=" * 60)
    
    text = "MISSISSIPPI"
    tree = build_tree(text)
    
    print(f"\nText: \"{text}\"")
    print()
    print(tree.visualize())
    print()


def example_encoding_trace():
    """
    Example 4: Watch Encoding Step by Step
    """
    print("=" * 60)
    print("Example 4: 🔍 Watch the Encoding")
    print("=" * 60)
    
    print(visualize_encoding("ABBA"))
    print()


def example_tree_building():
    """
    Example 5: Watch the Tree Being Built
    """
    print("=" * 60)
    print("Example 5: 🔨 Tree Construction")
    print("=" * 60)
    
    print(visualize_tree_building("ABRACADABRA"))
    print()


def example_compression_stats():
    """
    Example 6: Compression Statistics
    """
    print("=" * 60)
    print("Example 6: 📊 Compression Analysis")
    print("=" * 60)
    
    # Text with skewed frequency (compresses well)
    text = "AAAAAAAAABBBCCDD"
    print(f"\nText: \"{text}\"")
    print(compare_compression(text))
    
    print("\n" + "-" * 60)
    
    # More uniform text (compresses less)
    text2 = "ABCDEFGHIJ"
    print(f"\nText: \"{text2}\"")
    print(compare_compression(text2))
    print()


def example_full_compression():
    """
    Example 7: Full Compress/Decompress Cycle
    """
    print("=" * 60)
    print("Example 7: 📦 Full Compression")
    print("=" * 60)
    
    text = "The quick brown fox jumps over the lazy dog."
    print(f"\nOriginal: \"{text}\"")
    print(f"Original size: {len(text)} bytes ({len(text) * 8} bits)")
    
    # Compress
    compressed = compress(text)
    print(f"Compressed: {len(compressed.data)} bytes + tree")
    
    # Decompress
    decompressed = decompress(compressed)
    print(f"Decompressed: \"{decompressed}\"")
    
    # Verify
    assert text == decompressed
    print("\n✓ Roundtrip successful!")
    print()


def example_real_text():
    """
    Example 8: Real-World Text Compression
    """
    print("=" * 60)
    print("Example 8: 📚 Real Text Analysis")
    print("=" * 60)
    
    # A paragraph of real text
    text = """
    Huffman coding is a data compression algorithm developed by David Huffman 
    in 1952 while he was a student at MIT. The algorithm builds a binary tree 
    based on the frequency of characters in the input, with more frequent 
    characters receiving shorter codes. This greedy algorithm produces an 
    optimal prefix-free code, meaning no code is a prefix of any other code.
    """
    
    text = ' '.join(text.split())  # Normalize whitespace
    
    tree = build_tree(text)
    stats = tree.get_stats(text)
    
    print(f"\nText length: {len(text)} characters")
    print(f"Unique symbols: {len(tree.codes)}")
    print(f"Original bits: {stats['original_bits']}")
    print(f"Encoded bits: {stats['encoded_bits']}")
    print(f"Compression ratio: {stats['compression_ratio']*100:.1f}%")
    print(f"Space saved: {stats['savings_percent']:.1f}%")
    
    # Show most frequent symbols
    from collections import Counter
    freq = Counter(text)
    most_common = freq.most_common(5)
    
    print("\nMost frequent symbols (shorter codes):")
    for char, count in most_common:
        display = repr(char) if char not in ' \n\t' else f"'{char}'"
        code = tree.codes[char]
        print(f"  {display}: count={count:3d}, code={code} ({len(code)} bits)")
    
    # Show least frequent
    least_common = freq.most_common()[-5:]
    print("\nLeast frequent symbols (longer codes):")
    for char, count in least_common:
        display = repr(char) if char not in ' \n\t' else f"'{char}'"
        code = tree.codes[char]
        print(f"  {display}: count={count:3d}, code={code} ({len(code)} bits)")
    print()


def example_graphviz():
    """
    Example 9: Graphviz Export
    """
    print("=" * 60)
    print("Example 9: 📊 Graphviz Export")
    print("=" * 60)
    
    text = "ABCD"
    tree = build_tree(text)
    
    print(f"\nText: \"{text}\"")
    print("\nDOT output (paste into https://dreampuf.github.io/GraphvizOnline/):")
    print("-" * 40)
    print(tree.to_dot())
    print("-" * 40)
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ███╗   ███╗ ██████╗ ██████╗ ███████╗███████╗                ║
║  ████╗ ████║██╔═══██╗██╔══██╗██╔════╝██╔════╝                ║
║  ██╔████╔██║██║   ██║██████╔╝███████╗█████╗                  ║
║  ██║╚██╔╝██║██║   ██║██╔══██╗╚════██║██╔══╝                  ║
║  ██║ ╚═╝ ██║╚██████╔╝██║  ██║███████║███████╗                ║
║  ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝                ║
║                                                               ║
║          🌲 Huffman Coding Engine 🌲                          ║
║                                                               ║
║   Watch your text flow through the tree.                      ║
║   Finally understand how compression works.                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_code_table()
    example_tree_visualization()
    example_encoding_trace()
    example_tree_building()
    example_compression_stats()
    example_full_compression()
    example_real_text()
    example_graphviz()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
