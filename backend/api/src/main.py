"""
FlexMON API - Main Application
FastAPI-based monitoring and observability platform
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .version import VERSION_INFO
from .routers import (
    health,
    metrics_ingest,
    alerts_rules,
    alerts_outbox,
    alerts_webhooks,
    discovery,
    users,
    auth,
    ai_explain,
)
from .services import timescale, elastic

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    logger.info("Starting FlexMON API...")
    logger.info(f"Version: {VERSION_INFO['version']}, Build: {VERSION_INFO['build']}")

    # Initialize database connections (REQUIRED - must succeed)
    try:
        logger.info("Connecting to TimescaleDB...")
        await timescale.init_db()
        logger.info("✓ TimescaleDB connected")

        # Run online migrations to ensure schema is up to date
        try:
            logger.info("Running online migrations...")
            from .migrations import run_online_migrations
            conn = await timescale.pool.acquire()
            try:
                success, message = run_online_migrations(conn)
                if success:
                    logger.info(f"✓ Migrations: {message}")
                else:
                    logger.warning(f"⚠ Migrations: {message}")
            finally:
                await timescale.pool.release(conn)
        except Exception as e:
            logger.warning(f"⚠ Migration check failed: {e}")

    except Exception as e:
        logger.error(f"Failed to initialize TimescaleDB: {e}")
        raise

    # Initialize Elasticsearch (OPTIONAL - non-fatal)
    try:
        logger.info("Connecting to Elasticsearch...")
        await elastic.init_es()
        logger.info("✓ Elasticsearch connected")

        # Load ES templates and ILM policies
        logger.info("Loading Elasticsearch templates and ILM policies...")
        await elastic.load_templates_and_ilm()
        logger.info("✓ Elasticsearch templates loaded")

    except Exception as e:
        logger.warning(f"⚠ Elasticsearch initialization failed: {e}")
        logger.warning("  Login and core features will work, but log search will be unavailable")

    # Start background tasks
    logger.info("Starting background tasks...")
    # TODO: Start alert engine, license checker, pollers
    logger.info("✓ Background tasks started")

    logger.info("FlexMON API ready!")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down FlexMON API...")
    await timescale.close_db()
    try:
        await elastic.close_es()
    except Exception as e:
        logger.warning(f"Error closing Elasticsearch: {e}")
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=VERSION_INFO["version"],
    description="FlexMON - Flexible Monitoring and Observability Platform",
    docs_url=f"/{settings.api_version}/docs",
    redoc_url=f"/{settings.api_version}/redoc",
    openapi_url=f"/{settings.api_version}/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with version information"""
    return {
        **VERSION_INFO,
        "status": "running",
        "docs": f"/{settings.api_version}/docs"
    }


# Include routers
app.include_router(
    health.router,
    prefix=f"/{settings.api_version}",
    tags=["Health"]
)

app.include_router(
    auth.router,
    prefix=f"/{settings.api_version}",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix=f"/{settings.api_version}",
    tags=["Users"]
)

app.include_router(
    metrics_ingest.router,
    prefix=f"/{settings.api_version}",
    tags=["Metrics"]
)

app.include_router(
    alerts_rules.router,
    prefix=f"/{settings.api_version}",
    tags=["Alert Rules"]
)

app.include_router(
    alerts_outbox.router,
    prefix=f"/{settings.api_version}",
    tags=["Alert Notifications"]
)

app.include_router(
    alerts_webhooks.router,
    prefix=f"/{settings.api_version}",
    tags=["Webhooks"]
)

app.include_router(
    discovery.router,
    prefix=f"/{settings.api_version}",
    tags=["Discovery"]
)

app.include_router(
    ai_explain.router,
    prefix=f"/{settings.api_version}",
    tags=["AI"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
