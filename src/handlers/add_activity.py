"""
Add activity command handler -- falls through to the LLM agent for guided creation flow.
"""
import logging

from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command,
)

logger = logging.getLogger("kalendbot.handlers.add_activity")


async def handle_add_activity(ctx: CommandContext) -> CommandResult:
    """
    Always falls through to the LLM agent for guided event creation.
    The agent uses ActivityCreator tool with preview/confirm flow.
    """
    return CommandResult(text=None)


register_command(CommandDef(
    name="agregar",
    aliases=["add", "toevoegen"],
    handler=handle_add_activity,
    permission="contacto",
    description={
        "es": "Agregar nueva actividad",
        "en": "Add new activity",
        "nl": "Nieuwe activiteit toevoegen",
    },
))
