"""
Telegram channel adapter for KalendBot.
Thin wrapper: wires Telegram handlers to shared command handlers in src/handlers/.
Uses polling (no public URL needed).
"""
import os
import re
import json
import uuid
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes

from src.config import settings
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
    get_contact_language,
    set_contact_language,
    SUPPORTED_LANGUAGES,
)

# Import shared handlers (this triggers command registration)
from src.handlers.registry import CommandContext, find_command, get_all_commands
import src.handlers.exports  # noqa: F401 — registers commands
import src.handlers.visibility  # noqa: F401
import src.handlers.help  # noqa: F401
import src.handlers.language  # noqa: F401
import src.handlers.status  # noqa: F401
import src.handlers.undo  # noqa: F401
import src.handlers.add_activity  # noqa: F401
from src.handlers.reminders import load_reminder_config, send_reminders

logger = logging.getLogger("kalendbot.telegram")

TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
DATA_DIR = settings.data_dir

# Temporary registration state
_pending_registrations: dict[int, dict] = {}


# ---------------------------------------------------------------------------
# Telegram-specific adapter for sending results from shared handlers
# ---------------------------------------------------------------------------

async def _send_command_result_telegram(update: Update, ctx: CommandContext):
    """Execute a shared command handler and send the result via Telegram."""
    cmd_def = find_command(ctx.text.split()[0] if ctx.text else "")
    if not cmd_def:
        return False

    result = await cmd_def.handler(ctx)

    if result.error:
        await update.message.reply_text(result.error)
    elif result.file_path:
        with open(result.file_path, "rb") as doc:
            await update.message.reply_document(
                document=doc,
                filename=os.path.basename(result.file_path),
                caption=result.text or "",
            )
    elif result.image_path:
        with open(result.image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=result.text or "")
    elif result.text:
        await update.message.reply_text(result.text)
    return True


def _make_ctx(contact_id: str | None, chat_id: str, text: str, lang: str = "es") -> CommandContext:
    """Create a CommandContext for Telegram."""
    return CommandContext(
        contact_id=contact_id,
        phone=chat_id,
        text=text,
        language=lang,
        channel="telegram",
    )


# ---------------------------------------------------------------------------
# Reminders — delegates to shared engine
# ---------------------------------------------------------------------------

async def _send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily job: delegates to shared reminder engine with Telegram-specific send functions."""
    async def send_text(recipient_id: str, message: str):
        await context.bot.send_message(chat_id=int(recipient_id), text=message)

    async def send_to_group(group_id: str, message: str):
        await context.bot.send_message(chat_id=group_id, text=message)

    await send_reminders(
        channel="telegram",
        send_text_fn=send_text,
        send_to_group_fn=send_to_group,
    )


# ---------------------------------------------------------------------------
# Text message handling
# ---------------------------------------------------------------------------

async def _handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming text messages."""
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    chat_id = str(update.message.chat_id)
    text = update.message.text.strip()

    if not text:
        return

    # Group messages: only respond if bot was mentioned
    if update.message.chat.type in ("group", "supergroup"):
        await _handle_group_text(update, context, text)
        return

    logger.info(f"Mensaje de {user.first_name} ({chat_id}): {text[:80]}")

    # Registration flow
    if user.id in _pending_registrations and _pending_registrations[user.id]["step"] == "awaiting_name":
        reg = _pending_registrations[user.id]
        reg["nombre"] = text
        reg["step"] = "awaiting_approval"

        await update.message.reply_text(
            f"Gracias, {text}. Tu solicitud de acceso ha sido enviada al administrador.\n"
            "Te notificaré cuando seas autorizado.",
            reply_markup=ReplyKeyboardRemove(),
        )

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

    # Identify contact
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
# Group message handling
# ---------------------------------------------------------------------------

def _get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    return (context.bot.username or "").lower()


def _extract_group_text(text: str, bot_username: str) -> str | None:
    """Extract clean text from a group message if the bot was mentioned."""
    lower = text.lower()
    if bot_username and lower.startswith(f"@{bot_username}"):
        clean = text[len(bot_username) + 1:].strip()
        return clean if clean else None
    if bot_username and f"@{bot_username}" in lower:
        clean = re.sub(rf'@{re.escape(bot_username)}\s*', '', text, flags=re.IGNORECASE).strip()
        return clean if clean else None
    return None


async def _handle_group_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    bot_username = _get_bot_username(context)
    clean_text = _extract_group_text(text, bot_username)

    if clean_text is None:
        if (update.message.reply_to_message
                and update.message.reply_to_message.from_user
                and update.message.reply_to_message.from_user.id == context.bot.id):
            clean_text = text
        else:
            return

    await _process_group_message(update, context, clean_text)


