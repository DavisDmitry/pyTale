"""Plugin builder for PyTale.

Produces a Hytale plugin JAR in the GraalPy Virtual Filesystem (VFS) layout under
``GRAALPY-VFS/<group>/<module>``: the plugin's own code goes into ``src/`` (GraalPy's PYTHONPATH)
and its third-party dependencies into ``venv/``. Dependencies are downloaded as wheels from PyPI
(or provided locally) and unpacked directly into the VFS layout — no venv creation or pip subprocess
is involved. At runtime the PyTale framework mounts this through a ``VirtualFileSystem`` so Python
imports resolve directly from the jar (no temp extraction).
"""

import json
import re
import tomllib
import zipfile
from pathlib import Path
from typing import Any

from pytale_tools.builder.classgen import generate_plugin_class, module_to_class_name
from pytale_tools.builder.pypi import download_wheels_sync
from pytale_tools.builder.req_parser import Requirement, parse_requirements

VFS_GROUP = "TaleDale"
PYTHON_VERSION = "3.12"

_SKIP_DIRS = {"test", "tests", "docs", "doc", "build", "dist"}


def _find_packages(project_dir: Path) -> list[Path]:
    """Find Python package directories to bundle from a project directory.

    Respects [tool.hatch.build.targets.wheel].packages if present.
    Falls back to auto-detection in src/ then project root.
    """
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        packages = (
            data.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages", None)
        )
        if packages:
            result = []
            for pkg in packages:
                pkg_path = (project_dir / pkg).resolve()
                if pkg_path.exists():
                    result.append(pkg_path)
            if result:
                return result

    # fallback: src/ layout first, then flat
    for search_root in [project_dir / "src", project_dir]:
        if not search_root.is_dir():
            continue
        found = []
        for candidate in sorted(search_root.iterdir()):
            if not candidate.is_dir():
                continue
            name = candidate.name
            if name.startswith(".") or name.startswith("_"):
                continue
            if name.lower() in _SKIP_DIRS or name.lower().startswith("test"):
                continue
            if (candidate / "__init__.py").exists():
                found.append(candidate)
        if found:
            return found

    return []


def _copy_dir_to_vfs(jar: zipfile.ZipFile, dest_prefix: str, pkg_dir: Path) -> None:
    """Copy all files from a package directory into the JAR under dest_prefix."""
    for file_path in sorted(pkg_dir.rglob("*")):
        if file_path.is_dir():
            continue
        if "__pycache__" in file_path.parts:
            continue
        rel = file_path.relative_to(pkg_dir.parent)
        jar.writestr(f"{dest_prefix}{rel}", file_path.read_bytes())


def _parse_wheel_authors(metadata_content: str) -> list[dict]:
    """Parse authors from wheel METADATA headers into AuthorInfo dicts."""
    authors: list[dict] = []

    author_email_line = None
    author_line = None
    for line in metadata_content.split("\n"):
        if line.startswith("Author-email:"):
            author_email_line = line.split(":", 1)[1].strip()
        elif line.startswith("Author:"):
            author_line = line.split(":", 1)[1].strip()

    if author_email_line:
        # "Name <email>, Name2 <email2>" or plain "email@example.com"
        for entry in re.split(r",(?![^<>]*>)", author_email_line):
            entry = entry.strip()
            m = re.match(r"^(.*?)\s*<([^>]+)>$", entry)
            if m:
                info: dict = {}
                if m.group(1).strip():
                    info["Name"] = m.group(1).strip()
                info["Email"] = m.group(2).strip()
                authors.append(info)
            elif entry:
                authors.append({"Email": entry})
    elif author_line:
        authors.append({"Name": author_line})

    return authors


def _parse_pyproject_authors(authors_list: list) -> list[dict]:
    """Convert pyproject.toml project.authors to AuthorInfo dicts."""
    result = []
    for entry in authors_list:
        if not isinstance(entry, dict):
            continue
        info: dict = {}
        if entry.get("name"):
            info["Name"] = entry["name"]
        if entry.get("email"):
            info["Email"] = entry["email"]
        if entry.get("url"):
            info["Url"] = entry["url"]
        if info:
            result.append(info)
    return result


