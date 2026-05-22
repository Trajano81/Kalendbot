"""
LangSmith tracing integration for KalendBot.
Enables observability for LLM calls, tool usage, and costs.
"""
import os
import logging

from src.core.config import settings

logger = logging.getLogger("kalendbot.tracing")


def setup_langsmith() -> bool:
    """
    Configure LangSmith tracing via environment variables.
    Returns True if tracing is enabled.
    """
    if settings.langchain_tracing_v2.lower() != "true":
        logger.info("LangSmith tracing disabled")
        return False

    if not settings.langchain_api_key:
        logger.warning("LANGCHAIN_API_KEY not set, tracing disabled")
        return False

    # LangChain reads these env vars automatically
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

    logger.info("LangSmith tracing enabled (project: %s)", settings.langchain_project)
    return True


def get_run_metadata(contact_id: str, role: str, gateway: str = "unknown") -> dict:
    """Build metadata dict for LangSmith run tagging."""
    return {
        "contact_id": contact_id,
        "role": role,
        "gateway": gateway,
    }
