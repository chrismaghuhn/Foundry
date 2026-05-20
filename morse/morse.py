"""
Morse: Huffman Coding Engine

A complete Huffman coding implementation with visualization.
Watch your text flow through the tree. Finally understand compression.

Huffman coding (1952) is one of the most elegant algorithms in CS:
- Greedy construction produces optimal prefix-free codes
- More frequent symbols get shorter codes
- Used in ZIP, GZIP, JPEG, PNG, MP3, and countless other formats

How it works:

    1. Count symbol frequencies in input
    2. Build a binary tree bottom-up:
       - Start with leaf nodes for each symbol
       - Repeatedly merge the two lowest-frequency nodes
       - Combined node's frequency = sum of children
    3. Assign codes by tree traversal:
       - Left edge = 0
       - Right edge = 1
       - Code = path from root to leaf
    4. Encode: Replace each symbol with its code
    5. Decode: Walk the tree following the bits

Example:
    Input: "AAAAABBBCCCD" (12 chars = 96 bits)
    
    Frequencies: A=5, B=3, C=3, D=1
    
    Tree:
                (12)
               /    \\
             (7)    (5)
            /   \\     \\
          (4)   (3)   (5)
           A     B     ...
    
    Codes: A=0, B=10, C=110, D=111
    Encoded: 000001010101101101111 (21 bits)
    Compression: 78% reduction!

The magic is that frequent symbols get short codes,
and the prefix-free property means no ambiguity in decoding.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import heapq
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterator, Any
from io import StringIO


# =============================================================================
# Huffman Tree
# =============================================================================

@dataclass
class HuffmanNode:
    """
    A node in the Huffman tree.
    
    Internal nodes have left and right children.
    Leaf nodes have a symbol.
    All nodes have a frequency (weight).
    """
    frequency: int
    symbol: Optional[str] = None
    left: Optional['HuffmanNode'] = None
    right: Optional['HuffmanNode'] = None
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (has a symbol)."""
        return self.symbol is not None
    
    def __lt__(self, other: 'HuffmanNode') -> bool:
        """For heap comparison - lower frequency = higher priority."""
        if self.frequency != other.frequency:
            return self.frequency < other.frequency
        # Tie-breaker: leaves before internal, then by symbol
        if self.is_leaf() != other.is_leaf():
            return self.is_leaf()
        if self.symbol and other.symbol:
            return self.symbol < other.symbol
        return False
    
    def __repr__(self) -> str:
        if self.is_leaf():
            return f"Leaf({self.symbol!r}, freq={self.frequency})"
        return f"Node(freq={self.frequency})"


