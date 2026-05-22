"""
Export command handlers — shared across Telegram and WhatsApp.
Handles: export_excel, export_jpeg, export_jpeg_codes, export_instructions.
"""
import logging

from src.gateways.contacts import load_contact
from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command, check_permission,
)

logger = logging.getLogger("kalendbot.handlers.exports")


def _check_export_permission(contact_id: str | None) -> str | None:
    """Returns error message if user lacks export permission, None if allowed."""
    if not contact_id:
        return "No estás identificado."
    contact = load_contact(contact_id)
    rol = contact.get("rol_kalendbot", "readonly") if contact else "readonly"
    if not check_permission(rol, "contacto"):
        return "No tienes permisos para exportar el calendario."
    return None


async def handle_export_excel(ctx: CommandContext) -> CommandResult:
    """Generate and return Excel calendar export."""
    error = _check_export_permission(ctx.contact_id)
    if error:
        return CommandResult(error=error)

    try:
        from src.tools.calendar_exporter import export_calendar
        output_path = export_calendar(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            return CommandResult(error=output_path)

        return CommandResult(file_path=output_path, text="Calendario NV Mexico 2026 actualizado")
    except Exception as e:
        logger.error(f"Error exportando calendario: {e}")
        return CommandResult(error=f"Error generando el archivo: {e}")


async def handle_export_jpeg(ctx: CommandContext) -> CommandResult:
    """Generate and return JPEG calendar image."""
    error = _check_export_permission(ctx.contact_id)
    if error:
        return CommandResult(error=error)

    try:
        from src.tools.calendar_exporter import export_calendar_as_jpeg
        output_path = export_calendar_as_jpeg(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            return CommandResult(error=output_path)

        return CommandResult(image_path=output_path, text="Jaarplanning NV Mexico 2026")
    except Exception as e:
        logger.error(f"Error exportando JPEG: {e}")
        return CommandResult(error=f"Error generando la imagen: {e}")


async def handle_export_jpeg_codes(ctx: CommandContext) -> CommandResult:
    """Generate and return JPEG codes image."""
    error = _check_export_permission(ctx.contact_id)
    if error:
        return CommandResult(error=error)

    try:
        from src.tools.calendar_exporter import export_calendar_as_jpeg_codes
        output_path = export_calendar_as_jpeg_codes(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            return CommandResult(error=output_path)

        return CommandResult(image_path=output_path, text="Códigos de actividades — NV Mexico 2026")
    except Exception as e:
        logger.error(f"Error exportando JPEG codes: {e}")
        return CommandResult(error=f"Error generando la imagen: {e}")


async def handle_export_instructions(ctx: CommandContext) -> CommandResult:
    """Return editable fields and permissions guide."""
    try:
        from src.tools.rules_engine import _get_instrucciones
        instructions = _get_instrucciones()
        return CommandResult(text=instructions)
    except Exception as e:
        logger.error(f"Error generando instrucciones: {e}")
        return CommandResult(error=f"Error generando instrucciones: {e}")


# --- Register commands ---

register_command(CommandDef(
    name="export_excel",
    aliases=["export", "exportar_excel"],
    handler=handle_export_excel,
    permission="contacto",
    description={
        "es": "Exportar calendario a Excel",
        "en": "Export calendar to Excel",
        "nl": "Kalender exporteren naar Excel",
    },
))

register_command(CommandDef(
    name="export_jpeg",
    aliases=["jpeg", "exportar_jpeg"],
    handler=handle_export_jpeg,
    permission="contacto",
    description={
        "es": "Exportar como imagen",
        "en": "Export as image",
        "nl": "Exporteren als afbeelding",
    },
))

register_command(CommandDef(
    name="export_jpeg_codes",
    aliases=["exportar_codigos"],
    handler=handle_export_jpeg_codes,
    permission="contacto",
    description={
        "es": "Ver códigos de actividades",
        "en": "View activity codes",
        "nl": "Activiteitscodes bekijken",
    },
))

register_command(CommandDef(
    name="export_instructions",
    aliases=["exportar_instrucciones"],
    handler=handle_export_instructions,
    permission="readonly",
    description={
        "es": "Ver campos editables y permisos",
        "en": "View editable fields and permissions",
        "nl": "Bewerkbare velden en rechten",
    },
))
