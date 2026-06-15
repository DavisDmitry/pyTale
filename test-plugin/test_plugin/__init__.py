import asyncio
from typing import TYPE_CHECKING

import java
from pytale.events import on_async_event, on_event
from pytale.plugin import (
    get_context,
    get_data_directory,
    get_identifier,
    get_manifest,
    on_setup,
    on_shutdown,
    on_start,
)

if TYPE_CHECKING:
    from java import JavaObject

_AddPlayerToWorldEvent = java.type(
    "com.hypixel.hytale.server.core.event.events.player.AddPlayerToWorldEvent"
)
_PlayerReadyEvent = java.type(
    "com.hypixel.hytale.server.core.event.events.player.PlayerReadyEvent"
)
_PlayerChatEvent = java.type(
    "com.hypixel.hytale.server.core.event.events.player.PlayerChatEvent"
)

print("=" * 60)
print("pyTale Plugin Information")
print("=" * 60)

identifier = get_identifier()
print(f"\nIdentifier:")
print(f"  Group: {identifier.group}")
print(f"  Name: {identifier.name}")

manifest = get_manifest()
print(f"\nManifest:")
print(f"  Name: {manifest.name}")
print(f"  Version: {manifest.version}")
print(f"  Description: {manifest.description}")
print(f"  Authors: {manifest.authors}")
print(f"  Website: {manifest.website}")

data_dir = get_data_directory()
print(f"\nData Directory: {data_dir}")

context = get_context()
print(f"\nExecution Context: {context.name} ({context.value})")

print("\n" + "=" * 60)


@on_setup
def on_plugin_setup() -> None:
    print("[LIFECYCLE] Plugin setup!")


@on_start
def on_plugin_start() -> None:
    print("[LIFECYCLE] Plugin started!")


@on_shutdown
def on_plugin_shutdown() -> None:
    print("[LIFECYCLE] Plugin shutting down!")


@on_event(_AddPlayerToWorldEvent)
def handle_add_player_to_world(event: "JavaObject") -> None:
    print(
        f"[EVENT/off-WorldThread] AddPlayerToWorldEvent: world={event.getWorld().getName()}"
    )


@on_event(_PlayerReadyEvent)
def handle_player_ready(event: "JavaObject") -> None:
    print(f"[EVENT/WorldThread] PlayerReadyEvent: player={event.getPlayer().getUuid()}")


@on_async_event(_PlayerChatEvent)
async def handle_player_chat_async(event: "JavaObject") -> None:
    sender = event.getSender().getUsername()
    original = event.getContent()
    # Simulate async work (e.g. database lookup, moderation check).
    await asyncio.sleep(0.05)
    event.setContent(f"[async] {original}")
    print(
        f"[ASYNC-EVENT] PlayerChatEvent: {sender!r} said {original!r} → content prefixed"
    )