# Known verbs for multi-task detection
_KNOWN_VERBS = re.compile(
    r'^(cambiar?|change|ocultar|verbergen|hide|mostrar|tonen|show|'
    r'estado|status|buscar|search|zoek|deshacer|undo|evento|event|'
    r'agregar|add|toevoegen|'
    r'pendientes?|pending|proximos?|próximos?|upcoming|volgende)\b',
    re.IGNORECASE
)


def _split_multi_task(text: str) -> list[str]:
    """Split a message with multiple tasks into individual tasks."""
    if not _KNOWN_VERBS.match(text):
        return [text]

    lines = text.split("\n")
    tasks = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^(\*\.?\s+|[-–•]\s+|\d+[.)]\s+)', stripped) and current:
            tasks.append("\n".join(current))
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        tasks.append("\n".join(current))

    cleaned = []
    for task in tasks:
        task = re.sub(r'^(\*\.?\s*|[-–•]\s*|\d+[.)]\s*)', '', task).strip()
        if not _KNOWN_VERBS.match(task):
            task = f"cambiar {task}"
        cleaned.append(task)

    if len(cleaned) > 2 and _KNOWN_VERBS.match(cleaned[0].strip()) and not _KNOWN_VERBS.sub('', cleaned[0].strip()):
        cleaned = cleaned[1:]

    return cleaned if len(cleaned) > 1 else [text]


async def _process_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
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

        await update.message.reply_text(combined, reply_to_message_id=update.message.message_id)
    else:
        message = f"[Grupo] [BATCH: aplica cambios directo con batch_confirm, NO uses batch_preview ni GroupNotifier] {text}"
        response = handle_message(phone=str(telegram_id), message=message, contact_id=contact_id)
        response = strip_markdown(response)
        await update.message.reply_text(response, reply_to_message_id=update.message.message_id)


# ---------------------------------------------------------------------------
# Group command routing
# ---------------------------------------------------------------------------

async def _handle_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if update.message.chat.type not in ("group", "supergroup"):
        return

    text = update.message.text.strip()
    clean = re.sub(r'^/\S*\s*', '', text).strip()
    cmd_match = re.match(r'^/(\w+)', text)
    if cmd_match:
        cmd = cmd_match.group(1).split("@")[0]

        # Try shared handler first
        cmd_def = find_command(cmd)
        if cmd_def:
            contact_id = identify_by_telegram_id(update.message.from_user.id)
            lang = get_contact_language(contact_id) if contact_id else "es"
            ctx = _make_ctx(contact_id, str(update.message.chat_id), clean, lang)
            result = await cmd_def.handler(ctx)
            await _send_result(update, result)
            return

        # Telegram-only handlers
        _tg_only = {
            "start": _start_command,
            "idioma": _handle_idioma, "language": _handle_idioma,
        }
        if cmd in _tg_only:
            return await _tg_only[cmd](update, context)
        clean = f"{cmd} {clean}".strip()

    if not clean:
        return

    await _process_group_message(update, context, clean)


async def _send_result(update: Update, result) -> None:
    """Send a CommandResult via Telegram."""
    if result.error:
        await update.message.reply_text(result.error, reply_to_message_id=update.message.message_id)
    elif result.file_path:
        with open(result.file_path, "rb") as doc:
            await update.message.reply_document(
                document=doc, filename=os.path.basename(result.file_path),
                caption=result.text or "",
            )
    elif result.image_path:
        with open(result.image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=result.text or "")
    elif result.text:
        await update.message.reply_text(result.text, reply_to_message_id=update.message.message_id)


# ---------------------------------------------------------------------------
# Contact sharing / Registration
# ---------------------------------------------------------------------------

async def _handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    else:
        _pending_registrations[telegram_id] = {"phone": phone, "step": "awaiting_name"}
        await update.message.reply_text(
            "Tu número no está registrado en el sistema.\n\n"
            "Para solicitar acceso, escríbeme tu nombre completo (nombre y apellido).",
            reply_markup=ReplyKeyboardRemove(),
        )


async def _handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            nombre=reg["nombre"], telefono=reg["phone"], telegram_id=telegram_id,
        )
        del _pending_registrations[telegram_id]
        await query.edit_message_text(f"{query.message.text}\n\nAPROBADO. Contacto creado: {contact_id} (readonly)")
        await context.bot.send_message(
            chat_id=telegram_id,
            text="Tu acceso ha sido aprobado! Bienvenido a KalendBot.\nYa puedes escribirme para consultar sobre eventos y calendario.",
        )
    elif action == "deny":
        del _pending_registrations[telegram_id]
        await query.edit_message_text(f"{query.message.text}\n\nRECHAZADO.")
        await context.bot.send_message(
            chat_id=telegram_id,
            text="Tu solicitud de acceso no fue aprobada. Contacta al administrador si crees que es un error.",
        )


