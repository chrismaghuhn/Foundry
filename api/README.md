# Foundry Runner API

Localhost-only FastAPI service that runs **whitelisted** test and example commands for Foundry packages.

## Security

- No `shell=True`
- No commands, paths, or env vars from HTTP requests
- Only `module_id` values in `runner/module_registry.py`
- Output truncated to 40,000 characters per stream
- CORS limited to Vite dev origins (`localhost:5173`, `127.0.0.1:5173`)

## Run

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Optional: `FOUNDRY_ROOT` env var overrides auto-detected repo root.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | API and repo root path |
| GET | `/api/modules` | Runner availability per module |
| POST | `/api/modules/{id}/test` | Run pytest (30s timeout) |
| POST | `/api/modules/{id}/example` | Run example script (8s timeout) |

## Adding a module

1. Add the package to `web/src/data/modules.json` (UI catalog).
2. Add a matching `ModuleRunnerSpec` in `runner/module_registry.py`.
3. Run `python -m pytest` in `api/` — registry must match `modules.json` ids exactly.

## Interactive Labs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/labs` | List all labs |
| GET | `/api/labs/{id}` | Lab definition (inputs, presets, mission) |
| POST | `/api/labs/{id}/run` | Run lab with `{ "presetId", "input" }` |

Labs run **in-process** via whitelisted adapters under `labs/adapters/`. Limits: 5s timeout, 5k text / 10k JSON, no subprocess/eval/shell.

To add a lab: register in `labs/lab_registry.py` and implement `get_definition()` + `run_lab()` in a new adapter module.

## Tests

```powershell
python -m pytest -q
```
