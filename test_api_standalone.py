"""
Test script for Manual Trading API in standalone mode.

This starts the API without MT5Client or Orchestrator integration.
Only basic endpoints will work (auth, manual trading, automation, system monitoring).

Usage:
    python test_api_standalone.py
"""

import asyncio
import logging
from app.infrastructure.event_bus import EventBus
from app.api.service import APIService
from app.api.main import create_app
import uvicorn


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("=== Starting Manual Trading API (Standalone Mode) ===")
    logger.info("Only these endpoints will work:")
    logger.info("  ✓ POST /auth/login")
    logger.info("  ✓ POST /signals/entry")
    logger.info("  ✓ POST /signals/exit")
    logger.info("  ✓ POST /automation/enable")
    logger.info("  ✓ POST /automation/disable")
    logger.info("  ✓ GET /system/status")
    logger.info("  ✓ GET /system/metrics")
    logger.info("")
    logger.info("These will return errors (need integration):")
    logger.info("  ✗ GET /account/* (need MT5Client)")
    logger.info("  ✗ GET /positions/* (need MT5Client)")
    logger.info("  ✗ GET /indicators/* (need Orchestrator)")
    logger.info("  ✗ GET /strategies/* (need Orchestrator)")
    logger.info("")

    # Initialize EventBus only (standalone mode)
    event_bus = EventBus(logger=logger, log_all_events=False)

    # Initialize APIService without MT5Client or Orchestrator
    api_service = APIService(
        event_bus=event_bus,
        logger=logger
    )
    await api_service.start()

    # Create FastAPI app
    app = create_app()
    app.state.api_service = api_service

    logger.info("API server starting on http://0.0.0.0:8080")
    logger.info("")
    logger.info("Default credentials:")
    logger.info("  Username: admin")
    logger.info("  Password: check .env file or use default")
    logger.info("")
    logger.info("Test with:")
    logger.info("  curl -X POST http://localhost:8080/auth/login \\")
    logger.info("    -H 'Content-Type: application/json' \\")
    logger.info("    -d '{\"username\":\"admin\",\"password\":\"your_password\"}'")
    logger.info("")

    # Start server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await api_service.stop()
        logger.info("API service stopped")


if __name__ == "__main__":
    asyncio.run(main())
