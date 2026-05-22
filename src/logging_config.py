"""Backward-compatible re-export from src.core.logging_config."""
from src.core.logging_config import (  # noqa: F401
    correlation_id, generate_correlation_id, setup_logging,
    JSONFormatter, TextFormatter,
)
