from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Nullability(Enum):
    UNSPECIFIED = auto()
    NONNULL = auto()
    NULLABLE = auto()


@dataclass(frozen=True)
class MethodMeta:
    name: str
    descriptor: str
    return_type_descriptor: str
    param_type_descriptors: tuple[str, ...]
    is_public: bool
    is_static: bool
    is_bridge: bool
    is_synthetic: bool
    nullability: Nullability
    is_deprecated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "descriptor": self.descriptor,
            "return_type_descriptor": self.return_type_descriptor,
            "param_type_descriptors": list(self.param_type_descriptors),
            "is_public": self.is_public,
            "is_static": self.is_static,
            "is_bridge": self.is_bridge,
            "is_synthetic": self.is_synthetic,
            "nullability": self.nullability.name,
            "is_deprecated": self.is_deprecated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MethodMeta":
        return cls(
            name=data["name"],
            descriptor=data["descriptor"],
            return_type_descriptor=data["return_type_descriptor"],
            param_type_descriptors=tuple(data["param_type_descriptors"]),
            is_public=data["is_public"],
            is_static=data["is_static"],
            is_bridge=data["is_bridge"],
            is_synthetic=data["is_synthetic"],
            nullability=Nullability[data["nullability"]],
            is_deprecated=data.get("is_deprecated", False),
        )


@dataclass
class ClassMeta:
    java_fqn: str
    java_dotted: str
    python_class_name: str
    super_class: str | None
    interfaces: tuple[str, ...]
    is_abstract: bool
    is_sync_event: bool
    is_async_event: bool
    is_cancellable: bool
    is_deprecated: bool = False
    methods: list[MethodMeta] = field(default_factory=list)
    properties: list[Any] = field(default_factory=list)
    inner_classes: list["ClassMeta"] = field(default_factory=list)
    is_inner: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "java_fqn": self.java_fqn,
            "java_dotted": self.java_dotted,
            "python_class_name": self.python_class_name,
            "super_class": self.super_class,
            "interfaces": list(self.interfaces),
            "is_abstract": self.is_abstract,
            "is_sync_event": self.is_sync_event,
            "is_async_event": self.is_async_event,
            "is_cancellable": self.is_cancellable,
            "is_deprecated": self.is_deprecated,
            "methods": [m.to_dict() for m in self.methods],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassMeta":
        return cls(
            java_fqn=data["java_fqn"],
            java_dotted=data["java_dotted"],
            python_class_name=data["python_class_name"],
            super_class=data["super_class"],
            interfaces=tuple(data["interfaces"]),
            is_abstract=data["is_abstract"],
            is_sync_event=data["is_sync_event"],
            is_async_event=data["is_async_event"],
            is_cancellable=data["is_cancellable"],
            is_deprecated=data.get("is_deprecated", False),
            methods=[MethodMeta.from_dict(m) for m in data["methods"]],
        )
