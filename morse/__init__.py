"""
Morse: Huffman Coding Engine

A complete Huffman coding implementation with visualization.
Watch your text flow through the tree. Finally understand compression.

Quick Start:
    >>> from morse import encode, decode, build_tree
    >>> 
    >>> text = "HELLO WORLD"
    >>> tree = build_tree(text)
    >>> bits, _ = encode(text)
    >>> decoded = decode(bits, tree)
    >>> 
    >>> # Visualize!
    >>> from morse import visualize
    >>> print(visualize("ABRACADABRA"))

Compression:
    >>> from morse import compress, decompress
    >>> compressed = compress("Hello, World!")
    >>> decompressed = decompress(compressed)

How Huffman Coding Works:
    1. Count symbol frequencies
    2. Build tree bottom-up (greedy algorithm)
    3. Assign codes by tree traversal (left=0, right=1)
    4. More frequent symbols get shorter codes
    5. Result is an optimal prefix-free code

The Algorithm:
    - Start with leaf nodes for each symbol
    - Repeatedly merge the two lowest-frequency nodes
    - The code for a symbol is the path from root to leaf
    - Prefix-free: no code is a prefix of another

Why It Matters:
    Huffman coding is used in ZIP, GZIP, JPEG, PNG, MP3,
    and countless other formats. It's one of the most
    elegant algorithms in computer science.
"""

from .morse import (
    # Core classes
    HuffmanNode,
    HuffmanTree,
    HuffmanBuilder,
    HuffmanCodec,
    CompressedData,
    
    # Bit utilities
    BitWriter,
    BitReader,
    
    # Convenience functions
    compress,
    decompress,
    encode,
    decode,
    build_tree,
    visualize,
    
    # Visualization
    visualize_encoding,
    visualize_tree_building,
    compare_compression,
)

__version__ = "1.0.0"
__author__ = "chrismaghuhn"

__all__ = [
    # Core
    'HuffmanNode',
    'HuffmanTree',
    'HuffmanBuilder',
    'HuffmanCodec',
    'CompressedData',
    
    # Utilities
    'BitWriter',
    'BitReader',
    
    # Functions
    'compress',
    'decompress',
    'encode',
    'decode',
    'build_tree',
    'visualize',
    
    # Visualization
    'visualize_encoding',
    'visualize_tree_building',
    'compare_compression',
]
