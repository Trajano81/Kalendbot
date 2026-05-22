"""
Servidor FastAPI que recibe webhooks de WhatsApp (WAHA)
y los procesa con el agente KalendBot.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import uvicorn

from src.config import settings
from src.logging_config import setup_logging
from src.middleware import RequestLoggingMiddleware
from src.channels.whatsapp.bot import handle_whatsapp_message, send_whatsapp_reminders

setup_logging()
logger = logging.getLogger("kalendbot.server")


# ---------------------------------------------------------------------------
# Scheduler de recordatorios WhatsApp (APScheduler)
# ---------------------------------------------------------------------------

_scheduler = None


def _start_whatsapp_scheduler():
    """Inicia el scheduler de recordatorios de WhatsApp si APScheduler está instalado."""
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler no instalado. Recordatorios WA desactivados. pip install apscheduler")
        return

    # Leer hora de la config de recordatorios
    reminder_config_path = os.path.join(settings.data_dir, "config", "recordatorios.json")
    hora, minuto = 9, 0
    tz_name = "America/Mexico_City"
    try:
        import json
        with open(reminder_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        if config.get("activo"):
            hora_str = config.get("hora_envio", "09:00")
            hora, minuto = map(int, hora_str.split(":"))
            tz_name = config.get("timezone", tz_name)
        else:
            logger.info("Recordatorios desactivados en config")
            return
    except (FileNotFoundError, Exception) as e:
        logger.warning(f"No se pudo cargar config recordatorios: {e}")

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        send_whatsapp_reminders,
        CronTrigger(hour=hora, minute=minuto, timezone=tz_name),
        id="wa_daily_reminders",
        name="WhatsApp daily reminders",
    )
    _scheduler.start()
    logger.info(f"WA recordatorios programados: {hora:02d}:{minuto:02d} ({tz_name})")


# ---------------------------------------------------------------------------
# FastAPI app con lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown del servidor."""
    _start_whatsapp_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown()


app = FastAPI(title="KalendBot", description="Bot de calendario NV Mexico", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Recibe webhooks de WAHA (WhatsApp HTTP API)."""
    data = await request.json()
    event = data.get("event", "")

    if event == "session.status":
        status = data.get("payload", {}).get("status", "")
        logger.info(f"WAHA session status: {status}")
        if status == "SCAN_QR_CODE":
            logger.warning("WAHA necesita re-escanear QR — abrir http://localhost:3000/dashboard")
        return {"status": "noted", "session_status": status}

    if event == "message":
        await handle_whatsapp_message(data)
        return {"status": "processed"}

    return {"status": "ignored", "event": event}


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check del servidor."""
    waha_status = "unknown"
    try:
        from src.gateways.whatsapp_provider import get_whatsapp_provider
        provider = get_whatsapp_provider()
        waha_status = provider.get_session_status()
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "kalendbot",
        "waha_session": waha_status,
    }


@app.get("/status")
async def status():
    """Estado del calendario — resumen rápido."""
    from src.tools.calendar_manager import calendar_manager
    pending = calendar_manager('{"action": "list_pending"}')
    return {"pending_events": pending}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def start_server():
    port = settings.webhook_port
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    start_server()
