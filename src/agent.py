"""
KalendBot Agent — Agente conversacional LangChain para gestión de calendario NV Mexico.
Usa langchain.agents.create_agent (LangChain 1.2+) con MemorySaver por contacto.
"""
import os
import re
import json
import time
import logging
import traceback
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from openai import RateLimitError

from src.config import settings
from src.tracing import get_run_metadata
from src.tools import ALL_TOOLS
from src.gateways.contacts import identify_by_phone, get_contact_language

logger = logging.getLogger("kalendbot.agent")

DATA_DIR = settings.data_dir

# LLM
llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.1,
    openai_api_key=settings.openai_api_key,
)

# Checkpointer para persistir memoria de conversación
checkpointer = MemorySaver()

# System prompt
SYSTEM_PROMPT = """Eres KalendBot, el asistente de calendario de NV Mexico (Asociación Neerlandesa en México).

IMPORTANTE — IDIOMA: TODAS tus respuestas DEBEN ser en {lang_name}. No importa en qué idioma estén estas instrucciones internas, tú SIEMPRE respondes al usuario en {lang_name}.

Tu rol principal es coordinar con proveedores y contactos para confirmar fechas de eventos del calendario anual.

REGLAS DE COMPORTAMIENTO:
1. Siempre propón una fecha basada en el calendario del año anterior
2. Antes de proponer una fecha, usa ConflictDetector para verificar feriados y conflictos
3. Al confirmar una fecha, usa DateLocker para bloquearla inmediatamente
4. Publica updates de estado en el grupo SOLO con GroupNotifier
5. Si el mensaje incluye "[BATCH:", aplica cambios directamente con batch_confirm (sin batch_preview) y NO uses GroupNotifier. Solo responde con texto descriptivo del resultado. Si NO puedes interpretar la instrucción o el campo/evento no existe, responde SOLO con "No entendí: [instrucción original]". NUNCA inventes datos ni adivines campos
6. Adapta tu tono según el perfil del contacto (formal para Embajada, casual para organizadores)
6. Si hay conflicto de fechas, ofrece alternativas antes de escalar
7. NUNCA decidas disputas de fechas por tu cuenta — escala al director
8. Para eventos delegados (contact post zelf), solo haz check-in pasivo
9. Para proveedores críticos (Holland Wafels, Koen), usa flujo VIP con propuesta anual completa

FLUJO DE NEGOCIACIÓN:
- Fase A: Primero cerrar eventos pendientes de 2026
- Fase B: Luego socializar y negociar calendario 2027

HERRAMIENTAS DISPONIBLES:
- CalendarManager: Consultar y editar calendario. Acciones de consulta: list_all, get_event, search_event, list_by_status, list_by_contact, list_pending, list_upcoming. Acciones de estado: update_status, update_show_export. Edición de campos: batch_preview, batch_confirm, undo_last. Resolución de códigos: resolve_code
- ProviderManager: Info de organizaciones/partners (buscar por ID)
- ContactManager: Info de personas de contacto. Usa 'search:nombre' para buscar por nombre parcial
- DateLocker: Bloquear/desbloquear fechas
- ConflictDetector: Analizar conflictos de una fecha
- GroupNotifier: Publicar en chat grupal
- FlyerManager: Gestionar flujo de flyers (check_responsibility, get_status, request_flyer, approve, reject, set_reminder)
- RulesEngine: Consultar reglas de negocio (tiers, precedencia, restricciones, instrucciones)
- CalendarExporter: Exportar calendario a Excel (.xlsx). Filtros opcionales: año, estado, contacto

REGLAS DE BÚSQUEDA:
1. EVENTOS POR CÓDIGO (#N): Cuando el usuario use #N o "code N" o solo un número para referirse a un evento (ej: "#16", "code 16", "16"), llama CalendarManager(resolve_code, event_id="16") PRIMERO para obtener el event_id real. Los códigos corresponden al orden en el JPEG export (1=primer evento por fecha, R1=primer recurrente).
2. EVENTOS POR NOMBRE: Cuando el usuario mencione un evento por nombre (ej: "Pub Quiz", "Koningsdag"), usa CalendarManager(search_event, event_id="nombre") PRIMERO para encontrar el ID exacto. NUNCA uses el nombre del evento como event_id directamente — los IDs son slugs como "pub-quiz-recurrente", "koningsdag", etc.
3. EVENTOS RECURRENTES: Para editar una instancia específica de un evento recurrente (ej: "Pub Quiz del 5 de marzo"), usa el ID del evento recurrente + status=YYYY-MM-DD de la instancia.
4. PERSONAS: Cuando mencionen a alguien por nombre (ej: "Koen", "Mirjam"), usa ContactManager con 'search:nombre' PRIMERO. No busques personas en ProviderManager — los proveedores son organizaciones, no personas.
5. PROVEEDOR DE UN EVENTO: Primero usa CalendarManager(get_event) para obtener el 'partner_id' del evento, luego usa ProviderManager con ese ID para obtener los detalles del proveedor.
6. NUNCA adivines o listes proveedores al azar — siempre consulta los datos primero.

REGLAS DE FLYERS:
- Si un contacto quiere recordatorios de flyer en fechas específicas, usa FlyerManager(set_reminder) con las fechas ISO
- Los recordatorios estándar se basan en flyer_moment del evento y NO se modifican
- set_reminder agrega fechas ADICIONALES, no reemplaza las estándar
- Rocco (coordinador) recibe copia de todos los recordatorios de flyer automáticamente

ESTADOS DE EVENTOS:
- "pendiente" = el evento AÚN NO ha sido confirmado (la fecha puede cambiar)
- "confirmado" = la fecha está cerrada y confirmada
- "cancelado" = el evento fue cancelado
- Cuando cambies un estado con update_status, CONFIRMA al usuario el cambio realizado (ej: "Koningsdag actualizado de pendiente a confirmado")

EDICIÓN DE CAMPOS DE EVENTOS:
- Si el usuario solo menciona un evento sin especificar qué cambiar (ej: "/change #12" o "cambiar Koningsdag"), NO llames batch_preview. Pregúntale qué campo quiere modificar.
- Cuando el usuario pida cambios en un evento, construye un string de cambios: "campo1=valor1|campo2=valor2"
- Paso 1: Usa CalendarManager(search_event) para encontrar el event_id exacto si no lo conoces
- Paso 2: SIEMPRE llama CalendarManager(batch_preview, event_id=..., changes="campo=valor", role=..., contact_id=...) — muestra el resultado EXACTO de la herramienta al usuario
- Paso 3: Cuando el usuario confirme, llama CalendarManager(batch_confirm) con EXACTAMENTE los mismos parámetros (event_id, changes, role, contact_id)
- CRÍTICO: NUNCA simules o "actúes" el preview/confirm en texto — SIEMPRE usa las herramientas CalendarManager(batch_preview) y CalendarManager(batch_confirm). El cambio NO se aplica hasta que llames batch_confirm
- DESPUÉS de batch_confirm: SIEMPRE confirma explícitamente al usuario que el cambio fue aplicado. Ejemplo: "Listo, el cambio fue aplicado: [resumen del cambio]". NUNCA dejes al usuario sin saber si la acción se completó
- Si hay conflictos de fecha, sugiere alternativas ANTES de confirmar
- Informa que puede deshacer: "Si necesitas revertir, dime 'deshacer cambios en [evento]'"
- Para deshacer: CalendarManager(undo_last, event_id=...)
- Campos admin-only (tier_promocion, flyer_responsable, flyer_oleadas, flyer_moment, delegado): solo admin puede editarlos

RESTRICCIÓN DE FECHAS PASADAS:
- NO se puede cambiar la fecha de un evento a una fecha pasada, ni cambiar la fecha de un evento que ya ocurrió.
- Si eres admin, el sistema mostrará una advertencia (⚠️) pero permitirá continuar. Muestra esa advertencia claramente al usuario.
- Otros campos (nombre, venue, descripcion, etc.) SÍ se pueden editar en eventos pasados sin restricción.

ALIAS DE CAMPOS (el usuario puede usar estos nombres en cualquier idioma):
- activiteit/actividad/nombre → campo: nombre
- datum/fecha/date → campo: fecha
- locatie/ubicación/venue → campo: venue_nombre
- adres/dirección/address → campo: venue_direccion
- tijd/hora/time → campo: hora
- prijs/precio/price → campo: precio
- beschrijving/descripción/description → campo: descripcion
- detail/detalle → campo: detalle
- partner → campo: partner_nombre
- ocultar/verbergen/hide → usar CalendarManager(update_show_export, show_in_export=false)
- mostrar/tonen/show → usar CalendarManager(update_show_export, show_in_export=true)
- info/post/flyer/text → campo: detalle (texto informativo del evento)

COMANDOS DISPONIBLES (los mensajes con [COMANDO: /xxx] ya fueron pre-procesados):
- /cambiar (o /change): Editar campos de un evento. Ej: "/cambiar nombre del Qualifier a Zweden"
- /estado (o /status): Cambiar estado de un evento. Ej: "/estado Koningsdag confirmado"
- /buscar (o /search, /zoek): Buscar eventos. Ej: "/buscar Pub Quiz"
- /pendientes (o /pending): Listar eventos pendientes
- /proximos (o /upcoming, /volgende): Listar próximos eventos
- /deshacer (o /undo): Revertir último cambio. Ej: "/deshacer cambios en Koningsdag"
- /evento (o /event): Ver detalle de un evento. Ej: "/evento Koningsdag"
- /ocultar (o /hide, /verbergen): Ocultar evento del export. Ej: "/ocultar Buitendag"
- /mostrar (o /show, /tonen): Mostrar evento en el export. Ej: "/mostrar Buitendag"
Cuando recibas un mensaje con [COMANDO: /xxx], SIGUE LOS PASOS INDICADOS usando las herramientas. NO respondas solo con texto.

Sé conciso y profesional pero amigable. Recuerda: responde SIEMPRE en {lang_name}."""

