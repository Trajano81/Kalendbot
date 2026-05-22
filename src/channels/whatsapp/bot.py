"""
WhatsApp channel adapter for KalendBot via WAHA.
Thin wrapper: wires WAHA webhooks to shared command handlers in src/handlers/.
"""
import re
import logging

from src.config import settings
from src.agent import handle_message
from src.gateways.contacts import (
    identify_by_phone,
    load_contact,
    create_contact_json,
    get_admin_phone,
    get_contact_phone,
    normalize_phone,
    get_contact_language,
)
from src.gateways.whatsapp_provider import get_whatsapp_provider, phone_to_chat_id
from src.gateways.templates import render_template

# Import shared handlers (triggers command registration)
from src.handlers.registry import CommandContext, find_command
import src.handlers.exports  # noqa: F401
import src.handlers.visibility  # noqa: F401
import src.handlers.help  # noqa: F401
import src.handlers.language  # noqa: F401
import src.handlers.status  # noqa: F401
import src.handlers.undo  # noqa: F401
from src.handlers.reminders import load_reminder_config, send_reminders

logger = logging.getLogger("kalendbot.whatsapp")

DATA_DIR = settings.data_dir

# Temporary registration state
_pending_registrations: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Incoming message handling
# ---------------------------------------------------------------------------

async def handle_whatsapp_message(data: dict) -> None:
    """Process an incoming WAHA webhook. Entry point called from server.py."""
    provider = get_whatsapp_provider()
    parsed = provider.parse_webhook(data)

    if not parsed:
        return

    # Group messages
    if parsed["is_group"]:
        allowed = settings.whatsapp_group_chat_id
        if allowed and parsed["group_id"] != allowed:
            logger.info(f"WA grupo no autorizado: {parsed['group_id']}")
            return

        triggered, clean_text = _is_bot_triggered(parsed)
        if not triggered:
            return

        await _handle_group_message(parsed, clean_text, provider)
        return

    phone = parsed["sender_phone"]
    text = parsed["message_text"]
    chat_id = phone_to_chat_id(phone)

    logger.info(f"WA mensaje de {phone}: {text[:80]}")

    # Check for commands
    if text.startswith(("!", "/")):
        await _handle_command(phone, chat_id, text, provider)
        return

    # Registration flow
    if phone in _pending_registrations:
        await _handle_registration_flow(phone, chat_id, text, provider)
        return

    # Admin approval commands
    if _is_admin(phone) and text.upper().startswith(("APROBAR ", "RECHAZAR ")):
        await _handle_admin_approval(phone, chat_id, text, provider)
        return

    # Identify contact
    contact_id, _ = identify_by_phone(phone)

    if not contact_id:
        _pending_registrations[phone] = {"step": "awaiting_name"}
        msg = render_template("registration_pending")
        provider.send_text(chat_id, msg)
        logger.info(f"WA registro iniciado para {phone}")
        return

    # Process with agent
    response = handle_message(phone=phone, message=text, contact_id=contact_id)
    response = _convert_markdown_to_whatsapp(response)
    provider.send_text(chat_id, response)
    logger.info(f"WA respuesta a {contact_id}: {response[:80]}")


# ---------------------------------------------------------------------------
# Group: trigger detection
# ---------------------------------------------------------------------------

WHATSAPP_BOT_JID = settings.whatsapp_bot_jid


def _is_bot_triggered(parsed: dict) -> tuple[bool, str]:
    """Detect if a group message is directed at the bot."""
    text = parsed["message_text"]

    if WHATSAPP_BOT_JID and WHATSAPP_BOT_JID in parsed.get("mentioned_jids", []):
        clean = re.sub(r'^@\S+\s*', '', text).strip()
        return (True, clean) if clean else (False, "")

    if text.startswith("/"):
        clean = text[1:].strip()
        return (True, clean) if clean else (False, "")

    return (False, "")


async def _handle_group_message(parsed: dict, text: str, provider) -> None:
    phone = parsed["sender_phone"]
    group_id = parsed["group_id"]
    message_id = parsed.get("message_id")

    contact_id, _ = identify_by_phone(phone)

    if not contact_id:
        provider.send_reply(
            group_id,
            "Ik ken je nog niet. Stuur mij een privébericht om je te registreren.",
            message_id,
        )
        return

    logger.info(f"WA grupo trigger de {contact_id}: {text[:80]}")

    message = f"[Grupo] {text}"
    response = handle_message(phone=phone, message=message, contact_id=contact_id)
    response = _convert_markdown_to_whatsapp(response)
    provider.send_reply(group_id, response, message_id)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def _handle_registration_flow(phone: str, chat_id: str, text: str, provider) -> None:
    reg = _pending_registrations[phone]

    if reg["step"] == "awaiting_name":
        reg["nombre"] = text.strip()
        reg["step"] = "awaiting_approval"

        msg = render_template("registration_submitted", name=reg["nombre"])
        provider.send_text(chat_id, msg)

        admin_phone = get_admin_phone()
        if admin_phone:
            admin_chat_id = phone_to_chat_id(admin_phone)
            admin_msg = (
                f"Solicitud de acceso al bot:\n\n"
                f"Nombre: {reg['nombre']}\n"
                f"WhatsApp: +{phone}\n"
                f"Rol asignado: readonly (solo lectura)\n\n"
                f"Responde:\n"
                f"APROBAR {phone}\n"
                f"o\n"
                f"RECHAZAR {phone}"
            )
            provider.send_text(admin_chat_id, admin_msg)
        else:
            logger.warning("No se encontró admin para notificar solicitud WA")