@dataclass
class HuffmanTree:
    """
    A complete Huffman tree with encoding/decoding capabilities.
    
    The tree is built from frequency analysis and provides:
    - Code generation for each symbol
    - Encoding of strings to bit sequences
    - Decoding of bit sequences back to strings
    - ASCII visualization of the tree structure
    """
    root: HuffmanNode
    codes: Dict[str, str] = field(default_factory=dict)
    reverse_codes: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate codes from tree structure."""
        self._generate_codes(self.root, "")
        self.reverse_codes = {v: k for k, v in self.codes.items()}
    
    def _generate_codes(self, node: Optional[HuffmanNode], prefix: str) -> None:
        """Recursively generate codes by tree traversal."""
        if node is None:
            return
        
        if node.is_leaf():
            # Handle single-symbol edge case
            code = prefix if prefix else "0"
            self.codes[node.symbol] = code
        else:
            self._generate_codes(node.left, prefix + "0")
            self._generate_codes(node.right, prefix + "1")
    
    def encode(self, text: str) -> str:
        """
        Encode text to a bit string.
        
        Args:
            text: The text to encode
        
        Returns:
            A string of '0' and '1' characters
        
        Raises:
            ValueError: If text contains symbols not in the tree
        """
        bits = []
        for char in text:
            if char not in self.codes:
                raise ValueError(f"Symbol {char!r} not in Huffman tree")
            bits.append(self.codes[char])
        return ''.join(bits)
    
    def decode(self, bits: str) -> str:
        """
        Decode a bit string back to text.
        
        Args:
            bits: A string of '0' and '1' characters
        
        Returns:
            The decoded text
        
        Raises:
            ValueError: If bit string is invalid
        """
        result = []
        current = self.root
        
        for bit in bits:
            if bit not in '01':
                raise ValueError(f"Invalid bit: {bit!r}")
            
            if bit == '0':
                current = current.left
            else:
                current = current.right
            
            if current is None:
                raise ValueError("Invalid bit sequence")
            
            if current.is_leaf():
                result.append(current.symbol)
                current = self.root
        
        # Check we ended at root (complete decode)
        if current != self.root:
            raise ValueError("Incomplete bit sequence")
        
        return ''.join(result)
    
    def encode_with_trace(self, text: str) -> Iterator[Tuple[str, str, List[str]]]:
        """
        Encode with step-by-step trace.
        
        Yields:
            (symbol, code, path) tuples where path shows tree traversal
        """
        for char in text:
            code = self.codes[char]
            path = self._trace_path(char)
            yield (char, code, path)
    
    def _trace_path(self, symbol: str) -> List[str]:
        """Get the path from root to a symbol."""
        path = ["root"]
        code = self.codes[symbol]
        current = self.root
        
        for bit in code:
            if bit == '0':
                path.append("← left (0)")
                current = current.left
            else:
                path.append("→ right (1)")
                current = current.right
        
        path.append(f"[{symbol!r}]")
        return path
    
    def get_stats(self, text: str) -> Dict[str, Any]:
        """
        Calculate compression statistics.
        
        Returns:
            Dict with original_bits, encoded_bits, ratio, savings
        """
        original_bits = len(text) * 8  # Assuming ASCII
        encoded = self.encode(text)
        encoded_bits = len(encoded)
        
        ratio = encoded_bits / original_bits if original_bits > 0 else 0
        savings = 1 - ratio
        
        return {
            "original_bits": original_bits,
            "encoded_bits": encoded_bits,
            "compression_ratio": ratio,
            "savings_percent": savings * 100,
            "avg_bits_per_symbol": encoded_bits / len(text) if text else 0,
        }
    
    def visualize(self) -> str:
        """
        Generate ASCII art visualization of the tree.
        """
        lines = []
        lines.append("Huffman Tree")
        lines.append("=" * 50)
        self._visualize_node(self.root, "", True, lines)
        return '\n'.join(lines)
    
    def _visualize_node(
        self,
        node: Optional[HuffmanNode],
        prefix: str,
        is_last: bool,
        lines: List[str]
    ) -> None:
        """Recursively build tree visualization."""
        if node is None:
            return
        
        connector = "└── " if is_last else "├── "
        
        if node.is_leaf():
            # Show symbol and its code
            code = self.codes.get(node.symbol, "?")
            display_char = repr(node.symbol) if node.symbol not in ' \n\t' else f"'{node.symbol}'"
            lines.append(f"{prefix}{connector}[{display_char}] freq={node.frequency} code={code}")
        else:
            lines.append(f"{prefix}{connector}({node.frequency})")
        
        # Recurse to children
        child_prefix = prefix + ("    " if is_last else "│   ")
        
        if node.left or node.right:
            self._visualize_node(node.left, child_prefix, node.right is None, lines)
            if node.right:
                self._visualize_node(node.right, child_prefix, True, lines)
    
    def to_code_table(self) -> str:
        """Generate a formatted code table."""
        lines = []
        lines.append("Code Table")
        lines.append("=" * 40)
        lines.append(f"{'Symbol':<10} {'Code':<20} {'Length':<6}")
        lines.append("-" * 40)
        
        # Sort by code length, then by symbol
        sorted_codes = sorted(self.codes.items(), key=lambda x: (len(x[1]), x[0]))
        
        for symbol, code in sorted_codes:
            display = repr(symbol) if symbol not in ' \n\t' else f"'{symbol}'"
            lines.append(f"{display:<10} {code:<20} {len(code):<6}")
        
        return '\n'.join(lines)
    
    def to_dot(self) -> str:
        """Generate Graphviz DOT representation."""
        lines = ['digraph HuffmanTree {']
        lines.append('  node [shape=circle];')
        
        node_id = [0]
        
        def add_node(node: HuffmanNode, parent_id: Optional[int], edge_label: str) -> int:
            current_id = node_id[0]
            node_id[0] += 1
            
            if node.is_leaf():
                label = f"{node.symbol}\\n({node.frequency})"
                lines.append(f'  n{current_id} [label="{label}" shape=box];')
            else:
                lines.append(f'  n{current_id} [label="{node.frequency}"];')
            
            if parent_id is not None:
                lines.append(f'  n{parent_id} -> n{current_id} [label="{edge_label}"];')
            
            if node.left:
                add_node(node.left, current_id, "0")
            if node.right:
                add_node(node.right, current_id, "1")
            
            return current_id
        
        add_node(self.root, None, "")
        
        lines.append('}')
        return '\n'.join(lines)


# =============================================================================
# Huffman Builder
# =============================================================================

class HuffmanBuilder:
    """
    Builds Huffman trees from text or frequency tables.
    
    The classic Huffman algorithm:
    1. Create a leaf node for each symbol
    2. Build a min-heap of nodes by frequency
    3. While heap has more than one node:
       a. Pop two lowest-frequency nodes
       b. Create new internal node with these as children
       c. Push new node back to heap
    4. Remaining node is the root
    """
    
    @staticmethod
    def from_text(text: str) -> HuffmanTree:
        """
        Build a Huffman tree from input text.
        
        Args:
            text: The text to analyze
        
        Returns:
            A HuffmanTree optimized for this text
        """
        if not text:
            raise ValueError("Cannot build Huffman tree from empty text")
        
        # Count frequencies
        frequencies = Counter(text)
        
        return HuffmanBuilder.from_frequencies(frequencies)
    
    @staticmethod
    def from_frequencies(frequencies: Dict[str, int]) -> HuffmanTree:
        """
        Build a Huffman tree from a frequency table.
        
        Args:
            frequencies: Dict mapping symbols to their frequencies
        
        Returns:
            A HuffmanTree with optimal prefix-free codes
        """
        if not frequencies:
            raise ValueError("Cannot build Huffman tree from empty frequencies")
        
        # Create leaf nodes
        heap: List[HuffmanNode] = []
        for symbol, freq in frequencies.items():
            node = HuffmanNode(frequency=freq, symbol=symbol)
            heapq.heappush(heap, node)
        
        # Build tree bottom-up
        while len(heap) > 1:
            # Pop two lowest
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            
            # Create internal node
            internal = HuffmanNode(
                frequency=left.frequency + right.frequency,
                left=left,
                right=right
            )
            
            heapq.heappush(heap, internal)
        
        root = heap[0]
        return HuffmanTree(root=root)
    
    @staticmethod
    def build_with_trace(text: str) -> Iterator[Tuple[str, List[HuffmanNode]]]:
        """
        Build tree with step-by-step trace for visualization.
        
        Yields:
            (description, heap_state) tuples showing build progress
        """
        frequencies = Counter(text)
        
        # Create initial heap
        heap: List[HuffmanNode] = []
        for symbol, freq in sorted(frequencies.items()):
            node = HuffmanNode(frequency=freq, symbol=symbol)
            heapq.heappush(heap, node)
        
        yield ("Initial leaves", list(heap))
        
        step = 1
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            
            internal = HuffmanNode(
                frequency=left.frequency + right.frequency,
                left=left,
                right=right
            )
            
            heapq.heappush(heap, internal)
            
            left_desc = f"'{left.symbol}'" if left.is_leaf() else f"({left.frequency})"
            right_desc = f"'{right.symbol}'" if right.is_leaf() else f"({right.frequency})"
            
            yield (f"Step {step}: Merge {left_desc} + {right_desc} = ({internal.frequency})", list(heap))
            step += 1
        
        yield ("Complete!", list(heap))


# =============================================================================
# Bit Stream Utilities
# =============================================================================

class BitWriter:
    """
    Writes bits to a byte buffer.
    
    Accumulates bits until a full byte is ready,
    then flushes to the output buffer.
    """
    
    def __init__(self):
        self.buffer = bytearray()
        self.current_byte = 0
        self.bit_count = 0
    
    def write_bit(self, bit: int) -> None:
        """Write a single bit (0 or 1)."""
        self.current_byte = (self.current_byte << 1) | bit
        self.bit_count += 1
        
        if self.bit_count == 8:
            self.buffer.append(self.current_byte)
            self.current_byte = 0
            self.bit_count = 0
    
    def write_bits(self, bits: str) -> None:
        """Write a string of bits."""
        for b in bits:
            self.write_bit(int(b))
    
    def flush(self) -> bytes:
        """
        Flush remaining bits and return buffer.
        
        Pads with zeros if necessary.
        Returns (bytes, padding_bits).
        """
        padding = 0
        if self.bit_count > 0:
            padding = 8 - self.bit_count
            self.current_byte <<= padding
            self.buffer.append(self.current_byte)
        
        return bytes(self.buffer), padding


class BitReader:
    """
    Reads bits from a byte buffer.
    """
    
    def __init__(self, data: bytes, padding: int = 0):
        self.data = data
        self.padding = padding
        self.byte_index = 0
        self.bit_index = 0
        self.total_bits = len(data) * 8 - padding
    
    def read_bit(self) -> Optional[int]:
        """Read a single bit, or None if exhausted."""
        bit_pos = self.byte_index * 8 + self.bit_index
        if bit_pos >= self.total_bits:
            return None
        
        byte = self.data[self.byte_index]
        bit = (byte >> (7 - self.bit_index)) & 1
        
        self.bit_index += 1
        if self.bit_index == 8:
            self.bit_index = 0
            self.byte_index += 1
        
        return bit
    
    def read_bits(self, count: int) -> str:
        """Read multiple bits as a string."""
        result = []
        for _ in range(count):
            bit = self.read_bit()
            if bit is None:
                break
            result.append(str(bit))
        return ''.join(result)


# =============================================================================
# Codec - Complete Compression
# =============================================================================

@dataclass
class CompressedData:
    """Result of Huffman compression."""
    data: bytes
    padding: int
    tree: HuffmanTree
    original_length: int
    
    def decompress(self) -> str:
        """Decompress back to original text."""
        # Edge case: single symbol tree (only one unique char)
        if self.tree.root.is_leaf():
            return self.tree.root.symbol * self.original_length
        
        reader = BitReader(self.data, self.padding)
        result = []
        current = self.tree.root
        
        while len(result) < self.original_length:
            bit = reader.read_bit()
            if bit is None:
                break
            
            if bit == 0:
                current = current.left
            else:
                current = current.right
            
            if current is None:
                raise ValueError("Invalid bit sequence")
            
            if current.is_leaf():
                result.append(current.symbol)
                current = self.tree.root
        
        return ''.join(result)


class HuffmanCodec:
    """
    Complete Huffman compression codec.
    
    Provides high-level compress/decompress operations
    with tree serialization included.
    """
    
    @staticmethod
    def compress(text: str) -> CompressedData:
        """
        Compress text using Huffman coding.
        
        Returns CompressedData with everything needed to decompress.
        """
        if not text:
            raise ValueError("Cannot compress empty text")
        
        # Build tree
        tree = HuffmanBuilder.from_text(text)
        
        # Encode
        bits = tree.encode(text)
        
        # Convert to bytes
        writer = BitWriter()
        writer.write_bits(bits)
        data, padding = writer.flush()
        
        return CompressedData(
            data=data,
            padding=padding,
            tree=tree,
            original_length=len(text)
        )
    
    @staticmethod
    def compress_with_stats(text: str) -> Tuple[CompressedData, Dict[str, Any]]:
        """Compress and return statistics."""
        result = HuffmanCodec.compress(text)
        stats = result.tree.get_stats(text)
        stats["compressed_bytes"] = len(result.data)
        stats["original_bytes"] = len(text)
        return result, stats


# =============================================================================
# Visualization Helpers
# =============================================================================

def visualize_encoding(text: str, max_chars: int = 20) -> str:
    """
    Visualize the encoding process step by step.
    
    Shows each character being encoded through the tree.
    """
    if len(text) > max_chars:
        text = text[:max_chars]
    
    tree = HuffmanBuilder.from_text(text)
    lines = []
    
    lines.append("=" * 60)
    lines.append("🌲 HUFFMAN ENCODING VISUALIZATION")
    lines.append("=" * 60)
    lines.append(f"\nInput: \"{text}\"")
    lines.append(f"Length: {len(text)} characters")
    lines.append("\n" + tree.to_code_table())
    lines.append("\n" + "-" * 60)
    lines.append("Encoding Process:")
    lines.append("-" * 60)
    
    total_bits = []
    for symbol, code, path in tree.encode_with_trace(text):
        display = repr(symbol) if symbol not in ' \n\t' else f"'{symbol}'"
        lines.append(f"\n  {display} →")
        for step in path:
            lines.append(f"    {step}")
        lines.append(f"  Code: {code}")
        total_bits.append(code)
    
    encoded = ''.join(total_bits)
    lines.append("\n" + "=" * 60)
    lines.append(f"Encoded: {encoded}")
    lines.append(f"Total bits: {len(encoded)}")
    lines.append(f"Original bits (ASCII): {len(text) * 8}")
    lines.append(f"Compression: {(1 - len(encoded)/(len(text)*8))*100:.1f}% saved")
    lines.append("=" * 60)
    
    return '\n'.join(lines)


def visualize_tree_building(text: str) -> str:
    """
    Visualize the tree building process step by step.
    """
    lines = []
    
    lines.append("=" * 60)
    lines.append("🔨 HUFFMAN TREE CONSTRUCTION")
    lines.append("=" * 60)
    lines.append(f"\nInput: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
    
    # Show frequency analysis
    freq = Counter(text)
    lines.append("\nFrequency Analysis:")
    for char, count in sorted(freq.items(), key=lambda x: -x[1]):
        display = repr(char) if char not in ' \n\t' else f"'{char}'"
        bar = "█" * min(count, 30)
        lines.append(f"  {display}: {bar} ({count})")
    
    lines.append("\n" + "-" * 60)
    lines.append("Building Tree:")
    lines.append("-" * 60)
    
    for desc, heap in HuffmanBuilder.build_with_trace(text):
        lines.append(f"\n{desc}")
        heap_display = []
        for node in sorted(heap):
            if node.is_leaf():
                heap_display.append(f"'{node.symbol}':{node.frequency}")
            else:
                heap_display.append(f"({node.frequency})")
        lines.append(f"  Heap: [{', '.join(heap_display)}]")
    
    # Final tree
    tree = HuffmanBuilder.from_text(text)
    lines.append("\n" + "=" * 60)
    lines.append("Final Tree:")
    lines.append("=" * 60)
    lines.append(tree.visualize())
    
    return '\n'.join(lines)


def compare_compression(text: str) -> str:
    """
    Show compression comparison with statistics.
    """
    tree = HuffmanBuilder.from_text(text)
    stats = tree.get_stats(text)
    encoded = tree.encode(text)
    
    lines = []
    lines.append("=" * 60)
    lines.append("📊 COMPRESSION ANALYSIS")
    lines.append("=" * 60)
    
    lines.append(f"\nOriginal Text: {len(text)} characters")
    lines.append(f"Original Size: {stats['original_bits']} bits ({stats['original_bits']//8} bytes)")
    lines.append(f"\nEncoded Size: {stats['encoded_bits']} bits ({(stats['encoded_bits']+7)//8} bytes)")
    lines.append(f"Average bits/symbol: {stats['avg_bits_per_symbol']:.2f}")
    
    lines.append(f"\n{'─' * 40}")
    lines.append(f"Compression Ratio: {stats['compression_ratio']*100:.1f}%")
    lines.append(f"Space Saved: {stats['savings_percent']:.1f}%")
    lines.append(f"{'─' * 40}")
    
    # Visual bar
    saved = int(stats['savings_percent'] / 2)
    used = 50 - saved
    lines.append(f"\n[{'█' * used}{'░' * saved}]")
    lines.append(f" {'Used':<{used}}{'Saved':>{saved}}")
    
    return '\n'.join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def compress(text: str) -> CompressedData:
    """Compress text using Huffman coding."""
    return HuffmanCodec.compress(text)


def decompress(data: CompressedData) -> str:
    """Decompress Huffman-encoded data."""
    return data.decompress()


def encode(text: str) -> Tuple[str, HuffmanTree]:
    """Encode text, returning bit string and tree."""
    tree = HuffmanBuilder.from_text(text)
    return tree.encode(text), tree


def decode(bits: str, tree: HuffmanTree) -> str:
    """Decode bit string using tree."""
    return tree.decode(bits)


def build_tree(text: str) -> HuffmanTree:
    """Build a Huffman tree from text."""
    return HuffmanBuilder.from_text(text)


def visualize(text: str) -> str:
    """Visualize encoding process."""
    return visualize_encoding(text)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core classes
    'HuffmanNode',
    'HuffmanTree',
    'HuffmanBuilder',
    'HuffmanCodec',
    'CompressedData',
    
    # Bit utilities
    'BitWriter',
    'BitReader',
    
    # Convenience functions
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