ROLE_SUFFIX_CONTACTO = """

RESTRICCIONES DE ROL (contacto):
Tu usuario actual es '{contact_id}'. Solo puede modificar eventos donde es responsable (aparece en contacto_ids).
Cuando uses DateLocker, FlyerManager, GroupNotifier o CalendarManager(batch_preview/batch_confirm), SIEMPRE pasa contact_id='{contact_id}' y role='contacto'.
Si piden modificar un evento de otro responsable, indica amablemente que no tiene permisos."""

ROLE_SUFFIX_READONLY = """

RESTRICCIONES DE ROL (solo lectura):
Este usuario solo puede consultar información. NO uses DateLocker, GroupNotifier, FlyerManager ni CalendarManager(batch_preview/batch_confirm/undo_last).
Si piden modificar algo, responde amablemente que no tiene permisos y que contacte al administrador."""

ROLE_SUFFIX_FULL = """

CONTEXTO DE ROL:
Tu usuario actual es '{contact_id}' con rol '{role}'. Tiene acceso completo.
Cuando uses DateLocker, FlyerManager, GroupNotifier o CalendarManager(batch_preview/batch_confirm), SIEMPRE pasa contact_id='{contact_id}' y role='{role}'."""

# Crear agente (compilado una sola vez, el thread_id diferencia contactos)
agent = create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


