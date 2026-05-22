"""
Tool 6: GroupNotifier
Publica mensajes en el chat grupal de NV Mexico.
Envía a Telegram, WhatsApp, o ambos según configuración.
"""
import logging
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger("kalendbot.group_notifier")


def group_notifier(message: str, role: str = None) -> str:
    """
    Publica un mensaje en el chat grupal de NV Mexico.
    Input: el mensaje de texto a publicar.
    SOLO usar para updates de estado del calendario, nunca para negociación individual.
    """
    if role == "readonly":
        return "No tienes permisos para enviar mensajes al grupo. Contacta al administrador."

    if not message.strip():
        return "Error: Mensaje vacío"

    from src.gateways.dispatcher import send_to_group

    has_telegram = bool(settings.telegram_group_chat_id)
    has_whatsapp = bool(settings.whatsapp_group_chat_id)

    if has_telegram and has_whatsapp:
        channel = "both"
    elif has_whatsapp:
        channel = "whatsapp"
    elif has_telegram:
        channel = "telegram"
    else:
        logger.warning("Ningún GROUP_CHAT_ID configurado. Mensaje no enviado.")
        return f"[MOCK - sin GROUP_CHAT_ID] Mensaje para grupo:\n{message}"

    success = send_to_group(message, channel=channel)
    if success:
        return "Mensaje publicado en grupo exitosamente"
    else:
        return "Error enviando al grupo. Revisa los logs."


class GroupNotifierInput(BaseModel):
    message: str = Field(description="Texto del mensaje a publicar en el grupo")
    role: Optional[str] = Field(default=None, description="Rol del usuario: admin, tester, contacto, readonly")


group_notifier_tool = StructuredTool.from_function(
    name="GroupNotifier",
    description="Publica un mensaje en el chat grupal de NV Mexico. SOLO usar para updates de estado del calendario (confirmaciones, alertas, reportes). NUNCA usar para negociación individual con proveedores.",
    func=group_notifier,
    args_schema=GroupNotifierInput,
)
