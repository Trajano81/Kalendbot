"""
Gateway de WhatsApp para KalendBot via WAHA.
Maneja mensajes, registro de usuarios, comandos y recordatorios.
"""
import os
import re
import json
import logging
from datetime import datetime, date

from src.agent import handle_message
from src.gateways.contacts import (
    identify_by_phone,
    load_contact,
    create_contact_json,
    get_admin_phone,
    get_contact_phone,
    strip_markdown,
    normalize_phone,
)
from src.gateways.whatsapp_provider import get_whatsapp_provider, phone_to_chat_id
from src.gateways.templates import render_template

logger = logging.getLogger("kalendbot.whatsapp")

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
COORDINATOR_ID = "rocco-van-velzen"
CONTENT_MANAGER_ID = "hanna-van-rijsse"

# Estado temporal de usuarios en proceso de registro
# { phone: { "step": "awaiting_name" | "awaiting_approval", "nombre": str } }
_pending_registrations: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Manejo de mensajes entrantes
# ---------------------------------------------------------------------------

async def handle_whatsapp_message(data: dict) -> None:
    """
    Procesa un webhook entrante de WAHA.
    Entry point llamado desde server.py.
    """
    provider = get_whatsapp_provider()
    parsed = provider.parse_webhook(data)

    if not parsed:
        return

    # Mensajes de grupo: solo responder si el bot fue invocado
    if parsed["is_group"]:
        allowed = os.getenv("WHATSAPP_GROUP_CHAT_ID", "")
        if allowed and parsed["group_id"] != allowed:
            logger.info(f"WA grupo no autorizado: {parsed['group_id']}")
            return

        triggered, clean_text = _is_bot_triggered(parsed)
        if not triggered:
            return  # Conversación normal del grupo, ignorar

        await _handle_group_message(parsed, clean_text, provider)
        return

    phone = parsed["sender_phone"]
    text = parsed["message_text"]
    chat_id = phone_to_chat_id(phone)

    logger.info(f"WA mensaje de {phone}: {text[:80]}")

    # Verificar si es un comando
    if text.startswith(("!", "/")):
        await _handle_command(phone, chat_id, text, provider)
        return

    # Verificar si está en proceso de registro
    if phone in _pending_registrations:
        await _handle_registration_flow(phone, chat_id, text, provider)
        return

    # Verificar comandos de admin (APROBAR/RECHAZAR)
    if _is_admin(phone) and text.upper().startswith(("APROBAR ", "RECHAZAR ")):
        await _handle_admin_approval(phone, chat_id, text, provider)
        return

    # Identificar contacto por teléfono
    contact_id, _ = identify_by_phone(phone)

    if not contact_id:
        # Iniciar flujo de registro
        _pending_registrations[phone] = {"step": "awaiting_name"}
        msg = render_template("registration_pending")
        provider.send_text(chat_id, msg)
        logger.info(f"WA registro iniciado para {phone}")
        return

    # Procesar con el agente
    response = handle_message(phone=phone, message=text, contact_id=contact_id)
    response = _convert_markdown_to_whatsapp(response)
    provider.send_text(chat_id, response)
    logger.info(f"WA respuesta a {contact_id}: {response[:80]}")


# ---------------------------------------------------------------------------
# Grupo: detección de trigger y manejo de mensajes
# ---------------------------------------------------------------------------

WHATSAPP_BOT_JID = os.getenv("WHATSAPP_BOT_JID", "")


def _is_bot_triggered(parsed: dict) -> tuple[bool, str]:
    """
    Detecta si un mensaje de grupo va dirigido al bot.
    Returns: (triggered, cleaned_message_text)

    Prioridad:
    1. mentionedJids contiene WHATSAPP_BOT_JID
    2. Mensaje empieza con "/" (slash trigger)
    """
    text = parsed["message_text"]

    # 1. @mention via WAHA mentionedJids
    if WHATSAPP_BOT_JID and WHATSAPP_BOT_JID in parsed.get("mentioned_jids", []):
        # Strip the @mention text from the beginning (e.g., "@5215XXXXXXXX ")
        clean = re.sub(r'^@\S+\s*', '', text).strip()
        return (True, clean) if clean else (False, "")

    # 2. Slash trigger: /texto libre para el agente
    if text.startswith("/"):
        clean = text[1:].strip()
        return (True, clean) if clean else (False, "")

    return (False, "")


