import asyncio
import tempfile
from pathlib import Path

import pytest

from src.config_watcher import watch_config_file


@pytest.mark.asyncio
async def test_config_reload_on_change():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("labels: {}\nsettings: {llm_provider: claude}")
        temp_path = Path(f.name)

    reload_count = 0

    async def on_reload():
        nonlocal reload_count
        reload_count += 1

    try:
        # Start watcher in background
        watcher_task = asyncio.create_task(watch_config_file(temp_path, on_reload))

        # Give it time to start
        await asyncio.sleep(0.1)

        # Modify file
        with open(temp_path, "w") as f:
            config_str = (
                "labels: {finance: {description: test, rules: []}}\n"
                "settings: {llm_provider: claude}"
            )
            f.write(config_str)

        # Wait for reload
        await asyncio.sleep(0.5)

        assert reload_count >= 1

        watcher_task.cancel()
    finally:
        temp_path.unlink()
