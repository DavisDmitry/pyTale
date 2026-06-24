import json
from enum import Enum
from pathlib import Path

from pytale_tools.exporter.models import ClassMeta
from pytale_tools.generator.analyzer import analyze_properties, nest_inner_classes
from pytale_tools.generator.codegen import generate_module, group_by_package


class GenerateTarget(str, Enum):
    ALL = "all"
    EVENTS = "events"


def generate(source: Path, output_dir: Path, target: GenerateTarget) -> None:
    if source.suffix == ".jar":
        from pytale_tools.exporter import ExportTarget, export

        classes = export(source, ExportTarget(target.value))
    else:
        classes = _load_from_json(source)

    for cls in classes:
        analyze_properties(cls)

    top_level = nest_inner_classes(classes)
    grouped = group_by_package(top_level)

    output_dir.mkdir(parents=True, exist_ok=True)

    init_dirs: set[Path] = set()

    for package_path, module_classes in grouped.items():
        parts = package_path.rsplit("/", 1)
        if len(parts) == 2:
            dir_part, file_name = parts
            module_dir = output_dir / dir_part
        else:
            module_dir = output_dir
            file_name = parts[0]

        module_dir.mkdir(parents=True, exist_ok=True)
        _collect_init_dirs(output_dir, module_dir, init_dirs)

        code = generate_module(module_classes, jar_name=source.name)
        file_path = module_dir / f"{file_name}.py"
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