async def _handle_group_message(parsed: dict, text: str, provider) -> None:
    """Procesa un mensaje de grupo dirigido al bot."""
    phone = parsed["sender_phone"]
    group_id = parsed["group_id"]
    message_id = parsed.get("message_id")

    contact_id, _ = identify_by_phone(phone)

    if not contact_id:
        provider.send_reply(
            group_id,
            "Ik ken je nog niet. Stuur mij een privébericht om je te registreren.",
            message_id,
        )
        return

    logger.info(f"WA grupo trigger de {contact_id}: {text[:80]}")

    # Hint para que el agente sea conciso en respuestas de grupo
    message = f"[Grupo] {text}"

    response = handle_message(phone=phone, message=message, contact_id=contact_id)
    response = _convert_markdown_to_whatsapp(response)
    provider.send_reply(group_id, response, message_id)
    logger.info(f"WA grupo respuesta a {contact_id}: {response[:80]}")


# ---------------------------------------------------------------------------
# Registro de usuarios
# ---------------------------------------------------------------------------

async def _handle_registration_flow(phone: str, chat_id: str, text: str, provider) -> None:
    """Maneja el flujo de registro paso a paso."""
    reg = _pending_registrations[phone]

    if reg["step"] == "awaiting_name":
        reg["nombre"] = text.strip()
        reg["step"] = "awaiting_approval"

        # Notificar al usuario
        msg = render_template("registration_submitted", name=reg["nombre"])
        provider.send_text(chat_id, msg)

        # Notificar al admin
        admin_phone = get_admin_phone()
        if admin_phone:
            admin_chat_id = phone_to_chat_id(admin_phone)
            admin_msg = (
                f"Solicitud de acceso al bot:\n\n"
                f"Nombre: {reg['nombre']}\n"
                f"WhatsApp: +{phone}\n"
                f"Rol asignado: readonly (solo lectura)\n\n"
                f"Responde:\n"
                f"APROBAR {phone}\n"
                f"o\n"
                f"RECHAZAR {phone}"
            )
            provider.send_text(admin_chat_id, admin_msg)
        else:
            logger.warning("No se encontró admin para notificar solicitud WA")

        logger.info(f"WA registro: {reg['nombre']} ({phone}) esperando aprobación")


async def _handle_admin_approval(phone: str, chat_id: str, text: str, provider) -> None:
    """Procesa comandos APROBAR/RECHAZAR del admin."""
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        provider.send_text(chat_id, "Formato: APROBAR <número> o RECHAZAR <número>")
        return

    action = parts[0].upper()
    target_phone = normalize_phone(parts[1])

    # Buscar en registros pendientes
    reg = None
    reg_phone = None
    for p, r in _pending_registrations.items():
        if normalize_phone(p) == target_phone or target_phone in normalize_phone(p):
            reg = r
            reg_phone = p
            break

    if not reg or reg.get("step") != "awaiting_approval":
        provider.send_text(chat_id, f"No hay solicitud pendiente para {parts[1]}")
        return

    if action == "APROBAR":
        contact_id = create_contact_json(
            nombre=reg["nombre"],
            telefono=f"+{reg_phone}",
            canal="whatsapp",
        )
        del _pending_registrations[reg_phone]

        provider.send_text(chat_id, f"APROBADO. Contacto creado: {contact_id} (readonly)")

        # Notificar al usuario
        target_chat_id = phone_to_chat_id(reg_phone)
        welcome_msg = render_template("welcome_registered", name=reg["nombre"])
        provider.send_text(target_chat_id, welcome_msg)
        logger.info(f"WA usuario aprobado: {contact_id} ({reg_phone})")

    elif action == "RECHAZAR":
        del _pending_registrations[reg_phone]
        provider.send_text(chat_id, "RECHAZADO.")

        target_chat_id = phone_to_chat_id(reg_phone)
        provider.send_text(
            target_chat_id,
            "Je aanvraag is niet goedgekeurd. Neem contact op met de beheerder.",
        )
        logger.info(f"WA usuario rechazado: {reg_phone}")


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

async def _handle_command(phone: str, chat_id: str, text: str, provider) -> None:
    """Maneja comandos tipo !export, !help, !status."""
    cmd = text.lower().strip().lstrip("!/")

    if cmd in ("export", "export_excel"):
        await _cmd_export(phone, chat_id, provider)
    elif cmd in ("help", "ayuda"):
        _cmd_help(chat_id, provider)
    elif cmd in ("status", "estado"):
        _cmd_status(chat_id, provider)
    else:
        # Comando desconocido → pasar al agente como mensaje normal
        contact_id, _ = identify_by_phone(phone)
        if contact_id:
            response = handle_message(phone=phone, message=text, contact_id=contact_id)
            response = _convert_markdown_to_whatsapp(response)
            provider.send_text(chat_id, response)


