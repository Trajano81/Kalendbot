"""
Tool 8: RulesEngine
Consulta reglas de negocio: tiers, precedencia, restricciones, reglas implícitas.
"""
import json
import os
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
CONFIG_DIR = os.path.join(DATA_DIR, "config")


def rules_engine(query: str) -> str:
    """
    Consulta reglas de negocio del calendario.
    Input: tipo de regla a consultar:
      - "tiers" → tiers de promoción
      - "precedencia" → reglas de precedencia para disputas
      - "restricciones" → feriados y reglas implícitas
      - "eventos_externos" → eventos externos del año
      - "compatibilidad" → reglas de compatibilidad de fechas
      - "all" → resumen de todas las reglas
    """
    query = query.strip().lower()

    if query == "tiers":
        path = os.path.join(CONFIG_DIR, "tiers-promocion.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            lines = []
            for tid, tier in data.get("tiers", {}).items():
                lines.append(f"**{tier['nombre']}**: {tier['descripcion']}")
                lines.append(f"  Oleadas: {tier['oleadas_flyer']} | Momentos: {', '.join(tier['flyer_moments'])}")
                lines.append(f"  Canales: {', '.join(tier['canales']) if tier['canales'] else 'ninguno'}")
                lines.append("")
            return "\n".join(lines)
        return "Archivo de tiers no encontrado"

    elif query == "precedencia":
        path = os.path.join(CONFIG_DIR, "precedencia.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
        return "Archivo de precedencia no encontrado"

    elif query == "restricciones":
        path = os.path.join(CONFIG_DIR, "restricciones.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            lines = ["Feriados mexicanos:\n"]
            for fer in data.get("feriados_mexico_2026", []):
                lines.append(f"  {fer['fecha']}: {fer['nombre']}")
            lines.append("\nReglas implícitas:\n")
            for regla in data.get("reglas_implicitas", []):
                estado = "✅ activa" if regla.get("activa") else "❌ inactiva"
                lines.append(f"  [{estado}] {regla['regla']}")
                lines.append(f"    Evidencia: {regla['evidencia']}")
                lines.append("")
            return "\n".join(lines)
        return "Archivo de restricciones no encontrado"

    elif query.startswith("eventos_externos"):
        # Extraer año si se provee, default 2026
        parts = query.split()
        year = int(parts[1]) if len(parts) > 1 else 2026
        path = os.path.join(CONFIG_DIR, f"eventos-externos-{year}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            lines = [f"Eventos externos {year}:\n"]
            for ext in data.get("eventos", []):
                conf = "✅" if ext.get("confirmado") else "⏳"
                lines.append(f"  {conf} {ext['nombre']} — {ext.get('fecha_estimada', ext.get('fecha_inicio', 'TBD'))}")
                lines.append(f"     Relevancia: {ext.get('relevancia', 'N/A')}")
            lines.append("\nCiclos deportivos:")
            for deporte, info in data.get("ciclos_deportivos", {}).items():
                lines.append(f"  {deporte}: cada {info['frecuencia']} años, próximo {info['proxima']}")
            return "\n".join(lines)
        return f"Archivo de eventos externos para {year} no encontrado"

    elif query == "compatibilidad":
        path = os.path.join(CONFIG_DIR, "precedencia.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            compat = data.get("compatibilidad_fechas", {})
            lines = ["Reglas de compatibilidad de fechas:\n"]
            for scenario, rule in compat.items():
                if isinstance(rule, str):
                    lines.append(f"  {scenario}: {rule}")
                elif isinstance(rule, dict):
                    permitido = "✅ Permitido" if rule.get("permitido") else "❌ Bloqueado"
                    lines.append(f"  {scenario}: {permitido}")
                    for k, v in rule.items():
                        if k != "permitido":
                            lines.append(f"    {k}: {v}")
                lines.append("")
            return "\n".join(lines)
        return "Archivo de compatibilidad no encontrado"

    elif query == "all":
        # Resumen ejecutivo de todas las reglas
        lines = ["=== RESUMEN DE REGLAS DE NEGOCIO ===\n"]
        for sub_query in ["tiers", "precedencia", "restricciones", "compatibilidad"]:
            lines.append(f"\n--- {sub_query.upper()} ---")
            lines.append(rules_engine(sub_query))
        return "\n".join(lines)

    return f"Consulta no reconocida: '{query}'. Opciones: tiers, precedencia, restricciones, eventos_externos, compatibilidad, all"


rules_engine_tool = Tool(
    name="RulesEngine",
    description="""Consulta reglas de negocio del calendario de NV Mexico.
    Input: tipo de regla ('tiers', 'precedencia', 'restricciones', 'eventos_externos', 'compatibilidad', 'all').
    Retorna las reglas configuradas para toma de decisiones del bot.""",
    func=rules_engine,
)
