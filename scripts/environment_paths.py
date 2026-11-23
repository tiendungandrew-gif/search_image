"""Resolve environment files while keeping historical CLI aliases usable."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_ALIASES = {
    ".env.phase12": "config/environments/deployment.env",
    ".env.phase12-restore": "config/environments/restore.env",
    ".env.phase04": "config/environments/archive/phase04.env",
    ".env.native": "config/environments/archive/native.env",
}
PROTECTED_ENVIRONMENTS = {
    ".env",
    ".env.qa",
    ".env.host",
    ".env.native",
    "config/environments/archive/native.env",
    "config/environments/archive/phase04.env",
}


def resolve_env_file(path: str | Path, *, root: Path = ROOT) -> Path:
    """Only resolve aliases at the project root; explicit external files stay explicit."""
    requested = Path(path).absolute()
    if requested.is_file():
        return requested.resolve()
    if requested.parent == root and requested.name in ENVIRONMENT_ALIASES:
        return root / ENVIRONMENT_ALIASES[requested.name]
    return requested.resolve()


def is_protected_environment(path: str | Path, *, root: Path = ROOT) -> bool:
    requested = Path(path).absolute()
    if requested.name in {".env", ".env.qa", ".env.host", ".env.native"}:
        return True
    resolved = resolve_env_file(path, root=root)
    return any(resolved == root / name for name in PROTECTED_ENVIRONMENTS)
