"""
Status command handler — show pending events.
Shared across Telegram and WhatsApp.
"""
import logging

from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command,
)

logger = logging.getLogger("kalendbot.handlers.status")


async def handle_status(ctx: CommandContext) -> CommandResult:
    """Return list of pending events."""
    try:
        from src.tools.calendar_manager import calendar_manager
        pending = calendar_manager('{"action": "list_pending"}')
        return CommandResult(text=pending)
    except Exception as e:
        logger.error(f"Error listing pending events: {e}")
        return CommandResult(error=f"Error: {e}")


# --- Register command ---

register_command(CommandDef(
    name="status",
    aliases=["estado"],
    handler=handle_status,
    permission="readonly",
    description={
        "es": "Ver eventos pendientes",
        "en": "View pending events",
        "nl": "Openstaande evenementen",
    },
))
