"""
Sistema de templates para mensajes de WhatsApp.
Con WAHA: se renderizan como texto plano.
Con Meta Cloud API (futuro): se mapean a templates HSM aprobados.
"""
import logging

logger = logging.getLogger("kalendbot.templates")

# Cada template tiene:
#   text: formato con placeholders Python {var}
#   meta_template_name: nombre del template HSM en Meta (para migración futura)
#   has_media: si el template incluye media (imagen header en Meta)
TEMPLATES = {
    "event_reminder": {
        "text": (
            "📅 Herinnering: {event_name} is over {days} dagen, op {date}.\n"
            "Bevestig je deelname alsjeblieft."
        ),
        "meta_template_name": "event_reminder_nl",
    },
    "date_change": {
        "text": (
            "🔄 Agenda update: {event_name} is verplaatst naar {new_date}.\n"
            "Neem contact op als dit problemen oplevert."
        ),
        "meta_template_name": "date_change_nl",
    },
    "flyer_ready": {
        "text": "🎨 De flyer voor {event_name} is klaar voor review.",
        "meta_template_name": "flyer_ready_nl",
        "has_media": True,
    },
    "flyer_reminder": {
        "text": (
            "🎨 Herinnering: de flyer voor {event_name} moet nog worden aangeleverd.\n"
            "Deadline: {deadline}."
        ),
        "meta_template_name": "flyer_reminder_nl",
    },
    "confirmation_request": {
        "text": (
            "✅ Bevestig je deelname: {event_name} op {date}.\n"
            "Antwoord JA of NEE."
        ),
        "meta_template_name": "confirmation_request_nl",
    },
    "flyer_approved": {
        "text": "✅ Flyer GOEDGEKEURD voor '{event_name}'. Klaar voor publicatie.",
        "meta_template_name": "flyer_approved_nl",
    },
    "admin_summary": {
        "text": "📋 Resumen de recordatorios de hoy:\n\n{summary}",
        "meta_template_name": "admin_summary_es",
    },
    "group_event_reminder": {
        "text": "📅 Reminder: {event_name} is op {date}. Nog {days} dagen!",
        "meta_template_name": "group_event_reminder_nl",
    },
    "welcome_registered": {
        "text": (
            "Welkom bij KalendBot, {name}! 🎉\n"
            "Je bent nu geregistreerd. Stuur een bericht om te beginnen."
        ),
        "meta_template_name": "welcome_registered_nl",
    },
    "registration_pending": {
        "text": (
            "Hallo! Ik ben KalendBot, de kalenderassistent van NV Mexico.\n"
            "Je nummer is nog niet geregistreerd.\n"
            "Antwoord met je volledige naam om toegang aan te vragen."
        ),
        "meta_template_name": "registration_pending_nl",
    },
    "group_help": {
        "text": (
            "KalendBot actief!\n\n"
            "Activeer mij met @KalendBot of begin met '/'.\n\n"
            "Voorbeelden:\n"
            "- /wanneer is Koningsdag?\n"
            "- @KalendBot bevestig datum Koningsdag 27 april\n"
            "- /status\n"
            "- /export"
        ),
        "meta_template_name": "group_help_nl",
    },
    "registration_submitted": {
        "text": (
            "Bedankt, {name}. Je aanvraag is verzonden naar de beheerder.\n"
            "Je ontvangt een bericht zodra je bent goedgekeurd."
        ),
        "meta_template_name": "registration_submitted_nl",
    },
}


def render_template(template_id: str, **kwargs) -> str:
    """
    Renderiza un template con variables.
    Con WAHA: retorna texto plano formateado.
    Futuro Meta API: retornaría objeto template con meta_template_name + variables.
    """
    template = TEMPLATES.get(template_id)
    if not template:
        logger.warning(f"Template '{template_id}' no encontrado, usando texto directo")
        return kwargs.get("message", kwargs.get("text", str(kwargs)))

    try:
        return template["text"].format(**kwargs)
    except KeyError as e:
        logger.error(f"Variable faltante en template '{template_id}': {e}")
        return template["text"]


def get_template_meta_name(template_id: str) -> str | None:
    """Retorna el nombre del template HSM de Meta (para migración futura)."""
    template = TEMPLATES.get(template_id)
    return template.get("meta_template_name") if template else None


def template_has_media(template_id: str) -> bool:
    """Verifica si un template incluye media."""
    template = TEMPLATES.get(template_id)
    return template.get("has_media", False) if template else False
