"""
Implementación de WhatsAppProvider para WAHA (WhatsApp HTTP API).
Docs: https://waha.devlike.pro/
"""
import os
import base64
import logging
import mimetypes
import httpx

logger = logging.getLogger("kalendbot.waha")

WAHA_API_URL = os.getenv("WAHA_API_URL", "http://localhost:3000")
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "")
WAHA_SESSION = os.getenv("WAHA_SESSION_NAME", "kalendbot")


class WAHAProvider:
    """Proveedor de WhatsApp via WAHA REST API."""

    def __init__(self):
        self.api_url = WAHA_API_URL
        self.api_key = WAHA_API_KEY
        self.session = WAHA_SESSION

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key, "Content-Type": "application/json"}

    def _is_mock(self) -> bool:
        return not self.api_key

    def send_text(self, chat_id: str, text: str) -> dict:
        """Envía un mensaje de texto via WAHA."""
        if self._is_mock():
            logger.warning("WAHA_API_KEY no configurada. Mensaje en modo MOCK.")
            logger.info(f"[MOCK WA] → {chat_id}: {text[:100]}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendText"
        payload = {
            "session": self.session,
            "chatId": chat_id,
            "text": text,
        }
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=15)
            response.raise_for_status()
            logger.info(f"WA mensaje enviado a {chat_id}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error enviando WA mensaje a {chat_id}: {e}")
            raise

    def send_reply(self, chat_id: str, text: str, reply_to: str = "") -> dict:
        """Envía un mensaje de texto como respuesta a otro mensaje (reply-to)."""
        if self._is_mock():
            logger.info(f"[MOCK WA] reply → {chat_id}: {text[:100]}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendText"
        payload = {
            "session": self.session,
            "chatId": chat_id,
            "text": text,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=15)
            response.raise_for_status()
            logger.info(f"WA reply enviado a {chat_id}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error enviando WA reply a {chat_id}: {e}")
            raise

    def send_file(self, chat_id: str, file_path: str, caption: str = "") -> dict:
        """Envía un archivo (documento) via WAHA."""
        if self._is_mock():
            logger.info(f"[MOCK WA] → {chat_id}: archivo {file_path}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendFile"
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "session": self.session,
            "chatId": chat_id,
            "file": {
                "mimetype": mime_type,
                "filename": filename,
                "data": f"data:{mime_type};base64,{file_data}",
            },
            "caption": caption,
        }
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            logger.info(f"WA archivo enviado a {chat_id}: {filename}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error enviando WA archivo a {chat_id}: {e}")
            raise

    def send_image(self, chat_id: str, image_path: str, caption: str = "") -> dict:
        """Envía una imagen via WAHA."""
        if self._is_mock():
            logger.info(f"[MOCK WA] → {chat_id}: imagen {image_path}")
            return {"status": "mock", "to": chat_id}

        url = f"{self.api_url}/api/sendImage"
        mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        filename = os.path.basename(image_path)

        with open(image_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "session": self.session,
            "chatId": chat_id,
            "file": {
                "mimetype": mime_type,
                "filename": filename,
                "data": f"data:{mime_type};base64,{file_data}",
            },
            "caption": caption,
        }
        try:
            response = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            logger.info(f"WA imagen enviada a {chat_id}: {filename}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error enviando WA imagen a {chat_id}: {e}")
            raise

    def parse_webhook(self, data: dict) -> dict | None:
        """
        Parsea un webhook entrante de WAHA.
        Retorna dict con: sender_phone, message_text, is_group, group_id, has_media
        O None si el evento debe ignorarse.
        """
        try:
            event = data.get("event", "")
            if event != "message":
                return None

            payload = data.get("payload", {})

            # Ignorar mensajes propios
            if payload.get("fromMe", False):
                return None

            from_id = payload.get("from", "")
            text = (payload.get("body") or "").strip()

            # Sin texto → ignorar (podría ser sticker, audio, etc.)
            if not text:
                return None

            is_group = "@g.us" in from_id

            if is_group:
                # En grupo: from = group_id, participant = sender
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
            logger.error(f"Error parseando webhook WAHA: {e}")
            return None

    def get_session_status(self) -> str:
        """Consulta el estado de la sesión WAHA."""
        if self._is_mock():
            return "MOCK"

        url = f"{self.api_url}/api/sessions/{self.session}"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            return response.json().get("status", "UNKNOWN")
        except httpx.HTTPError as e:
            logger.error(f"Error consultando sesión WAHA: {e}")
            return "ERROR"
