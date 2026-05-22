"""
FastAPI middleware for KalendBot.
Adds correlation IDs and request timing to all requests.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging_config import correlation_id, generate_correlation_id

logger = logging.getLogger("kalendbot.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Adds correlation ID and logs request timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = generate_correlation_id()
        token = correlation_id.set(cid)

        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 1)

            logger.info(
                "%s %s → %s (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Correlation-ID"] = cid
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                "%s %s → ERROR (%.1fms)",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            correlation_id.reset(token)
