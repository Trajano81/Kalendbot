"""
Tool 1: CalendarManager
Lee y actualiza el calendario de eventos (JSON).
"""
import json
import os
from datetime import datetime
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")


def _load_calendar(year: int = 2026) -> dict:
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_calendar(data: dict, year: int = 2026):
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class CalendarManagerInput(BaseModel):
    action: str = Field(
        description="Acción a ejecutar: list_all, get_event, list_by_status, list_by_contact, list_pending, update_status"
    )
    year: int = Field(default=2026, description="Año del calendario")
    event_id: Optional[str] = Field(default=None, description="ID del evento (para get_event, update_status)")
    status: Optional[str] = Field(default=None, description="Estado del evento (para list_by_status, update_status)")
    contact_id: Optional[str] = Field(default=None, description="ID del contacto (para list_by_contact)")


def calendar_manager(
    action: str,
    year: int = 2026,
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    contact_id: Optional[str] = None,
) -> str:
    """Gestiona el calendario de eventos de NV Mexico."""
    try:
        cal = _load_calendar(year)
    except FileNotFoundError:
        return f"Error: No existe calendario para el año {year}"

    all_events = cal.get("eventos", [])
    recurrentes = cal.get("eventos_recurrentes", [])

    if action == "list_all":
        summary = []
        for e in recurrentes:
            summary.append(f"[RECURRENTE] {e['id']}: {e['nombre']} — regla: {e.get('regla', 'N/A')}")
        for e in all_events:
            fecha = e.get("fecha", "sin fecha")
            estado = e.get("estado", "desconocido")
            summary.append(f"[{estado.upper()}] {e['id']}: {e['nombre']} — {fecha}")
        return "\n".join(summary) if summary else "Calendario vacío"

    elif action == "get_event":
        if not event_id:
            return "Error: Falta event_id"
        for e in all_events + recurrentes:
            if e["id"] == event_id:
                return json.dumps(e, ensure_ascii=False, indent=2)
        return f"Evento '{event_id}' no encontrado"

    elif action == "list_by_status":
        st = status or "pendiente"
        filtered = [e for e in all_events if e.get("estado") == st]
        if not filtered:
            return f"No hay eventos con estado '{st}'"
        return "\n".join([f"{e['id']}: {e['nombre']} — {e.get('fecha', 'sin fecha')}" for e in filtered])

    elif action == "list_by_contact":
        if not contact_id:
            return "Error: Falta contact_id"
        filtered = [e for e in all_events + recurrentes if contact_id in e.get("contacto_ids", [])]
        if not filtered:
            return f"No hay eventos para contacto '{contact_id}'"
        return "\n".join([f"{e['id']}: {e['nombre']} — {e.get('fecha', e.get('regla', 'N/A'))}" for e in filtered])

    elif action == "list_pending":
        pending = [e for e in all_events if e.get("estado") == "pendiente"]
        pending.sort(key=lambda e: e.get("fecha", "9999-12-31"))
        if not pending:
            return "No hay eventos pendientes"
        lines = []
        for e in pending:
            exacta = "" if e.get("fecha_exacta", True) else " (fecha aproximada)"
            contactos = ", ".join(e.get("contacto_ids", []))
            lines.append(f"{e.get('fecha', 'sin fecha')}{exacta} | {e['nombre']} | contacto: {contactos}")
        return "\n".join(lines)

    elif action == "update_status":
        if not event_id or not status:
            return "Error: Faltan event_id y/o status"
        for e in all_events:
            if e["id"] == event_id:
                old_status = e.get("estado")
                e["estado"] = status
                e["ultima_actualizacion"] = datetime.now().isoformat()
                _save_calendar(cal, year)
                return f"Evento '{event_id}' actualizado: {old_status} → {status}"
        return f"Evento '{event_id}' no encontrado"

    else:
        return f"Acción desconocida: {action}. Opciones: list_all, get_event, list_by_status, list_by_contact, list_pending, update_status"


calendar_manager_tool = StructuredTool.from_function(
    name="CalendarManager",
    description="Lee y actualiza el calendario de eventos de NV Mexico. Acciones: list_all, get_event, list_by_status, list_by_contact, list_pending, update_status.",
    func=calendar_manager,
    args_schema=CalendarManagerInput,
)
