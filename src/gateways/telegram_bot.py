"""
Gateway de Telegram para KalendBot.
Usa polling (sin necesidad de URL pública).
"""
import os
import re
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes

from src.agent import handle_message

logger = logging.getLogger("kalendbot.telegram")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")

# Estado temporal de usuarios en proceso de registro
# { telegram_id: { "phone": str, "step": "awaiting_name" } }
_pending_registrations: dict[int, dict] = {}


def _get_admin_telegram_id() -> int | None:
    """Busca el telegram_id del admin principal."""
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    if not os.path.exists(contacts_dir):
        return None
    for filename in os.listdir(contacts_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(contacts_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                contact = json.load(f)
            if contact.get("rol_kalendbot") == "admin" and contact.get("telegram_id"):
                return contact["telegram_id"]
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return None


def _identify_by_telegram_id(telegram_id: int) -> str | None:
    """Busca un contacto por su telegram_id."""
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    if not os.path.exists(contacts_dir):
        return None
    for filename in os.listdir(contacts_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(contacts_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                contact = json.load(f)
            if contact.get("telegram_id") == telegram_id:
                return contact["id"]
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return None


def _identify_by_phone(phone: str) -> tuple[str | None, str | None]:
    """Busca un contacto por teléfono. Retorna (contact_id, filepath) o (None, None)."""
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    if not os.path.exists(contacts_dir):
        return None, None
    normalized = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    for filename in os.listdir(contacts_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(contacts_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                contact = json.load(f)
            contact_phone = contact.get("telefono", "").replace("+", "").replace(" ", "").replace("-", "")
            if contact_phone and (contact_phone in normalized or normalized in contact_phone):
                return contact["id"], filepath
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return None, None


def _save_telegram_id(filepath: str, telegram_id: int) -> None:
    """Guarda el telegram_id en el JSON del contacto para futuras sesiones."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            contact = json.load(f)
        contact["telegram_id"] = telegram_id
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(contact, f, ensure_ascii=False, indent=2)
        logger.info(f"telegram_id {telegram_id} guardado en {filepath}")
    except Exception as e:
        logger.error(f"Error guardando telegram_id: {e}")


def _create_contact_json(nombre: str, telefono: str, telegram_id: int) -> str:
    """Crea el archivo JSON de un nuevo contacto con rol readonly. Retorna el contact_id."""
    # Generar ID: nombre en minúsculas, espacios a guiones
    contact_id = re.sub(r'[^a-z0-9]+', '-', nombre.lower().strip()).strip('-')
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    os.makedirs(contacts_dir, exist_ok=True)
    filepath = os.path.join(contacts_dir, f"{contact_id}.json")

    contact_data = {
        "id": contact_id,
        "nombre": nombre,
        "telefono": telefono,
        "perfil_comunicacion": "casual",
        "canal_preferido": "telegram",
        "rol": "Usuario",
        "rol_kalendbot": "readonly",
        "telegram_id": telegram_id,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(contact_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Contacto creado: {filepath}")
    return contact_id


def _strip_markdown(text: str) -> str:
    """Elimina formato markdown para respuestas en texto plano."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*(.+?)\*', r'\1', text)        # *italic*
    return text


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
        admin_tid = _get_admin_telegram_id()
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
    contact_id = _identify_by_telegram_id(user.id)
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
    response = _strip_markdown(response)

    await update.message.reply_text(response)
    logger.info(f"Respuesta enviada a {chat_id}: {response[:80]}")


async def _handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa cuando el usuario comparte su contacto (teléfono)."""
    shared = update.message.contact
    phone = shared.phone_number
    telegram_id = update.message.from_user.id

    logger.info(f"Contacto compartido: {phone} (telegram_id: {telegram_id})")

    contact_id, filepath = _identify_by_phone(phone)
    if contact_id:
        _save_telegram_id(filepath, telegram_id)
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
        contact_id = _create_contact_json(
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


async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde al comando /start. Si no está identificado, pide compartir contacto."""
    telegram_id = update.message.from_user.id
    contact_id = _identify_by_telegram_id(telegram_id)

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


def start_telegram_bot() -> None:
    """Inicia el bot de Telegram con polling."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        print("Error: TELEGRAM_BOT_TOKEN no está configurado en .env")
        return

    logger.info("Iniciando KalendBot en Telegram...")
    print("KalendBot Telegram iniciado. Ctrl+C para detener.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", _start_command))
    app.add_handler(CallbackQueryHandler(_handle_approval))
    app.add_handler(MessageHandler(filters.CONTACT, _handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    start_telegram_bot()