class PluginBuilder:
    def __init__(
        self,
        source: Path,
        requirements_path: Path | None = None,
        max_workers: int = 10,
    ):
        source = source.resolve()

        if source.suffix == ".whl":
            if not source.exists():
                raise FileNotFoundError(f"Wheel not found: {source}")
            self._wheel_path: Path | None = source
            self._module_dir: Path | None = None
            self.metadata = self._read_metadata_from_wheel()
        elif source.is_dir():
            self._wheel_path = None
            self._module_dir = source
            self.metadata = self._read_metadata_from_pyproject(source)
        else:
            raise ValueError(f"Source must be a .whl file or a directory: {source}")

        self.requirements_path = (
            requirements_path.resolve() if requirements_path else None
        )
        if self.requirements_path and not self.requirements_path.exists():
            raise FileNotFoundError(
                f"Requirements file not found: {self.requirements_path}"
            )

        self.max_workers = max_workers
        self.module_name = self.metadata["name"].replace("-", "_")
        self._pytale_cfg = self._load_pytale_config()
        self.cache_dir = self._find_project_dir() / ".pytale" / "wheels"

    @property
    def wheel_path(self) -> Path | None:
        return self._wheel_path

    def _find_project_dir(self) -> Path:
        root = self._module_dir or (
            self._wheel_path.parent if self._wheel_path else Path.cwd()
        )
        for d in [root, *root.parents]:
            if (d / ".pytale").exists() or (d / "pyproject.toml").exists():
                return d
        return Path.cwd()

    def _read_metadata_from_wheel(self) -> dict[str, Any]:
        assert self._wheel_path is not None
        with zipfile.ZipFile(self._wheel_path, "r") as whl:
            dist_info_dirs = [n for n in whl.namelist() if ".dist-info/" in n]
            if not dist_info_dirs:
                raise ValueError(f"No dist-info found in wheel {self._wheel_path.name}")

            dist_info_dir = dist_info_dirs[0].split("/")[0]
            metadata_file = f"{dist_info_dir}/METADATA"

            try:
                metadata_content = whl.read(metadata_file).decode("utf-8")
            except KeyError:
                raise FileNotFoundError(
                    f"METADATA not found in {self._wheel_path.name}"
                )

            name = None
            version = None
            description = ""

            for line in metadata_content.split("\n"):
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("Summary:"):
                    description = line.split(":", 1)[1].strip()

            if not name:
                raise ValueError("Package name not found in wheel metadata")

            return {
                "name": name,
                "version": version or "1.0.0",
                "description": description,
                "authors": _parse_wheel_authors(metadata_content),
            }

    def _read_metadata_from_pyproject(self, project_dir: Path) -> dict[str, Any]:
        pyproject = project_dir / "pyproject.toml"
        if not pyproject.exists():
            return {"name": project_dir.name, "version": "1.0.0", "description": ""}

        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        name = project.get("name", project_dir.name)
        version = project.get("version", "1.0.0")
        description = project.get("description", "")

        website = ""
        urls = project.get("urls", {})
        for key in ("Homepage", "homepage", "Repository", "repository"):
            if key in urls:
                website = urls[key]
                break

        return {
            "name": name,
            "version": version,
            "description": description,
            "website": website,
            "authors": _parse_pyproject_authors(project.get("authors", [])),
        }

    def _is_self_reference(self, req: Requirement) -> bool:
        """True if the requirement refers to the plugin being built."""
        from pytale_tools.builder.req_parser import _normalize_name

        if req.name == _normalize_name(self.metadata["name"]):
            return True
        if (
            self._module_dir is not None
            and req.path is not None
            and req.path.resolve() == self._module_dir.resolve()
        ):
            return True
        return False

    def _resolve_dependencies(self) -> tuple[list[Path], list[Path]]:
        """Returns (wheel_paths, editable_dirs)."""
        wheels: list[Path] = []
        editable_dirs: list[Path] = []

        if self.requirements_path:
            all_reqs = parse_requirements(self.requirements_path)
            local_wheels = [
                r for r in all_reqs if r.path is not None and not r.is_editable
            ]
            editables = [
                r for r in all_reqs if r.is_editable and not self._is_self_reference(r)
            ]
            remote = [r for r in all_reqs if r.path is None]

            for r in local_wheels:
                assert r.path is not None
                print(f"  Local wheel: {r.path.name}")
                wheels.append(r.path)

            for r in editables:
                assert r.path is not None
                print(f"  Editable: {r.path}")
                editable_dirs.append(r.path)

            if remote:
                print(f"Downloading {len(remote)} PyPI dependencies...")
                wheels.extend(
                    download_wheels_sync(
                        remote, self.cache_dir, max_workers=self.max_workers
                    )
                )

        return wheels, editable_dirs

    @staticmethod
    def _unpack_wheel(
        wheel_path: Path,
        jar: zipfile.ZipFile,
        dest_prefix: str,
        *,
        include_dist_info: bool = True,
    ) -> set[str]:
        top_level: set[str] = set()
        with zipfile.ZipFile(wheel_path, "r") as whl:
            for info in whl.infolist():
                if info.is_dir():
                    continue

                first = info.filename.split("/")[0]

                if not include_dist_info and (
                    first.endswith(".dist-info") or first.endswith(".data")
                ):
                    continue

                if "__pycache__" in info.filename:
                    continue

                top_level.add(first)
                jar.writestr(f"{dest_prefix}{info.filename}", whl.read(info))

        return top_level

    def _manifest_group(self) -> str:
        return self._pytale_cfg.get("group", VFS_GROUP)

    def _vfs_root_rel(self) -> str:
        return f"GRAALPY-VFS/{self._manifest_group()}/{self.module_name}"

    @staticmethod
    def _write_pyvenv_cfg(jar: zipfile.ZipFile, venv_prefix: str) -> None:
        cfg = (
            "home = .\n"
            "include-system-site-packages = false\n"
            f"version = {PYTHON_VERSION}\n"
        )
        jar.writestr(f"{venv_prefix}pyvenv.cfg", cfg)

    def _write_vfs(
        self,
        jar: zipfile.ZipFile,
        dependency_wheels: list[Path],
        editable_dirs: list[Path],
    ) -> str:
        vfs_root_rel = self._vfs_root_rel()
        venv_prefix = f"{vfs_root_rel}/venv/"

        self._write_pyvenv_cfg(jar, venv_prefix)
        jar.writestr(f"{venv_prefix}bin/python", b"")

        site_packages = f"{venv_prefix}lib/python{PYTHON_VERSION}/site-packages/"
        for wheel_path in dependency_wheels:
            self._unpack_wheel(wheel_path, jar, site_packages, include_dist_info=True)
        for pkg_dir in editable_dirs:
            packages = _find_packages(pkg_dir)
            if not packages:
                raise RuntimeError(
                    f"No Python packages found in editable dep: {pkg_dir}"
                )
            for pkg in packages:
                _copy_dir_to_vfs(jar, site_packages, pkg)

        dep_count = len(dependency_wheels) + len(editable_dirs)
        if dep_count:
            print(f"✓ Bundled {dep_count} dependencies -> {vfs_root_rel}/venv")

        src_prefix = f"{vfs_root_rel}/src/"
        if self._module_dir:
            packages = _find_packages(self._module_dir)
            if not packages:
                raise RuntimeError(
                    f"No Python packages found in module directory: {self._module_dir}"
                )
            for pkg in packages:
                _copy_dir_to_vfs(jar, src_prefix, pkg)
        else:
            assert self._wheel_path is not None
            plugin_top_level = self._unpack_wheel(
                self._wheel_path, jar, src_prefix, include_dist_info=False
            )
            if not plugin_top_level:
                raise RuntimeError(
                    f"No importable code found in plugin wheel {self._wheel_path.name}"
                )

        print(f"✓ Bundled plugin source -> {vfs_root_rel}/src")
        return vfs_root_rel

    def _write_fileslist(self, jar: zipfile.ZipFile, vfs_root_rel: str) -> None:
        vfs_prefix = f"{vfs_root_rel}/"
        entries: set[str] = set()

        for name in jar.namelist():
            if not name.startswith(vfs_prefix):
                continue
            entries.add(f"/{name}")
            parts = name[len(vfs_prefix) :].split("/")
            for i in range(1, len(parts)):
                dir_path = "/".join(parts[:i])
                entries.add(f"/{vfs_prefix}{dir_path}/")

        lines = sorted(entries)
        jar.writestr(f"{vfs_prefix}fileslist.txt", f"{'\n'.join(lines)}\n")
        print(f"✓ Wrote {vfs_root_rel}/fileslist.txt ({len(lines)} entries)")

    def _plugin_class_internal_name(self) -> str:
        class_name = module_to_class_name(self.module_name)
        group_pkg = self._manifest_group().lower()
        return f"{group_pkg}/{self.module_name}/{class_name}"

    def _write_loader_class(self, jar: zipfile.ZipFile) -> str:
        internal_name = self._plugin_class_internal_name()
        jar.writestr(f"{internal_name}.class", generate_plugin_class(internal_name))
        return internal_name.replace("/", ".")

    def _load_pytale_config(self) -> dict:
        project_dir = self._module_dir or self._find_project_dir()
        pyproject = project_dir / "pyproject.toml"
        if not pyproject.exists():
            return {}
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("pytale", {})

    def _write_manifest_json(self, jar: zipfile.ZipFile, main_class: str) -> None:
        cfg = self._pytale_cfg

        deps: dict[str, str] = {"TaleDale:PyTale": ">=0.0.1"}
        deps.update(cfg.get("dependencies", {}))

        manifest: dict = {
            "Group": self._manifest_group(),
            "Name": self.metadata["name"],
            "Version": self.metadata["version"],
            "Description": self.metadata.get("description") or None,
            "Authors": self.metadata.get("authors", []),
            "Website": cfg.get("website") or self.metadata.get("website") or None,
            "DisabledByDefault": cfg.get("disabled_by_default", False),
            "IncludesAssetPack": cfg.get("includes_asset_pack", False),
            "Dependencies": deps,
            "OptionalDependencies": cfg.get("optional_dependencies", {}),
            "LoadBefore": cfg.get("load_before", {}),
            "ServerVersion": cfg.get("server_version", "=0.5.6"),
            "Main": main_class,
        }
        manifest = {k: v for k, v in manifest.items() if v is not None}
        jar.writestr("manifest.json", json.dumps(manifest, indent=4))

    def build(self, output_path: Path) -> Path:
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        dependency_wheels, editable_dirs = self._resolve_dependencies()

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as jar:
            main_class = self._write_loader_class(jar)
            self._write_manifest_json(jar, main_class)
            vfs_root_rel = self._write_vfs(jar, dependency_wheels, editable_dirs)
            self._write_fileslist(jar, vfs_root_rel)

        print(f"✓ Plugin JAR created: {output_path}")
        return output_path
