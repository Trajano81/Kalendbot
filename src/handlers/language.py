"""
Language command handler — set user language preference.
Shared across Telegram and WhatsApp.
"""
import logging

from src.gateways.contacts import set_contact_language, get_contact_language, SUPPORTED_LANGUAGES
from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command,
)

logger = logging.getLogger("kalendbot.handlers.language")


async def handle_language(ctx: CommandContext) -> CommandResult:
    """Set or show language preference."""
    if not ctx.contact_id:
        return CommandResult(error="No estás identificado.")

    # If user passed a language code directly (e.g. /idioma en)
    lang_arg = ctx.text.strip().lower()
    if lang_arg in SUPPORTED_LANGUAGES:
        set_contact_language(ctx.contact_id, lang_arg)
        msg = {"es": "Idioma actualizado a", "en": "Language set to", "nl": "Taal ingesteld op"}
        return CommandResult(text=f"{msg.get(lang_arg, msg['es'])}: {SUPPORTED_LANGUAGES[lang_arg]}")

    # Show available options
    current = get_contact_language(ctx.contact_id)
    options = []
    for code, name in SUPPORTED_LANGUAGES.items():
        marker = "> " if code == current else "  "
        options.append(f"{marker}{name} ({code})")

    return CommandResult(
        text="Selecciona tu idioma / Select your language:\n\n"
        + "\n".join(options)
        + "\n\nUso: /idioma <es|en|nl>"
    )


# --- Register command ---

register_command(CommandDef(
    name="idioma",
    aliases=["language"],
    handler=handle_language,
    permission="readonly",
    description={
        "es": "Cambiar idioma",
        "en": "Change language",
        "nl": "Taal wijzigen",
    },
))
