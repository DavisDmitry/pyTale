"""Access to the server-wide universe singleton"""

import java as _java
from pytale.universe._types import Universe

_Universe = _java.type("com.hypixel.hytale.server.core.universe.Universe")

__universe: Universe | None = None


def get_universe() -> Universe:
    """Get the server Universe.

    Unlike ``get_world``, this is available in any execution context: the
    universe is a process-wide singleton resolved on first use and cached.
    """
    global __universe
    if __universe is None:
        __universe = Universe(_Universe.get())
    return __universe
