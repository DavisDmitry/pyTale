import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any, Protocol

from pytale.commands._context import CommandContext
from pytale.commands._types import (
    ASYNC_TYPES,
    WORLD_THREAD_TYPES,
    Arg,
    CommandHandler,
    CommandType,
    FlagArg,
)
from pytale.plugin._plugin import get_context, get_state
from pytale.plugin._types import ExecutionContext, PluginState

_logger = logging.getLogger(__name__)

_sync_handlers: list[CommandHandler[Any]] = []
_async_handlers: list[CommandHandler[Any]] = []
_tasks: set[asyncio.Task[None]] = set()

_RuntimeException = None


def _get_runtime_exception() -> Any:
    global _RuntimeException
    if _RuntimeException is None:
        import java as _java

        _RuntimeException = _java.type("java.lang.RuntimeException")
    return _RuntimeException


class _JavaFuture(Protocol):
    def complete(self, value: Any) -> bool: ...
    def completeExceptionally(self, ex: Any) -> bool: ...


class _QueuedCommand(Protocol):
    def index(self) -> int: ...
    def ctx(self) -> Any: ...
    def future(self) -> _JavaFuture: ...


class CommandQueue(Protocol):
    def take(self) -> _QueuedCommand: ...


def _validate_registration() -> None:
    if get_context() == ExecutionContext.GENERAL:
        state = get_state()
        if state != PluginState.SETUP:
            raise RuntimeError(
                f"Commands can only be registered during plugin setup "
                f"(current state: {state.name})"
            )


def _register_handler(handler: CommandHandler[Any]) -> None:
    if handler.command_type in WORLD_THREAD_TYPES:
        handler.index = len(_sync_handlers)
        _sync_handlers.append(handler)
    else:
        if get_context() == ExecutionContext.WORLD:
            return
        handler.index = len(_async_handlers)
        _async_handlers.append(handler)


def _make_handler(
    name: str,
    func: Callable[..., Any],
    *,
    description: str,
    permission: str | None,
    aliases: list[str] | None,
    args: list[Arg | FlagArg] | None,
    command_type: CommandType,
) -> CommandHandler[Any]:
    actual = func
    if command_type in ASYNC_TYPES and not inspect.iscoroutinefunction(func):

        async def _async_wrapper(ctx: CommandContext) -> Any:
            return func(ctx)

        _async_wrapper.__name__ = func.__name__
        _async_wrapper.__qualname__ = func.__qualname__
        actual = _async_wrapper

    if command_type in WORLD_THREAD_TYPES and inspect.iscoroutinefunction(func):
        raise TypeError(
            f"async def {func.__name__} cannot be used with {command_type.name} "
            "commands; world-thread commands must be synchronous"
        )

    return CommandHandler(
        name,
        actual,
        description=description,
        permission=permission,
        aliases=aliases,
        args=args,
        command_type=command_type,
    )


class CommandCollection:
    """A named group of sub-commands.

    Top-level collections are created via the module-level ``collection()``
    function. Nested collections are created via ``.collection()`` on an
    existing collection.
    """

    def __init__(
        self,
        name: str,
        *,
        description: str = "",
        permission: str | None = None,
        aliases: list[str] | None = None,
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.permission: str | None = permission
        self.aliases: list[str] = aliases or []
        self.sub_commands: list[CommandHandler[Any]] = []
        self.sub_collections: list[CommandCollection] = []

    def command(
        self,
        name: str,
        *,
        description: str = "",
        permission: str | None = None,
        aliases: list[str] | None = None,
        args: list[Arg | FlagArg] | None = None,
        type: CommandType = CommandType.DEFAULT,
    ) -> Callable[[Callable[..., Any]], CommandHandler[Any]]:
        _validate_registration()

        def decorator(func: Callable[..., Any]) -> CommandHandler[Any]:
            handler = _make_handler(
                name,
                func,
                description=description,
                permission=permission,
                aliases=aliases,
                args=args,
                command_type=type,
            )
            _register_handler(handler)
            self.sub_commands.append(handler)
            _logger.debug(
                "Registered command /%s (type=%s, index=%d)",
                name,
                type.name,
                handler.index,
            )
            return handler

        return decorator

    def collection(
        self,
        name: str,
        *,
        description: str = "",
        permission: str | None = None,
        aliases: list[str] | None = None,
    ) -> "CommandCollection":
        child = CommandCollection(
            name,
            description=description,
            permission=permission,
            aliases=aliases,
        )
        self.sub_collections.append(child)
        return child


_root = CommandCollection("__root__")

command = _root.command
collection = _root.collection

_commands = _root.sub_commands
_collections = _root.sub_collections


def _execute_command(index: int, java_context: Any) -> None:
    """Synchronous dispatch for world-thread commands (WORLD, PLAYER)."""
    handler = _sync_handlers[index]
    try:
        ctx = CommandContext(java_context)
        handler(ctx)
    except Exception as error:
        _logger.exception("Error in command handler /%s: %s", handler.name, repr(error))


async def _invoke_command(queued: _QueuedCommand) -> None:
    """Async dispatch for async-context commands (DEFAULT, ASYNC_WORLD, ASYNC_PLAYER)."""
    handler = _async_handlers[queued.index()]
    try:
        ctx = CommandContext(queued.ctx())
        await handler(ctx)
        queued.future().complete(None)
    except Exception as error:
        _logger.exception("Error in command handler /%s: %s", handler.name, repr(error))
        queued.future().completeExceptionally(_get_runtime_exception()(repr(error)))


async def command_loop(java_queue: CommandQueue) -> None:
    """Drain the command queue until a poison pill arrives."""
    while True:
        queued = await asyncio.to_thread(java_queue.take)
        if queued.index() < 0:
            await asyncio.gather(*_tasks, return_exceptions=True)
            return
        task = asyncio.create_task(_invoke_command(queued))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
