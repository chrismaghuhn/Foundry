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

## Author

chrismaghuhn
