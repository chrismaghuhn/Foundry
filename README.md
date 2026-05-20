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

## Web console

Interactive catalog of all Foundry packages (read-only, no Python execution in the browser):

```powershell
cd web
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). Production build: `npm run build`.

## Author

chrismaghuhn
