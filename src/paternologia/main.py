# ABOUTME: FastAPI application entry point for Paternologia.
# ABOUTME: Configures app with Jinja2 templates, static files, and API routers.

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from paternologia.dependencies import get_storage
from paternologia.routers import devices_router, songs_router

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    storage = get_storage()
    storage._ensure_dirs()
    yield


app = FastAPI(
    title="Paternologia",
    description="MIDI configuration manager for songs",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(songs_router)
app.include_router(devices_router)
