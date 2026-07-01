import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from javatools import unpack_class  # type: ignore[import-not-found]
from pytale_tools.exporter.models import ClassMeta, MethodMeta, Nullability
from pytale_tools.generator.naming import java_class_to_python_name

_IBASE_EVENT = "com/hypixel/hytale/event/IBaseEvent"
_IEVENT = "com/hypixel/hytale/event/IEvent"
_IASYNC_EVENT = "com/hypixel/hytale/event/IAsyncEvent"
_ICANCELLABLE = "com/hypixel/hytale/event/ICancellable"
_ICANCELLABLE_ECS = "com/hypixel/hytale/component/event/ICancellableEcsEvent"
_COMPONENT = "com/hypixel/hytale/component/Component"

_NONNULL_PATTERN = re.compile(r"Nonnull")
_NULLABLE_PATTERN = re.compile(r"Nullable")
_DEPRECATED_PATTERN = re.compile(r"java\.lang\.Deprecated")

_DESCRIPTOR_RETURN = re.compile(r"\)(.+)$")
_DESCRIPTOR_PARAMS = re.compile(r"\(([^)]*)\)")
_PARAM_TOKEN = re.compile(r"\[*(?:[ZBCSIJFD]|L[^;]+;)")


def _parse_return_type(descriptor: str) -> str:
    m = _DESCRIPTOR_RETURN.search(descriptor)
    return m.group(1) if m else "V"


def _parse_param_types(descriptor: str) -> tuple[str, ...]:
    m = _DESCRIPTOR_PARAMS.search(descriptor)
    if not m or not m.group(1):
        return ()
    return tuple(_PARAM_TOKEN.findall(m.group(1)))


def _detect_nullability(method: Any) -> Nullability:
    for annotations_fn in (method.get_annotations, method.get_invisible_annotations):
        for annotation in annotations_fn():
            type_str = str(annotation)
            if _NONNULL_PATTERN.search(type_str):
                return Nullability.NONNULL
            if _NULLABLE_PATTERN.search(type_str):
                return Nullability.NULLABLE
    return Nullability.UNSPECIFIED


def _is_deprecated(annotations: Any) -> bool:
    return any(_DEPRECATED_PATTERN.search(str(a)) for a in annotations)


def _extract_methods(class_info: Any) -> list[MethodMeta]:
    methods: list[MethodMeta] = []
    for m in class_info.methods:
        descriptor = m.get_descriptor()
        methods.append(
            MethodMeta(
                name=m.get_name(),
                descriptor=descriptor,
                return_type_descriptor=_parse_return_type(descriptor),
                param_type_descriptors=_parse_param_types(descriptor),
                is_public=bool(m.is_public()),
                is_static=bool(m.is_static()),
                is_bridge=bool(m.is_bridge()),
                is_synthetic=bool(m.is_synthetic()),
                nullability=_detect_nullability(m),
                is_deprecated=_is_deprecated(m.get_annotations()),
            )
        )
    return methods


def _build_hierarchy(
    jar: zipfile.ZipFile,
) -> tuple[dict[str, set[str]], dict[str, bytes]]:
    children: dict[str, set[str]] = defaultdict(set)
    class_bytes: dict[str, bytes] = {}

    for entry in jar.namelist():
        if not entry.endswith(".class"):
            continue
        data = jar.read(entry)
        class_bytes[entry] = data
        try:
            ci = unpack_class(data)
        except Exception:
            continue

        fqn = ci.get_this()
        super_cls = ci.get_super()
        if super_cls:
            children[super_cls].add(fqn)
        for iface in ci.get_interfaces():
            children[iface].add(fqn)

    return children, class_bytes


def _find_descendants(children: dict[str, set[str]], root: str) -> set[str]:
    result: set[str] = set()
    stack = list(children.get(root, set()))
    while stack:
        fqn = stack.pop()
        if fqn in result:
            continue
        result.add(fqn)
        stack.extend(children.get(fqn, set()))
    return result


def read_event_classes(jar_path: Path) -> list[ClassMeta]:
    with zipfile.ZipFile(jar_path) as jar:
        children, class_bytes = _build_hierarchy(jar)

    event_fqns = _find_descendants(children, _IBASE_EVENT)

    ievent_descendants = _find_descendants(children, _IEVENT)
    iasync_descendants = _find_descendants(children, _IASYNC_EVENT)
    icancellable_descendants = _find_descendants(children, _ICANCELLABLE)
    icancellable_ecs_descendants = _find_descendants(children, _ICANCELLABLE_ECS)

    classes: list[ClassMeta] = []
    for fqn in sorted(event_fqns):
        class_path = fqn + ".class"
        data = class_bytes.get(class_path)
        if data is None:
            continue

        try:
            ci = unpack_class(data)
        except Exception:
            continue

        is_abstract = bool(ci.is_abstract())
        is_interface = bool(ci.is_interface())
        if is_interface:
            continue

        name_parts = java_class_to_python_name(fqn)
        python_name = name_parts[-1]

        classes.append(
            ClassMeta(
                java_fqn=fqn,
                java_dotted=fqn.replace("/", "."),
                python_class_name=python_name,
                super_class=ci.get_super(),
                interfaces=tuple(ci.get_interfaces()),
                is_abstract=is_abstract,
                is_sync_event=fqn in ievent_descendants,
                is_async_event=fqn in iasync_descendants,
                is_cancellable=(
                    fqn in icancellable_descendants
                    or fqn in icancellable_ecs_descendants
                ),
                is_deprecated=_is_deprecated(ci.get_annotations()),
                methods=_extract_methods(ci),
            )
        )

    return classes


def read_component_classes(jar_path: Path) -> list[ClassMeta]:
    with zipfile.ZipFile(jar_path) as jar:
        children, class_bytes = _build_hierarchy(jar)

    component_fqns = _find_descendants(children, _COMPONENT)

    classes: list[ClassMeta] = []
    for fqn in sorted(component_fqns):
        class_path = fqn + ".class"
        data = class_bytes.get(class_path)
        if data is None:
            continue

        try:
            ci = unpack_class(data)
        except Exception:
            continue

        if bool(ci.is_interface()):
            continue

        name_parts = java_class_to_python_name(fqn)
        python_name = name_parts[-1]

        classes.append(
            ClassMeta(
                java_fqn=fqn,
                java_dotted=fqn.replace("/", "."),
                python_class_name=python_name,
                super_class=ci.get_super(),
                interfaces=tuple(ci.get_interfaces()),
                is_abstract=bool(ci.is_abstract()),
                is_sync_event=False,
                is_async_event=False,
                is_cancellable=False,
                is_deprecated=_is_deprecated(ci.get_annotations()),
                methods=_extract_methods(ci),
            )
        )

    return classes
