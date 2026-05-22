"""
Centralized logging configuration for KalendBot.
Supports JSON format (production) and human-readable format (development).
"""
import logging
import json
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar

from src.core.config import settings

# Context variable for request correlation ID
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        cid = correlation_id.get("")
        if cid:
            log_entry["correlation_id"] = cid

        # Include extra fields if set
        for key in ("contact_id", "role", "gateway", "action", "duration_ms", "token_count"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        cid = correlation_id.get("")
        if cid:
            base = f"[{cid[:8]}] {base}"
        return base


def generate_correlation_id() -> str:
    """Generate a new correlation ID for a request."""
    return uuid.uuid4().hex[:16]


def setup_logging() -> None:
    """Configure logging based on settings."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
