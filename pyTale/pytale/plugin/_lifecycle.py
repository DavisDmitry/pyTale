"""Plugin lifecycle event handlers"""

import logging
from collections.abc import Callable
from typing import Any, Literal, TypedDict, TypeVar

from pytale.plugin._plugin import get_context
from pytale.plugin._types import ExecutionContext

_TLifecycleListener = TypeVar("_TLifecycleListener", bound=Callable[[], Any])
_EventType = Literal["setup", "start", "shutdown"]

_logger = logging.getLogger(__name__)


class _LifecycleListeners(TypedDict, total=True):
    """Registered listeners for lifecycle events"""

    setup: list[Callable[[], Any]]
    start: list[Callable[[], Any]]
    shutdown: list[Callable[[], Any]]


__listeners = _LifecycleListeners(setup=[], start=[], shutdown=[])


def __add_listener(event: _EventType, listener: Callable[[], Any]) -> None:
    """Add a listener to the specified event"""
    if get_context() == ExecutionContext.GENERAL:
        __listeners[event].append(listener)


def on_setup(listener: _TLifecycleListener) -> _TLifecycleListener:
    """Register listener for plugin setup (before start)"""
    __add_listener("setup", listener)
    return listener


def on_start(listener: _TLifecycleListener) -> _TLifecycleListener:
    """Register listener for plugin start (after setup, before enabled)"""
    __add_listener("start", listener)
    return listener


def on_shutdown(listener: _TLifecycleListener) -> _TLifecycleListener:
    """Register listener for plugin shutdown"""
    __add_listener("shutdown", listener)
    return listener


def _execute_listeners(event: _EventType) -> None:
    """Internal: execute all listeners for an event"""
    listeners = __listeners[event]
    for listener in listeners:
        try:
            listener()
        except Exception as error:
            _logger.exception(
                "Error in %s listener %s: %s", event, listener.__name__, repr(error)
            )
