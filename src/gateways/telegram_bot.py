"""
Gateway de Telegram para KalendBot.
Usa polling (sin necesidad de URL pública).
"""
import os
import re
import json
import uuid
import logging
from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

from src.config import settings
from src.agent import handle_message
from src.tools.calendar_manager import calendar_manager
from src.gateways.contacts import (
    identify_by_phone,
    identify_by_telegram_id,
    get_admin_telegram_id,
    get_contact_telegram_id,
    create_contact_json,
    save_telegram_id,
    load_contact,
    strip_markdown,
    get_contact_language,
    set_contact_language,
    SUPPORTED_LANGUAGES,
)

logger = logging.getLogger("kalendbot.telegram")

TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
DATA_DIR = settings.data_dir

# Coordinador principal — recibe copia de recordatorios de flyer
COORDINATOR_ID = "rocco-van-velzen"
CONTENT_MANAGER_ID = "hanna-van-rijsse"

# Estado temporal de usuarios en proceso de registro
# { telegram_id: { "phone": str, "step": "awaiting_name" } }
_pending_registrations: dict[int, dict] = {}


def _load_reminder_config() -> dict:
    """Carga la configuración de recordatorios."""
    config_path = os.path.join(DATA_DIR, "config", "recordatorios.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"No se pudo cargar {config_path}")
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
    """Registra que un recordatorio fue enviado para no duplicar."""
    filepath = os.path.join(DATA_DIR, "config", "recordatorios-enviados.json")
    sent = _load_sent_reminders()
    sent[reminder_key] = datetime.now().isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sent, f, ensure_ascii=False, indent=2)


def _parse_flyer_moment(flyer_moment: str) -> list[int]:
    """Parsea el campo flyer_moment del evento. Ej: '-60,-30,-7 dagen' -> [60, 30, 7]."""
    if not flyer_moment or flyer_moment.lower() == "x":
        return []
    # Extraer todos los números del string
    numbers = re.findall(r'(\d+)', flyer_moment)
    return [int(n) for n in numbers]


