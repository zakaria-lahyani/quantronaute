"""
FastAPI application entry point.

This module creates and configures the FastAPI application for manual trading operations.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import automation, positions, orders, indicators, strategies, risk, account, system


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
        redoc_url="/redoc"
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
    app.include_router(automation.router, prefix="/automation", tags=["Automation"])
    app.include_router(positions.router, prefix="/positions", tags=["Positions"])
    app.include_router(orders.router, prefix="/orders", tags=["Orders"])
    app.include_router(indicators.router, prefix="/indicators", tags=["Indicators"])
    app.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
    app.include_router(risk.router, prefix="/risk", tags=["Risk"])
    app.include_router(account.router, prefix="/account", tags=["Account"])
    app.include_router(system.router, prefix="/system", tags=["System"])

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
    return {"status": "healthy"}
