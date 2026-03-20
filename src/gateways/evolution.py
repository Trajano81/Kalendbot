"""
Gateway de Evolution API para WhatsApp.
Envía y recibe mensajes via REST API.
"""
import os
import logging
import httpx

logger = logging.getLogger("kalendbot.evolution")

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE_NAME", "kalendbot")


def send_message(phone_number: str, text: str) -> dict:
    """Envía un mensaje de texto via Evolution API."""
    if not EVOLUTION_API_KEY:
        logger.warning("EVOLUTION_API_KEY no configurada. Mensaje en modo MOCK.")
        logger.info(f"[MOCK] → {phone_number}: {text}")
        return {"status": "mock", "to": phone_number, "text": text}

    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": phone_number, "text": text}

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Mensaje enviado a {phone_number}")
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error enviando mensaje a {phone_number}: {e}")
        raise


def parse_incoming_webhook(data: dict) -> dict | None:
    """
    Parsea un webhook entrante de Evolution API.
    Retorna dict con: sender_phone, message_text, is_group, group_id
    """
    try:
        event = data.get("event", "")
        if event != "messages.upsert":
            return None

        message_data = data.get("data", {})
        key = message_data.get("key", {})
        is_from_me = key.get("fromMe", False)

        if is_from_me:
            return None  # Ignorar mensajes propios

        remote_jid = key.get("remoteJid", "")
        is_group = "@g.us" in remote_jid

        # Extraer texto del mensaje
        message = message_data.get("message", {})
        text = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or ""
        )

        if not text.strip():
            return None

        # Extraer número del sender
        if is_group:
            sender_phone = key.get("participant", "").replace("@s.whatsapp.net", "")
            group_id = remote_jid
        else:
            sender_phone = remote_jid.replace("@s.whatsapp.net", "")
            group_id = None

        return {
            "sender_phone": sender_phone,
            "message_text": text.strip(),
            "is_group": is_group,
            "group_id": group_id,
        }
    except Exception as e:
        logger.error(f"Error parseando webhook: {e}")
        return None
