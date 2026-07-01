"""Type wrapper for entity/component access via a world's ECS store"""

from typing import TYPE_CHECKING, TypeVar

import java as _java

if TYPE_CHECKING:
    from java import JavaObject

from pytale._java_wrapper import JavaWrapper
from pytale.components import Component
from pytale.world.errors import NotInWorldThreadError

_RemoveReason = _java.type("com.hypixel.hytale.component.RemoveReason")

C = TypeVar("C", bound=Component)


class EntityRef(JavaWrapper):
    """Wrapper for com.hypixel.hytale.component.Ref<EntityStore>: a stable handle to
    one entity in a world's ECS store (players, mobs, item drops, etc.).

    Every property/method except ``is_valid`` touches the world's entity component
    store directly and therefore must run on that world's own tick thread, raising
    NotInWorldThreadError otherwise (mirrors World.get_block). Obtain instances via
    World.entities, World.get_entity(), World.get_entity_by_network_id(), or
    World.spawn_entity().
    """

    def __init__(
        self,
        java_ref: "JavaObject",
        java_store: "JavaObject",
        world_name: str,
        java_world: "JavaObject",
    ) -> None:
        super().__init__(java_ref)
        self._store = java_store
        self._world_name = world_name
        self._world = java_world

    def _require_thread(self, operation: str) -> None:
        if not self._world.isInThread():
            raise NotInWorldThreadError(self._world_name, operation)

    @property
    def is_valid(self) -> bool:
        """Whether this reference still points at a live entity. Safe from any context."""
        return self._java.isValid()

    # --- component access, generic over any pytale.components.Component subclass ---

    def get_component(self, component_class: type[C]) -> C | None:
        """Return this entity's component wrapped as an instance of the given
        auto-generated component class (e.g. TransformComponent), or None if absent.
        """
        self._require_thread("get_component")
        component_type = component_class._java_class.getComponentType()
        raw = self._store.getComponent(self._java, component_type)
        return component_class(raw) if raw is not None else None

    def has_component(self, component_class: type[Component]) -> bool:
        """Whether this entity has a component of the given generated type."""
        self._require_thread("has_component")
        component_type = component_class._java_class.getComponentType()
        return self._store.getComponent(self._java, component_type) is not None

    def ensure_component(self, component_class: type[C]) -> C:
        """Return this entity's component of the given type, creating a default
        instance first if it doesn't already have one."""
        self._require_thread("ensure_component")
        component_type = component_class._java_class.getComponentType()
        return component_class(
            self._store.ensureAndGetComponent(self._java, component_type)
        )

    def put_component(self, component: Component) -> None:
        """Attach ``component`` (an instance of a generated component class) to this
        entity, replacing any existing component of that same type. Idempotent: never
        throws whether or not the entity already has one (Store.putComponent, not the
        throwing addComponent/replaceComponent — Java exceptions from host calls can't
        be caught from Python, see project notes on GraalPy exception interop).
        """
        self._require_thread("put_component")
        component_type = type(component)._java_class.getComponentType()
        self._store.putComponent(self._java, component_type, component._java)

    def remove_component(self, component_class: type[Component]) -> bool:
        """Remove this entity's component of the given type. Returns whether it was
        present (Store.removeComponentIfExists, which never throws for a missing
        component, unlike Store.removeComponent)."""
        self._require_thread("remove_component")
        component_type = component_class._java_class.getComponentType()
        return self._store.removeComponentIfExists(self._java, component_type)

    # --- lifecycle ---

    def remove(self) -> bool:
        """Remove this entity from the world. Returns False as a no-op if this entity
        was already invalid (checked here rather than relying on catching a Java
        validation exception, which host calls can't raise catchably into Python)."""
        self._require_thread("remove")
        if not self._java.isValid():
            return False
        self._store.removeEntity(self._java, _RemoveReason.REMOVE)
        return True

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, EntityRef)
            and self._store == other._store
            and self._java.getIndex() == other._java.getIndex()
        )

    def __hash__(self) -> int:
        return hash((self._store, self._java.getIndex()))

    def __repr__(self) -> str:
        return f"EntityRef({self._java})"
