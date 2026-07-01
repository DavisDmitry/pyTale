"""Wrappers for common ECS/math value types (JOML vectors, Hytale rotations)"""

from pytale._java_wrapper import JavaWrapper


class Vector3(JavaWrapper):
    """Wrapper for org.joml.Vector3d / org.joml.Vector3f: public x/y/z fields of the
    same shape, used across many generated component properties (positions,
    directions, etc.)."""

    @property
    def x(self) -> float:
        return float(self._java.x)

    @property
    def y(self) -> float:
        return float(self._java.y)

    @property
    def z(self) -> float:
        return float(self._java.z)

    def __repr__(self) -> str:
        return f"Vector3({self.x}, {self.y}, {self.z})"


class Rotation3(JavaWrapper):
    """Wrapper for com.hypixel.hytale.math.vector.Rotation3f: pitch/yaw/roll in
    degrees, same x/y/z field shape as Vector3."""

    @property
    def x(self) -> float:
        return float(self._java.x)

    @property
    def y(self) -> float:
        return float(self._java.y)

    @property
    def z(self) -> float:
        return float(self._java.z)

    def __repr__(self) -> str:
        return f"Rotation3({self.x}, {self.y}, {self.z})"
