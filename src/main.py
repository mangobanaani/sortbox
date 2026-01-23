import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.analytics import router as analytics_router
from src.api.labels import router as labels_router
from src.classifier.providers.claude import ClaudeProvider
from src.classifier.providers.ollama_provider import OllamaProvider
from src.classifier.providers.openai_provider import OpenAIProvider
from src.classifier.service import create_app
from src.config import LabelConfig, load_config
from src.config_watcher import watch_config_file
from src.database import init_database


def get_provider(
    config: LabelConfig,
) -> ClaudeProvider | OpenAIProvider | OllamaProvider:
    match config.settings.llm_provider:
        case "claude":
            return ClaudeProvider()
        case "openai":
            return OpenAIProvider()
        case "ollama":
            return OllamaProvider()
        case _:
            raise ValueError(f"Unknown provider: {config.settings.llm_provider}")


config_path = Path("labels.yaml")
config = load_config(config_path)
provider = get_provider(config)

# Initialize database
init_database()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Start config watcher
    async def reload_config() -> None:
        new_config = load_config(config_path)
        app.state.config = new_config
        # TODO: broadcast SSE event

    watcher_task = asyncio.create_task(watch_config_file(config_path, reload_config))

    yield

    # Cleanup
    watcher_task.cancel()


app = create_app(config_path=config_path, provider=provider)
app.router.lifespan_context = lifespan

# Mount API routers
app.include_router(labels_router)
app.include_router(analytics_router)

# Serve frontend in production (if dist exists)
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    # Serve index.html for all other routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> FileResponse:
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