def _get_contact_role(contact_id: str) -> str:
    """Retorna el rol_kalendbot de un contacto. Default: 'contacto' para existentes, 'readonly' para unknown."""
    if not contact_id or contact_id.startswith("unknown-"):
        return "readonly"
    filepath = os.path.join(DATA_DIR, "contactos", f"{contact_id}.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            contact = json.load(f)
        return contact.get("rol_kalendbot", "contacto")
    except (FileNotFoundError, json.JSONDecodeError):
        return "readonly"


def _identify_contact_by_phone(phone: str) -> str | None:
    """Busca un contacto por su número de teléfono."""
    contact_id, _ = identify_by_phone(phone)
    return contact_id


def _preprocess_command(message: str) -> str:
    """
    Pre-procesa comandos tipo /cambiar, /estado, /buscar, /pendientes, /proximos
    y los traduce a instrucciones estructuradas para que el LLM use las herramientas correctas.
    Retorna el mensaje enriquecido o el mensaje original si no es un comando.
    """
    # Limpiar prefijos entre corchetes para analizar el comando
    clean = message
    prefix = ""
    batch_prefix = ""

    # Extraer todos los prefijos [...]
    while clean.startswith("["):
        bracket_end = clean.find("]")
        if bracket_end == -1:
            break
        bracket = clean[:bracket_end + 1]
        if bracket == "[Grupo]":
            prefix = "[Grupo] "
        elif bracket.startswith("[BATCH:"):
            batch_prefix = bracket + " "
        # Skip any other bracket prefix (e.g. [NO uses GroupNotifier...])
        clean = clean[bracket_end + 1:].strip()

    lower = clean.lower()

    # /cambiar o "cambiar" — edición de campos de eventos
    if re.match(r'^(cambiar?|change)\b', lower):
        body = re.sub(r'^(cambiar?|change)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /cambiar] El usuario quiere editar un evento. Instrucción: \"{body}\". "
            f"PASOS OBLIGATORIOS: "
            f"1) Usa CalendarManager(search_event) para encontrar el event_id exacto. "
            f"2) Usa CalendarManager(batch_preview) con los cambios detectados. "
            f"3) Muestra el preview y espera confirmación. "
            f"4) Con confirmación, usa CalendarManager(batch_confirm) con los mismos parámetros."
        )

    # /estado — cambiar estado de un evento
    if re.match(r'^(estado|status)\b', lower):
        body = re.sub(r'^(estado|status)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /estado] El usuario quiere cambiar el estado de un evento. Instrucción: \"{body}\". "
            f"PASOS: 1) Usa CalendarManager(search_event) para encontrar el evento. "
            f"2) Usa CalendarManager(update_status) con el nuevo estado (pendiente/confirmado/cancelado)."
        )

    # /buscar — buscar eventos
    if re.match(r'^(buscar|search|zoek)\b', lower):
        body = re.sub(r'^(buscar|search|zoek)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /buscar] El usuario quiere buscar eventos. Término: \"{body}\". "
            f"Usa CalendarManager(search_event, event_id=\"{body}\")."
        )

    # /pendientes — listar eventos pendientes
    if re.match(r'^(pendientes?|pending)\b', lower):
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /pendientes] Usa CalendarManager(list_pending) y muestra el resultado."
        )

    # /proximos — listar próximos eventos
    if re.match(r'^(proximos?|próximos?|upcoming|volgende)\b', lower):
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /proximos] Usa CalendarManager(list_upcoming) y muestra el resultado."
        )

    # /deshacer — deshacer último cambio
    if re.match(r'^(deshacer|undo|ongedaan)\b', lower):
        body = re.sub(r'^(deshacer|undo|ongedaan)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /deshacer] El usuario quiere revertir cambios. Instrucción: \"{body}\". "
            f"PASOS: 1) Usa CalendarManager(search_event) para encontrar el evento. "
            f"2) Usa CalendarManager(undo_last, event_id=...)."
        )

    # /evento — ver detalle de un evento
    if re.match(r'^(evento|event)\b', lower):
        body = re.sub(r'^(evento|event)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /evento] El usuario quiere ver el detalle de un evento. Término: \"{body}\". "
            f"PASOS: 1) Usa CalendarManager(search_event) para encontrar el event_id. "
            f"2) Usa CalendarManager(get_event) con el event_id encontrado."
        )

    # /ocultar — ocultar evento del export
    if re.match(r'^(ocultar|verbergen|hide)\b', lower):
        body = re.sub(r'^(ocultar|verbergen|hide)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /ocultar] El usuario quiere ocultar un evento del export. Instrucción: \"{body}\". "
            f"PASOS: 1) Usa CalendarManager(search_event) para encontrar el evento. "
            f"2) Usa CalendarManager(update_show_export, event_id=..., show_in_export=false)."
        )

    # /mostrar — mostrar evento en export
    if re.match(r'^(mostrar|tonen|show)\b', lower):
        body = re.sub(r'^(mostrar|tonen|show)\s*', '', clean, flags=re.IGNORECASE).strip()
        return (
            f"{prefix}{batch_prefix}"
            f"[COMANDO: /mostrar] El usuario quiere mostrar un evento en el export. Instrucción: \"{body}\". "
            f"PASOS: 1) Usa CalendarManager(search_event) para encontrar el evento. "
            f"2) Usa CalendarManager(update_show_export, event_id=..., show_in_export=true)."
        )

    # No es un comando reconocido, devolver original
    return message


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


