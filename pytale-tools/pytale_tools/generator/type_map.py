from pytale_tools.exporter.models import Nullability

_PRIMITIVE_MAP: dict[str, str] = {
    "Z": "bool",
    "B": "int",
    "C": "str",
    "S": "int",
    "I": "int",
    "J": "int",
    "F": "float",
    "D": "float",
    "V": "None",
}

_REFERENCE_MAP: dict[str, str] = {
    "Ljava/lang/String;": "str",
    "Ljava/lang/Boolean;": "bool",
    "Ljava/lang/Byte;": "int",
    "Ljava/lang/Short;": "int",
    "Ljava/lang/Integer;": "int",
    "Ljava/lang/Long;": "int",
    "Ljava/lang/Float;": "float",
    "Ljava/lang/Double;": "float",
    "Ljava/lang/Void;": "None",
}

_WRAPPER_MAP: dict[str, tuple[str, str]] = {
    "Lcom/hypixel/hytale/server/core/universe/PlayerRef;": (
        "PlayerRef",
        "pytale.players",
    ),
    "Lcom/hypixel/hytale/server/core/universe/world/World;": (
        "World",
        "pytale.world",
    ),
    "Lcom/hypixel/hytale/server/core/Message;": (
        "Message",
        "pytale.message",
    ),
    "Lorg/joml/Vector3d;": ("Vector3", "pytale.math"),
    "Lorg/joml/Vector3dc;": ("Vector3", "pytale.math"),
    "Lorg/joml/Vector3f;": ("Vector3", "pytale.math"),
    "Lorg/joml/Vector3fc;": ("Vector3", "pytale.math"),
    "Lcom/hypixel/hytale/math/vector/Rotation3f;": ("Rotation3", "pytale.math"),
    "Lcom/hypixel/hytale/math/vector/Rotation3fc;": ("Rotation3", "pytale.math"),
}


def map_descriptor(
    descriptor: str, nullability: Nullability = Nullability.UNSPECIFIED
) -> str:
    mapped = _PRIMITIVE_MAP.get(descriptor)
    if mapped is not None:
        return mapped

    mapped = _REFERENCE_MAP.get(descriptor)
    if mapped is not None:
        if nullability == Nullability.NULLABLE:
            return f"{mapped} | None"
        return mapped

    wrapper = _WRAPPER_MAP.get(descriptor)
    if wrapper is not None:
        cls_name = wrapper[0]
        if nullability == Nullability.NULLABLE:
            return f"{cls_name} | None"
        return cls_name

    if nullability == Nullability.NULLABLE:
        return '"JavaObject | None"'
    return '"JavaObject"'


def get_wrapper_info(descriptor: str) -> tuple[str, str] | None:
    return _WRAPPER_MAP.get(descriptor)
