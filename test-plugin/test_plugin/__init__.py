import asyncio
from typing import TYPE_CHECKING

import java
from pytale.events import on_async_event, on_event
from pytale.players import PlayerRef
from pytale.plugin import (
    ExecutionContext,
    PluginState,
    get_context,
    get_data_directory,
    get_identifier,
    get_manifest,
    get_state,
    on_setup,
    on_shutdown,
    on_start,
)
from pytale.universe import get_universe
from pytale.world import ChunkNotLoadedError, NotInWorldThreadError, get_world

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

state = get_state()
ctx = get_context()
print(f"\nPlugin State (module import, ctx={ctx.name}): {state.name}")
if ctx == ExecutionContext.GENERAL:
    assert (
        state == PluginState.SETUP
    ), f"Expected SETUP at module import in GENERAL, got {state.name}"
else:
    assert (
        state == PluginState.ENABLED
    ), f"Expected ENABLED at module import in WORLD, got {state.name}"

print("\n" + "=" * 60)


@on_setup
def on_plugin_setup() -> None:
    state = get_state()
    print(f"[LIFECYCLE] Plugin setup! state={state.name}")
    assert state == PluginState.SETUP, f"Expected SETUP in @on_setup, got {state.name}"

    # Universe API demo: reachable from the GENERAL context (no WorldThread).
    universe = get_universe()
    world_names = [world.name for world in universe.worlds]
    default_world = universe.get_default_world()
    print(
        f"[UNIVERSE/GENERAL] worlds={world_names} "
        f"default={default_world.name if default_world else None} "
        f"players={universe.player_count}"
    )


@on_start
def on_plugin_start() -> None:
    state = get_state()
    print(f"[LIFECYCLE] Plugin started! state={state.name}")
    assert state == PluginState.START, f"Expected START in @on_start, got {state.name}"


@on_shutdown
def on_plugin_shutdown() -> None:
    state = get_state()
    print(f"[LIFECYCLE] Plugin shutting down! state={state.name}")
    assert (
        state == PluginState.SHUTDOWN
    ), f"Expected SHUTDOWN in @on_shutdown, got {state.name}"


@on_event(_AddPlayerToWorldEvent)
def handle_add_player_to_world(event: "JavaObject") -> None:
    world_name = event.getWorld().getName()
    print(f"[EVENT/off-WorldThread] AddPlayerToWorldEvent: world={world_name}")

    # This handler runs off the WorldThread, so the world-thread guard should
    # reject block access on a World obtained via the Universe.
    world = get_universe().get_world(world_name)
    assert world is not None
    try:
        world.get_block(0, 64, 0)
        print("[GUARD] ERROR: off-thread get_block was NOT blocked")
    except NotInWorldThreadError as error:
        print(f"[GUARD] off-thread get_block correctly blocked: {error}")


@on_event(_PlayerReadyEvent)
def handle_player_ready(event: "JavaObject") -> None:
    state = get_state()
    print(
        f"[EVENT/WorldThread] PlayerReadyEvent: player={event.getPlayer().getUuid()} state={state.name}"
    )
    assert (
        state == PluginState.ENABLED
    ), f"Expected ENABLED in event handler, got {state.name}"

    # World API demo (runs on the WorldThread, so get_world() is available here)
    world = get_world()
    config = world.config
    print(f"[WORLD] name={world.name!r} tick={world.tick} alive={world.is_alive}")
    print(f"[WORLD] players={world.player_count} ticking={world.is_ticking}")
    print(
        f"[WORLD] config: uuid={config.uuid} seed={config.seed} "
        f"pvp={config.is_pvp_enabled} game_mode={config.game_mode}"
    )
    try:
        block = world.get_block(0, 64, 0)
        print(f"[WORLD] block at (0, 64, 0) = {block}")
    except ChunkNotLoadedError as error:
        print(f"[WORLD] block read skipped: {error}")

    # Universe API demo: same singleton, now from the WORLD context.
    universe = get_universe()
    print(
        f"[UNIVERSE/WorldThread] worlds={[w.name for w in universe.worlds]} "
        f"players={universe.player_count}"
    )
    looked_up = universe.get_world_by_uuid(config.uuid)
    print(
        f"[UNIVERSE] get_world_by_uuid({config.uuid}) -> "
        f"{looked_up.name if looked_up else None}"
    )
    universe.send_message(f"[universe broadcast] {world.name} is online")

    # PlayerRef API demo: list players in this world and round-trip lookups.
    for player in world.players:
        print(
            f"[PLAYER] {player.username} uuid={player.uuid} "
            f"pos={player.position} world={player.world_uuid}"
        )
        by_uuid = universe.get_player(player.uuid)
        by_name = universe.get_player_by_name(player.username)
        print(
            f"[PLAYER] lookups: by_uuid={by_uuid == player} "
            f"by_name={by_name == player} "
            f"can_fly={player.has_permission('hytale.fly', False)}"
        )
        assert isinstance(player, PlayerRef)
        player.send_message(f"Welcome to {world.name}, {player.username}!")


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
