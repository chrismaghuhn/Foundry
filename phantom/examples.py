#!/usr/bin/env python3
"""
Phantom Usage Examples

The Regex Engine You Can See!
Watch your regex "think" step by step.
"""

from phantom import (
    Regex,
    compile,
    match,
    search,
    fullmatch,
    trace,
    visualize,
)


def example_basic():
    """
    Example 1: Basic Matching
    """
    print("=" * 60)
    print("Example 1: Basic Matching")
    print("=" * 60)
    
    print("\n--- Literal matching ---")
    print(f"match('hello', 'hello world') = {match('hello', 'hello world').matched}")
    print(f"match('world', 'hello world') = {match('world', 'hello world').matched}")
    
    print("\n--- Search anywhere ---")
    result = search('world', 'hello world')
    print(f"search('world', 'hello world') = found at position {result.match_start}")
    
    print("\n--- Full match ---")
    print(f"fullmatch('hello', 'hello') = {fullmatch('hello', 'hello').matched}")
    print(f"fullmatch('hello', 'hello!') = {fullmatch('hello', 'hello!').matched}")
    print()


def example_quantifiers():
    """
    Example 2: Quantifiers
    """
    print("=" * 60)
    print("Example 2: Quantifiers (*, +, ?, {n,m})")
    print("=" * 60)
    
    print("\n--- Zero or more (*) ---")
    print(f"match('a*', '') = {match('a*', '').matched}")
    print(f"match('a*', 'aaa') = {match('a*', 'aaa').matched}")
    
    print("\n--- One or more (+) ---")
    print(f"match('a+', '') = {match('a+', '').matched}")
    print(f"match('a+', 'aaa') = {match('a+', 'aaa').matched}")
    
    print("\n--- Optional (?) ---")
    print(f"match('colou?r', 'color') = {match('colou?r', 'color').matched}")
    print(f"match('colou?r', 'colour') = {match('colou?r', 'colour').matched}")
    
    print("\n--- Bounded repetition ---")
    print(f"fullmatch('a{{2,4}}', 'a') = {fullmatch('a{2,4}', 'a').matched}")
    print(f"fullmatch('a{{2,4}}', 'aa') = {fullmatch('a{2,4}', 'aa').matched}")
    print(f"fullmatch('a{{2,4}}', 'aaaa') = {fullmatch('a{2,4}', 'aaaa').matched}")
    print(f"fullmatch('a{{2,4}}', 'aaaaa') = {fullmatch('a{2,4}', 'aaaaa').matched}")
    print()


def example_character_classes():
    """
    Example 3: Character Classes
    """
    print("=" * 60)
    print("Example 3: Character Classes")
    print("=" * 60)
    
    print("\n--- Simple class [abc] ---")
    print(f"match('[aeiou]', 'a') = {match('[aeiou]', 'a').matched}")
    print(f"match('[aeiou]', 'x') = {match('[aeiou]', 'x').matched}")
    
    print("\n--- Range [a-z] ---")
    print(f"match('[a-z]+', 'hello') = {match('[a-z]+', 'hello').matched}")
    print(f"match('[A-Z]+', 'hello') = {match('[A-Z]+', 'hello').matched}")
    
    print("\n--- Negated [^abc] ---")
    print(f"match('[^0-9]', 'a') = {match('[^0-9]', 'a').matched}")
    print(f"match('[^0-9]', '5') = {match('[^0-9]', '5').matched}")
    
    print("\n--- Shortcuts ---")
    digit_pat = r'\d+'
    word_pat = r'\w+'
    space_pat = r'\s+'
    print(f"match(r'\\d+', '123') = {match(digit_pat, '123').matched}")
    print(f"match(r'\\w+', 'hello_123') = {match(word_pat, 'hello_123').matched}")
    print(f"match(r'\\s+', '   ') = {match(space_pat, '   ').matched}")
    print()


def example_visualization():
    """
    Example 4: The Magic - Visualize the NFA!
    """
    print("=" * 60)
    print("Example 4: 👻 VISUALIZE THE NFA")
    print("=" * 60)
    
    pattern = "a+b*"
    print(f"\nPattern: {pattern}")
    print("\n" + visualize(pattern))
    print()


def example_trace():
    """
    Example 5: Watch the Regex Think!
    """
    print("=" * 60)
    print("Example 5: 🔮 WATCH THE REGEX THINK")
    print("=" * 60)
    
    pattern = "a+b"
    text = "aaab"
    
    print(f"\nPattern: {pattern}")
    print(f"Text: {text}")
    print()
    print(trace(pattern, text, show_all=True))
    print()


def example_no_match_trace():
    """
    Example 6: Why Didn't It Match?
    """
    print("=" * 60)
    print("Example 6: 🔍 WHY DIDN'T IT MATCH?")
    print("=" * 60)
    
    pattern = "abc"
    text = "abd"
    
    print(f"\nPattern: {pattern}")
    print(f"Text: {text}")
    print()
    print(trace(pattern, text, show_all=True))
    print()


def example_complex():
    """
    Example 7: Complex Pattern
    """
    print("=" * 60)
    print("Example 7: Complex Pattern")
    print("=" * 60)
    
    # Simple email-like pattern
    pattern = r"\w+@\w+\.\w+"
    
    print(f"\nPattern: {pattern}")
    print(f"(Simple email-like pattern)")
    
    tests = [
        "user@example.com",
        "test.user@domain.org",
        "invalid-email",
        "@missing.user",
    ]
    
    rx = compile(pattern)
    
    print("\nTesting:")
    for text in tests:
        result = rx.search(text)
        status = "✓" if result.matched else "✗"
        print(f"  {status} '{text}'")
    print()


def example_graphviz():
    """
    Example 8: Graphviz Export
    """
    print("=" * 60)
    print("Example 8: 📊 Graphviz Export")
    print("=" * 60)
    
    rx = Regex("(a|b)*c")
    
    print(f"\nPattern: (a|b)*c")
    print("\nDOT output (paste into https://dreampuf.github.io/GraphvizOnline/):")
    print("-" * 40)
    print(rx.to_dot())
    print("-" * 40)
    print()


def example_banner():
    """Print a cool banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
║  ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
║  ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
║  ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
║  ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
║  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
║                                                               ║
║         👻 The Regex Engine You Can See 👻                    ║
║                                                               ║
║   See the NFA. Watch the matching. Understand your regex.     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    """Run all examples."""
    example_banner()
    
    example_basic()
    example_quantifiers()
    example_character_classes()
    example_visualization()
    example_trace()
    example_no_match_trace()
    example_complex()
    example_graphviz()
    
    print("=" * 60)
    print("  ✨ All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
