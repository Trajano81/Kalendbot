"""
Tool 7: FlyerManager
Gestiona el flujo de flyers: solicitar, rastrear aprobación, programar oleadas.
"""
import json
import os
from datetime import datetime
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")

# Content Manager de NV Mexico
CONTENT_MANAGER = {
    "nombre": "Hanna van Rijsse",
    "telefono": "+528120264857",
    "contact_id": "hanna-van-rijsse"
}


def flyer_manager(action_json: str) -> str:
    """
    Gestiona el flujo de flyers para eventos.
    Input JSON:
      - action: "check_responsibility" | "get_status" | "request_flyer" | "approve" | "reject"
      - event_id: ID del evento
      - year: (opcional, default 2026)
      - feedback: (para reject, motivo del rechazo)
    """
    action_json = action_json.strip()
    try:
        params = json.loads(action_json)
    except json.JSONDecodeError:
        params = {"action": action_json}

    action = params.get("action", "check_responsibility")
    event_id = params.get("event_id")
    year = params.get("year", 2026)

    if not event_id:
        return "Error: Falta event_id"

    # Cargar evento del calendario
    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    try:
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
    except FileNotFoundError:
        return f"Error: No existe calendario para {year}"

    evento = None
    for e in cal.get("eventos", []) + cal.get("eventos_recurrentes", []):
        if e["id"] == event_id:
            evento = e
            break

    if not evento:
        return f"Evento '{event_id}' no encontrado"

    if action == "check_responsibility":
        responsable = evento.get("flyer_responsable", "desconocido")
        if responsable == "nv":
            oleadas = evento.get("flyer_oleadas", 1)
            return (
                f"Flyer responsabilidad de NV (Content Manager).\n"
                f"Content Manager: {CONTENT_MANAGER['nombre']}\n"
                f"Teléfono: {CONTENT_MANAGER['telefono']}\n"
                f"Oleadas de flyer: {oleadas}\n"
                f"Tier: {evento.get('tier_promocion', 'N/A')}"
            )
        elif responsable == "proveedor":
            nombre_resp = evento.get("flyer_responsable_nombre", "desconocido")
            return (
                f"Flyer responsabilidad del proveedor: {nombre_resp}.\n"
                f"El proveedor debe enviar el flyer.\n"
                f"NV (Hanna) debe validar antes de publicar."
            )
        elif responsable == "ninguno":
            return f"Este evento no tiene flyer ({evento.get('nombre')})"
        return f"Responsable de flyer: {responsable}"

    elif action == "get_status":
        flyer_status = evento.get("flyer_status", "no_solicitado")
        return (
            f"Estado de flyer para '{evento['nombre']}':\n"
            f"Responsable: {evento.get('flyer_responsable', 'N/A')}\n"
            f"Estado: {flyer_status}\n"
            f"Oleadas: {evento.get('flyer_oleadas', 0)}\n"
            f"Flyer moment: {evento.get('flyer_moment', 'N/A')}"
        )

    elif action == "request_flyer":
        evento["flyer_status"] = "solicitado"
        evento["flyer_solicitado_fecha"] = datetime.now().isoformat()
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)

        responsable = evento.get("flyer_responsable", "nv")
        if responsable == "nv":
            return (
                f"Flyer SOLICITADO al Content Manager.\n"
                f"Contactar a: {CONTENT_MANAGER['nombre']} ({CONTENT_MANAGER['telefono']})\n"
                f"Evento: {evento['nombre']}\n"
                f"Fecha: {evento.get('fecha', 'por definir')}\n"
                f"Venue: {evento.get('venue_nombre', evento.get('venue_id', 'N/A'))}\n"
                f"Precio: {json.dumps(evento.get('precio', 'gratis'), ensure_ascii=False)}"
            )
        else:
            nombre_resp = evento.get("flyer_responsable_nombre", "proveedor")
            contacto_ids = evento.get("contacto_ids", [])
            return (
                f"Flyer SOLICITADO al proveedor: {nombre_resp}\n"
                f"Contacto(s): {', '.join(contacto_ids)}\n"
                f"Una vez recibido, Hanna ({CONTENT_MANAGER['telefono']}) debe validar."
            )

    elif action == "approve":
        evento["flyer_status"] = "aprobado"
        evento["flyer_aprobado_fecha"] = datetime.now().isoformat()
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)
        return f"Flyer APROBADO para '{evento['nombre']}'. Listo para publicación."

    elif action == "reject":
        iteraciones = evento.get("flyer_revisiones", 0) + 1
        evento["flyer_status"] = "rechazado"
        evento["flyer_revisiones"] = iteraciones
        feedback = params.get("feedback", "sin feedback")
        evento["flyer_ultimo_feedback"] = feedback
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)

        if iteraciones >= 3:
            return (
                f"Flyer RECHAZADO (iteración {iteraciones}/3). MÁXIMO ALCANZADO.\n"
                f"Feedback: {feedback}\n"
                f"ESCALAR: se necesita intervención manual para el diseño."
            )
        return (
            f"Flyer RECHAZADO (iteración {iteraciones}/3).\n"
            f"Feedback: {feedback}\n"
            f"Enviar feedback al responsable para corrección."
        )

    return f"Acción desconocida: {action}"


flyer_manager_tool = Tool(
    name="FlyerManager",
    description="""Gestiona el flujo de flyers para eventos de NV Mexico.
    Input: JSON con 'action' (check_responsibility, get_status, request_flyer, approve, reject)
    y 'event_id'. Determina si el flyer es responsabilidad del Content Manager de NV (Hanna)
    o del proveedor. Rastrea estado de aprobación con máximo 3 iteraciones.""",
    func=flyer_manager,
)
