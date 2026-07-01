"""
HFB Backend Application — FastAPI entry point.

皇甫谧数字人文平台
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import health, ready, version
from app.api.v1 import router as v1_router
from app.api.v2 import router as v2_router
from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.db.database import close_database, init_database
from app.middleware.request_id import RequestIDMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    configure_logging()
    logger.info(
        "hfb_starting environment=%s version=%s", settings.ENVIRONMENT, settings.VERSION
    )

    await init_database()
    logger.info("database_initialized")

    yield

    await close_database()
    logger.info("database_closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="皇甫谧数字人文平台",
        description="Huangfu Mi Digital Humanities & TCM Classics Intelligent Research Platform",
        version=settings.VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Middleware — Starlette's add_middleware wraps: last-registered is outermost.
    # RequestIDMiddleware MUST be outermost so CORS preflight and error handlers
    # always have access to request.state.request_id.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )
    app.add_middleware(RequestIDMiddleware)

    # Error handlers — must be registered before routes
    register_error_handlers(app)

    # API routes
    app.include_router(health.router, tags=["Health"])
    app.include_router(ready.router, tags=["Readiness"])
    app.include_router(version.router, tags=["Version"])
    app.include_router(v1_router)
    app.include_router(v2_router, prefix="/api/v2")

    return app


app = create_app()
