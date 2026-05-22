"""
Proveedor de WhatsApp: interfaz abstracta, utilidades y implementación WAHA.
Para agregar un proveedor nuevo: crear clase que implemente WhatsAppProvider,
agregar elif en get_whatsapp_provider(), y configurar WHATSAPP_PROVIDER en .env.
"""
import os
import base64
import logging
import mimetypes
import httpx
from typing import Protocol, runtime_checkable

from src.config import settings

logger = logging.getLogger("kalendbot.whatsapp_provider")


# ---------------------------------------------------------------------------
# Interfaz abstracta
# ---------------------------------------------------------------------------

@runtime_checkable
class WhatsAppProvider(Protocol):
    """Interfaz que todo proveedor de WhatsApp debe implementar."""

    def send_text(self, chat_id: str, text: str) -> dict: ...
    def send_reply(self, chat_id: str, text: str, reply_to: str = "") -> dict: ...
    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> dict: ...
    def send_image(self, chat_id: str, image_path: str, caption: str = "") -> dict: ...
    def parse_webhook(self, data: dict) -> dict | None: ...
    def get_session_status(self) -> str: ...


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def normalize_phone(phone: str) -> str:
    """Normaliza un número de teléfono: quita +, espacios, guiones, paréntesis."""
    return phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def phone_to_chat_id(phone: str) -> str:
    """Convierte un teléfono a formato chat_id de WhatsApp (number@c.us)."""
    normalized = normalize_phone(phone)
    if "@" in normalized:
        return normalized
    return f"{normalized}@c.us"


# ---------------------------------------------------------------------------
# Implementación WAHA
# ---------------------------------------------------------------------------

WAHA_API_URL = settings.waha_api_url
WAHA_API_KEY = settings.waha_api_key
WAHA_SESSION = settings.waha_session_name


class WAHAProvider:
    """Proveedor de WhatsApp via WAHA REST API. Docs: https://waha.devlike.pro/"""

    def __init__(self):
        self.api_url = WAHA_API_URL
        self.api_key = WAHA_API_KEY
        self.session = WAHA_SESSION
        self.provider_name = "WAHA"

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key, "Content-Type": "application/json"}

    def _is_mock(self) -> bool:
        return not self.api_key

    def send_text(self, chat_id: str, text: str) -> dict:
        if self._is_mock():
            logger.warning(f"{self.provider_name}: API_KEY no configurada. Modo MOCK.")
            logger.info(f"[MOCK {self.provider_name}] → {chat_id}: {text[:100]}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendText"
        payload = {"session": self.session, "chatId": chat_id, "text": text}
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=15)
            response.raise_for_status()
            logger.info(f"{self.provider_name}: mensaje enviado a {chat_id}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"{self.provider_name}: error enviando mensaje a {chat_id}: {e}")
            raise

    def send_reply(self, chat_id: str, text: str, reply_to: str = "") -> dict:
        if self._is_mock():
            logger.info(f"[MOCK {self.provider_name}] reply → {chat_id}: {text[:100]}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendText"
        payload = {"session": self.session, "chatId": chat_id, "text": text}
        if reply_to:
            payload["reply_to"] = reply_to

        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=15)
            response.raise_for_status()
            logger.info(f"{self.provider_name}: reply enviado a {chat_id}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"{self.provider_name}: error enviando reply a {chat_id}: {e}")
            raise

    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> dict:
        if self._is_mock():
            logger.info(f"[MOCK {self.provider_name}] → {chat_id}: archivo {file_path}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendFile"
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "session": self.session,
            "chatId": chat_id,
            "file": {"mimetype": mime_type, "filename": filename, "data": f"data:{mime_type};base64,{file_data}"},
            "caption": caption,
        }
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            logger.info(f"{self.provider_name}: archivo enviado a {chat_id}: {filename}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"{self.provider_name}: error enviando archivo a {chat_id}: {e}")
            raise

    def send_image(self, chat_id: str, image_path: str, caption: str = "") -> dict:
        if self._is_mock():
            logger.info(f"[MOCK {self.provider_name}] → {chat_id}: imagen {image_path}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendImage"
        mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "session": self.session,
            "chatId": chat_id,
            "file": {"mimetype": mime_type, "filename": filename, "data": f"data:{mime_type};base64,{file_data}"},
            "caption": caption,
        }
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            logger.info(f"{self.provider_name}: imagen enviada a {chat_id}: {filename}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"{self.provider_name}: error enviando imagen a {chat_id}: {e}")
            raise

    def parse_webhook(self, data: dict) -> dict | None:
        try:
            event = data.get("event", "")
            if event != "message":
                return None

            payload = data.get("payload", {})
            if payload.get("fromMe", False):
                return None

            from_id = payload.get("from", "")
            text = (payload.get("body") or "").strip()
            if not text:
                return None

            is_group = "@g.us" in from_id

            if is_group:
                participant = payload.get("participant", from_id)
                sender_phone = participant.replace("@c.us", "").replace("@s.whatsapp.net", "")
                group_id = from_id
            else:
                sender_phone = from_id.replace("@c.us", "").replace("@s.whatsapp.net", "")
                group_id = None

            return {
                "sender_phone": sender_phone,
                "message_text": text,
                "is_group": is_group,
                "group_id": group_id,
                "has_media": payload.get("hasMedia", False),
                "mentioned_jids": payload.get("mentionedJids", []),
                "message_id": payload.get("id"),
            }
        except Exception as e:
            logger.error(f"{self.provider_name}: error parseando webhook: {e}")
            return None

    def get_session_status(self) -> str:
        if self._is_mock():
            return "MOCK"

        url = f"{self.api_url}/api/sessions/{self.session}"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            return response.json().get("status", "UNKNOWN")
        except httpx.HTTPError as e:
            logger.error(f"{self.provider_name}: error consultando sesión: {e}")
            return "ERROR"


# ---------------------------------------------------------------------------
# Factory — configurable via WHATSAPP_PROVIDER env var
# ---------------------------------------------------------------------------

def get_whatsapp_provider() -> WhatsAppProvider:
    """Retorna el proveedor configurado en .env (WHATSAPP_PROVIDER=waha)."""
    provider_type = settings.whatsapp_provider.lower()

    if provider_type == "waha":
        return WAHAProvider()
    else:
        raise ValueError(f"Proveedor de WhatsApp desconocido: {provider_type}. Configurar WHATSAPP_PROVIDER en .env")
