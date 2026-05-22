"""
Dispatcher de notificaciones canal-agnóstico.
Enruta mensajes a Telegram o WhatsApp según canal_preferido del contacto.
"""
import logging
import httpx

from src.config import settings
from src.gateways.contacts import load_contact, get_contact_telegram_id, get_contact_phone
from src.gateways.whatsapp_provider import get_whatsapp_provider, phone_to_chat_id
from src.gateways.templates import render_template

logger = logging.getLogger("kalendbot.dispatcher")


def _send_telegram_message(chat_id: int | str, text: str) -> bool:
    """Envía un mensaje via Telegram Bot API."""
    bot_token = settings.telegram_bot_token
    if not bot_token:
        logger.warning("Sin TELEGRAM_BOT_TOKEN, mensaje no enviado")
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        resp = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.error(f"Error enviando Telegram a {chat_id}: {e}")
        return False


def send_dm(contact_id: str, message: str = None, template_id: str = None, **template_vars) -> bool:
    """
    Envía un DM a un contacto por su canal preferido.
    Usa template_id + vars para mensaje templated, o message para texto directo.
    """
    contact = load_contact(contact_id)
    if not contact:
        logger.warning(f"Contacto {contact_id} no encontrado")
        return False

    canal = contact.get("canal_preferido", "telegram")
    text = render_template(template_id, **template_vars) if template_id else message

    if not text:
        logger.warning(f"Sin texto para enviar a {contact_id}")
        return False

    if canal == "whatsapp":
        phone = contact.get("telefono")
        if not phone:
            logger.warning(f"Contacto {contact_id} sin teléfono para WhatsApp")
            return False
        try:
            provider = get_whatsapp_provider()
            chat_id = phone_to_chat_id(phone)
            provider.send_text(chat_id, text)
            logger.info(f"DM enviado a {contact_id} via WhatsApp")
            return True
        except Exception as e:
            logger.error(f"Error enviando WA DM a {contact_id}: {e}")
            return False
    else:
        # Default: Telegram
        tid = contact.get("telegram_id")
        if not tid:
            logger.warning(f"Contacto {contact_id} sin telegram_id")
            return False
        success = _send_telegram_message(tid, text)
        if success:
            logger.info(f"DM enviado a {contact_id} via Telegram")
        return success


def send_to_group(message: str, channel: str = "both") -> bool:
    """
    Envía un mensaje al grupo.
    channel: "telegram", "whatsapp", o "both"
    """
    sent = False

    if channel in ("telegram", "both"):
        group_id = settings.telegram_group_chat_id
        if group_id:
            sent = _send_telegram_message(group_id, message) or sent
        else:
            logger.warning("TELEGRAM_GROUP_CHAT_ID no configurado")

    if channel in ("whatsapp", "both"):
        wa_group_id = settings.whatsapp_group_chat_id
        if wa_group_id:
            try:
                provider = get_whatsapp_provider()
                provider.send_text(wa_group_id, message)
                sent = True
            except Exception as e:
                logger.error(f"Error enviando a grupo WA: {e}")
        else:
            logger.warning("WHATSAPP_GROUP_CHAT_ID no configurado")

    return sent
