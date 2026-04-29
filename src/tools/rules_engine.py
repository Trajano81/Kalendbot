"""
Tool 8: RulesEngine
Consulta reglas de negocio: tiers, precedencia, restricciones, reglas implícitas.
"""
import json
import os
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
CONFIG_DIR = os.path.join(DATA_DIR, "config")


def _load_json(filename: str) -> dict | None:
    path = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _get_tiers() -> str:
    data = _load_json("tiers-promocion.json")
    if not data:
        return "Archivo de tiers no encontrado"
    lines = []
    for tid, tier in data.get("tiers", {}).items():
        lines.append(f"**{tier['nombre']}**: {tier['descripcion']}")
        lines.append(f"  Oleadas: {tier['oleadas_flyer']} | Momentos: {', '.join(tier['flyer_moments'])}")
        lines.append(f"  Canales: {', '.join(tier['canales']) if tier['canales'] else 'ninguno'}")
        lines.append("")
    return "\n".join(lines)


def _get_precedencia() -> str:
    data = _load_json("precedencia.json")
    if not data:
        return "Archivo de precedencia no encontrado"
    lines = ["Reglas de precedencia para disputas de fechas:\n"]
    for regla in data.get("reglas_precedencia", []):
        lines.append(f"{regla['id']}. {regla['regla']}")
        if "ejemplo" in regla:
            lines.append(f"   Ejemplo: {regla['ejemplo']}")
        if "razon" in regla:
            lines.append(f"   Razón: {regla['razon']}")
        lines.append("")
    lines.append(f"Última instancia: {data.get('ultima_instancia', 'director_proyecto')}")
    return "\n".join(lines)


def _get_restricciones() -> str:
    data = _load_json("restricciones.json")
    if not data:
        return "Archivo de restricciones no encontrado"
    lines = ["Feriados mexicanos:\n"]
    for fer in data.get("feriados_mexico_2026", []):
        lines.append(f"  {fer['fecha']}: {fer['nombre']}")
    lines.append("\nReglas implícitas:\n")
    for regla in data.get("reglas_implicitas", []):
        estado = "activa" if regla.get("activa") else "inactiva"
        lines.append(f"  [{estado}] {regla['regla']}")
        lines.append(f"    Evidencia: {regla['evidencia']}")
        lines.append("")
    return "\n".join(lines)


def _get_eventos_externos(year: int = 2026) -> str:
    data = _load_json(f"eventos-externos-{year}.json")
    if not data:
        return f"Archivo de eventos externos para {year} no encontrado"
    lines = [f"Eventos externos {year}:\n"]
    for ext in data.get("eventos", []):
        conf = "confirmado" if ext.get("confirmado") else "pendiente"
        lines.append(f"  [{conf}] {ext['nombre']} — {ext.get('fecha_estimada', ext.get('fecha_inicio', 'TBD'))}")
        lines.append(f"     Relevancia: {ext.get('relevancia', 'N/A')}")
    lines.append("\nCiclos deportivos:")
    for deporte, info in data.get("ciclos_deportivos", {}).items():
        lines.append(f"  {deporte}: cada {info['frecuencia']} años, próximo {info['proxima']}")
    return "\n".join(lines)


def _get_instrucciones() -> str:
    data = _load_json("instrucciones-edicion.json")
    if not data:
        return "Archivo de instrucciones no encontrado"
    lines = ["═══ GUÍA DE EDICIÓN DE EVENTOS ═══\n"]

    # Fields table
    lines.append("CAMPOS EDITABLES:")
    lines.append(f"{'Campo':<28} {'Excel':<6} {'Tipo':<8} {'Permiso':<8}")
    lines.append("─" * 54)
    for f in data.get("fields", []):
        lines.append(f"{f['field']:<28} {f['excel_col']:<6} {f['type']:<8} {f['permission']:<8}")

    # Roles
    lines.append("\nROLES:")
    for role, desc in data.get("roles", {}).items():
        lines.append(f"  {role}: {desc}")

    # Usage
    guide = data.get("usage_guide", {})
    lines.append(f"\nFLUJO: {guide.get('edit_flow', '')}")
    lines.append("\nEJEMPLOS:")
    for ex in guide.get("examples", []):
        lines.append(f"  • {ex}")

    # Commands
    lines.append("\nCOMANDOS DISPONIBLES:")
    for cmd, desc in data.get("agent_activation", {}).get("commands", {}).items():
        lines.append(f"  {cmd}: {desc}")

    return "\n".join(lines)


def _get_compatibilidad() -> str:
    data = _load_json("precedencia.json")
    if not data:
        return "Archivo de compatibilidad no encontrado"
    compat = data.get("compatibilidad_fechas", {})
    lines = ["Reglas de compatibilidad de fechas:\n"]
    for scenario, rule in compat.items():
        if isinstance(rule, str):
            lines.append(f"  {scenario}: {rule}")
        elif isinstance(rule, dict):
            permitido = "Permitido" if rule.get("permitido") else "Bloqueado"
            lines.append(f"  {scenario}: {permitido}")
            for k, v in rule.items():
                if k != "permitido":
                    lines.append(f"    {k}: {v}")
        lines.append("")
    return "\n".join(lines)


# Dispatch table — no recursion
_HANDLERS = {
    "tiers": _get_tiers,
    "precedencia": _get_precedencia,
    "restricciones": _get_restricciones,
    "compatibilidad": _get_compatibilidad,
    "instrucciones": _get_instrucciones,
}


def rules_engine(query: str) -> str:
    """
    Consulta reglas de negocio del calendario.
    Input: tipo de regla ('tiers', 'precedencia', 'restricciones', 'eventos_externos', 'compatibilidad', 'all').
    """
    query = query.strip().lower()

    if query in _HANDLERS:
        return _HANDLERS[query]()

    if query.startswith("eventos_externos"):
        parts = query.split()
        year = int(parts[1]) if len(parts) > 1 else 2026
        return _get_eventos_externos(year)

    if query == "all":
        lines = ["=== RESUMEN DE REGLAS DE NEGOCIO ===\n"]
        for name, handler in _HANDLERS.items():
            lines.append(f"\n--- {name.upper()} ---")
            lines.append(handler())
        return "\n".join(lines)

    return f"Consulta no reconocida: '{query}'. Opciones: tiers, precedencia, restricciones, eventos_externos, compatibilidad, instrucciones, all"


rules_engine_tool = Tool(
    name="RulesEngine",
    description="Consulta reglas de negocio del calendario de NV Mexico. Input: tipo de regla ('tiers', 'precedencia', 'restricciones', 'eventos_externos', 'compatibilidad', 'instrucciones', 'all').",
    func=rules_engine,
)
