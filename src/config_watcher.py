from collections.abc import Awaitable, Callable
from pathlib import Path

from watchfiles import awatch


async def watch_config_file(
    path: Path, on_reload: Callable[[], Awaitable[None]]
) -> None:
    """Watch config file and trigger reload callback on changes."""
    async for _changes in awatch(path):
        await on_reload()
