"""
Visibility command handlers — ocultar/mostrar events from export.
Shared across Telegram and WhatsApp. Direct calendar_manager calls (no LLM).
"""
import re
import logging

from src.tools.calendar_manager import calendar_manager
from src.gateways.contacts import identify_by_telegram_id
from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command,
)

logger = logging.getLogger("kalendbot.handlers.visibility")


def _build_event_list() -> list[dict]:
    """Returns a list of all events with id, name, and extra info."""
    result = calendar_manager(action="list_all")
    events = []
    for line in result.strip().split("\n"):
        if not line.strip():
            continue
        match = re.match(r'^(?:\[.*?\]\s*)?(\S+):\s*(.+?)\s*—\s*(.+)$', line.strip())
        if match:
            events.append({"id": match.group(1), "nombre": match.group(2), "extra": match.group(3)})
    return events


async def handle_toggle_visibility(ctx: CommandContext, show: bool) -> CommandResult:
    """Toggle show_in_export for an event. Used by both /ocultar and /mostrar."""
    if not ctx.contact_id:
        return CommandResult(error="No estás identificado.")

    action = "mostrar" if show else "ocultar"
    query = ctx.text.strip()
    events = _build_event_list()

    # No args: show numbered list
    if not query:
        lines = [f"{i}. {evt['nombre']} ({evt['id']})" for i, evt in enumerate(events, 1)]
        return CommandResult(
            text=f"Eventos disponibles:\n\n" + "\n".join(lines) + f"\n\nUso: /{action} <numero o nombre>"
        )

    # If query is a number, use it as index
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(events):
            event_id = events[idx]["id"]
            action_word = "Visible" if show else "Oculto"
            result = calendar_manager(action="update_show_export", event_id=event_id, show_in_export=show)
            logger.info(f"{action} evento #{query} por {ctx.contact_id}: {result}")
            return CommandResult(text=f"{action_word}: {result}")
        else:
            return CommandResult(error=f"Número {query} fuera de rango (1-{len(events)}).")

    # Search by name
    search_result = calendar_manager(action="search_event", event_id=query)
    if "No se encontraron" in search_result:
        return CommandResult(error=f"No encontré eventos con '{query}'.")

    lines = [l.strip() for l in search_result.strip().split("\n") if l.strip()]
    if len(lines) > 1:
        return CommandResult(
            text=f"Encontré {len(lines)} eventos. Sé más específico:\n\n" + search_result
        )

    # Single match
    event_id = lines[0].split(":")[0].strip()
    action_word = "Visible" if show else "Oculto"
    result = calendar_manager(action="update_show_export", event_id=event_id, show_in_export=show)
    logger.info(f"{action} evento por {ctx.contact_id}: {result}")
    return CommandResult(text=f"{action_word}: {result}")


async def handle_hide(ctx: CommandContext) -> CommandResult:
    return await handle_toggle_visibility(ctx, show=False)


async def handle_show(ctx: CommandContext) -> CommandResult:
    return await handle_toggle_visibility(ctx, show=True)


# --- Register commands ---

register_command(CommandDef(
    name="ocultar",
    aliases=["hide", "verbergen"],
    handler=handle_hide,
    permission="contacto",
    description={
        "es": "Ocultar evento del export",
        "en": "Hide event from export",
        "nl": "Evenement verbergen uit export",
    },
))

register_command(CommandDef(
    name="mostrar",
    aliases=["show", "tonen"],
    handler=handle_show,
    permission="contacto",
    description={
        "es": "Mostrar evento en el export",
        "en": "Show event in export",
        "nl": "Evenement tonen in export",
    },
))