async def _cmd_export(phone: str, chat_id: str, provider) -> None:
    """Genera y envía el Excel del calendario."""
    contact_id, _ = identify_by_phone(phone)
    if not contact_id:
        provider.send_text(chat_id, "No estás identificado.")
        return

    contact = load_contact(contact_id)
    rol = contact.get("rol_kalendbot", "readonly") if contact else "readonly"

    if rol == "readonly":
        provider.send_text(chat_id, "No tienes permisos para exportar el calendario.")
        return

    provider.send_text(chat_id, "Generando Excel del calendario...")

    try:
        from src.tools.calendar_exporter import export_calendar
        output_path = export_calendar(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            provider.send_text(chat_id, f"Error: {output_path}")
            return

        provider.send_file(chat_id, output_path, caption="Calendario NV Mexico 2026 actualizado")
    except Exception as e:
        logger.error(f"Error exportando calendario WA: {e}")
        provider.send_text(chat_id, f"Error generando el archivo: {e}")


def _cmd_help(chat_id: str, provider) -> None:
    """Envía resumen de capacidades."""
    help_text = (
        "KalendBot - Commando's:\n\n"
        "Stuur een bericht om informatie te vragen over evenementen, contacten of leveranciers.\n\n"
        "!export - Exporteer de kalender naar Excel\n"
        "!status - Bekijk openstaande evenementen\n"
        "!help - Dit bericht\n\n"
        "Je kunt ook gewoon in het Nederlands of Spaans schrijven."
    )
    provider.send_text(chat_id, help_text)


def _cmd_status(chat_id: str, provider) -> None:
    """Envía resumen de eventos pendientes."""
    try:
        from src.tools.calendar_manager import calendar_manager
        pending = calendar_manager('{"action": "list_pending"}')
        provider.send_text(chat_id, pending)
    except Exception as e:
        provider.send_text(chat_id, f"Error: {e}")


# ---------------------------------------------------------------------------
# Recordatorios diarios (llamado por APScheduler)
# ---------------------------------------------------------------------------

def send_whatsapp_reminders() -> None:
    """
    Job diario: envía recordatorios via WhatsApp.
    Solo procesa contactos con canal_preferido == "whatsapp".
    Misma lógica que telegram_bot._send_reminders pero via WAHA.
    """
    config = _load_reminder_config()
    if not config.get("activo"):
        return

    provider = get_whatsapp_provider()
    sent = _load_sent_reminders()
    conf_config = config.get("confirmacion", {})
    flyer_config = config.get("flyer", {})
    grupo_config = config.get("grupo", {})
    wa_group_id = os.getenv("WHATSAPP_GROUP_CHAT_ID", "")

    year = datetime.now().year
    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    try:
        with open(cal_path, "r", encoding="utf-8") as f:
            calendario = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"WA reminders: no se pudo cargar {cal_path}")
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

        # --- TIPO 1: Recordatorio de confirmación ---
        if evento.get("estado") == "pendiente":
            for dias in conf_config.get("dias", [30, 14, 7]):
                if dias_restantes != dias:
                    continue
                key = f"conf:{evt_id}:{dias}:wa"
                if key in sent:
                    continue

                mensaje = render_template(
                    "event_reminder",
                    event_name=evt_nombre,
                    days=dias,
                    date=evt_fecha,
                )

                contacto_ids = evento.get("contacto_ids", [])
                for cid in contacto_ids:
                    if _contact_prefers_whatsapp(cid):
                        phone = get_contact_phone(cid)
                        if phone:
                            try:
                                provider.send_text(phone_to_chat_id(phone), mensaje)
                            except Exception as e:
                                logger.error(f"Error WA confirmación a {cid}: {e}")

                _save_sent_reminder(key)
                enviados_hoy += 1
                admin_resumen.append(f"Confirmación ({dias}d): {evt_nombre}")

        # --- TIPO 2: Recordatorio de flyer ---
        flyer_resp = evento.get("flyer_responsable", "")
        flyer_status = evento.get("flyer_status", "no_solicitado")

        if flyer_resp.lower() in ("nv", "proveedor") and flyer_status != "aprobado":
            flyer_moment = evento.get("flyer_moment", "")
            toca_standard = False
            dias_match = 0
            if flyer_moment and flyer_moment.lower() != "x":
                flyer_dias = _parse_flyer_moment(flyer_moment)
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
                key_suffix = f"{dias_match}" if toca_standard else f"custom:{hoy.isoformat()}"
                key = f"flyer:{evt_id}:{key_suffix}:wa"
                if key not in sent:
                    mensaje = render_template(
                        "flyer_reminder",
                        event_name=evt_nombre,
                        deadline=evt_fecha,
                    )
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
                        if _contact_prefers_whatsapp(cid):
                            phone = get_contact_phone(cid)
                            if phone:
                                try:
                                    provider.send_text(phone_to_chat_id(phone), mensaje)
                                except Exception as e:
                                    logger.error(f"Error WA flyer a {cid}: {e}")

                    _save_sent_reminder(key)
                    enviados_hoy += 1
                    admin_resumen.append(f"Flyer ({dias_restantes}d): {evt_nombre}")

        # --- TIPO 3: Recordatorio grupal ---
        if wa_group_id:
            for dias in grupo_config.get("dias", [14, 7, 1]):
                if dias_restantes != dias:
                    continue
                key = f"grupo:{evt_id}:{dias}:wa"
                if key in sent:
                    continue

                mensaje = render_template(
                    "group_event_reminder",
                    event_name=evt_nombre,
                    date=evt_fecha,
                    days=dias,
                )
                try:
                    provider.send_text(wa_group_id, mensaje)
                except Exception as e:
                    logger.error(f"Error WA grupo: {e}")

                _save_sent_reminder(key)
                enviados_hoy += 1
                admin_resumen.append(f"Grupo ({dias}d): {evt_nombre}")

    # Resumen al admin
    if admin_resumen and config.get("notificar_admin"):
        admin_phone = get_admin_phone()
        if admin_phone and _contact_prefers_whatsapp_by_phone(admin_phone):
            resumen = render_template(
                "admin_summary",
                summary="\n".join(f"- {r}" for r in admin_resumen),
            )
            try:
                provider.send_text(phone_to_chat_id(admin_phone), resumen)
            except Exception as e:
                logger.error(f"Error WA resumen admin: {e}")

    if enviados_hoy > 0:
        logger.info(f"WA recordatorios enviados: {enviados_hoy}")
    else:
        logger.info("WA sin recordatorios pendientes")


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _is_admin(phone: str) -> bool:
    """Verifica si un teléfono pertenece al admin."""
    contact_id, _ = identify_by_phone(phone)
    if not contact_id:
        return False
    contact = load_contact(contact_id)
    return contact.get("rol_kalendbot") == "admin" if contact else False


