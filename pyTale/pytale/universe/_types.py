"""Type wrapper for the server-wide universe API"""

from typing import TYPE_CHECKING

import java as _java

if TYPE_CHECKING:
    from java import JavaObject

from pytale.world._types import World

_Message = _java.type("com.hypixel.hytale.server.core.Message")
_UUID = _java.type("java.util.UUID")


class Universe:
    """Wrapper for com.hypixel.hytale.server.core.universe.Universe.

    The universe is a process-wide singleton that owns every loaded world and
    connected player, so it can be reached from any execution context (see
    ``get_universe``).

    Worlds returned from here are real ``World`` wrappers, but note: a world
    obtained outside its own WORLD context is safe for metadata/config reads and
    ``send_message``. Block access and world-state mutation must run on that
    world's thread; calling those methods here raises
    ``pytale.world.NotInWorldThreadError``.
    """

    def __init__(self, java_obj: "JavaObject") -> None:
        self._java = java_obj

    # --- read-only properties ---

    @property
    def player_count(self) -> int:
        """Total number of players connected across all worlds."""
        return self._java.getPlayerCount()

    @property
    def worlds(self) -> list[World]:
        """All currently loaded worlds."""
        return [World(world) for world in self._java.getWorlds().values()]

    # --- lookups ---

    def get_world(self, name: str) -> World | None:
        """Return the world with the given name, or None if not loaded."""
        world = self._java.getWorld(name)
        return World(world) if world is not None else None

    def get_world_by_uuid(self, uuid: str) -> World | None:
        """Return the world with the given UUID, or None if not loaded."""
        world = self._java.getWorld(_UUID.fromString(uuid))
        return World(world) if world is not None else None

    def get_default_world(self) -> World | None:
        """Return the configured default world, or None if unavailable."""
        world = self._java.getDefaultWorld()
        return World(world) if world is not None else None

    # --- other methods ---

    def send_message(self, message: str) -> None:
        """Broadcast a raw text message to every connected player."""
        self._java.sendMessage(_Message.raw(message))

    def __repr__(self) -> str:
        return f"Universe(worlds={len(self.worlds)}, players={self.player_count})"
