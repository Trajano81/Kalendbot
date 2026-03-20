"""
KalendBot Agent — Agente conversacional LangChain para gestión de calendario NV Mexico.
Usa langchain.agents.create_agent (LangChain 1.2+) con MemorySaver por contacto.
"""
import os
import json
import time
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from openai import RateLimitError

from src.tools import ALL_TOOLS

load_dotenv()
logger = logging.getLogger("kalendbot.agent")

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")

# LLM
llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.1,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

# Checkpointer para persistir memoria de conversación
checkpointer = MemorySaver()

# System prompt
SYSTEM_PROMPT = """Eres KalendBot, el asistente de calendario de NV Mexico (Asociación Neerlandesa en México).

Tu rol principal es coordinar con proveedores y contactos para confirmar fechas de eventos del calendario anual.

REGLAS DE COMPORTAMIENTO:
1. Siempre propón una fecha basada en el calendario del año anterior
2. Antes de proponer una fecha, usa ConflictDetector para verificar feriados y conflictos
3. Al confirmar una fecha, usa DateLocker para bloquearla inmediatamente
4. Publica updates de estado en el grupo SOLO con GroupNotifier
5. Adapta tu tono según el perfil del contacto (formal para Embajada, casual para organizadores)
6. Si hay conflicto de fechas, ofrece alternativas antes de escalar
7. NUNCA decidas disputas de fechas por tu cuenta — escala al director
8. Para eventos delegados (contact post zelf), solo haz check-in pasivo
9. Para proveedores críticos (Holland Wafels, Koen), usa flujo VIP con propuesta anual completa

FLUJO DE NEGOCIACIÓN:
- Fase A: Primero cerrar eventos pendientes de 2026
- Fase B: Luego socializar y negociar calendario 2027

HERRAMIENTAS DISPONIBLES:
- CalendarManager: Consultar y actualizar calendario (list_all, get_event, list_by_status, list_by_contact, list_pending, list_upcoming, update_status)
- ProviderManager: Info de organizaciones/partners (buscar por ID)
- ContactManager: Info de personas de contacto. Usa 'search:nombre' para buscar por nombre parcial
- DateLocker: Bloquear/desbloquear fechas
- ConflictDetector: Analizar conflictos de una fecha
- GroupNotifier: Publicar en chat grupal
- FlyerManager: Gestionar flujo de flyers
- RulesEngine: Consultar reglas de negocio

REGLAS DE BÚSQUEDA:
1. PERSONAS: Cuando mencionen a alguien por nombre (ej: "Koen", "Mirjam"), usa ContactManager con 'search:nombre' PRIMERO. No busques personas en ProviderManager — los proveedores son organizaciones, no personas.
2. PROVEEDOR DE UN EVENTO: Primero usa CalendarManager(get_event) para obtener el 'partner_id' del evento, luego usa ProviderManager con ese ID para obtener los detalles del proveedor.
3. NUNCA adivines o listes proveedores al azar — siempre consulta los datos primero.

ESTADOS DE EVENTOS:
- "pendiente" = el evento AÚN NO ha sido confirmado (la fecha puede cambiar)
- "confirmado" = la fecha está cerrada y confirmada
- "cancelado" = el evento fue cancelado
- Cuando cambies un estado con update_status, CONFIRMA al usuario el cambio realizado (ej: "Koningsdag actualizado de pendiente a confirmado")

Responde siempre en español. Sé conciso y profesional pero amigable."""

# Crear agente (compilado una sola vez, el thread_id diferencia contactos)
agent = create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


def _identify_contact_by_phone(phone: str) -> str | None:
    """Busca un contacto por su número de teléfono."""
    contacts_dir = os.path.join(DATA_DIR, "contactos")
    if not os.path.exists(contacts_dir):
        return None

    # Normalizar: quitar +, espacios, guiones
    normalized = phone.replace("+", "").replace(" ", "").replace("-", "")

    for filename in os.listdir(contacts_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(contacts_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            contact = json.load(f)
        contact_phone = contact.get("telefono", "").replace("+", "").replace(" ", "").replace("-", "")
        if contact_phone and (contact_phone in normalized or normalized in contact_phone):
            return contact["id"]
    return None


def _check_faq(message: str) -> str | None:
    """Busca si el mensaje coincide con una FAQ predefinida. Retorna respuesta o None."""
    faq_path = os.path.join(DATA_DIR, "config", "faq.json")
    if not os.path.exists(faq_path):
        return None
    try:
        with open(faq_path, "r", encoding="utf-8") as f:
            faq_data = json.load(f)
        msg_lower = message.lower().strip()
        for faq in faq_data.get("faqs", []):
            for keyword in faq.get("keywords", []):
                if keyword in msg_lower:
                    return faq["respuesta"]
    except Exception:
        pass
    return None


def handle_message(phone: str, message: str, contact_id: str | None = None) -> str:
    """
    Punto de entrada principal.
    Recibe un mensaje y retorna la respuesta del agente.
    Si contact_id viene (CLI), lo usa directo. Si no (WhatsApp), busca por teléfono.
    """
    # FAQ lookup — responde sin LLM si hay match
    faq_answer = _check_faq(message)
    if faq_answer:
        logger.info(f"FAQ match para: {message[:50]}...")
        return faq_answer

    if not contact_id:
        contact_id = _identify_contact_by_phone(phone)

    if not contact_id:
        logger.warning(f"Contacto no identificado para teléfono: {phone}")
        contact_id = f"unknown-{phone[-4:]}"

    logger.info(f"Mensaje de {contact_id}: {message[:50]}...")

    config = {
        "configurable": {"thread_id": contact_id},
        "recursion_limit": 25,  # Máx ~10 tool calls por mensaje
    }
    max_retries = 3

    for attempt in range(max_retries):
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
            )
            response = result["messages"][-1].content
            logger.info(f"Respuesta a {contact_id}: {response[:50]}...")
            return response
        except RateLimitError as e:
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Rate limit (intento {attempt + 1}/{max_retries}), esperando {wait}s...")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Error procesando mensaje de {contact_id}: {e}")
            return "Lo siento, tuve un problema procesando tu mensaje. Intentaré de nuevo."

    return "El servicio está saturado en este momento. Intentaré de nuevo en unos minutos."
