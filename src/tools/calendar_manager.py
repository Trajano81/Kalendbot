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

VALID_STATUSES = {"pendiente", "confirmado", "cancelado"}


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
        description="Acción a ejecutar: list_all, get_event, list_by_status, list_by_contact, list_pending, list_upcoming, update_status, update_show_export"
    )
    year: int = Field(default=2026, description="Año del calendario")
    event_id: Optional[str] = Field(default=None, description="ID del evento (para get_event, update_status, update_show_export)")
    status: Optional[str] = Field(default=None, description="Estado: pendiente, confirmado, cancelado (para list_by_status, update_status). También fecha de instancia recurrente (para update_show_export)")
    contact_id: Optional[str] = Field(default=None, description="ID del contacto (para list_by_contact)")
    show_in_export: Optional[bool] = Field(default=None, description="Mostrar en exports: true/false (para update_show_export)")


def calendar_manager(
    action: str,
    year: int = 2026,
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    contact_id: Optional[str] = None,
    show_in_export: Optional[bool] = None,
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
        today = datetime.now().strftime("%Y-%m-%d")
        pending = [e for e in all_events if e.get("estado") == "pendiente"]
        # Separar en futuros y pasados
        future = [e for e in pending if e.get("fecha", e.get("fecha_inicio", "9999-12-31")) >= today]
        past = [e for e in pending if e.get("fecha", e.get("fecha_inicio", "9999-12-31")) < today]
        future.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))
        past.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))

        lines = []
        if future:
            lines.append(f"═══ PENDIENTES FUTUROS ({len(future)}) ═══")
            for e in future:
                exacta = "" if e.get("fecha_exacta", True) else " (aprox)"
                contactos = ", ".join(e.get("contacto_ids", []))
                lines.append(f"{e.get('fecha', e.get('fecha_inicio', 'sin fecha'))}{exacta} | {e['nombre']} | {contactos}")
        if past:
            lines.append(f"\n═══ PENDIENTES PASADOS — requieren actualización ({len(past)}) ═══")
            for e in past:
                contactos = ", ".join(e.get("contacto_ids", []))
                lines.append(f"⚠️ {e.get('fecha', 'sin fecha')} | {e['nombre']} | {contactos}")

        if not lines:
            return "No hay eventos pendientes"
        return "\n".join(lines)

    elif action == "list_upcoming":
        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = [e for e in all_events if e.get("fecha", e.get("fecha_inicio", "0000-01-01")) >= today and e.get("estado") != "cancelado"]
        upcoming.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))
        if not upcoming:
            return "No hay eventos próximos"
        lines = []
        for e in upcoming:
            estado = e.get("estado", "desconocido").upper()
            exacta = "" if e.get("fecha_exacta", True) else " (aprox)"
            lines.append(f"[{estado}] {e.get('fecha', e.get('fecha_inicio', 'sin fecha'))}{exacta} | {e['nombre']}")
        return "\n".join(lines)

    elif action == "update_status":
        if not event_id or not status:
            return "Error: Faltan event_id y/o status"
        if status not in VALID_STATUSES:
            return f"Error: Estado '{status}' no válido. Opciones: {', '.join(sorted(VALID_STATUSES))}"
        for e in all_events:
            if e["id"] == event_id:
                old_status = e.get("estado")
                e["estado"] = status
                e["ultima_actualizacion"] = datetime.now().isoformat()
                _save_calendar(cal, year)
                return f"Evento '{event_id}' actualizado: {old_status} → {status}"
        return f"Evento '{event_id}' no encontrado"

    elif action == "update_show_export":
        if not event_id or show_in_export is None:
            return "Error: Faltan event_id y/o show_in_export"
        # Search in regular events
        for e in all_events:
            if e["id"] == event_id:
                old_val = e.get("show_in_export", True)
                e["show_in_export"] = show_in_export
                e["ultima_actualizacion"] = datetime.now().isoformat()
                _save_calendar(cal, year)
                return f"Evento '{event_id}' show_in_export: {old_val} → {show_in_export}"
        # Search in recurring events (optionally target a specific instance via status=fecha)
        for rec in recurrentes:
            if rec["id"] == event_id:
                if status:
                    # Target specific instance by fecha
                    for inst in rec.get("instancias_2026", []):
                        if inst.get("fecha") == status:
                            old_val = inst.get("show_in_export", True)
                            inst["show_in_export"] = show_in_export
                            _save_calendar(cal, year)
                            return f"Instancia '{event_id}' fecha {status} show_in_export: {old_val} → {show_in_export}"
                    return f"Instancia con fecha '{status}' no encontrada en '{event_id}'"
                else:
                    # Target the whole recurring event
                    old_val = rec.get("show_in_export", True)
                    rec["show_in_export"] = show_in_export
                    _save_calendar(cal, year)
                    return f"Evento recurrente '{event_id}' show_in_export: {old_val} → {show_in_export}"
        return f"Evento '{event_id}' no encontrado"

    else:
        return f"Acción desconocida: {action}. Opciones: list_all, get_event, list_by_status, list_by_contact, list_pending, list_upcoming, update_status, update_show_export"


calendar_manager_tool = StructuredTool.from_function(
    name="CalendarManager",
    description="Lee y actualiza el calendario de eventos de NV Mexico. Acciones: list_all, get_event, list_by_status, list_by_contact, list_pending (solo pendientes, separados en futuros/pasados), list_upcoming (todos los futuros no cancelados), update_status (estados: pendiente/confirmado/cancelado), update_show_export (mostrar/ocultar en exports, usa status=fecha para instancias recurrentes específicas).",
    func=calendar_manager,
    args_schema=CalendarManagerInput,
)
