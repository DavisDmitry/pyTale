import json
from enum import Enum
from pathlib import Path

from pytale_tools.exporter.models import ClassMeta
from pytale_tools.generator.analyzer import analyze_properties, nest_inner_classes
from pytale_tools.generator.codegen import generate_module, group_by_package


class GenerateTarget(str, Enum):
    ALL = "all"
    EVENTS = "events"
    COMPONENTS = "components"


_SCHEME: dict[GenerateTarget, tuple[str, str]] = {
    GenerateTarget.EVENTS: ("pytale.events", "BaseEvent"),
    GenerateTarget.COMPONENTS: ("pytale.components", "Component"),
}

# Subdirectory each target is written under when generating GenerateTarget.ALL in one
# call, mirroring the real destinations used in this repo (pytale/hytale/events,
# pytale/hytale/components) so `-o pyTale/pytale` "just works" for a full regeneration.
_ALL_SUBDIRS: dict[GenerateTarget, str] = {
    GenerateTarget.EVENTS: "hytale/events",
    GenerateTarget.COMPONENTS: "hytale/components",
}


def generate(source: Path, output_dir: Path, target: GenerateTarget) -> None:
    if target == GenerateTarget.ALL:
        for sub_target, subdir in _ALL_SUBDIRS.items():
            generate(source, output_dir / subdir, sub_target)
        return

    if source.suffix == ".jar":
        from pytale_tools.exporter import ExportTarget, export

        classes = export(source, ExportTarget(target.value))
    else:
        classes = _load_from_json(source)

    for cls in classes:
        analyze_properties(cls)

    top_level = nest_inner_classes(classes)
    grouped = group_by_package(top_level)
    base_module, default_base = _SCHEME[target]

    output_dir.mkdir(parents=True, exist_ok=True)

    init_dirs: set[Path] = set()
    package_paths = set(grouped.keys())

    for package_path, module_classes in grouped.items():
        parts = package_path.rsplit("/", 1)
        if len(parts) == 2:
            dir_part, file_name = parts
            module_dir = output_dir / dir_part
        else:
            module_dir = output_dir
            file_name = parts[0]

        code = generate_module(
            module_classes,
            jar_name=source.name,
            base_module=base_module,
            default_base=default_base,
        )

        # A Java package can have both classes of its own and a subpackage of the
        # same name (e.g. com.hypixel.hytale.server.core.entity classes alongside
        # com.hypixel.hytale.server.core.entity.entities). Writing both as sibling
        # `entity.py` / `entity/` would make the package directory shadow the module
        # file, so classes belonging directly to a package that also has a
        # generated subpackage go into that subpackage's __init__.py instead.
        if any(other.startswith(package_path + "/") for other in package_paths):
            module_dir = module_dir / file_name
            file_path = module_dir / "__init__.py"
        else:
            file_path = module_dir / f"{file_name}.py"

        module_dir.mkdir(parents=True, exist_ok=True)
        _collect_init_dirs(output_dir, module_dir, init_dirs)
        file_path.write_text(code)

        relative = file_path.relative_to(output_dir)
        print(f"  {relative} ({len(module_classes)} classes)")

    for init_dir in sorted(init_dirs):
        init_file = init_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()


def _collect_init_dirs(root: Path, target: Path, dirs: set[Path]) -> None:
    dirs.add(root)
    current = target
    while current != root:
        dirs.add(current)
        current = current.parent


def _load_from_json(path: Path) -> list[ClassMeta]:
    data = json.loads(path.read_text())
    return [ClassMeta.from_dict(entry) for entry in data]
