# Foundry

Collection of Python libraries and demonstration modules: algorithms, DSLs, async utilities, and protocol-style experiments.

## Requirements

- Python 3.10+
- `pytest`, `pytest-asyncio` for tests

## Run tests

Each package is tested from its own directory:

```powershell
cd graph
python -m pytest -q
```

Run all packages with tests (PowerShell):

```powershell
Get-ChildItem -Directory | ForEach-Object {
  if (Test-Path "$($_.FullName)\test_*.py") {
    Push-Location $_.FullName
    python -m pytest -q --tb=no
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: $($_.Name)" }
    Pop-Location
  }
}
```

## Layout

| Cluster | Packages |
|---------|----------|
| Algorithms | `graph`, `shamir`, `diff`, `automata`, `lisp`, `parsec`, `turing`, `lambda`, `enigma`, `morse`, `phantom`, `lattice`, `sketch` |
| DSL / data | `glyph`, `forge`, `rune`, `prism`, `malo`, `chrono` |
| Async | `arc`, `sentinel`, `flux`, `styx` |
| Integration / demo | `nexus`, `reactor`, `forge_vm`, `bastion`, `audit`, `tribunal`, `signal`, `ledger`, `pact`, `witness`, `specter` |

Protocol and crypto-related modules are **reference implementations for learning**, not audited for production.

## Web console with local runners

The catalog works in the browser alone. To **run tests or examples** from module detail pages, start the localhost runner API and the Vite dev server in two terminals.

**Terminal 1 — Runner API (localhost only, whitelisted commands):**

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Web console:**

```powershell
cd web
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Use **Run tests** / **Run example** on a module detail page when the API is up.

- Commands are **whitelisted** in `api/runner/module_registry.py` — the browser never sends arbitrary shell input.
- Example timeout: 8s; test timeout: 30s.
- Without the API, the catalog, search, filters, and static playgrounds still work.
- Protocol and crypto modules are **learning demos**, not audited production cryptography.

Production build: `cd web && npm run build`.

## Interactive Labs

**Labs** let you play with each module in the browser (pathfinding, diffs, JSON queries, secret sharing, Game of Life, and more). The **Technical runner** section on each detail page still runs whitelisted `pytest` / `examples.py` when you need raw stdout.

Use the same two-terminal setup as above (API on port 8000, Vite on 5173). Open any module detail page — the **Interactive Lab** runs automatically with a default preset.

- 12 Tier-1 labs: full interactive visuals (graph, diff, prism, shamir, automata, enigma, turing, lambda, phantom, sketch, forge, rune)
- 11 Tier-2 labs: curated preset scenarios (lisp, parsec, morse/Huffman, lattice, glyph, chrono, malo, arc, sentinel, flux, styx)
- 11 Tier-3 labs: guided protocol/security explainers (integration modules + bastion read-only)

Protocol and crypto modules are **learning demos**, not audited for production.

## Author

chrismaghuhn