def _contact_prefers_whatsapp(contact_id: str) -> bool:
    """Verifica si un contacto prefiere WhatsApp."""
    contact = load_contact(contact_id)
    return contact.get("canal_preferido") == "whatsapp" if contact else False


def _contact_prefers_whatsapp_by_phone(phone: str) -> bool:
    """Verifica si un contacto (por teléfono) prefiere WhatsApp."""
    contact_id, _ = identify_by_phone(phone)
    if not contact_id:
        return False
    return _contact_prefers_whatsapp(contact_id)


def _convert_markdown_to_whatsapp(text: str) -> str:
    """Convierte markdown de LLM a formato WhatsApp."""
    # WhatsApp usa *bold* (no **bold**), _italic_ (no *italic*)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)  # **bold** → *bold*
    return text


def _load_reminder_config() -> dict:
    """Carga la configuración de recordatorios."""
    config_path = os.path.join(DATA_DIR, "config", "recordatorios.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"activo": False}


def _load_sent_reminders() -> dict:
    """Carga el registro de recordatorios ya enviados."""
    filepath = os.path.join(DATA_DIR, "config", "recordatorios-enviados.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_sent_reminder(reminder_key: str) -> None:
    """Registra que un recordatorio fue enviado."""
    filepath = os.path.join(DATA_DIR, "config", "recordatorios-enviados.json")
    sent = _load_sent_reminders()
    sent[reminder_key] = datetime.now().isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sent, f, ensure_ascii=False, indent=2)


def _parse_flyer_moment(flyer_moment: str) -> list[int]:
    """Parsea el campo flyer_moment. Ej: '-60,-30,-7 dagen' -> [60, 30, 7]."""
    if not flyer_moment or flyer_moment.lower() == "x":
        return []
    numbers = re.findall(r'(\d+)', flyer_moment)
    return [int(n) for n in numbers]