async def _send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job diario: revisa el calendario y envía 3 tipos de recordatorio."""
    config = _load_reminder_config()
    if not config.get("activo"):
        return

    sent = _load_sent_reminders()
    conf_config = config.get("confirmacion", {})
    flyer_config = config.get("flyer", {})
    grupo_config = config.get("grupo", {})
    group_chat_id = settings.telegram_group_chat_id

    # Cargar calendario
    year = datetime.now().year
    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    try:
        with open(cal_path, "r", encoding="utf-8") as f:
            calendario = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"No se pudo cargar calendario: {cal_path}")
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

        # --- TIPO 1: Recordatorio de confirmación (solo eventos pendientes) ---
        if evento.get("estado") == "pendiente":
            for dias in conf_config.get("dias", [30, 14, 7]):
                if dias_restantes != dias:
                    continue
                key = f"conf:{evt_id}:{dias}"
                if key in sent:
                    continue

                mensajes_conf = conf_config.get("mensajes", {})
                template = mensajes_conf.get(str(dias), "Recordatorio: '{nombre}' el {fecha} aún no está confirmado.")
                mensaje = template.format(nombre=evt_nombre, fecha=evt_fecha, dias=dias)

                contacto_ids = evento.get("contacto_ids", [])
                for cid in contacto_ids:
                    # Skip contactos que prefieren WhatsApp (los maneja whatsapp_bot)
                    cdata = load_contact(cid)
                    if cdata and cdata.get("canal_preferido") == "whatsapp":
                        continue
                    tid = get_contact_telegram_id(cid)
                    if tid:
                        try:
                            await context.bot.send_message(chat_id=tid, text=mensaje)
                        except Exception as e:
                            logger.error(f"Error enviando confirmación a {cid}: {e}")

                _save_sent_reminder(key)
                enviados_hoy += 1
                admin_resumen.append(f"Confirmación ({dias}d): {evt_nombre}")
                logger.info(f"Recordatorio confirmación: {evt_id} ({dias}d)")

        # --- TIPO 2: Recordatorio de flyer (basado en flyer_moment + custom) ---
        flyer_resp = evento.get("flyer_responsable", "")
        flyer_status = evento.get("flyer_status", "no_solicitado")

        # Skip: sin flyer, flyer aprobado, o responsable "ninguno"/"x"
        if flyer_resp.lower() not in ("nv", "proveedor"):
            pass  # no tiene flyer, skip
        elif flyer_status == "aprobado":
            pass  # flyer listo, no más recordatorios
        else:
            # Determinar si hoy toca recordatorio
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

            # Custom reminder dates (campo separado, no modifica flyer_moment)
            toca_custom = False
            custom_dates = evento.get("flyer_reminder_custom", [])
            for cd in custom_dates:
                try:
                    if date.fromisoformat(cd) == hoy:
                        toca_custom = True
                        break
                except ValueError:
                    continue

            if toca_standard or toca_custom:
                key_suffix = f"{dias_match}" if toca_standard else f"custom:{hoy.isoformat()}"
                key = f"flyer:{evt_id}:{key_suffix}"
                if key not in sent:
                    template = flyer_config.get("mensaje", "Recordatorio de flyer: '{nombre}' el {fecha}. Faltan {dias} días.")
                    mensaje = template.format(nombre=evt_nombre, fecha=evt_fecha, dias=dias_restantes)
                    if flyer_status == "rechazado":
                        mensaje += "\n⚠️ El flyer fue rechazado. Por favor envía la corrección."
                    mensaje += "\nSi no apruebas o actualizas el status del flyer, seguirás recibiendo recordatorios."

                    # Destinatarios según responsable
                    destinatarios = []
                    if flyer_resp == "proveedor":
                        destinatarios = list(evento.get("contacto_ids", []))
                    elif flyer_resp == "nv":
                        destinatarios = [CONTENT_MANAGER_ID]
                    # Siempre agregar coordinador (Rocco)
                    if COORDINATOR_ID not in destinatarios:
                        destinatarios.append(COORDINATOR_ID)

                    for cid in destinatarios:
                        # Skip contactos que prefieren WhatsApp
                        cdata = load_contact(cid)
                        if cdata and cdata.get("canal_preferido") == "whatsapp":
                            continue
                        tid = get_contact_telegram_id(cid)
                        if tid:
                            try:
                                await context.bot.send_message(chat_id=tid, text=mensaje)
                            except Exception as e:
                                logger.error(f"Error enviando flyer reminder a {cid}: {e}")

                    _save_sent_reminder(key)
                    enviados_hoy += 1
                    admin_resumen.append(f"Flyer ({dias_restantes}d): {evt_nombre}")
                    logger.info(f"Recordatorio flyer: {evt_id} ({key_suffix}) → {destinatarios}")

        # --- TIPO 3: Recordatorio grupal ---
        if group_chat_id:
            for dias in grupo_config.get("dias", [14, 7, 1]):
                if dias_restantes != dias:
                    continue
                key = f"grupo:{evt_id}:{dias}"
                if key in sent:
                    continue

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
                    await context.bot.send_message(chat_id=group_chat_id, text=mensaje)
                except Exception as e:
                    logger.error(f"Error enviando recordatorio grupal: {e}")

                _save_sent_reminder(key)
                enviados_hoy += 1
                admin_resumen.append(f"Grupo ({dias}d): {evt_nombre}")
                logger.info(f"Recordatorio grupo: {evt_id} ({dias}d)")

    # Resumen diario al admin
    if admin_resumen and config.get("notificar_admin"):
        admin_tid = get_admin_telegram_id()
        if admin_tid:
            resumen = "Resumen de recordatorios de hoy:\n\n" + "\n".join(f"- {r}" for r in admin_resumen)
            try:
                await context.bot.send_message(chat_id=admin_tid, text=resumen)
            except Exception as e:
                logger.error(f"Error notificando admin resumen: {e}")

    if enviados_hoy > 0:
        logger.info(f"Total recordatorios enviados hoy: {enviados_hoy}")
    else:
        logger.info("Sin recordatorios pendientes para hoy")


async def _handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa mensajes de texto entrantes."""
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    chat_id = str(update.message.chat_id)
    text = update.message.text.strip()

    if not text:
        return

    # Mensajes de grupo: solo responder si el bot fue mencionado
    if update.message.chat.type in ("group", "supergroup"):
        await _handle_group_text(update, context, text)
        return

    logger.info(f"Mensaje de {user.first_name} ({chat_id}): {text[:80]}")

    # Si el usuario está en proceso de registro, capturar su nombre
    if user.id in _pending_registrations and _pending_registrations[user.id]["step"] == "awaiting_name":
        reg = _pending_registrations[user.id]
        reg["nombre"] = text
        reg["step"] = "awaiting_approval"

        await update.message.reply_text(
            f"Gracias, {text}. Tu solicitud de acceso ha sido enviada al administrador.\n"
            "Te notificaré cuando seas autorizado.",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Notificar al admin con botones Si/No
        admin_tid = get_admin_telegram_id()
        if admin_tid:
            username = f"@{user.username}" if user.username else "sin username"
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Aprobar", callback_data=f"approve:{user.id}"),
                    InlineKeyboardButton("Rechazar", callback_data=f"deny:{user.id}"),
                ]
            ])
            await context.bot.send_message(
                chat_id=admin_tid,
                text=(
                    f"Solicitud de acceso al bot:\n\n"
                    f"Nombre: {text}\n"
                    f"Username: {username}\n"
                    f"Teléfono: {reg['phone']}\n"
                    f"Telegram ID: {user.id}\n\n"
                    f"Rol asignado: readonly (solo lectura)"
                ),
                reply_markup=keyboard,
            )
        return

    # Identificar contacto por telegram_id
    contact_id = identify_by_telegram_id(user.id)
    if contact_id:
        logger.info(f"Contacto identificado: {contact_id}")
    else:
        logger.info(f"Contacto no identificado (telegram_id: {user.id})")
        keyboard = [[KeyboardButton("Compartir mi número", request_contact=True)]]
        await update.message.reply_text(
            "Hola! Soy KalendBot, el asistente de calendario de NV Mexico.\n\n"
            "Para poder ayudarte, primero necesito identificarte.\n\n"
            "Paso 1: Presiona el botón 'Compartir mi número' que aparece abajo.\n"
            "Paso 2: Telegram te pedirá confirmar. Acepta para compartir tu número.\n"
            "Paso 3: Una vez identificado, ya puedes escribirme normalmente.\n\n"
            "Si no ves el botón, escribe /start para activarlo.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        )
        return

    response = handle_message(phone=chat_id, message=text, contact_id=contact_id)
    response = strip_markdown(response)

    await update.message.reply_text(response)
    logger.info(f"Respuesta enviada a {chat_id}: {response[:80]}")


# ---------------------------------------------------------------------------
# Grupo: detección de trigger y manejo de mensajes
# ---------------------------------------------------------------------------

def _get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Retorna el username del bot (sin @)."""
    return (context.bot.username or "").lower()


def _extract_group_text(text: str, bot_username: str) -> str | None:
    """
    Extrae texto limpio de un mensaje de grupo si menciona al bot.
    Returns cleaned text or None if bot wasn't mentioned.
    """
    lower = text.lower()
    # @botname at the start: "@Kalend0001_bot cambiar fecha..."
    if bot_username and lower.startswith(f"@{bot_username}"):
        clean = text[len(bot_username) + 1:].strip()
        return clean if clean else None
    # @botname anywhere in the text
    if bot_username and f"@{bot_username}" in lower:
        clean = re.sub(rf'@{re.escape(bot_username)}\s*', '', text, flags=re.IGNORECASE).strip()
        return clean if clean else None
    return None


async def _handle_group_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Procesa mensajes de texto en grupo — solo responde si el bot fue mencionado."""
    bot_username = _get_bot_username(context)
    clean_text = _extract_group_text(text, bot_username)

    if clean_text is None:
        # Si es un reply a un mensaje del bot, procesarlo como dirigido al bot
        if (update.message.reply_to_message
                and update.message.reply_to_message.from_user
                and update.message.reply_to_message.from_user.id == context.bot.id):
            clean_text = text
        else:
            return  # No mencionaron al bot ni respondieron a su mensaje, ignorar

    await _process_group_message(update, context, clean_text)


async def _handle_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa /comandos en grupo — todo va al agente como texto libre."""
    if not update.message or not update.message.text:
        return
    if update.message.chat.type not in ("group", "supergroup"):
        return

    text = update.message.text.strip()
    # Strip the /command (and optional @botname suffix)
    # e.g., "/cambiar fecha..." or "/cambiar@Kalend0001_bot fecha..."
    clean = re.sub(r'^/\S*\s*', '', text).strip()
    # Also use the command itself as part of the message
    cmd_match = re.match(r'^/(\w+)', text)
    if cmd_match:
        cmd = cmd_match.group(1).split("@")[0]  # Remove @botname from command
        # Route to dedicated handler if one exists
        _direct = {
            "start": _start_command,
            "export_excel": _handle_export_excel, "exportar_excel": _handle_export_excel,
            "export_jpeg": _handle_export_jpeg, "exportar_jpeg": _handle_export_jpeg,
            "export_jpeg_codes": _handle_export_jpeg_codes, "exportar_codigos": _handle_export_jpeg_codes,
            "export_instructions": _handle_export_instructions, "exportar_instrucciones": _handle_export_instructions,
            "help": _handle_help, "ayuda": _handle_help,
            "ocultar": _handle_hide, "hide": _handle_hide, "verbergen": _handle_hide,
            "mostrar": _handle_show, "show": _handle_show, "tonen": _handle_show,
            "idioma": _handle_idioma, "language": _handle_idioma,
        }
        if cmd in _direct:
            return await _direct[cmd](update, context)
        clean = f"{cmd} {clean}".strip()

    if not clean:
        return

    await _process_group_message(update, context, clean)


# Verbos reconocidos como inicio de tarea (no necesitan prefijo "cambiar")
_KNOWN_VERBS = re.compile(
    r'^(cambiar?|change|ocultar|verbergen|hide|mostrar|tonen|show|'
    r'estado|status|buscar|search|zoek|deshacer|undo|evento|event|'
    r'pendientes?|pending|proximos?|próximos?|upcoming|volgende)\b',
    re.IGNORECASE
)


def _split_multi_task(text: str) -> list[str]:
    """Divide un mensaje con múltiples tareas (separadas por *. o -) en tareas individuales."""
    # Solo dividir si empieza con un verbo conocido
    if not _KNOWN_VERBS.match(text):
        return [text]

    lines = text.split("\n")
    tasks = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Nueva tarea si empieza con bullet: *. / * / - / – / • / 1. / 2. etc.
        if re.match(r'^(\*\.?\s+|[-–•]\s+|\d+[.)]\s+)', stripped) and current:
            tasks.append("\n".join(current))
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        tasks.append("\n".join(current))

    # Limpiar prefijos de bullet y asegurar contexto
    cleaned = []
    for task in tasks:
        task = re.sub(r'^(\*\.?\s*|[-–•]\s*|\d+[.)]\s*)', '', task).strip()
        # Solo agregar "cambiar" si no empieza con un verbo conocido
        if not _KNOWN_VERBS.match(task):
            task = f"cambiar {task}"
        cleaned.append(task)

    # Drop header-only first task (e.g. bare "cambiar" before bullets)
    if len(cleaned) > 2 and _KNOWN_VERBS.match(cleaned[0].strip()) and not _KNOWN_VERBS.sub('', cleaned[0].strip()):
        cleaned = cleaned[1:]

    return cleaned if len(cleaned) > 1 else [text]


async def _process_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Procesa un mensaje de grupo dirigido al bot."""
    user = update.message.from_user
    telegram_id = user.id

    contact_id = identify_by_telegram_id(telegram_id)
    if not contact_id:
        await update.message.reply_text(
            "Ik ken je nog niet. Stuur mij een privébericht om je te registreren.",
            reply_to_message_id=update.message.message_id,
        )
        return

    logger.info(f"Grupo trigger de {contact_id}: {text[:80]}")

    # Pre-procesador: dividir mensajes multi-tarea en tareas individuales
    tasks = _split_multi_task(text)

    if len(tasks) > 1:
        logger.info(f"Multi-tarea detectado: {len(tasks)} tareas para {contact_id}")
        responses = []
        for i, task in enumerate(tasks, 1):
            logger.info(f"  Tarea {i}/{len(tasks)}: {task[:60]}")
            batch_thread = f"{contact_id}-batch-{uuid.uuid4().hex[:8]}"
            message = f"[Grupo] [BATCH: aplica cambios directo con batch_confirm, NO uses batch_preview ni GroupNotifier] {task}"
            resp = handle_message(phone=str(telegram_id), message=message, contact_id=contact_id, thread_id=batch_thread)
            responses.append(f"{i}. {strip_markdown(resp)}")

        combined = "\n\n".join(responses)
        if len(combined) > 4000:
            combined = combined[:4000] + "\n\n... (respuesta truncada)"

        await update.message.reply_text(
            combined,
            reply_to_message_id=update.message.message_id,
        )
        logger.info(f"Grupo multi-respuesta a {contact_id}: {len(tasks)} tareas procesadas")
    else:
        message = f"[Grupo] [NO uses GroupNotifier, solo responde con texto. Si es un cambio, aplica directo con batch_confirm sin batch_preview] {text}"
        response = handle_message(phone=str(telegram_id), message=message, contact_id=contact_id)
        response = strip_markdown(response)

        await update.message.reply_text(
            response,
            reply_to_message_id=update.message.message_id,
        )
        logger.info(f"Grupo respuesta a {contact_id}: {response[:80]}")


async def _handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa cuando el usuario comparte su contacto (teléfono)."""
    shared = update.message.contact
    phone = shared.phone_number
    telegram_id = update.message.from_user.id

    logger.info(f"Contacto compartido: {phone} (telegram_id: {telegram_id})")

    contact_id, filepath = identify_by_phone(phone)
    if contact_id:
        save_telegram_id(filepath, telegram_id)
        await update.message.reply_text(
            f"Identificado como: {contact_id}. Ya puedes escribirme normalmente.",
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.info(f"Vinculado: telegram_id {telegram_id} -> {contact_id}")
    else:
        # Iniciar flujo de registro: pedir nombre completo
        _pending_registrations[telegram_id] = {
            "phone": phone,
            "step": "awaiting_name",
        }
        await update.message.reply_text(
            "Tu número no está registrado en el sistema.\n\n"
            "Para solicitar acceso, escríbeme tu nombre completo (nombre y apellido).",
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.warning(f"Teléfono {phone} no encontrado — pidiendo nombre para registro")


async def _handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa la respuesta del admin (aprobar/rechazar usuario)."""
    query = update.callback_query
    await query.answer()

    action, tid_str = query.data.split(":")
    telegram_id = int(tid_str)

    reg = _pending_registrations.get(telegram_id)
    if not reg:
        await query.edit_message_text("Esta solicitud ya fue procesada o expiró.")
        return

    if action == "approve":
        contact_id = create_contact_json(
            nombre=reg["nombre"],
            telefono=reg["phone"],
            telegram_id=telegram_id,
        )
        del _pending_registrations[telegram_id]

        await query.edit_message_text(
            f"{query.message.text}\n\n"
            f"APROBADO. Contacto creado: {contact_id} (readonly)"
        )
        # Notificar al usuario
        await context.bot.send_message(
            chat_id=telegram_id,
            text=(
                f"Tu acceso ha sido aprobado! Bienvenido a KalendBot.\n"
                f"Ya puedes escribirme para consultar sobre eventos y calendario."
            ),
        )
        logger.info(f"Usuario aprobado: {contact_id} (telegram_id: {telegram_id})")

    elif action == "deny":
        del _pending_registrations[telegram_id]

        await query.edit_message_text(
            f"{query.message.text}\n\n"
            f"RECHAZADO."
        )
        # Notificar al usuario
        await context.bot.send_message(
            chat_id=telegram_id,
            text="Tu solicitud de acceso no fue aprobada. Contacta al administrador si crees que es un error.",
        )
        logger.info(f"Usuario rechazado: telegram_id {telegram_id}")


async def _handle_new_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detecta cuando el bot es agregado a un grupo y guarda el chat_id."""
    if not update.my_chat_member:
        return

    new_status = update.my_chat_member.new_chat_member.status
    chat = update.my_chat_member.chat

    if new_status in ("member", "administrator") and chat.type in ("group", "supergroup"):
        group_id = str(chat.id)
        group_title = chat.title or "Sin nombre"
        logger.info(f"Bot agregado al grupo: {group_title} (chat_id: {group_id})")

        # Guardar en .env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                env_content = f.read()

            if "TELEGRAM_GROUP_CHAT_ID=" in env_content:
                lines = env_content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("TELEGRAM_GROUP_CHAT_ID="):
                        lines[i] = f"TELEGRAM_GROUP_CHAT_ID={group_id}"
                env_content = "\n".join(lines)
            else:
                env_content += f"\nTELEGRAM_GROUP_CHAT_ID={group_id}\n"

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            logger.info(f"TELEGRAM_GROUP_CHAT_ID={group_id} guardado en .env")

            # Actualizar variable de entorno en runtime
            os.environ["TELEGRAM_GROUP_CHAT_ID"] = group_id
        except Exception as e:
            logger.error(f"Error guardando group chat_id: {e}")

        # Notificar al admin
        admin_tid = get_admin_telegram_id()
        logger.info(f"Admin telegram_id encontrado: {admin_tid}")
        if admin_tid:
            try:
                result = await context.bot.send_message(
                    chat_id=admin_tid,
                    text=f"Bot agregado al grupo: {group_title}\nChat ID: {group_id}\nRecordatorios grupales activados.",
                )
                logger.info(f"Admin notificado sobre grupo: {group_title} (msg_id: {result.message_id}, chat_id: {result.chat.id})")
            except Exception as e:
                logger.error(f"Error notificando al admin sobre grupo: {e}")
        else:
            logger.warning("No se encontró admin para notificar sobre grupo")


async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start. Si no está identificado, pide compartir contacto."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)

    if contact_id:
        await update.message.reply_text(
            f"Hola de nuevo. Identificado como: {contact_id}.\n"
            "Escríbeme lo que necesites sobre eventos, contactos o proveedores."
        )
    else:
        keyboard = [[KeyboardButton("Compartir mi número", request_contact=True)]]
        await update.message.reply_text(
            "Hola! Soy KalendBot, el asistente de calendario de NV Mexico.\n\n"
            "Para identificarte, comparte tu número con el botón de abajo.\n"
            "Si no estás registrado, se enviará una solicitud al administrador.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        )


async def _handle_export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /export_excel — genera y envía el Excel del calendario sin consumir tokens."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)

    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    try:
        with open(os.path.join(DATA_DIR, "contactos", f"{contact_id}.json"), "r", encoding="utf-8") as f:
            contact_data = json.load(f)
        rol = contact_data.get("rol_kalendbot", "readonly")
    except (FileNotFoundError, json.JSONDecodeError):
        rol = "readonly"

    if rol == "readonly":
        await update.message.reply_text("No tienes permisos para exportar el calendario.")
        return

    await update.message.reply_text("Generando Excel del calendario...")

    try:
        from src.tools.calendar_exporter import export_calendar
        output_path = export_calendar(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            await update.message.reply_text(f"Error: {output_path}")
            return

        with open(output_path, "rb") as doc:
            await update.message.reply_document(
                document=doc,
                filename=os.path.basename(output_path),
                caption="Calendario NV Mexico 2026 actualizado",
            )
    except Exception as e:
        logger.error(f"Error exportando calendario: {e}")
        await update.message.reply_text(f"Error generando el archivo: {e}")


async def _handle_export_jpeg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /export_jpeg — genera y envía imagen JPEG del calendario."""
    # Route "/export_jpeg codes" to the codes handler
    if context.args and context.args[0].lower() == "codes":
        return await _handle_export_jpeg_codes(update, context)

    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)

    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    try:
        with open(os.path.join(DATA_DIR, "contactos", f"{contact_id}.json"), "r", encoding="utf-8") as f:
            contact_data = json.load(f)
        rol = contact_data.get("rol_kalendbot", "readonly")
    except (FileNotFoundError, json.JSONDecodeError):
        rol = "readonly"

    if rol == "readonly":
        await update.message.reply_text("No tienes permisos para exportar el calendario.")
        return

    await update.message.reply_text("Generando imagen del calendario...")

    try:
        from src.tools.calendar_exporter import export_calendar_as_jpeg
        output_path = export_calendar_as_jpeg(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            await update.message.reply_text(f"Error: {output_path}")
            return

        with open(output_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="Jaarplanning NV Mexico 2026",
            )
    except Exception as e:
        logger.error(f"Error exportando JPEG: {e}")
        await update.message.reply_text(f"Error generando la imagen: {e}")


async def _handle_export_jpeg_codes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /export_jpeg_codes — genera JPEG compacto con códigos de actividad."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)

    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    try:
        with open(os.path.join(DATA_DIR, "contactos", f"{contact_id}.json"), "r", encoding="utf-8") as f:
            contact_data = json.load(f)
        rol = contact_data.get("rol_kalendbot", "readonly")
    except (FileNotFoundError, json.JSONDecodeError):
        rol = "readonly"

    if rol == "readonly":
        await update.message.reply_text("No tienes permisos para exportar el calendario.")
        return

    await update.message.reply_text("Generando imagen de códigos...")

    try:
        from src.tools.calendar_exporter import export_calendar_as_jpeg_codes
        output_path = export_calendar_as_jpeg_codes(year=2026)

        if output_path.startswith("Error") or output_path.startswith("No hay"):
            await update.message.reply_text(f"Error: {output_path}")
            return

        with open(output_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="Códigos de actividades — NV Mexico 2026",
            )
    except Exception as e:
        logger.error(f"Error exportando JPEG codes: {e}")
        await update.message.reply_text(f"Error generando la imagen: {e}")


async def _handle_hide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /ocultar — ocultar evento del export sin usar LLM."""
    await _toggle_show_export(update, show=False)


async def _handle_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /mostrar — mostrar evento en el export sin usar LLM."""
    await _toggle_show_export(update, show=True)


def _build_event_list() -> list[dict]:
    """Returns a numbered list of all events with id, name, date, and show_in_export status."""
    result = calendar_manager(action="list_all")
    events = []
    for line in result.strip().split("\n"):
        if not line.strip():
            continue
        # Parse "id: nombre — fecha [estado]" or "[RECURRENTE] id: nombre — ..."
        match = re.match(r'^(?:\[.*?\]\s*)?(\S+):\s*(.+?)\s*—\s*(.+)$', line.strip())
        if match:
            events.append({"id": match.group(1), "nombre": match.group(2), "extra": match.group(3)})
    return events


async def _toggle_show_export(update: Update, show: bool) -> None:
    """Busca evento por nombre o numero y cambia show_in_export directamente."""
    user = update.message.from_user
    contact_id = identify_by_telegram_id(user.id)
    if not contact_id:
        await update.message.reply_text("No estas identificado. Usa /start primero.")
        return

    text = update.message.text.strip()
    # Extract search query: strip /command[@botname]
    query = re.sub(r'^/\S*\s*', '', text).strip()
    action = "ocultar" if not show else "mostrar"

    events = _build_event_list()

    # No args: show numbered list
    if not query:
        lines = []
        for i, evt in enumerate(events, 1):
            lines.append(f"{i}. {evt['nombre']} ({evt['id']})")
        await update.message.reply_text(
            f"Eventos disponibles:\n\n" + "\n".join(lines) + f"\n\nUso: /{action} <numero o nombre>",
            reply_to_message_id=update.message.message_id,
        )
        return

    # If query is a number, use it as index
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(events):
            event_id = events[idx]["id"]
            action_word = "Oculto" if not show else "Visible"
            result = calendar_manager(action="update_show_export", event_id=event_id, show_in_export=show)
            await update.message.reply_text(
                f"{action_word}: {result}",
                reply_to_message_id=update.message.message_id,
            )
            logger.info(f"{action} evento #{query} por {contact_id}: {result}")
            return
        else:
            await update.message.reply_text(f"Numero {query} fuera de rango (1-{len(events)}).")
            return

    # Search by name
    search_result = calendar_manager(action="search_event", event_id=query)
    if "No se encontraron" in search_result:
        await update.message.reply_text(f"No encontre eventos con '{query}'.")
        return

    lines = [l.strip() for l in search_result.strip().split("\n") if l.strip()]
    if len(lines) > 1:
        await update.message.reply_text(
            f"Encontre {len(lines)} eventos. Se mas especifico:\n\n" + search_result,
            reply_to_message_id=update.message.message_id,
        )
        return

    # Single match
    event_id = lines[0].split(":")[0].strip()
    action_word = "Oculto" if not show else "Visible"
    result = calendar_manager(action="update_show_export", event_id=event_id, show_in_export=show)
    await update.message.reply_text(
        f"{action_word}: {result}",
        reply_to_message_id=update.message.message_id,
    )
    logger.info(f"{action} evento por {contact_id}: {result}")


_HELP_TEXT = {
    "es": (
        "Comandos disponibles:\n\n"
        "Calendario:\n"
        "/cambiar — Editar campos de eventos\n"
        "/estado — Cambiar estado de un evento\n"
        "/buscar — Buscar eventos por nombre\n"
        "/pendientes — Listar eventos pendientes\n"
        "/proximos — Listar proximos eventos\n"
        "/evento — Ver detalle de un evento\n"
        "/deshacer — Revertir ultimo cambio\n"
        "/ocultar — Ocultar evento del export\n"
        "/mostrar — Mostrar evento en el export\n\n"
        "Exportar:\n"
        "/exportar_excel — Exportar calendario a Excel\n"
        "/exportar_jpeg — Exportar como imagen\n"
        "/exportar_codigos — Ver codigos de actividades\n"
        "/exportar_instrucciones — Ver campos editables y permisos\n\n"
        "Configuracion:\n"
        "/idioma — Cambiar idioma del bot\n"
        "/ayuda — Mostrar esta ayuda\n\n"
        "En grupo, tambien puedes mencionarme seguido de tu pregunta.\n"
        "Tip: Usa bullet points (*.) para enviar multiples cambios en un solo mensaje."
    ),
    "en": (
        "Available commands:\n\n"
        "Calendar:\n"
        "/change — Edit event fields\n"
        "/status — Change event status\n"
        "/search — Search events by name\n"
        "/pending — List pending events\n"
        "/upcoming — View upcoming events\n"
        "/event — View event details\n"
        "/undo — Revert last change\n"
        "/hide — Hide event from export\n"
        "/show — Show event in export\n\n"
        "Export:\n"
        "/export_excel — Export calendar to Excel\n"
        "/export_jpeg — Export as image\n"
        "/export_jpeg_codes — View activity codes\n"
        "/export_instructions — View editable fields and permissions\n\n"
        "Settings:\n"
        "/language — Change bot language\n"
        "/help — Show this help\n\n"
        "In groups, you can also mention me followed by your question.\n"
        "Tip: Use bullet points (*.) to send multiple changes in a single message."
    ),
    "nl": (
        "Beschikbare commando's:\n\n"
        "Kalender:\n"
        "/change — Evenementvelden bewerken\n"
        "/status — Evenementstatus wijzigen\n"
        "/search — Evenementen zoeken op naam\n"
        "/pending — Openstaande evenementen\n"
        "/upcoming — Komende evenementen\n"
        "/event — Evenementdetails bekijken\n"
        "/undo — Laatste wijziging ongedaan maken\n"
        "/hide — Evenement verbergen uit export\n"
        "/show — Evenement tonen in export\n\n"
        "Exporteren:\n"
        "/export_excel — Kalender exporteren naar Excel\n"
        "/export_jpeg — Exporteren als afbeelding\n"
        "/export_jpeg_codes — Activiteitscodes bekijken\n"
        "/export_instructions — Bewerkbare velden en rechten\n\n"
        "Instellingen:\n"
        "/language — Taal wijzigen\n"
        "/help — Deze hulp tonen\n\n"
        "In groepen kun je me ook noemen gevolgd door je vraag.\n"
        "Tip: Gebruik bullet points (*.) om meerdere wijzigingen in een bericht te sturen."
    ),
}


async def _handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /help — lista comandos disponibles, in the user's language."""
    contact_id = identify_by_telegram_id(update.message.from_user.id)
    lang = get_contact_language(contact_id) if contact_id else "es"
    await update.message.reply_text(_HELP_TEXT.get(lang, _HELP_TEXT["es"]))


async def _set_user_commands(bot, telegram_id: int, lang: str, chat_id: int = None) -> None:
    """Sets the command menu for a specific user based on their language.
    Sets for DM (BotCommandScopeChat) and group (BotCommandScopeChatMember) if chat_id differs.
    """
    from telegram import BotCommandScopeChat, BotCommandScopeChatMember
    cmds = _COMMANDS_BY_LANG.get(lang, _COMMANDS_BY_LANG["es"])
    # Always set for DM — delete first to bust Telegram cache
    dm_scope = BotCommandScopeChat(chat_id=telegram_id)
    try:
        await bot.delete_my_commands(scope=dm_scope)
        await bot.set_my_commands(cmds, scope=dm_scope)
    except Exception as e:
        logger.warning(f"Could not set DM commands for {telegram_id}: {e}")
    # If called from a group, also set for that group
    if chat_id and chat_id != telegram_id:
        group_scope = BotCommandScopeChatMember(chat_id=chat_id, user_id=telegram_id)
        try:
            await bot.delete_my_commands(scope=group_scope)
            await bot.set_my_commands(cmds, scope=group_scope)
        except Exception as e:
            logger.warning(f"Could not set group commands for {telegram_id} in {chat_id}: {e}")


async def _handle_idioma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /idioma — muestra o cambia el idioma preferido del usuario."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)
    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    # If user passed a language code directly (e.g. /idioma en)
    if context.args and context.args[0].lower() in SUPPORTED_LANGUAGES:
        lang = context.args[0].lower()
        set_contact_language(contact_id, lang)
        await _set_user_commands(context.bot, telegram_id, lang, chat_id=update.message.chat.id)
        msg = {"es": "Idioma actualizado a", "en": "Language set to", "nl": "Taal ingesteld op"}
        await update.message.reply_text(f"{msg.get(lang, msg['es'])}: {SUPPORTED_LANGUAGES[lang]}")
        return

    # Show inline keyboard with language options
    current = get_contact_language(contact_id)
    buttons = []
    for code, name in SUPPORTED_LANGUAGES.items():
        label = f"{'> ' if code == current else ''}{name}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"lang:{code}"))
    keyboard = InlineKeyboardMarkup([buttons])
    await update.message.reply_text("Selecciona tu idioma / Select your language:", reply_markup=keyboard)


async def _handle_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline button callback for language selection."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("lang:"):
        return
    lang = data.split(":")[1]
    if lang not in SUPPORTED_LANGUAGES:
        return

    telegram_id = query.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)
    if not contact_id:
        await query.edit_message_text("No estás identificado. Usa /start primero.")
        return

    set_contact_language(contact_id, lang)
    await _set_user_commands(context.bot, telegram_id, lang, chat_id=query.message.chat.id)
    msg = {"es": "Idioma actualizado a", "en": "Language set to", "nl": "Taal ingesteld op"}
    await query.edit_message_text(f"{msg.get(lang, msg['es'])}: {SUPPORTED_LANGUAGES[lang]}")


