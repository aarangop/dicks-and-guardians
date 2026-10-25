"""The dependency rule: the core must not know about frameworks or outer layers."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src" / "dont_be_a_dick"
FRAMEWORKS = (
    "langchain",
    "langgraph",
    "tavily",
    "fastapi",
    "anthropic",
    "openrouter",
    "starlette",
    "tinydb",
)
OUTER_LAYERS = ("agents", "tools", "dependencies", "main", "prompts", "storage", "evals", "tracing")


def imported_modules(package: str) -> set[tuple[Path, str]]:
    found = set()
    for path in (SRC / package).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                found.update((path, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add((path, node.module))
    return found


def violations(package: str, forbidden: tuple[str, ...]) -> list[str]:
    return sorted(
        f"{path.relative_to(SRC)} imports {module}"
        for path, module in imported_modules(package)
        if any(module == f or module.startswith(f + ".") for f in forbidden)
    )


@pytest.mark.parametrize("package", ["domain", "workflows"])
def test_core_does_not_import_frameworks(package: str) -> None:
    assert violations(package, FRAMEWORKS) == []


@pytest.mark.parametrize("package", ["domain", "workflows"])
def test_core_does_not_import_outer_layers(package: str) -> None:
    forbidden = tuple(f"dont_be_a_dick.{layer}" for layer in OUTER_LAYERS)
    assert violations(package, forbidden) == []


def test_domain_does_not_import_workflows() -> None:
    assert violations("domain", ("dont_be_a_dick.workflows",)) == []
