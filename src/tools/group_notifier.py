"""
Tool 6: GroupNotifier
Publica mensajes en el chat grupal de NV Mexico via Telegram Bot API.
"""
import os
import logging
import httpx
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger("kalendbot.group_notifier")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_GROUP_CHAT_ID = os.getenv("TELEGRAM_GROUP_CHAT_ID", "")


def group_notifier(message: str, role: str = None) -> str:
    """
    Publica un mensaje en el chat grupal de NV Mexico via Telegram.
    Input: el mensaje de texto a publicar.
    SOLO usar para updates de estado del calendario, nunca para negociación individual.
    """
    if role == "readonly":
        return "No tienes permisos para enviar mensajes al grupo. Contacta al administrador."

    if not message.strip():
        return "Error: Mensaje vacío"

    # Re-leer en runtime por si fue auto-detectado después del startup
    group_id = os.getenv("TELEGRAM_GROUP_CHAT_ID", "") or TELEGRAM_GROUP_CHAT_ID
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "") or TELEGRAM_BOT_TOKEN

    if not group_id:
        logger.warning("TELEGRAM_GROUP_CHAT_ID no configurado. Mensaje no enviado.")
        return f"[MOCK - sin GROUP_CHAT_ID] Mensaje para grupo:\n{message}"

    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado. Mensaje no enviado.")
        return f"[MOCK - sin BOT_TOKEN] Mensaje para grupo:\n{message}"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": group_id,
            "text": message,
        }
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return "Mensaje publicado en grupo exitosamente"
    except httpx.HTTPError as e:
        logger.error(f"Error enviando mensaje al grupo: {e}")
        return f"Error enviando al grupo: {str(e)}"


class GroupNotifierInput(BaseModel):
    message: str = Field(description="Texto del mensaje a publicar en el grupo")
    role: Optional[str] = Field(default=None, description="Rol del usuario: admin, tester, contacto, readonly")


group_notifier_tool = StructuredTool.from_function(
    name="GroupNotifier",
    description="Publica un mensaje en el chat grupal de NV Mexico. SOLO usar para updates de estado del calendario (confirmaciones, alertas, reportes). NUNCA usar para negociación individual con proveedores.",
    func=group_notifier,
    args_schema=GroupNotifierInput,
)