async def _handle_export_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /export_instructions — envía guía de campos editables y permisos."""
    from src.tools.rules_engine import _get_instrucciones
    try:
        instructions = _get_instrucciones()
        await update.message.reply_text(instructions)
    except Exception as e:
        logger.error(f"Error generando instrucciones: {e}")
        await update.message.reply_text(f"Error generando instrucciones: {e}")


_COMMANDS_BY_LANG = {
    "es": [
        BotCommand("cambiar", "Editar campos de eventos"),
        BotCommand("buscar", "Buscar eventos por nombre"),
        BotCommand("estado", "Cambiar estado de un evento"),
        BotCommand("pendientes", "Listar eventos pendientes"),
        BotCommand("proximos", "Ver proximos eventos"),
        BotCommand("ocultar", "Ocultar evento del export"),
        BotCommand("mostrar", "Mostrar evento en el export"),
        BotCommand("exportar_excel", "Exportar calendario a Excel"),
        BotCommand("exportar_jpeg", "Exportar como imagen"),
        BotCommand("exportar_codigos", "Ver codigos de actividades"),
        BotCommand("idioma", "Cambiar idioma"),
        BotCommand("ayuda", "Mostrar comandos disponibles"),
    ],
    "en": [
        BotCommand("change", "Edit event fields"),
        BotCommand("search", "Search events by name"),
        BotCommand("status", "Change event status"),
        BotCommand("pending", "List pending events"),
        BotCommand("upcoming", "View upcoming events"),
        BotCommand("hide", "Hide event from export"),
        BotCommand("show", "Show event in export"),
        BotCommand("export_excel", "Export calendar to Excel"),
        BotCommand("export_jpeg", "Export as image"),
        BotCommand("export_jpeg_codes", "View activity codes"),
        BotCommand("language", "Change language"),
        BotCommand("help", "Show available commands"),
    ],
    "nl": [
        BotCommand("change", "Evenementvelden bewerken"),
        BotCommand("search", "Evenementen zoeken op naam"),
        BotCommand("status", "Evenementstatus wijzigen"),
        BotCommand("pending", "Openstaande evenementen"),
        BotCommand("upcoming", "Komende evenementen"),
        BotCommand("hide", "Evenement verbergen uit export"),
        BotCommand("show", "Evenement tonen in export"),
        BotCommand("export_excel", "Kalender exporteren naar Excel"),
        BotCommand("export_jpeg", "Exporteren als afbeelding"),
        BotCommand("export_jpeg_codes", "Activiteitscodes bekijken"),
        BotCommand("language", "Taal wijzigen"),
        BotCommand("help", "Beschikbare commando's"),
    ],
}


async def _post_init(application: Application) -> None:
    """Register bot commands for the Telegram menu popup."""
    from telegram import BotCommandScopeDefault, BotCommandScopeAllGroupChats
    # Clear ALL old commands (every scope + every language override)
    for scope in (BotCommandScopeDefault(), BotCommandScopeAllGroupChats()):
        try:
            await application.bot.delete_my_commands(scope=scope)
        except Exception:
            pass
        for lc in ("es", "en", "nl"):
            try:
                await application.bot.delete_my_commands(scope=scope, language_code=lc)
            except Exception:
                pass
    # Set ONE command set (Spanish) for everyone, regardless of Telegram app language
    commands = _COMMANDS_BY_LANG["es"]
    await application.bot.set_my_commands(commands)
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    logger.info("Comandos del bot registrados en Telegram (es)")


async def _handle_dm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward unrecognized /commands in DMs to the agent."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.message.from_user

    contact_id = identify_by_telegram_id(user.id)
    if not contact_id:
        keyboard = [[KeyboardButton("Compartir mi numero", request_contact=True)]]
        await update.message.reply_text(
            "Para poder ayudarte, primero necesito identificarte.",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        )
        return

    # Strip /command prefix and prepend command name as text
    cmd_match = re.match(r'^/(\w+)(@\S+)?\s*(.*)', text, re.DOTALL)
    if cmd_match:
        cmd = cmd_match.group(1)
        # Route to dedicated handler if one exists
        _direct = {
            "start": _start_command,
            "export_excel": _handle_export_excel, "exportar_excel": _handle_export_excel,
            "export_jpeg": _handle_export_jpeg, "exportar_jpeg": _handle_export_jpeg,
            "export_jpeg_codes": _handle_export_jpeg_codes, "exportar_codigos": _handle_export_jpeg_codes,
            "export_instructions": _handle_export_instructions, "exportar_instrucciones": _handle_export_instructions,
            "help": _handle_help, "ayuda": _handle_help,
            "ocultar": _handle_hide, "hide": _handle_hide, "verbergen": _handle_hide,
            "mostrar": _handle_show, "show": _handle_show, "tonen": _handle_show,
            "idioma": _handle_idioma, "language": _handle_idioma,
        }
        if cmd in _direct:
            return await _direct[cmd](update, context)
        rest = cmd_match.group(3).strip()
        clean = f"{cmd} {rest}".strip()
    else:
        clean = text

    logger.info(f"DM comando de {contact_id}: {clean[:80]}")
    response = handle_message(phone=str(update.message.chat_id), message=clean, contact_id=contact_id)
    response = strip_markdown(response)
    await update.message.reply_text(response)


def start_telegram_bot() -> None:
    """Inicia el bot de Telegram con polling."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        print("Error: TELEGRAM_BOT_TOKEN no está configurado en .env")
        return

    logger.info("Iniciando KalendBot en Telegram...")
    print("KalendBot Telegram iniciado. Ctrl+C para detener.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(_post_init).build()
    app.add_handler(ChatMemberHandler(_handle_new_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", _start_command))
    app.add_handler(CommandHandler(["export_excel", "exportar_excel"], _handle_export_excel))
    app.add_handler(CommandHandler(["export_jpeg", "exportar_jpeg"], _handle_export_jpeg))
    app.add_handler(CommandHandler(["export_jpeg_codes", "exportar_codigos"], _handle_export_jpeg_codes))
    app.add_handler(CommandHandler(["export_instructions", "exportar_instrucciones"], _handle_export_instructions))
    app.add_handler(CommandHandler(["help", "ayuda"], _handle_help))
    app.add_handler(CommandHandler(["ocultar", "hide", "verbergen"], _handle_hide))
    app.add_handler(CommandHandler(["mostrar", "show", "tonen"], _handle_show))
    app.add_handler(CommandHandler(["idioma", "language"], _handle_idioma))
    app.add_handler(CallbackQueryHandler(_handle_lang_callback, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(_handle_approval))
    app.add_handler(MessageHandler(filters.CONTACT, _handle_contact))
    # Grupo: capturar /comandos como texto libre para el agente
    group_filter = filters.ChatType.GROUPS & filters.COMMAND
    app.add_handler(MessageHandler(group_filter, _handle_group_command))
    # DM: capturar /comandos no explícitos (cambiar, buscar, etc.)
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.COMMAND, _handle_dm_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text))

    # Programar recordatorios diarios
    reminder_config = _load_reminder_config()
    if reminder_config.get("activo") and app.job_queue is not None:
        tz_name = reminder_config.get("timezone", "America/Mexico_City")
        hora_str = reminder_config.get("hora_envio", "09:00")
        hora, minuto = map(int, hora_str.split(":"))
        tz = ZoneInfo(tz_name)
        app.job_queue.run_daily(
            _send_reminders,
            time=time(hour=hora, minute=minuto, tzinfo=tz),
            name="daily_reminders",
        )
        logger.info(f"Recordatorios programados: diario a las {hora_str} ({tz_name})")
    elif reminder_config.get("activo"):
        logger.warning("JobQueue no disponible. Instalar: pip install 'python-telegram-bot[job-queue]'")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    start_telegram_bot()
