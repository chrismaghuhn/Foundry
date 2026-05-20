#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  GLYPH TEST-DOKUMENT — Experimentiere mit ASCII-Art-Programmen!
═══════════════════════════════════════════════════════════════

Führe dieses Skript aus:  python glyph_test.py

Oder importiere es und spiele im Python-REPL:
  >>> from glyph_test import *
  >>> test_mein_programm()
"""

from glyph import glyph, GlyphCompiler, NodeFunction
import asyncio


# ═══════════════════════════════════════════════════════════════
# TEST 1: Einfache Kette
# ═══════════════════════════════════════════════════════════════

def test_einfach():
    """Einfachstes Beispiel: input → double → print"""
    
    print("\n🧪 TEST 1: Einfache Kette")
    print("─" * 50)
    
    source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
'''
    print("Programm:")
    print(source)
    
    print("Eingabe: [21]")
    print("Erwartet: 42")
    result = glyph(source, input_data=[21])
    print(f"✅ Ausgabe: {result.print_output}\n")


# ═══════════════════════════════════════════════════════════════
# TEST 2: Längere Pipeline
# ═══════════════════════════════════════════════════════════════

def test_pipeline():
    """Mehrere Operationen hintereinander"""
    
    print("\n🧪 TEST 2: Pipeline")
    print("─" * 50)
    
    source = '''
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  square  │────>│  print  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
'''
    print("Programm: input → double → square → print")
    print("Eingabe: [3]")
    print("Erwartet: (3 × 2)² = 36")
    result = glyph(source, input_data=[3])
    print(f"✅ Ausgabe: {result.print_output}\n")


# ═══════════════════════════════════════════════════════════════
# TEST 3: ASCII-Stil (ohne Unicode)
# ═══════════════════════════════════════════════════════════════

def test_ascii_stil():
    """Funktioniert auch mit einfachen ASCII-Zeichen"""
    
    print("\n🧪 TEST 3: ASCII-Stil")
    print("─" * 50)
    
    source = '''
+----------+      +-----------+      +---------+
|  input   |----->|  double   |----->|  print  |
+----------+      +-----------+      +---------+
'''
    print("Programm (ASCII-Boxen):")
    print(source)
    
    print("Eingabe: [100]")
    result = glyph(source, input_data=[100])
    print(f"✅ Ausgabe: {result.print_output}\n")


# ═══════════════════════════════════════════════════════════════
# TEST 4: Fancy Unicode
# ═══════════════════════════════════════════════════════════════

def test_fancy():
    """Doppelte Unicode-Linien"""
    
    print("\n🧪 TEST 4: Fancy Unicode")
    print("─" * 50)
    
    source = '''
╔═════════╗      ╔══════════╗      ╔═════════╗
║  input  ║═════>║  double  ║═════>║  print  ║
╚═════════╝      ╚══════════╝      ╚═════════╝
'''
    print("Programm (doppelte Linien):")
    print(source)
    
    print("Eingabe: [7]")
    result = glyph(source, input_data=[7])
    print(f"✅ Ausgabe: {result.print_output}\n")


# ═══════════════════════════════════════════════════════════════
# TEST 5: Output sammeln
# ═══════════════════════════════════════════════════════════════

def test_output():
    """Ergebnisse in output_data sammeln"""
    
    print("\n🧪 TEST 5: Output sammeln")
    print("─" * 50)
    
    source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  square  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''
    print("Programm: input → square → output")
    print("Eingabe: [5]")
    result = glyph(source, input_data=[5])
    print(f"✅ output_data: {result.output_data}\n")


# ═══════════════════════════════════════════════════════════════
# TEST 6: +1 Operation
# ═══════════════════════════════════════════════════════════════

def test_increment():
    """Die +1 Operation"""
    
    print("\n🧪 TEST 6: Increment (+1)")
    print("─" * 50)
    
    source = '''
┌─────────┐     ┌─────┐     ┌─────┐     ┌─────────┐
│  input  │────>│ +1  │────>│ +1  │────>│  print  │
└─────────┘     └─────┘     └─────┘     └─────────┘
'''
    print("Programm: input → +1 → +1 → print")
    print("Eingabe: [10]")
    print("Erwartet: 12")
    result = glyph(source, input_data=[10])
    print(f"✅ Ausgabe: {result.print_output}\n")


# ═══════════════════════════════════════════════════════════════
# TEST 7: Eigene Operation definieren
# ═══════════════════════════════════════════════════════════════

def test_custom():
    """Eigene Operation erstellen"""
    
    print("\n🧪 TEST 7: Custom Operation")
    print("─" * 50)
    
    # Eigene Operation: Verdreifachen
    class TripleNode(NodeFunction):
        async def execute(self, inputs, context):
            if inputs:
                return inputs[0] * 3
            return None
    
    source = '''
┌─────────┐     ┌─────────┐     ┌─────────┐
│  input  │────>│ triple  │────>│  print  │
└─────────┘     └─────────┘     └─────────┘
'''
    print("Custom Operation 'triple' = × 3")
    print("Eingabe: [7]")
    print("Erwartet: 21")
    
    compiler = GlyphCompiler(custom_ops={'triple': TripleNode})
    compiled = compiler.compile(source)
    result = asyncio.run(compiled.execute([7]))
    print(f"✅ Ausgabe: {result.print_output}\n")


# ═══════════════════════════════════════════════════════════════
# DEIN EIGENES PROGRAMM
# ═══════════════════════════════════════════════════════════════

def test_mein_programm():
    """
    🎨 HIER KANNST DU EXPERIMENTIEREN!
    
    Ändere 'source' und 'eingabe' nach Belieben.
    
    Verfügbare Operationen:
      - input    : Nimmt Werte aus input_data
      - output   : Sammelt in output_data
      - print    : Gibt aus
      - double   : × 2
      - square   : x²
      - +1       : + 1
    """
    
    print("\n🎨 DEIN PROGRAMM")
    print("─" * 50)
    
    # ═══════════════════════════════════════════
    # ✏️  HIER BEARBEITEN:
    # ═══════════════════════════════════════════
    
    source = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
'''
    
    eingabe = [42]
    
    # ═══════════════════════════════════════════
    
    print("Dein Programm:")
    print(source)
    print(f"Eingabe: {eingabe}")
    
    result = glyph(source, eingabe)
    
    print(f"\n📤 print_output: {result.print_output}")
    print(f"📦 output_data:  {result.output_data}")


# ═══════════════════════════════════════════════════════════════
# ALLE TESTS AUSFÜHREN
# ═══════════════════════════════════════════════════════════════

def alle_tests():
    """Führt alle Tests durch"""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██╗  ██╗   ██╗██████╗ ██╗  ██╗                     ║
║  ██╔════╝ ██║  ╚██╗ ██╔╝██╔══██╗██║  ██║                     ║
║  ██║  ███╗██║   ╚████╔╝ ██████╔╝███████║                     ║
║  ██║   ██║██║    ╚██╔╝  ██╔═══╝ ██╔══██║                     ║
║  ╚██████╔╝███████╗██║   ██║     ██║  ██║                     ║
║   ╚═════╝ ╚══════╝╚═╝   ╚═╝     ╚═╝  ╚═╝                     ║
║                                                               ║
║              🧪 TEST-DOKUMENT 🧪                              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    test_einfach()
    test_pipeline()
    test_ascii_stil()
    test_fancy()
    test_output()
    test_increment()
    test_custom()
    test_mein_programm()
    
    print("═" * 60)
    print("  ✅ Alle Tests abgeschlossen!")
    print("═" * 60)
    print("""
💡 Tipps:
   - Bearbeite test_mein_programm() um zu experimentieren
   - Boxen müssen geschlossen sein (alle 4 Ecken)
   - Pfeile: ────>  oder  ═════>  oder  ----->
   - Leerzeichen zwischen Boxen sind egal
""")


if __name__ == "__main__":
    alle_tests()