# ---------------------------------------------------------------------------
# New group detection
# ---------------------------------------------------------------------------

async def _handle_new_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.my_chat_member:
        return
    new_status = update.my_chat_member.new_chat_member.status
    chat = update.my_chat_member.chat

    if new_status in ("member", "administrator") and chat.type in ("group", "supergroup"):
        group_id = str(chat.id)
        group_title = chat.title or "Sin nombre"
        logger.info(f"Bot agregado al grupo: {group_title} (chat_id: {group_id})")

        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
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
            os.environ["TELEGRAM_GROUP_CHAT_ID"] = group_id
        except Exception as e:
            logger.error(f"Error guardando group chat_id: {e}")

        admin_tid = get_admin_telegram_id()
        if admin_tid:
            try:
                await context.bot.send_message(
                    chat_id=admin_tid,
                    text=f"Bot agregado al grupo: {group_title}\nChat ID: {group_id}\nRecordatorios grupales activados.",
                )
            except Exception as e:
                logger.error(f"Error notificando al admin sobre grupo: {e}")


# ---------------------------------------------------------------------------
# /start command
# ---------------------------------------------------------------------------

async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


# ---------------------------------------------------------------------------
# Shared command wrappers (Telegram-specific UI + shared handler)
# ---------------------------------------------------------------------------

async def _handle_shared_command(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd_name: str) -> None:
    """Generic wrapper: identify user, build context, run shared handler, send result."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)

    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    cmd_def = find_command(cmd_name)
    if not cmd_def:
        return

    # Extract args after the /command
    text = update.message.text.strip()
    args_text = re.sub(r'^/\S*\s*', '', text).strip()
    lang = get_contact_language(contact_id)
    ctx = _make_ctx(contact_id, str(update.message.chat_id), args_text, lang)

    result = await cmd_def.handler(ctx)

    # Send generating message for exports
    if cmd_name in ("export_excel", "export_jpeg", "export_jpeg_codes"):
        await update.message.reply_text("Generando...")

    await _send_result(update, result)


async def _handle_export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "export_excel")


async def _handle_export_jpeg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Route "/export_jpeg codes" to codes handler
    if context.args and context.args[0].lower() == "codes":
        return await _handle_export_jpeg_codes(update, context)
    await _handle_shared_command(update, context, "export_jpeg")


async def _handle_export_jpeg_codes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "export_jpeg_codes")


async def _handle_export_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "export_instructions")


async def _handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "help")


async def _handle_hide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "ocultar")


async def _handle_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "mostrar")


async def _handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_shared_command(update, context, "status")


async def _handle_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Undo: direct handler for bare /undo, falls through to agent when event name given."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)
    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    cmd_def = find_command("undo")
    if not cmd_def:
        return

    text = update.message.text.strip()
    args_text = re.sub(r'^/\S*\s*', '', text).strip()
    lang = get_contact_language(contact_id)
    ctx = _make_ctx(contact_id, str(update.message.chat_id), args_text, lang)

    result = await cmd_def.handler(ctx)
    # Empty result means user specified an event name; delegate to agent
    if result.text or result.error or result.file_path or result.image_path:
        await _send_result(update, result)
        return

    # Fall through to agent for targeted undo
    clean = f"deshacer {args_text}".strip()
    response = handle_message(phone=str(update.message.chat_id), message=clean, contact_id=contact_id)
    response = strip_markdown(response)
    await update.message.reply_text(response)


async def _handle_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add activity: always falls through to agent for guided flow."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)
    if not contact_id:
        await update.message.reply_text("No estas identificado. Usa /start primero.")
        return

    text = update.message.text.strip()
    args_text = re.sub(r'^/\S*\s*', '', text).strip()

    clean = f"agregar {args_text}".strip()
    response = handle_message(phone=str(update.message.chat_id), message=clean, contact_id=contact_id)
    response = strip_markdown(response)
    await update.message.reply_text(response)


# ---------------------------------------------------------------------------
# Telegram-only: /idioma with inline keyboard
# ---------------------------------------------------------------------------

async def _handle_idioma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Language command — uses shared handler for direct args, inline keyboard for selection."""
    telegram_id = update.message.from_user.id
    contact_id = identify_by_telegram_id(telegram_id)
    if not contact_id:
        await update.message.reply_text("No estás identificado. Usa /start primero.")
        return

    # Direct arg: /idioma en
    if context.args and context.args[0].lower() in SUPPORTED_LANGUAGES:
        lang = context.args[0].lower()
        set_contact_language(contact_id, lang)
        await _set_user_commands(context.bot, telegram_id, lang, chat_id=update.message.chat.id)
        msg = {"es": "Idioma actualizado a", "en": "Language set to", "nl": "Taal ingesteld op"}
        await update.message.reply_text(f"{msg.get(lang, msg['es'])}: {SUPPORTED_LANGUAGES[lang]}")
        return

    # Show inline keyboard
    current = get_contact_language(contact_id)
    buttons = []
    for code, name in SUPPORTED_LANGUAGES.items():
        label = f"{'> ' if code == current else ''}{name}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"lang:{code}"))
    keyboard = InlineKeyboardMarkup([buttons])
    await update.message.reply_text("Selecciona tu idioma / Select your language:", reply_markup=keyboard)


