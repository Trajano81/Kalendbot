"""
Gateway de Telegram para KalendBot.
Usa polling (sin necesidad de URL pública).
"""
import os
import re
import json
import logging
from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

from src.agent import handle_message
from src.gateways.contacts import (
    identify_by_phone,
    identify_by_telegram_id,
    get_admin_telegram_id,
    get_contact_telegram_id,
    create_contact_json,
    save_telegram_id,
    load_contact,
    strip_markdown,
)

logger = logging.getLogger("kalendbot.telegram")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")

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
    group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID", "")

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


def start_telegram_bot() -> None:
    """Inicia el bot de Telegram con polling."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        print("Error: TELEGRAM_BOT_TOKEN no está configurado en .env")
        return

    logger.info("Iniciando KalendBot en Telegram...")
    print("KalendBot Telegram iniciado. Ctrl+C para detener.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(ChatMemberHandler(_handle_new_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", _start_command))
    app.add_handler(CommandHandler("export_excel", _handle_export_excel))
    app.add_handler(CallbackQueryHandler(_handle_approval))
    app.add_handler(MessageHandler(filters.CONTACT, _handle_contact))
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
