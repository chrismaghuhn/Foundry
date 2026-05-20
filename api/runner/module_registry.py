"""Whitelisted module runner commands — never trust modules.json for execution."""

from __future__ import annotations

from dataclasses import dataclass

from .paths import module_cwd, resolve_foundry_root

PYTEST = ["python", "-m", "pytest", "-q"]
EXAMPLES = ["python", "examples.py"]


@dataclass(frozen=True)
class ModuleRunnerSpec:
    module_id: str
    cwd: str
    test_command: list[str] | None
    example_command: list[str] | None


def _spec(
    module_id: str,
    *,
    test: bool = True,
    example: str | bool = True,
) -> ModuleRunnerSpec:
    """Build spec: example=True -> examples.py, example=str -> that script, False -> None."""
    ex_cmd: list[str] | None
    if example is False:
        ex_cmd = None
    elif example is True:
        ex_cmd = EXAMPLES
    else:
        ex_cmd = ["python", example]
    return ModuleRunnerSpec(
        module_id=module_id,
        cwd=module_id,
        test_command=PYTEST if test else None,
        example_command=ex_cmd,
    )


# Order matches modules.json for easier review. One entry per UI module id.
_SPECS: list[ModuleRunnerSpec] = [
    _spec("graph"),
    _spec("shamir"),
    _spec("diff"),
    _spec("automata"),
    _spec("lisp"),
    _spec("parsec"),
    _spec("turing"),
    _spec("lambda"),
    _spec("enigma"),
    _spec("morse"),
    _spec("phantom"),
    _spec("lattice"),
    _spec("sketch"),
    _spec("glyph"),
    _spec("forge"),
    _spec("rune"),
    _spec("prism"),
    _spec("malo"),
    _spec("chrono"),
    _spec("arc"),
    _spec("sentinel"),
    _spec("flux"),
    _spec("styx"),
    _spec("nexus", test=False, example="nexus_integration.py"),
    _spec("reactor", test=False, example="reactor.py"),
    _spec("forge_vm", test=False, example="forge.py"),
    _spec("bastion", test=False, example=False),
    _spec("audit", test=False, example="audit.py"),
    _spec("tribunal", test=False, example="tribunal.py"),
    _spec("signal", test=False, example="signal.py"),
    _spec("ledger", test=False, example="ledger.py"),
    _spec("pact", test=False, example="pact.py"),
    _spec("witness", test=False, example="witness.py"),
    _spec("specter", test=False, example="specter.py"),
]

REGISTRY: dict[str, ModuleRunnerSpec] = {s.module_id: s for s in _SPECS}


def get_spec(module_id: str) -> ModuleRunnerSpec | None:
    return REGISTRY.get(module_id)


def _script_in_command(command: list[str], cwd_rel: str) -> None:
    """Verify python script argv exists under module cwd."""
    root = resolve_foundry_root()
    for i, arg in enumerate(command):
        if arg == "python" and i + 1 < len(command) and command[i + 1].endswith(".py"):
            script = root / cwd_rel / command[i + 1]
            if not script.is_file():
                raise FileNotFoundError(f"Missing script for runner: {script}")


def validate_registry() -> None:
    """Startup check: cwd dirs and referenced scripts exist."""
    root = resolve_foundry_root()
    if not (root / "README.md").is_file() or not (root / "web").is_dir():
        raise RuntimeError(f"FOUNDRY_ROOT invalid: {root}")

    for spec in REGISTRY.values():
        cwd_path = module_cwd(spec.cwd)
        if not cwd_path.is_dir():
            raise FileNotFoundError(f"Module cwd missing: {cwd_path}")
        if spec.test_command:
            _script_in_command(spec.test_command, spec.cwd)
        if spec.example_command:
            _script_in_command(spec.example_command, spec.cwd)
