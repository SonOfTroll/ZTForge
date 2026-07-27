"""
ZTForge Backend — FastAPI application entry point.

Assembles middleware, routes, Socket.io, and lifespan management.
This is the ASGI app that Uvicorn serves.
"""

import time
import uuid
from contextlib import asynccontextmanager

import socketio
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.services.collab_manager import CollabManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    setup_logging()
    logger = get_logger("ztforge.main")
    settings = get_settings()
    logger.info("starting", version=settings.app_version, debug=settings.debug)
    yield
    logger.info("shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ZTForge API",
        description="Zero Trust Architecture Designer",
        version=settings.app_version,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
        redirect_slashes=False,
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Request ID + Timing Middleware ───────────────────────
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        response.headers["X-Request-ID"] = request_id

        logger = get_logger("ztforge.access")
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    # ── Register API Routes ──────────────────────────────────
    from app.api.v1.auth import router as auth_router
    from app.api.v1.canvas import router as canvas_router
    from app.api.v1.policies import router as policies_router
    from app.api.v1.simulation import router as simulation_router
    from app.api.v1.users import router as users_router
    from app.api.v1.hub import router as hub_router

    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(canvas_router, prefix=api_prefix)
    app.include_router(policies_router, prefix=api_prefix)
    app.include_router(simulation_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(hub_router, prefix=api_prefix)

    # ── Health Check ─────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": settings.app_version}

    # ── Socket.io ────────────────────────────────────────────
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=settings.allowed_origins,
        logger=False,  # We use our own structured logging
    )
    collab = CollabManager(sio)
    sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

    # Store on app for access in tests
    app.state.sio = sio
    app.state.collab = collab
    app.state.sio_app = sio_app

    return app


# The ASGI app that Uvicorn imports
app = create_app()

# Uvicorn needs to serve the socket.io-wrapped app
asgi_app = app.state.sio_app
