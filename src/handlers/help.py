"""
Help command handler — multi-language help text shared across channels.
"""
import logging

from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command,
)

logger = logging.getLogger("kalendbot.handlers.help")


HELP_TEXT = {
    "es": (
        "Comandos disponibles:\n\n"
        "Calendario:\n"
        "/cambiar — Editar campos de eventos\n"
        "/estado — Cambiar estado de un evento\n"
        "/buscar — Buscar eventos por nombre\n"
        "/pendientes — Listar eventos pendientes\n"
        "/proximos — Listar próximos eventos\n"
        "/evento — Ver detalle de un evento\n"
        "/deshacer — Revertir último cambio\n"
        "/ocultar — Ocultar evento del export\n"
        "/mostrar — Mostrar evento en el export\n"
        "/agregar — Agregar nueva actividad\n\n"
        "Exportar:\n"
        "/exportar_excel — Exportar calendario a Excel\n"
        "/exportar_jpeg — Exportar como imagen\n"
        "/exportar_codigos — Ver códigos de actividades\n"
        "/exportar_instrucciones — Ver campos editables y permisos\n\n"
        "Configuración:\n"
        "/idioma — Cambiar idioma del bot\n"
        "/ayuda — Mostrar esta ayuda\n\n"
        "En grupo, también puedes mencionarme seguido de tu pregunta.\n"
        "Tip: Usa bullet points (*.) para enviar múltiples cambios en un solo mensaje."
    ),
    "en": (
        "Available commands:\n\n"
        "Calendar:\n"
        "/change — Edit event fields\n"
        "/status — Change event status\n"
        "/search — Search events by name\n"
        "/pending — List pending events\n"
        "/upcoming — View upcoming events\n"
        "/event — View event details\n"
        "/undo — Revert last change\n"
        "/hide — Hide event from export\n"
        "/show — Show event in export\n"
        "/add — Add new activity\n\n"
        "Export:\n"
        "/export_excel — Export calendar to Excel\n"
        "/export_jpeg — Export as image\n"
        "/export_jpeg_codes — View activity codes\n"
        "/export_instructions — View editable fields and permissions\n\n"
        "Settings:\n"
        "/language — Change bot language\n"
        "/help — Show this help\n\n"
        "In groups, you can also mention me followed by your question.\n"
        "Tip: Use bullet points (*.) to send multiple changes in a single message."
    ),
    "nl": (
        "Beschikbare commando's:\n\n"
        "Kalender:\n"
        "/change — Evenementvelden bewerken\n"
        "/status — Evenementstatus wijzigen\n"
        "/search — Evenementen zoeken op naam\n"
        "/pending — Openstaande evenementen\n"
        "/upcoming — Komende evenementen\n"
        "/event — Evenementdetails bekijken\n"
        "/undo — Laatste wijziging ongedaan maken\n"
        "/hide — Evenement verbergen uit export\n"
        "/show — Evenement tonen in export\n"
        "/toevoegen — Nieuwe activiteit toevoegen\n\n"
        "Exporteren:\n"
        "/export_excel — Kalender exporteren naar Excel\n"
        "/export_jpeg — Exporteren als afbeelding\n"
        "/export_jpeg_codes — Activiteitscodes bekijken\n"
        "/export_instructions — Bewerkbare velden en rechten\n\n"
        "Instellingen:\n"
        "/language — Taal wijzigen\n"
        "/help — Deze hulp tonen\n\n"
        "In groepen kun je me ook noemen gevolgd door je vraag.\n"
        "Tip: Gebruik bullet points (*.) om meerdere wijzigingen in een bericht te sturen."
    ),
}


async def handle_help(ctx: CommandContext) -> CommandResult:
    """Return help text in the user's language."""
    text = HELP_TEXT.get(ctx.language, HELP_TEXT["es"])
    return CommandResult(text=text)


# --- Register command ---

register_command(CommandDef(
    name="help",
    aliases=["ayuda"],
    handler=handle_help,
    permission="readonly",
    description={
        "es": "Mostrar comandos disponibles",
        "en": "Show available commands",
        "nl": "Beschikbare commando's",
    },
))
