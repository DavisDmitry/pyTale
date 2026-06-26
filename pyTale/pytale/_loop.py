import asyncio

from pytale.commands.loop import CommandQueue, command_loop
from pytale.events.loop import AsyncEventQueue, event_loop


async def _main(event_queue: AsyncEventQueue, cmd_queue: CommandQueue) -> None:
    await asyncio.gather(
        event_loop(event_queue),
        command_loop(cmd_queue),
    )


def start_loop(event_queue: AsyncEventQueue, cmd_queue: CommandQueue) -> None:
    asyncio.run(_main(event_queue, cmd_queue))
