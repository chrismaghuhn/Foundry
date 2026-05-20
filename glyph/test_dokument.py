#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║                    GLYPH TEST-DOKUMENT                        ║
║                                                               ║
║   Kopiere dieses Skript und führe es aus!                     ║
║   Experimentiere mit den ASCII-Diagrammen!                    ║
╚═══════════════════════════════════════════════════════════════╝
"""

from glyph import glyph, GlyphCompiler, NodeFunction
import asyncio


# ═══════════════════════════════════════════════════════════════
# TEST 1: Einfache Verdopplung
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 1: Einfache Verdopplung")
print("═" * 60)

test1 = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
'''

print(test1)
print("Eingabe: 21")
print("Erwartet: 42")
print("-" * 40)
glyph(test1, input_data=[21])


# ═══════════════════════════════════════════════════════════════
# TEST 2: Kette von Operationen
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 2: Kette (double → square)")
print("═" * 60)

test2 = '''
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  square  │────>│  print  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
'''

print(test2)
print("Eingabe: 3")
print("Erwartet: (3 × 2)² = 36")
print("-" * 40)
glyph(test2, input_data=[3])


# ═══════════════════════════════════════════════════════════════
# TEST 3: Increment (+1)
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 3: Increment")
print("═" * 60)

test3 = '''
┌─────────┐     ┌─────┐     ┌─────┐     ┌─────────┐
│  input  │────>│ +1  │────>│ +1  │────>│  print  │
└─────────┘     └─────┘     └─────┘     └─────────┘
'''

print(test3)
print("Eingabe: 10")
print("Erwartet: 10 + 1 + 1 = 12")
print("-" * 40)
glyph(test3, input_data=[10])


# ═══════════════════════════════════════════════════════════════
# TEST 4: ASCII-Style Boxen
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 4: ASCII-Style Boxen")
print("═" * 60)

test4 = '''
+----------+      +-----------+      +---------+
|  input   |----->|  square   |----->|  print  |
+----------+      +-----------+      +---------+
'''

print(test4)
print("Eingabe: 7")
print("Erwartet: 7² = 49")
print("-" * 40)
glyph(test4, input_data=[7])


# ═══════════════════════════════════════════════════════════════
# TEST 5: Double-Line Unicode Boxen
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 5: Fancy Double-Line Boxen")
print("═" * 60)

test5 = '''
╔═════════╗      ╔══════════╗      ╔═════════╗
║  input  ║═════>║  double  ║═════>║  print  ║
╚═════════╝      ╚══════════╝      ╚═════════╝
'''

print(test5)
print("Eingabe: 100")
print("Erwartet: 200")
print("-" * 40)
glyph(test5, input_data=[100])


# ═══════════════════════════════════════════════════════════════
# TEST 6: Output sammeln (statt print)
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 6: Output sammeln")
print("═" * 60)

test6 = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  square  │────>│ output  │
└─────────┘     └──────────┘     └─────────┘
'''

print(test6)
print("Eingabe: 5")
print("Erwartet: output_data enthält [25]")
print("-" * 40)
result = glyph(test6, input_data=[5])
print(f"\n→ Gesammelter Output: {result.output_data}")


# ═══════════════════════════════════════════════════════════════
# TEST 7: Eigene Custom-Operation
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 7: Custom Operation (cube = x³)")
print("═" * 60)

class CubeNode(NodeFunction):
    """Berechnet x³"""
    async def execute(self, inputs, context):
        if inputs:
            return inputs[0] ** 3
        return None

test7 = '''
┌─────────┐     ┌────────┐     ┌─────────┐
│  input  │────>│  cube  │────>│  print  │
└─────────┘     └────────┘     └─────────┘
'''

print(test7)
print("Eingabe: 4")
print("Erwartet: 4³ = 64")
print("-" * 40)

compiler = GlyphCompiler(custom_ops={'cube': CubeNode})
compiled = compiler.compile(test7)
asyncio.run(compiled.execute([4]))


# ═══════════════════════════════════════════════════════════════
# TEST 8: Lange Pipeline
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("TEST 8: Lange Pipeline")
print("═" * 60)

test8 = '''
┌───────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌───────┐
│ input │────>│ double │────>│   +1   │────>│ double │────>│ print │
└───────┘     └────────┘     └────────┘     └────────┘     └───────┘
'''

print(test8)
print("Eingabe: 5")
print("Erwartet: ((5 × 2) + 1) × 2 = 22")
print("-" * 40)
glyph(test8, input_data=[5])


# ═══════════════════════════════════════════════════════════════
# DEIN SPIELPLATZ - Experimentiere hier!
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("DEIN SPIELPLATZ")
print("═" * 60)

# Ändere dieses Diagramm und schau was passiert!
mein_test = '''
┌─────────┐     ┌──────────┐     ┌─────────┐
│  input  │────>│  double  │────>│  print  │
└─────────┘     └──────────┘     └─────────┘
'''

meine_eingabe = [42]

print(mein_test)
print(f"Deine Eingabe: {meine_eingabe}")
print("-" * 40)
glyph(mein_test, input_data=meine_eingabe)


# ═══════════════════════════════════════════════════════════════
# ZUSAMMENFASSUNG
# ═══════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("VERFÜGBARE OPERATIONEN")
print("═" * 60)
print("""
┌────────────┬─────────────────────────────┐
│ Operation  │ Beschreibung                │
├────────────┼─────────────────────────────┤
│ input      │ Nimmt Werte aus input_data  │
│ output     │ Sammelt Ergebnisse          │
│ print      │ Gibt aus & leitet weiter    │
│ double     │ Multipliziert mit 2         │
│ square     │ Quadriert (x²)              │
│ +1         │ Addiert 1                   │
│ sum        │ Summiert alle Inputs        │
│ filter     │ Filtert falsy Werte         │
│ delay      │ Async Verzögerung           │
└────────────┴─────────────────────────────┘

BOX-STILE:
  ┌───────┐     +-------+     ╔═══════╗
  │ unicode│     | ascii |     ║ fancy ║
  └───────┘     +-------+     ╚═══════╝

PFEILE:
  ────>     --->     ═══>
""")

print("\n✨ Viel Spaß beim Experimentieren!")
