"""Parser for requirements.txt files.

Supports pinned versions (==) only. Rejects unpinned specifiers and URL requirements.
Pip-specific options (--find-links, --index-url, etc.) are silently ignored.
Editable installs (-e ./path) are supported: the package source is bundled from the local path.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_OPERATOR_RE = re.compile(r"(===|~=|!=|>=|<=|==|>|<)")
_PINNED_RE = re.compile(
    r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(\[[^\]]+\])?"
    r"\s*==\s*"
    r"([^\s;#]+)"
)


@dataclass(frozen=True)
class Requirement:
    name: str
    version: str
    path: Path | None = None
    is_editable: bool = False


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def _join_continuations(lines: list[str]) -> list[str]:
    result: list[str] = []
    buf = ""
    for line in lines:
        if line.endswith("\\"):
            buf += line[:-1]
        else:
            buf += line
            result.append(buf)
            buf = ""
    if buf:
        result.append(buf)
    return result


def _parse_wheel_filename(filename: str) -> tuple[str, str]:
    stem = filename.removesuffix(".whl")
    parts = stem.split("-")
    if len(parts) < 3:
        raise ValueError(f"Invalid wheel filename: {filename}")
    return _normalize_name(parts[0]), parts[1]


def _read_project_info(pkg_dir: Path) -> tuple[str, str]:
    """Read name and version from a local project directory."""
    pyproject = pkg_dir / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        name = project.get("name", pkg_dir.name)
        version = project.get("version", "0.0.0")
        return _normalize_name(name), version
    return _normalize_name(pkg_dir.name), "0.0.0"


def _parse_line(line: str, base_dir: Path) -> Requirement | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    if (
        line.startswith("-e ")
        or line.startswith("--editable ")
        or line.startswith("-e\t")
    ):
        path_str = re.split(r"\s+", line, 1)[1].strip()
        pkg_dir = (base_dir / path_str).resolve()
        if not pkg_dir.exists():
            # uv export writes paths relative to the workspace root (CWD at export time),
            # not relative to the requirements file location — try CWD as fallback
            pkg_dir = (Path.cwd() / path_str).resolve()
        if not pkg_dir.exists():
            raise FileNotFoundError(f"Editable install path not found: {path_str}")
        name, version = _read_project_info(pkg_dir)
        return Requirement(name=name, version=version, path=pkg_dir, is_editable=True)

    if line.startswith("-r ") or line.startswith("--requirement "):
        return None  # handled by caller

    if line.startswith("-"):
        return None

    if " @ " in line or line.endswith("@"):
        raise ValueError(f"URL requirements are not supported: {line}")

    stripped = line.split(";")[0].strip()
    stripped = stripped.split("#")[0].strip()
    if not stripped:
        return None

    if stripped.endswith(".whl"):
        wheel_path = (base_dir / stripped).resolve()
        if not wheel_path.exists():
            raise FileNotFoundError(f"Local wheel not found: {stripped}")
        name, version = _parse_wheel_filename(wheel_path.name)
        return Requirement(name=name, version=version, path=wheel_path)

    m = _PINNED_RE.match(stripped)
    if m:
        return Requirement(name=_normalize_name(m.group(1)), version=m.group(4))

    op_match = _OPERATOR_RE.search(stripped)
    if op_match:
        op = op_match.group(1)
        raise ValueError(f"Only pinned versions (==) are supported, got '{op}': {line}")

    name_only = re.match(
        r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?(\[[^\]]+\])?$", stripped
    )
    if name_only:
        raise ValueError(f"Version must be pinned with ==: {line}")

    raise ValueError(f"Cannot parse requirement: {line}")


def parse_requirements(
    path: Path, *, _visited: set[Path] | None = None
) -> list[Requirement]:
    path = path.resolve()

    if _visited is None:
        _visited = set()
    if path in _visited:
        raise ValueError(f"Circular -r include detected: {path}")
    _visited.add(path)

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = _join_continuations(raw_lines)

    seen: dict[str, str] = {}
    result: list[Requirement] = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("-r ") or stripped.startswith("--requirement "):
            ref = stripped.split(None, 1)[1].strip()
            ref_path = path.parent / ref
            sub = parse_requirements(ref_path, _visited=_visited)
            for req in sub:
                if req.name in seen:
                    if seen[req.name] != req.version:
                        raise ValueError(
                            f"Conflicting versions for {req.name}: "
                            f"{seen[req.name]} vs {req.version}"
                        )
                else:
                    seen[req.name] = req.version
                    result.append(req)
            continue

        parsed = _parse_line(line, path.parent)
        if parsed is None:
            continue
        req = parsed

        if req.name in seen:
            if seen[req.name] != req.version:
                raise ValueError(
                    f"Conflicting versions for {req.name}: "
                    f"{seen[req.name]} vs {req.version}"
                )
        else:
            seen[req.name] = req.version
            result.append(req)

    return result
