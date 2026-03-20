"""
Tool 4: DateLocker
Bloquea/desbloquea fechas con lock optimista.
"""
import json
import os
from datetime import datetime
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")


def _load_calendar(year: int = 2026) -> dict:
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_calendar(data: dict, year: int = 2026):
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def date_locker(action_json: str) -> str:
    """
    Bloquea o desbloquea una fecha para un evento.
    Input JSON:
      - action: "lock" | "unlock" | "check"
      - event_id: ID del evento
      - fecha: fecha a bloquear/verificar (YYYY-MM-DD)
      - year: (opcional, default 2026)
    """
    action_json = action_json.strip()
    try:
        params = json.loads(action_json)
    except json.JSONDecodeError:
        params = {"action": action_json}

    action = params.get("action", "check")
    event_id = params.get("event_id")
    fecha = params.get("fecha")
    year = params.get("year", 2026)

    if not event_id:
        return "Error: Falta event_id"

    try:
        cal = _load_calendar(year)
    except FileNotFoundError:
        return f"Error: No existe calendario para {year}"

    eventos = cal.get("eventos", [])

    if action == "check":
        # Verificar si una fecha está libre
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
        # Verificar conflictos primero
        for e in eventos:
            if e.get("fecha") == fecha and e.get("estado") == "confirmado" and e["id"] != event_id:
                return f"CONFLICTO: No se puede bloquear {fecha}. Ya está confirmado para {e['id']}: {e['nombre']}"

        # Bloquear
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


date_locker_tool = Tool(
    name="DateLocker",
    description="""Bloquea, desbloquea o verifica fechas para eventos.
    Input: JSON con 'action' (lock, unlock, check), 'event_id', 'fecha' (YYYY-MM-DD).
    Usa lock para confirmar una fecha (verifica conflictos antes de bloquear).
    Usa check para verificar si una fecha está disponible.
    Usa unlock para liberar una fecha confirmada.""",
    func=date_locker,
)