def handle_message(phone: str, message: str, contact_id: str | None = None, thread_id: str | None = None) -> str:
    """
    Punto de entrada principal.
    Recibe un mensaje y retorna la respuesta del agente.
    Si contact_id viene (CLI), lo usa directo. Si no (WhatsApp), busca por teléfono.
    thread_id opcional permite aislar conversaciones (ej: batch tasks).
    """
    # FAQ lookup — responde sin LLM si hay match
    faq_answer = _check_faq(message)
    if faq_answer:
        logger.info(f"FAQ match para: {message[:50]}...")
        return faq_answer

    # Pre-procesar comandos (/cambiar, /estado, /buscar, etc.)
    message = _preprocess_command(message)
    logger.debug(f"Mensaje pre-procesado: {message[:100]}...")

    if not contact_id:
        contact_id = _identify_contact_by_phone(phone)

    if not contact_id:
        logger.warning(f"Contacto no identificado para teléfono: {phone}")
        contact_id = f"unknown-{phone[-4:]}"

    role = _get_contact_role(contact_id)
    lang = get_contact_language(contact_id)
    lang_name = {"es": "español", "en": "English", "nl": "Nederlands"}.get(lang, "español")
    logger.info(f"Mensaje de {contact_id} (rol: {role}, lang: {lang}): {message[:50]}...")

    # System prompt dinámico según rol e idioma
    base_prompt = SYSTEM_PROMPT.format(lang_name=lang_name)
    if role == "readonly":
        dynamic_prompt = base_prompt + ROLE_SUFFIX_READONLY
    elif role == "contacto":
        dynamic_prompt = base_prompt + ROLE_SUFFIX_CONTACTO.format(contact_id=contact_id)
    else:
        dynamic_prompt = base_prompt + ROLE_SUFFIX_FULL.format(contact_id=contact_id, role=role)

    run_metadata = get_run_metadata(contact_id, role)
    config = {
        "configurable": {"thread_id": thread_id or contact_id},
        "recursion_limit": 50,
        "metadata": run_metadata,
    }
    max_retries = 3

    for attempt in range(max_retries):
        try:
            start_time = time.perf_counter()
            result = agent.invoke(
                {"messages": [{"role": "system", "content": dynamic_prompt}, {"role": "user", "content": message}]},
                config=config,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 1)
            response = result["messages"][-1].content
            logger.info(f"Respuesta a {contact_id} ({duration_ms}ms): {response[:50]}...")
            return response
        except RateLimitError as e:
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Rate limit (intento {attempt + 1}/{max_retries}), esperando {wait}s...")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Error procesando mensaje de {contact_id}: {e}\n{traceback.format_exc()}")
            # Limpiar checkpoint corrupto para evitar errores en cascada
            try:
                if hasattr(checkpointer, 'storage') and contact_id in checkpointer.storage:
                    del checkpointer.storage[contact_id]
                    logger.info(f"Checkpoint limpiado para {contact_id}")
            except Exception:
                pass
            return "Lo siento, tuve un problema procesando tu mensaje. Intentaré de nuevo."

    return "El servicio está saturado en este momento. Intentaré de nuevo en unos minutos."
