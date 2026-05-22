"""
Security utilities for KalendBot.
Rate limiting, input sanitization, and webhook validation.
"""
import time
import logging
import re
from collections import defaultdict

logger = logging.getLogger("kalendbot.security")

MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30  # max messages per window per phone


class RateLimiter:
    """Simple in-memory token bucket rate limiter per phone number."""

    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window = window
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if a request from key is allowed. Returns True if within limits."""
        now = time.time()
        cutoff = now - self.window

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= self.max_requests:
            logger.warning("Rate limit exceeded for %s (%d requests in %ds)", key, len(self._requests[key]), self.window)
            return False

        self._requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def sanitize_message(text: str) -> str:
    """
    Sanitize user input:
    - Strip control characters (except newlines/tabs)
    - Enforce max length
    - Strip leading/trailing whitespace
    """
    # Remove control characters (keep \n, \r, \t)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = text.strip()

    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH]
        logger.info("Message truncated to %d chars", MAX_MESSAGE_LENGTH)

    return text


def validate_webhook_api_key(provided_key: str, expected_key: str) -> bool:
    """Validate WAHA webhook API key."""
    if not expected_key:
        return True  # No key configured = no validation
    return provided_key == expected_key
