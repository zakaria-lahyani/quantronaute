"""
API middleware.

This module provides middleware for logging, error handling, and request tracking.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests and responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response details.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response
        """
        start_time = time.time()

        # Log request
        logger.info(f"→ {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info(
            f"← {request.method} {request.url.path} "
            f"[{response.status_code}] ({duration:.3f}s)"
        )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and handle unhandled exceptions.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Handle unhandled exceptions gracefully.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response
        """
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            return Response(
                content='{"error": "internal_server_error", "message": "An unexpected error occurred"}',
                status_code=500,
                media_type="application/json"
            )
