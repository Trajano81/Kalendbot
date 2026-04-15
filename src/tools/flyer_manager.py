"""
Tool 7: FlyerManager
Gestiona el flujo de flyers: solicitar, rastrear aprobación, programar oleadas.
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger("kalendbot.flyer_manager")

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
COORDINATOR_ID = "rocco-van-velzen"

# Content Manager de NV Mexico
CONTENT_MANAGER = {
    "nombre": "Hanna van Rijsse",
    "telefono": "+528120264857",
    "contact_id": "hanna-van-rijsse"
}


def _send_dm(contact_id: str, message: str) -> None:
    """Envía DM a un contacto por su canal preferido. No rompe el flujo si falla."""
    try:
        from src.gateways.dispatcher import send_dm
        send_dm(contact_id, message=message)
    except Exception as e:
        logger.error(f"Error enviando DM a {contact_id}: {e}")


class FlyerManagerInput(BaseModel):
    action: str = Field(
        description="Acción: check_responsibility, get_status, request_flyer, approve, reject, set_reminder"
    )
    event_id: str = Field(description="ID del evento")
    year: int = Field(default=2026, description="Año del calendario")
    feedback: Optional[str] = Field(default=None, description="Motivo del rechazo (para action=reject)")
    dates: Optional[str] = Field(default=None, description="Fechas ISO separadas por coma para set_reminder (ej: '2026-04-15,2026-04-20')")
    contact_id: Optional[str] = Field(default=None, description="ID del contacto que ejecuta la acción")
    role: Optional[str] = Field(default=None, description="Rol del usuario: admin, tester, contacto, readonly")


def flyer_manager(
    action: str,
    event_id: str,
    year: int = 2026,
    feedback: Optional[str] = None,
    dates: Optional[str] = None,
    contact_id: Optional[str] = None,
    role: Optional[str] = None,
) -> str:
    """Gestiona el flujo de flyers para eventos de NV Mexico."""
    # Validación de permisos
    if role == "readonly":
        return "No tienes permisos para gestionar flyers. Contacta al administrador."

    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    try:
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
    except FileNotFoundError:
        return f"Error: No existe calendario para {year}"

    # Para rol 'contacto', verificar permisos en acciones de escritura
    if role == "contacto" and action in ("request_flyer", "approve", "reject", "set_reminder") and contact_id:
        evento_check = next((e for e in cal.get("eventos", []) + cal.get("eventos_recurrentes", []) if e["id"] == event_id), None)
        if evento_check and contact_id not in evento_check.get("contacto_ids", []):
            return f"No tienes permisos para gestionar el flyer de este evento. Solo los responsables pueden hacerlo."

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
        _send_dm(COORDINATOR_ID, f"Flyer APROBADO para '{evento['nombre']}'. Listo para publicación.")
        return f"Flyer APROBADO para '{evento['nombre']}'. Listo para publicación."

    elif action == "reject":
        iteraciones = evento.get("flyer_revisiones", 0) + 1
        evento["flyer_status"] = "rechazado"
        evento["flyer_revisiones"] = iteraciones
        fb = feedback or "sin feedback"
        evento["flyer_ultimo_feedback"] = fb
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)

        if iteraciones >= 3:
            return (
                f"Flyer RECHAZADO (iteración {iteraciones}/3). MÁXIMO ALCANZADO.\n"
                f"Feedback: {fb}\n"
                f"ESCALAR: se necesita intervención manual para el diseño."
            )
        return (
            f"Flyer RECHAZADO (iteración {iteraciones}/3).\n"
            f"Feedback: {fb}\n"
            f"Enviar feedback al responsable para corrección."
        )

    elif action == "set_reminder":
        if not dates:
            return "Error: Debes proporcionar fechas (ej: dates='2026-04-15,2026-04-20')"
        date_list = [d.strip() for d in dates.split(",") if d.strip()]
        # Validar formato ISO
        valid_dates = []
        for d in date_list:
            try:
                datetime.fromisoformat(d)
                valid_dates.append(d)
            except ValueError:
                return f"Error: Fecha inválida '{d}'. Usa formato YYYY-MM-DD."
        evento["flyer_reminder_custom"] = valid_dates
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)
        return (
            f"Recordatorios custom configurados para '{evento['nombre']}':\n"
            f"Fechas: {', '.join(valid_dates)}\n"
            f"Estos recordatorios son adicionales a los estándar (flyer_moment)."
        )

    return f"Acción desconocida: {action}"


flyer_manager_tool = StructuredTool.from_function(
    name="FlyerManager",
    description="Gestiona el flujo de flyers para eventos de NV Mexico. Acciones: check_responsibility, get_status, request_flyer, approve, reject, set_reminder. set_reminder configura fechas custom de recordatorio (adicionales al flyer_moment estándar). Máximo 3 iteraciones de rechazo.",
    func=flyer_manager,
    args_schema=FlyerManagerInput,
)
