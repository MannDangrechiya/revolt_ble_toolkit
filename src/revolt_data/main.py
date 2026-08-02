"""FastAPI Application Entry Point for revolt_data."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from revolt_data.api import (
    auth_router,
    commands_router,
    telemetry_router,
    trips_router,
    users_router,
    vehicles_router,
    ws_router,
)
from revolt_data.config import get_settings
from revolt_data.database import init_db
from revolt_data.workers.telemetry_worker import TelemetryWorker

settings = get_settings()
telemetry_worker = TelemetryWorker()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for initializing database and background workers."""
    # Startup logic
    await init_db()
    telemetry_worker.start()

    yield

    # Shutdown logic
    await telemetry_worker.stop()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Production FastAPI Backend & Data Engine for Revolt Vehicles",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routers
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(vehicles_router)
    app.include_router(trips_router)
    app.include_router(telemetry_router)
    app.include_router(commands_router)
    app.include_router(ws_router)

    return app


app = create_app()
