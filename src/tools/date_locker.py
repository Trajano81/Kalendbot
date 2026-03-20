"""
Tool 4: DateLocker
Bloquea/desbloquea fechas con lock optimista.
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


class DateLockerInput(BaseModel):
    action: str = Field(description="Acción: lock, unlock, check")
    event_id: str = Field(description="ID del evento")
    fecha: Optional[str] = Field(default=None, description="Fecha en formato YYYY-MM-DD (requerida para lock y check)")
    year: int = Field(default=2026, description="Año del calendario")


def date_locker(
    action: str,
    event_id: str,
    fecha: Optional[str] = None,
    year: int = 2026,
) -> str:
    """Bloquea, desbloquea o verifica fechas para eventos."""
    try:
        cal = _load_calendar(year)
    except FileNotFoundError:
        return f"Error: No existe calendario para {year}"

    eventos = cal.get("eventos", [])

    if action == "check":
        if not fecha:
            return "Error: Falta fecha para verificar"
        conflictos = []
        for e in eventos:
            if e.get("fecha") == fecha and e.get("estado") == "confirmado" and e["id"] != event_id:
                conflictos.append(f"{e['id']}: {e['nombre']} (confirmado)")
        if conflictos:
            return f"FECHA OCUPADA ({fecha}):\n" + "\n".join(conflictos)
        return f"FECHA DISPONIBLE: {fecha} está libre"

    elif action == "lock":
        if not fecha:
            return "Error: Falta fecha para bloquear"
        for e in eventos:
            if e.get("fecha") == fecha and e.get("estado") == "confirmado" and e["id"] != event_id:
                return f"CONFLICTO: No se puede bloquear {fecha}. Ya está confirmado para {e['id']}: {e['nombre']}"

        for e in eventos:
            if e["id"] == event_id:
                e["fecha_confirmada"] = fecha
                e["estado"] = "confirmado"
                e["ultima_actualizacion"] = datetime.now().isoformat()
                _save_calendar(cal, year)
                return f"BLOQUEADA: {fecha} confirmada para '{e['nombre']}'. Estado: confirmado."
        return f"Evento '{event_id}' no encontrado"

    elif action == "unlock":
        for e in eventos:
            if e["id"] == event_id:
                old_status = e.get("estado")
                e["estado"] = "pendiente"
                e["fecha_confirmada"] = None
                e["ultima_actualizacion"] = datetime.now().isoformat()
                _save_calendar(cal, year)
                return f"DESBLOQUEADA: '{e['nombre']}' vuelve a estado pendiente (era: {old_status})"
        return f"Evento '{event_id}' no encontrado"

    return f"Acción desconocida: {action}. Opciones: lock, unlock, check"


date_locker_tool = StructuredTool.from_function(
    name="DateLocker",
    description="Bloquea, desbloquea o verifica fechas para eventos. Acciones: lock (confirmar fecha), unlock (liberar), check (verificar disponibilidad).",
    func=date_locker,
    args_schema=DateLockerInput,
)