async def _handle_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


# ---------------------------------------------------------------------------
# Command menu per user
# ---------------------------------------------------------------------------

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
        BotCommand("agregar", "Agregar nueva actividad"),
        BotCommand("deshacer", "Revertir ultimo cambio"),
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
        BotCommand("add", "Add new activity"),
        BotCommand("undo", "Revert last change"),
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
        BotCommand("toevoegen", "Nieuwe activiteit toevoegen"),
        BotCommand("undo", "Laatste wijziging ongedaan maken"),
        BotCommand("language", "Taal wijzigen"),
        BotCommand("help", "Beschikbare commando's"),
    ],
}


async def _set_user_commands(bot, telegram_id: int, lang: str, chat_id: int = None) -> None:
    from telegram import BotCommandScopeChat, BotCommandScopeChatMember
    cmds = _COMMANDS_BY_LANG.get(lang, _COMMANDS_BY_LANG["es"])
    dm_scope = BotCommandScopeChat(chat_id=telegram_id)
    try:
        await bot.delete_my_commands(scope=dm_scope)
        await bot.set_my_commands(cmds, scope=dm_scope)
    except Exception as e:
        logger.warning(f"Could not set DM commands for {telegram_id}: {e}")
    if chat_id and chat_id != telegram_id:
        group_scope = BotCommandScopeChatMember(chat_id=chat_id, user_id=telegram_id)
        try:
            await bot.delete_my_commands(scope=group_scope)
            await bot.set_my_commands(cmds, scope=group_scope)
        except Exception as e:
            logger.warning(f"Could not set group commands for {telegram_id} in {chat_id}: {e}")


# ---------------------------------------------------------------------------
# DM command forwarding
# ---------------------------------------------------------------------------

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

    cmd_match = re.match(r'^/(\w+)(@\S+)?\s*(.*)', text, re.DOTALL)
    if cmd_match:
        cmd = cmd_match.group(1)

        # Try shared handler first
        cmd_def = find_command(cmd)
        if cmd_def:
            lang = get_contact_language(contact_id)
            args_text = cmd_match.group(3).strip()
            ctx = _make_ctx(contact_id, str(update.message.chat_id), args_text, lang)
            result = await cmd_def.handler(ctx)
            # Empty result means handler defers to agent (e.g. /undo with event name)
            if result.text or result.error or result.file_path or result.image_path:
                await _send_result(update, result)
                return

        # Telegram-only handlers
        _tg_only = {
            "start": _start_command,
            "idioma": _handle_idioma, "language": _handle_idioma,
        }
        if cmd in _tg_only:
            return await _tg_only[cmd](update, context)

        rest = cmd_match.group(3).strip()
        clean = f"{cmd} {rest}".strip()
    else:
        clean = text

    logger.info(f"DM comando de {contact_id}: {clean[:80]}")
    response = handle_message(phone=str(update.message.chat_id), message=clean, contact_id=contact_id)
    response = strip_markdown(response)
    await update.message.reply_text(response)


# ---------------------------------------------------------------------------
# Post-init: register Telegram command menu
# ---------------------------------------------------------------------------

async def _post_init(application: Application) -> None:
    from telegram import BotCommandScopeDefault, BotCommandScopeAllGroupChats
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
    commands = _COMMANDS_BY_LANG["es"]
    await application.bot.set_my_commands(commands)
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    logger.info("Comandos del bot registrados en Telegram (es)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def start_telegram_bot() -> None:
    """Start the Telegram bot with polling."""
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
    app.add_handler(CommandHandler(["status", "estado"], _handle_status))
    app.add_handler(CommandHandler(["undo", "deshacer", "ongedaan"], _handle_undo))
    app.add_handler(CommandHandler(["agregar", "add", "toevoegen"], _handle_agregar))
    app.add_handler(CommandHandler(["idioma", "language"], _handle_idioma))
    app.add_handler(CallbackQueryHandler(_handle_lang_callback, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(_handle_approval))
    app.add_handler(MessageHandler(filters.CONTACT, _handle_contact))
    group_filter = filters.ChatType.GROUPS & filters.COMMAND
    app.add_handler(MessageHandler(group_filter, _handle_group_command))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.COMMAND, _handle_dm_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_text))

    # Schedule daily reminders
    reminder_config = load_reminder_config()
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
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    start_telegram_bot()
