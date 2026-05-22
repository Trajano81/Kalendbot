"""
Unified reminder engine — shared logic for Telegram and WhatsApp reminders.
Extracts the common reminder logic that was duplicated in both bot files.
"""
import os
import re
import json
import logging
from datetime import datetime, date
from typing import Callable, Awaitable

from src.config import settings
from src.gateways.contacts import load_contact, get_contact_phone, get_contact_telegram_id, get_admin_phone, get_admin_telegram_id
from src.gateways.templates import render_template

logger = logging.getLogger("kalendbot.handlers.reminders")

DATA_DIR = settings.data_dir

# Coordinador principal — recibe copia de recordatorios de flyer
COORDINATOR_ID = "rocco-van-velzen"
CONTENT_MANAGER_ID = "hanna-van-rijsse"


def load_reminder_config() -> dict:
    """Load reminder configuration from JSON."""
    config_path = os.path.join(DATA_DIR, "config", "recordatorios.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"No se pudo cargar {config_path}")
        return {"activo": False}


def load_sent_reminders() -> dict:
    """Load the record of already-sent reminders."""
    filepath = os.path.join(DATA_DIR, "config", "recordatorios-enviados.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_sent_reminder(reminder_key: str) -> None:
    """Record that a reminder was sent."""
    filepath = os.path.join(DATA_DIR, "config", "recordatorios-enviados.json")
    sent = load_sent_reminders()
    sent[reminder_key] = datetime.now().isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sent, f, ensure_ascii=False, indent=2)


def parse_flyer_moment(flyer_moment: str) -> list[int]:
    """Parse the flyer_moment field. E.g. '-60,-30,-7 dagen' -> [60, 30, 7]."""
    if not flyer_moment or flyer_moment.lower() == "x":
        return []
    numbers = re.findall(r'(\d+)', flyer_moment)
    return [int(n) for n in numbers]


def contact_prefers_channel(contact_id: str, channel: str) -> bool:
    """Check if a contact prefers the given channel."""
    contact = load_contact(contact_id)
    if not contact:
        return False
    return contact.get("canal_preferido", "telegram") == channel


async def send_reminders(
    channel: str,
    send_text_fn: Callable[[str, str], Awaitable[None] | None],
    send_to_group_fn: Callable[[str, str], Awaitable[None] | None] | None = None,
) -> None:
    """
    Unified reminder engine. Called by both Telegram and WhatsApp schedulers.

    Args:
        channel: "telegram" or "whatsapp"
        send_text_fn: async fn(recipient_id, message) — sends a DM.
                      recipient_id is telegram_id (int→str) for telegram, chat_id for whatsapp.
        send_to_group_fn: async fn(group_id, message) — sends to group. None to skip group reminders.
    """
    config = load_reminder_config()
    if not config.get("activo"):
        return

    sent = load_sent_reminders()
    conf_config = config.get("confirmacion", {})
    flyer_config = config.get("flyer", {})
    grupo_config = config.get("grupo", {})

    # Channel-specific group ID and key suffix
    if channel == "whatsapp":
        group_id = settings.whatsapp_group_chat_id
        key_suffix = ":wa"
    else:
        group_id = settings.telegram_group_chat_id
        key_suffix = ""

    year = datetime.now().year
    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    try:
        with open(cal_path, "r", encoding="utf-8") as f:
            calendario = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"{channel} reminders: no se pudo cargar {cal_path}")
        return

    hoy = date.today()
    enviados_hoy = 0
    admin_resumen = []

    for evento in calendario.get("eventos", []):
        if evento.get("estado") == "cancelado":
            continue

        try:
            fecha_evento = date.fromisoformat(evento["fecha"])
        except (ValueError, KeyError):
            continue

        dias_restantes = (fecha_evento - hoy).days
        if dias_restantes < 0:
            continue

        evt_nombre = evento.get("nombre", "Sin nombre")
        evt_fecha = evento.get("fecha", "")
        evt_id = evento["id"]

        # --- TYPE 1: Confirmation reminder (pending events only) ---
        if evento.get("estado") == "pendiente":
            for dias in conf_config.get("dias", [30, 14, 7]):
                if dias_restantes != dias:
                    continue
                key = f"conf:{evt_id}:{dias}{key_suffix}"
                if key in sent:
                    continue

                if channel == "whatsapp":
                    mensaje = render_template(
                        "event_reminder",
                        event_name=evt_nombre,
                        days=dias,
                        date=evt_fecha,
                    )
                else:
                    mensajes_conf = conf_config.get("mensajes", {})
                    template = mensajes_conf.get(str(dias), "Recordatorio: '{nombre}' el {fecha} aún no está confirmado.")
                    mensaje = template.format(nombre=evt_nombre, fecha=evt_fecha, dias=dias)

                contacto_ids = evento.get("contacto_ids", [])
                for cid in contacto_ids:
                    if not contact_prefers_channel(cid, channel):
                        continue
                    recipient = _get_recipient_id(cid, channel)
                    if recipient:
                        try:
                            await _call_send(send_text_fn, recipient, mensaje)
                        except Exception as e:
                            logger.error(f"Error {channel} confirmación a {cid}: {e}")

                save_sent_reminder(key)
                enviados_hoy += 1
                admin_resumen.append(f"Confirmación ({dias}d): {evt_nombre}")

        # --- TYPE 2: Flyer reminder ---
        flyer_resp = evento.get("flyer_responsable", "")
        flyer_status = evento.get("flyer_status", "no_solicitado")

        if flyer_resp.lower() in ("nv", "proveedor") and flyer_status != "aprobado":
            flyer_moment = evento.get("flyer_moment", "")
            toca_standard = False
            dias_match = 0
            if flyer_moment and flyer_moment.lower() != "x":
                flyer_dias = parse_flyer_moment(flyer_moment)
                for dias in flyer_dias:
                    if dias_restantes == dias:
                        toca_standard = True
                        dias_match = dias
                        break

            toca_custom = False
            for cd in evento.get("flyer_reminder_custom", []):
                try:
                    if date.fromisoformat(cd) == hoy:
                        toca_custom = True
                        break
                except ValueError:
                    continue

            if toca_standard or toca_custom:
                key_str = f"{dias_match}" if toca_standard else f"custom:{hoy.isoformat()}"
                key = f"flyer:{evt_id}:{key_str}{key_suffix}"
                if key not in sent:
                    if channel == "whatsapp":
                        mensaje = render_template(
                            "flyer_reminder",
                            event_name=evt_nombre,
                            deadline=evt_fecha,
                        )
                    else:
                        template = flyer_config.get("mensaje", "Recordatorio de flyer: '{nombre}' el {fecha}. Faltan {dias} días.")
                        mensaje = template.format(nombre=evt_nombre, fecha=evt_fecha, dias=dias_restantes)
                        mensaje += "\nSi no apruebas o actualizas el status del flyer, seguirás recibiendo recordatorios."

                    if flyer_status == "rechazado":
                        mensaje += "\n⚠️ De flyer is afgekeurd. Stuur de correctie alsjeblieft."

                    destinatarios = []
                    if flyer_resp == "proveedor":
                        destinatarios = list(evento.get("contacto_ids", []))
                    elif flyer_resp == "nv":
                        destinatarios = [CONTENT_MANAGER_ID]
                    if COORDINATOR_ID not in destinatarios:
                        destinatarios.append(COORDINATOR_ID)

                    for cid in destinatarios:
                        if not contact_prefers_channel(cid, channel):
                            continue
                        recipient = _get_recipient_id(cid, channel)
                        if recipient:
                            try:
                                await _call_send(send_text_fn, recipient, mensaje)
                            except Exception as e:
                                logger.error(f"Error {channel} flyer a {cid}: {e}")

                    save_sent_reminder(key)
                    enviados_hoy += 1
                    admin_resumen.append(f"Flyer ({dias_restantes}d): {evt_nombre}")

        # --- TYPE 3: Group reminder ---
        if group_id and send_to_group_fn:
            for dias in grupo_config.get("dias", [14, 7, 1]):
                if dias_restantes != dias:
                    continue
                key = f"grupo:{evt_id}:{dias}{key_suffix}"
                if key in sent:
                    continue

                if channel == "whatsapp":
                    mensaje = render_template(
                        "group_event_reminder",
                        event_name=evt_nombre,
                        date=evt_fecha,
                        days=dias,
                    )
                else:
                    mensajes_grupo = grupo_config.get("mensajes", {})
                    template = mensajes_grupo.get(str(dias), "Próximo evento: {nombre} - {fecha}")
                    mensaje = template.format(
                        nombre=evt_nombre,
                        fecha=evt_fecha,
                        estado=evento.get("estado", ""),
                        detalle=evento.get("detalle", ""),
                        dias=dias,
                    )

                try:
                    await _call_send(send_to_group_fn, group_id, mensaje)
                except Exception as e:
                    logger.error(f"Error {channel} grupo: {e}")

                save_sent_reminder(key)
                enviados_hoy += 1
                admin_resumen.append(f"Grupo ({dias}d): {evt_nombre}")

    # Admin summary
    if admin_resumen and config.get("notificar_admin"):
        _send_admin_summary(channel, send_text_fn, admin_resumen)

    if enviados_hoy > 0:
        logger.info(f"{channel} recordatorios enviados: {enviados_hoy}")
    else:
        logger.info(f"{channel} sin recordatorios pendientes")


