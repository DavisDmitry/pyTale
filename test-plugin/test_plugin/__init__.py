import asyncio

from pytale.commands import (
    Arg,
    ArgType,
    CommandContext,
    CommandType,
    FlagArg,
    collection,
    command,
)
from pytale.events import on_event
from pytale.events.hytale.server.core.event.events.player import (
    AddPlayerToWorldEvent,
    PlayerChatEvent,
    PlayerReadyEvent,
)
from pytale.message import Message
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


@on_event(AddPlayerToWorldEvent)
def handle_add_player_to_world(event: AddPlayerToWorldEvent) -> None:
    print(f"[EVENT/off-WorldThread] AddPlayerToWorldEvent: world={event.world.name}")

    world = get_universe().get_world(event.world.name)
    assert world is not None
    try:
        world.get_block(0, 64, 0)
        print("[GUARD] ERROR: off-thread get_block was NOT blocked")
    except NotInWorldThreadError as error:
        print(f"[GUARD] off-thread get_block correctly blocked: {error}")


@on_event(PlayerReadyEvent)
def handle_player_ready(event: PlayerReadyEvent) -> None:
    state = get_state()
    print(
        f"[EVENT/WorldThread] PlayerReadyEvent: player={event.player_ref} state={state.name}"
    )
    assert (
        state == PluginState.ENABLED
    ), f"Expected ENABLED in event handler, got {state.name}"

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
    universe.send_message(
        Message.raw(f"[universe broadcast] {world.name} is online").color("#aaaaaa")
    )

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
        player.send_message(
            Message.join(
                Message.raw(f"Welcome to {world.name}, "),
                Message.raw(player.username).bold().color("#ffaa00"),
                Message.raw("!"),
            )
        )


@on_event(PlayerChatEvent)
async def handle_player_chat(event: PlayerChatEvent) -> None:
    original = event.content
    await asyncio.sleep(0.05)
    event.content = f"[async] {original}"
    print(
        f"[ASYNC-EVENT] PlayerChatEvent: {event.sender!r} said {original!r} → content prefixed"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@command("ping", description="Check server responsiveness")
async def handle_ping(ctx: CommandContext) -> None:
    ctx.send_message("Pong!")


@command(
    "greet",
    description="Greet a player",
    aliases=["hello"],
    args=[
        Arg("player", ArgType.PLAYER_REF, required=False),
        FlagArg("loud"),
    ],
)
async def handle_greet(ctx: CommandContext) -> None:
    player = ctx.get("player", None)
    name = player.getUsername() if player is not None else ctx.sender.username
    msg = f"Hello, {name}!"
    if ctx.get("loud", False):
        msg = msg.upper()
    ctx.send_message(msg)


@command(
    "whereami",
    description="Show your position",
    type=CommandType.PLAYER,
)
def handle_whereami(ctx: CommandContext) -> None:
    assert ctx.player_ref is not None
    pos = ctx.player_ref.position
    ctx.send_message(f"You are at {pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}")


admin = collection(
    "pytale", description="pyTale admin commands", permission="pytale.admin"
)


@admin.command("status", description="Show plugin status")
async def handle_admin_status(ctx: CommandContext) -> None:
    ctx.send_message(
        f"pyTale is running! State: {get_state().name}, Context: {get_context().name}"
    )