async def _handle_admin_approval(phone: str, chat_id: str, text: str, provider) -> None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        provider.send_text(chat_id, "Formato: APROBAR <número> o RECHAZAR <número>")
        return

    action = parts[0].upper()
    target_phone = normalize_phone(parts[1])

    reg = None
    reg_phone = None
    for p, r in _pending_registrations.items():
        if normalize_phone(p) == target_phone or target_phone in normalize_phone(p):
            reg = r
            reg_phone = p
            break

    if not reg or reg.get("step") != "awaiting_approval":
        provider.send_text(chat_id, f"No hay solicitud pendiente para {parts[1]}")
        return

    if action == "APROBAR":
        contact_id = create_contact_json(nombre=reg["nombre"], telefono=f"+{reg_phone}", canal="whatsapp")
        del _pending_registrations[reg_phone]
        provider.send_text(chat_id, f"APROBADO. Contacto creado: {contact_id} (readonly)")
        target_chat_id = phone_to_chat_id(reg_phone)
        welcome_msg = render_template("welcome_registered", name=reg["nombre"])
        provider.send_text(target_chat_id, welcome_msg)
    elif action == "RECHAZAR":
        del _pending_registrations[reg_phone]
        provider.send_text(chat_id, "RECHAZADO.")
        target_chat_id = phone_to_chat_id(reg_phone)
        provider.send_text(target_chat_id, "Je aanvraag is niet goedgekeurd. Neem contact op met de beheerder.")


# ---------------------------------------------------------------------------
# Command handling — uses shared handlers
# ---------------------------------------------------------------------------

async def _handle_command(phone: str, chat_id: str, text: str, provider) -> None:
    """Route commands to shared handlers or agent."""
    cmd = text.lower().strip().lstrip("!/")

    # Try shared handler first
    cmd_def = find_command(cmd.split()[0] if cmd else "")
    if cmd_def:
        contact_id, _ = identify_by_phone(phone)
        lang = get_contact_language(contact_id) if contact_id else "es"
        # Extract args after command name
        parts = cmd.split(maxsplit=1)
        args_text = parts[1] if len(parts) > 1 else ""
        ctx = CommandContext(
            contact_id=contact_id,
            phone=phone,
            text=args_text,
            language=lang,
            channel="whatsapp",
        )
        result = await cmd_def.handler(ctx)
        # Empty result means handler defers to agent (e.g. /undo with event name)
        if result.text or result.error or result.file_path or result.image_path:
            _send_wa_result(provider, chat_id, result)
            return

    # Unknown command or deferred handler → forward to agent
    contact_id, _ = identify_by_phone(phone)
    if contact_id:
        response = handle_message(phone=phone, message=text, contact_id=contact_id)
        response = _convert_markdown_to_whatsapp(response)
        provider.send_text(chat_id, response)


def _send_wa_result(provider, chat_id: str, result) -> None:
    """Send a CommandResult via WhatsApp."""
    if result.error:
        provider.send_text(chat_id, result.error)
    elif result.file_path:
        provider.send_file(chat_id, result.file_path, caption=result.text or "")
    elif result.image_path:
        provider.send_image(chat_id, result.image_path, caption=result.text or "")
    elif result.text:
        text = _convert_markdown_to_whatsapp(result.text)
        provider.send_text(chat_id, text)


# ---------------------------------------------------------------------------
# Reminders — delegates to shared engine
# ---------------------------------------------------------------------------

def send_whatsapp_reminders() -> None:
    """Daily job: delegates to shared reminder engine with WhatsApp-specific send functions."""
    import asyncio

    provider = get_whatsapp_provider()

    def send_text(recipient_id: str, message: str):
        provider.send_text(recipient_id, message)

    def send_to_group(group_id: str, message: str):
        provider.send_text(group_id, message)

    # Run the async reminder engine in a sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(send_reminders(
                channel="whatsapp",
                send_text_fn=send_text,
                send_to_group_fn=send_to_group,
            ))
        else:
            loop.run_until_complete(send_reminders(
                channel="whatsapp",
                send_text_fn=send_text,
                send_to_group_fn=send_to_group,
            ))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_reminders(
            channel="whatsapp",
            send_text_fn=send_text,
            send_to_group_fn=send_to_group,
        ))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _is_admin(phone: str) -> bool:
    contact_id, _ = identify_by_phone(phone)
    if not contact_id:
        return False
    contact = load_contact(contact_id)
    return contact.get("rol_kalendbot") == "admin" if contact else False


def _convert_markdown_to_whatsapp(text: str) -> str:
    """Convert markdown from LLM to WhatsApp format."""
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)  # **bold** → *bold*
    return text