def _get_recipient_id(contact_id: str, channel: str) -> str | None:
    """Get the channel-specific recipient ID for a contact."""
    if channel == "whatsapp":
        from src.gateways.whatsapp_provider import phone_to_chat_id
        phone = get_contact_phone(contact_id)
        return phone_to_chat_id(phone) if phone else None
    else:
        tid = get_contact_telegram_id(contact_id)
        return str(tid) if tid else None


async def _call_send(fn, *args):
    """Call a send function, handling both sync and async."""
    import asyncio
    result = fn(*args)
    if asyncio.iscoroutine(result):
        await result


def _send_admin_summary(channel: str, send_text_fn, admin_resumen: list[str]):
    """Send daily summary to admin (fire-and-forget)."""
    import asyncio

    resumen_text = "Resumen de recordatorios de hoy:\n\n" + "\n".join(f"- {r}" for r in admin_resumen)

    if channel == "whatsapp":
        admin_phone = get_admin_phone()
        if admin_phone and contact_prefers_channel_by_phone(admin_phone, "whatsapp"):
            from src.gateways.whatsapp_provider import phone_to_chat_id
            recipient = phone_to_chat_id(admin_phone)
            try:
                result = send_text_fn(recipient, resumen_text)
                if asyncio.iscoroutine(result):
                    # Schedule it — we're in an async context already
                    asyncio.ensure_future(result)
            except Exception as e:
                logger.error(f"Error {channel} resumen admin: {e}")
    else:
        admin_tid = get_admin_telegram_id()
        if admin_tid:
            try:
                result = send_text_fn(str(admin_tid), resumen_text)
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
            except Exception as e:
                logger.error(f"Error {channel} resumen admin: {e}")


def contact_prefers_channel_by_phone(phone: str, channel: str) -> bool:
    """Check if a contact (by phone) prefers the given channel."""
    from src.gateways.contacts import identify_by_phone
    contact_id, _ = identify_by_phone(phone)
    if not contact_id:
        return False
    return contact_prefers_channel(contact_id, channel)
