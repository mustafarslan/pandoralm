"""
Pandora Cortex - FastAPI Application Factory
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.middleware import AuthMiddleware
from app.core.telemetry import setup_telemetry, ReBACTelemetryMiddleware

# =============================================================================
# High-Performance I/O Policy
# =============================================================================
try:
    import uvloop
    import os
    if os.getenv("ENABLE_UVLOOP", "false").lower() == "true":
        uvloop.install()
        print("🚀 High-performance 'uvloop' event loop policy installed.")
    else:
        print("ℹ️  'uvloop' installed but disabled. Using standard asyncio loop.")
except ImportError:
    print("⚠️  'uvloop' not found. Falling back to standard asyncio loop.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    print(f"🧠 Pandora Cortex starting on {settings.HOST}:{settings.PORT}")
    print(f"⚠️  DEBUG: Reload triggered at {datetime.now()}")
    print(f"📊 Neo4j: {settings.NEO4J_URI}")
    print(f"📦 LanceDB: {settings.LANCEDB_PATH}")
    print(f"📦 LanceDB: {settings.LANCEDB_PATH}")
    print(f"🔄 Redis: {settings.REDIS_URL}")

    # Initialize Telemetry (middleware already added in create_app)
    setup_telemetry(app)

    # Tiered Inference Configuration
    print(f"")
    print(f"⚡ Tiered Inference Configuration:")
    print(f"   Router Model: {settings.LLM_ROUTER_MODEL} @ {settings.LLM_ROUTER_API_BASE}")
    print(f"   Solver Model: {settings.LLM_SOLVER_MODEL} @ {settings.LLM_SOLVER_API_BASE}")

    # Warning about Ollama model swapping on single instance
    if settings.LLM_ROUTER_API_BASE == settings.LLM_SOLVER_API_BASE:
        print(f"")
        print(f"⚠️  Running Tiered Inference on single Ollama instance.")
        print(f"   Expect model loading delays unless OLLAMA_KEEP_ALIVE=-1 is set")
        print(f"   or sufficient VRAM is available for both models.")

    yield
    # Shutdown
    print("🧠 Pandora Cortex shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Pandora Cortex",
        description="Heavy compute engine for PandoraLM - GraphRAG, embeddings, and deep research",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ReBAC Telemetry middleware (must be added before app starts)
    app.add_middleware(ReBACTelemetryMiddleware)

    # Authentication middleware (Keycloak JWT)
    app.add_middleware(AuthMiddleware)

    # Include API routers
    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        # TODO: Add real DB checks (Postgres, MinIO) here for livenessProbe
        return {
            "status": "healthy",
            "service": "pandora-cortex",
            "version": "0.1.0",
            "telemetry": "enabled"
        }

    @app.get("/")
    async def root() -> dict:
        """Root endpoint."""
        return {
            "service": "Pandora Cortex",
            "description": "Heavy compute engine for PandoraLM",
            "docs": "/docs",
        }

    return app


app = create_app()
