import json
from enum import Enum
from pathlib import Path

from pytale_tools.exporter.jar_reader import read_component_classes, read_event_classes
from pytale_tools.exporter.models import ClassMeta


class ExportTarget(str, Enum):
    ALL = "all"
    EVENTS = "events"
    COMPONENTS = "components"


def export(jar_path: Path, target: ExportTarget) -> list[ClassMeta]:
    if target == ExportTarget.ALL:
        return read_event_classes(jar_path) + read_component_classes(jar_path)
    if target == ExportTarget.COMPONENTS:
        return read_component_classes(jar_path)
    if target == ExportTarget.EVENTS:
        return read_event_classes(jar_path)
    raise ValueError(f"Unknown export target: {target}")


def export_to_json(
    jar_path: Path, output_dir: Path, target: ExportTarget
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if target in (ExportTarget.ALL, ExportTarget.EVENTS):
        classes = read_event_classes(jar_path)
        data = [cls.to_dict() for cls in classes]
        path = output_dir / "events.json"
        path.write_text(json.dumps(data, indent=2))
        written.append(path)

    if target in (ExportTarget.ALL, ExportTarget.COMPONENTS):
        classes = read_component_classes(jar_path)
        data = [cls.to_dict() for cls in classes]
        path = output_dir / "components.json"
        path.write_text(json.dumps(data, indent=2))
        written.append(path)

    return written
