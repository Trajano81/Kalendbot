"""
Tool 6: GroupNotifier
Publica mensajes en el chat grupal de NV Mexico via Evolution API.
"""
import json
import os
import logging
import httpx
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger("kalendbot.group_notifier")

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE_NAME", "kalendbot")
GROUP_CHAT_ID = os.getenv("KALENDBOT_GROUP_CHAT_ID", "")


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

    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID no configurado. Mensaje no enviado.")
        return f"[MOCK - sin GROUP_CHAT_ID] Mensaje para grupo:\n{message}"

    if not EVOLUTION_API_KEY:
        logger.warning("EVOLUTION_API_KEY no configurada. Mensaje no enviado.")
        return f"[MOCK - sin API key] Mensaje para grupo:\n{message}"

    try:
        url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
        headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
        payload = {
            "number": GROUP_CHAT_ID,
            "text": message
        }
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return f"Mensaje publicado en grupo exitosamente"
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
