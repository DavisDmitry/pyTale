from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar


class CommandType(Enum):
    DEFAULT = "DEFAULT"
    WORLD = "WORLD"
    ASYNC_WORLD = "ASYNC_WORLD"
    PLAYER = "PLAYER"
    ASYNC_PLAYER = "ASYNC_PLAYER"


class ArgType(Enum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    STRING = "STRING"
    GREEDY_STRING = "GREEDY_STRING"
    UUID = "UUID"
    PLAYER_REF = "PLAYER_REF"
    WORLD = "WORLD"
    GAME_MODE = "GAME_MODE"


@dataclass(frozen=True)
class Arg:
    name: str
    arg_type: ArgType
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass(frozen=True)
class FlagArg:
    name: str
    description: str = ""


WORLD_THREAD_TYPES = frozenset({CommandType.WORLD, CommandType.PLAYER})
ASYNC_TYPES = frozenset(
    {CommandType.DEFAULT, CommandType.ASYNC_WORLD, CommandType.ASYNC_PLAYER}
)

TResult = TypeVar("TResult")


class CommandHandler(Generic[TResult]):
    def __init__(
        self,
        name: str,
        handler: Callable[..., TResult],
        *,
        description: str = "",
        permission: str | None = None,
        aliases: list[str] | None = None,
        args: list[Arg | FlagArg] | None = None,
        command_type: CommandType = CommandType.DEFAULT,
    ):
        self.name: str = name
        self.description: str = description
        self.permission: str | None = permission
        self.aliases: list[str] = aliases or []
        self.args: list[Arg | FlagArg] = args or []
        self.command_type: CommandType = command_type
        self.index: int = -1
        self._handler: Callable[..., TResult] = handler

    def __call__(self, *args: Any, **kwargs: Any) -> TResult:
        return self._handler(*args, **kwargs)
