from collections.abc import Awaitable, Callable
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Final, Generic, TypeVar

if TYPE_CHECKING:
    from java import JavaClass

TEvent = TypeVar("TEvent")
TResult = TypeVar("TResult")


class EventPriority(IntEnum):
    FIRST = -21844
    EARLY = -10922
    NORMAL = 0
    LATE = 10922
    LAST = 21844


class BaseEventHandler(Generic[TEvent, TResult]):
    _handler: Callable[..., Any]  # narrowed in subclasses; accessible for logging

    def __init__(
        self,
        java_class: "JavaClass",
        *,
        key: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
    ):
        self.java_class: Final["JavaClass"] = java_class
        self.key: Final[Any] = key
        self.priority: Final[EventPriority] = priority


class EventHandler(BaseEventHandler[TEvent, TResult]):
    def __init__(
        self,
        java_class: "JavaClass",
        handler: Callable[[TEvent], TResult],
        *,
        key: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
    ):
        super().__init__(java_class, key=key, priority=priority)
        self._handler: Callable[[TEvent], TResult] = handler

    def __call__(self, event: TEvent) -> TResult:
        return self._handler(event)


class AsyncEventHandler(BaseEventHandler[TEvent, TResult]):
    """Handler for IAsyncEvent events. Requires an async callable."""

    def __init__(
        self,
        java_class: "JavaClass",
        handler: Callable[[TEvent], Awaitable[TResult]],
        *,
        key: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
    ):
        super().__init__(java_class, key=key, priority=priority)
        self._handler = handler

    async def __call__(self, event: TEvent) -> TResult:
        return await self._handler(event)
