"""
Servidor FastAPI que recibe webhooks de Evolution API y los procesa con el agente.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import uvicorn

from src.agent import handle_message
from src.gateways.evolution import send_message, parse_incoming_webhook

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("kalendbot.server")

app = FastAPI(title="KalendBot", description="Bot de calendario NV Mexico")

GROUP_CHAT_ID = os.getenv("KALENDBOT_GROUP_CHAT_ID", "")


@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """Recibe webhooks de Evolution API."""
    data = await request.json()
    parsed = parse_incoming_webhook(data)

    if not parsed:
        return {"status": "ignored"}

    # Ignorar mensajes de grupo (el bot solo responde en privado)
    if parsed["is_group"]:
        logger.info(f"Mensaje de grupo ignorado: {parsed['message_text'][:50]}")
        return {"status": "group_ignored"}

    phone = parsed["sender_phone"]
    message = parsed["message_text"]

    logger.info(f"Mensaje entrante de {phone}: {message[:80]}")

    # Procesar con el agente
    response = handle_message(phone, message)

    # Enviar respuesta via Evolution API
    send_message(phone, response)

    return {"status": "processed", "to": phone}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "kalendbot"}


@app.get("/status")
async def status():
    """Estado del calendario — resumen rápido."""
    from src.tools.calendar_manager import calendar_manager
    pending = calendar_manager('{"action": "list_pending"}')
    return {"pending_events": pending}


def start_server():
    port = int(os.getenv("KALENDBOT_WEBHOOK_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    start_server()
