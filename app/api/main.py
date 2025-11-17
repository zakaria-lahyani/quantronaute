"""
FastAPI application entry point.

This module creates and configures the FastAPI application for manual trading operations.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.event_bus import EventBus
from app.infrastructure.redis_event_bus import RedisEventBus
from app.api.service import APIService
from app.api.routers import auth, automation, positions, orders, indicators, strategies, risk, account, system, config
from app.clients.mt5.client import create_client_with_retry

# Module-level logger
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.

    Initializes EventBus, MT5Client, and APIService on startup, cleans up on shutdown.
    """
    # Startup
    logger.info("Starting Manual Trading API...")

    # Initialize MT5 Client for positions/account data access
    mt5_client = None
    api_base_url = os.getenv("API_BASE_URL", "http://host.docker.internal:8000/mt5")

    try:
        logger.info(f"Connecting to MT5 API at {api_base_url}...")
        mt5_client = create_client_with_retry(api_base_url)
        logger.info("✓ MT5Client connected successfully")

        # Test connection
        try:
            balance = mt5_client.account.get_balance()
            logger.info(f"  Account balance: {balance}")
        except Exception as e:
            logger.warning(f"  Could not retrieve account balance: {e}")
    except Exception as e:
        logger.error(f"✗ Failed to connect MT5Client: {e}")
        logger.warning("  API will run in limited mode (no positions/account data)")

    # Initialize EventBus (Redis or in-memory)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            logger.info(f"Using RedisEventBus at {redis_url}")
            event_bus = RedisEventBus(redis_url=redis_url, logger=logger, log_all_events=False)
            event_bus.start()
            logger.info("✓ RedisEventBus connected and started")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            logger.warning("  Falling back to in-memory EventBus")
            event_bus = EventBus(logger=logger, log_all_events=False)
    else:
        logger.info("Using in-memory EventBus (no Redis configured)")
        event_bus = EventBus(logger=logger, log_all_events=False)

    # Initialize API Service WITH MT5Client
    api_service = APIService(
        event_bus=event_bus,
        logger=logger,
        mt5_client=mt5_client  # Pass the MT5Client here!
    )
    await api_service.start()
    logger.info("APIService started")

    # Store in app state for access in routers
    app.state.event_bus = event_bus
    app.state.api_service = api_service
    app.state.mt5_client = mt5_client

    logger.info("Manual Trading API ready")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down Manual Trading API...")

    await api_service.stop()
    logger.info("APIService stopped")

    # Stop RedisEventBus if it's being used
    if isinstance(event_bus, RedisEventBus):
        event_bus.stop()
        logger.info("RedisEventBus stopped")

    logger.info("Manual Trading API shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Quantronaute Trading API",
        description="RESTful API for manual trading operations and monitoring",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(automation.router, prefix="/automation", tags=["Automation Control"])
    app.include_router(orders.router, prefix="/signals", tags=["Manual Trading Signals"])  # Trigger entry/exit
    app.include_router(positions.router, prefix="/positions", tags=["Position Monitoring"])
    app.include_router(indicators.router, prefix="/indicators", tags=["Indicator Monitoring"])
    app.include_router(strategies.router, prefix="/strategies", tags=["Strategy Monitoring"])
    app.include_router(config.router, prefix="/config", tags=["Configuration Management"])  # NEW - Full config API
    app.include_router(risk.router, prefix="/risk", tags=["Risk Status"])
    app.include_router(account.router, prefix="/account", tags=["Account Info"])
    app.include_router(system.router, prefix="/system", tags=["System Health"])

    return app


app = create_app()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Quantronaute Trading API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    api_service = getattr(app.state, "api_service", None)

    return {
        "status": "healthy",
        "api_service_running": api_service.is_running if api_service else False
    }
