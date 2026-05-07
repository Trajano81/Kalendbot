"""
Utilidades compartidas para gestión de contactos.
Consolida funciones duplicadas entre telegram_bot.py, agent.py y whatsapp_bot.py.
"""
import os
import re
import json
import logging

logger = logging.getLogger("kalendbot.contacts")

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")


def normalize_phone(phone: str) -> str:
    """Normaliza un número de teléfono: quita +, espacios, guiones, paréntesis."""
    return phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def load_contact(contact_id: str) -> dict | None:
    """Carga un contacto por su ID. Retorna dict o None si no existe."""
    filepath = os.path.join(DATA_DIR, "contactos", f"{contact_id}.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def identify_by_phone(phone: str) -> tuple[str | None, str | None]:
    """
    Busca un contacto por teléfono.
    Retorna (contact_id, filepath) o (None, None).
    """
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    if not os.path.exists(contacts_dir):
        return None, None

    normalized = normalize_phone(phone)
    for filename in os.listdir(contacts_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(contacts_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                contact = json.load(f)
            contact_phone = normalize_phone(contact.get("telefono", ""))
            if contact_phone and (contact_phone in normalized or normalized in contact_phone):
                return contact["id"], filepath
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return None, None


def identify_by_telegram_id(telegram_id: int) -> str | None:
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


def get_admin_telegram_id() -> int | None:
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


def get_admin_phone() -> str | None:
    """Busca el teléfono del admin principal."""
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
            if contact.get("rol_kalendbot") == "admin" and contact.get("telefono"):
                return contact["telefono"]
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return None


def get_contact_telegram_id(contact_id: str) -> int | None:
    """Obtiene el telegram_id de un contacto por su ID."""
    contact = load_contact(contact_id)
    return contact.get("telegram_id") if contact else None


def get_contact_phone(contact_id: str) -> str | None:
    """Obtiene el teléfono de un contacto por su ID."""
    contact = load_contact(contact_id)
    return contact.get("telefono") if contact else None


def create_contact_json(nombre: str, telefono: str, telegram_id: int = None, canal: str = "telegram") -> str:
    """Crea el archivo JSON de un nuevo contacto con rol readonly. Retorna el contact_id."""
    contact_id = re.sub(r'[^a-z0-9]+', '-', nombre.lower().strip()).strip('-')
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    os.makedirs(contacts_dir, exist_ok=True)
    filepath = os.path.join(contacts_dir, f"{contact_id}.json")

    contact_data = {
        "id": contact_id,
        "nombre": nombre,
        "telefono": telefono,
        "perfil_comunicacion": "casual",
        "canal_preferido": canal,
        "rol": "Usuario",
        "rol_kalendbot": "readonly",
        "idioma": "es",
    }
    if telegram_id:
        contact_data["telegram_id"] = telegram_id

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(contact_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Contacto creado: {filepath}")
    return contact_id


def save_telegram_id(filepath: str, telegram_id: int) -> None:
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


SUPPORTED_LANGUAGES = {
    "es": "Español",
    "en": "English",
    "nl": "Nederlands",
}


def get_contact_language(contact_id: str) -> str:
    """Returns the preferred language code for a contact. Defaults to 'es'."""
    contact = load_contact(contact_id)
    if contact:
        return contact.get("idioma", "es")
    return "es"


def set_contact_language(contact_id: str, lang: str) -> bool:
    """Sets the preferred language for a contact. Returns True on success."""
    if lang not in SUPPORTED_LANGUAGES:
        return False
    filepath = os.path.join(DATA_DIR, "contactos", f"{contact_id}.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            contact = json.load(f)
        contact["idioma"] = lang
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(contact, f, ensure_ascii=False, indent=2)
        logger.info(f"Idioma de {contact_id} actualizado a {lang}")
        return True
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error actualizando idioma de {contact_id}: {e}")
        return False


def strip_markdown(text: str) -> str:
    """Elimina formato markdown para respuestas en texto plano."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*(.+?)\*', r'\1', text)        # *italic*
    return text
