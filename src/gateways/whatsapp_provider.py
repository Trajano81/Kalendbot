"""
Interfaz abstracta para proveedores de WhatsApp.
Permite intercambiar WAHA por Meta Cloud API sin cambiar el resto del código.
"""
import os
import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("kalendbot.whatsapp_provider")


@runtime_checkable
class WhatsAppProvider(Protocol):
    """Interfaz que todo proveedor de WhatsApp debe implementar."""

    def send_text(self, chat_id: str, text: str) -> dict:
        """Envía un mensaje de texto."""
        ...

    def send_reply(self, chat_id: str, text: str, reply_to: str = "") -> dict:
        """Envía un mensaje como respuesta a otro (reply-to en grupo)."""
        ...

    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> dict:
        """Envía un archivo (documento)."""
        ...

    def send_image(self, chat_id: str, image_path: str, caption: str = "") -> dict:
        """Envía una imagen."""
        ...

    def parse_webhook(self, data: dict) -> dict | None:
        """
        Parsea un webhook entrante.
        Retorna dict con: sender_phone, message_text, is_group, group_id, has_media
        O None si el evento debe ignorarse.
        """
        ...

    def get_session_status(self) -> str:
        """Retorna el estado de la sesión (ej: 'WORKING', 'SCAN_QR_CODE')."""
        ...


def normalize_phone(phone: str) -> str:
    """Normaliza un número de teléfono: quita +, espacios, guiones, paréntesis."""
    return phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def phone_to_chat_id(phone: str) -> str:
    """Convierte un teléfono a formato chat_id de WhatsApp (WAHA: number@c.us)."""
    normalized = normalize_phone(phone)
    if "@" in normalized:
        return normalized  # Ya tiene formato chat_id
    return f"{normalized}@c.us"


def get_whatsapp_provider() -> WhatsAppProvider:
    """Factory: retorna el proveedor de WhatsApp configurado en .env."""
    provider_type = os.getenv("WHATSAPP_PROVIDER", "waha").lower()

    if provider_type == "waha":
        from src.gateways.waha_provider import WAHAProvider
        return WAHAProvider()
    # elif provider_type == "meta":
    #     from src.gateways.meta_provider import MetaCloudProvider
    #     return MetaCloudProvider()
    else:
        raise ValueError(f"Proveedor de WhatsApp desconocido: {provider_type}")
