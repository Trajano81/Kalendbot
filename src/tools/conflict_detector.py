"""
Tool 5: ConflictDetector
Analiza una fecha contra feriados, eventos confirmados y reglas implícitas.
"""
import json
import os
from datetime import datetime, timedelta
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")


def conflict_detector(fecha_str: str) -> str:
    """
    Analiza una fecha propuesta contra todo el contexto del calendario.
    Input: fecha en formato YYYY-MM-DD
    Retorna: lista de conflictos, advertencias y oportunidades.
    """
    try:
        fecha = datetime.strptime(fecha_str.strip(), "%Y-%m-%d")
    except ValueError:
        return f"Error: Formato de fecha inválido '{fecha_str}'. Usa YYYY-MM-DD"

    year = fecha.year
    resultados = {
        "fecha": fecha_str.strip(),
        "dia_semana": fecha.strftime("%A"),
        "conflictos": [],
        "advertencias": [],
        "oportunidades": []
    }

    # 1. Verificar feriados mexicanos
    restricciones_path = os.path.join(DATA_DIR, "config", "restricciones.json")
    if os.path.exists(restricciones_path):
        with open(restricciones_path, "r", encoding="utf-8") as f:
            restricciones = json.load(f)

        feriados = restricciones.get(f"feriados_mexico_{year}", [])
        for fer in feriados:
            fer_date = datetime.strptime(fer["fecha"], "%Y-%m-%d")
            diff = abs((fecha - fer_date).days)
            if diff == 0:
                resultados["conflictos"].append(f"CAE EN FERIADO: {fer['nombre']} ({fer['fecha']})")
            elif diff <= 3:
                resultados["advertencias"].append(
                    f"Cerca de feriado: {fer['nombre']} ({fer['fecha']}) — {diff} día(s) de diferencia"
                )
                if diff <= 2 and fecha.weekday() in [4, 5]:  # viernes o sábado
                    resultados["oportunidades"].append(
                        f"Fin de semana largo por {fer['nombre']} — posible mayor asistencia"
                    )

        # 2. Verificar reglas implícitas
        reglas = restricciones.get("reglas_implicitas", [])
        for regla in reglas:
            if not regla.get("activa", True):
                continue
            rid = regla["id"]
            if rid == "no-navidad" and fecha.month == 12 and fecha.day >= 20:
                resultados["advertencias"].append(f"Regla implícita: {regla['regla']}")
            elif rid == "no-navidad" and fecha.month == 1 and fecha.day <= 5:
                resultados["advertencias"].append(f"Regla implícita: {regla['regla']}")
            elif rid == "verano-ligero" and fecha.month in [7, 8]:
                resultados["advertencias"].append(f"Regla implícita: {regla['regla']}")
            elif rid == "transicion-sep-oct" and fecha.month in [9, 10]:
                resultados["advertencias"].append(f"Regla implícita: {regla['regla']}")

    # 3. Verificar eventos ya confirmados ese día
    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    if os.path.exists(cal_path):
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
        for e in cal.get("eventos", []):
            if e.get("fecha") == fecha_str.strip() and e.get("estado") == "confirmado":
                resultados["conflictos"].append(
                    f"Evento confirmado el mismo día: {e['nombre']} ({e['id']})"
                )
            elif e.get("fecha") == fecha_str.strip() and e.get("estado") == "pendiente":
                resultados["advertencias"].append(
                    f"Evento pendiente el mismo día: {e['nombre']} ({e['id']})"
                )

    # 4. Verificar eventos externos
    ext_path = os.path.join(DATA_DIR, "config", f"eventos-externos-{year}.json")
    if os.path.exists(ext_path):
        with open(ext_path, "r", encoding="utf-8") as f:
            externos = json.load(f)
        for ext in externos.get("eventos", []):
            ext_fecha = ext.get("fecha_estimada")
            if ext_fecha == fecha_str.strip():
                resultados["advertencias"].append(
                    f"Evento externo el mismo día: {ext['nombre']}"
                )

    # Formatear resultado
    output = [f"Análisis de fecha: {fecha_str.strip()} ({resultados['dia_semana']})"]
    output.append("")

    if resultados["conflictos"]:
        output.append("🔴 CONFLICTOS:")
        for c in resultados["conflictos"]:
            output.append(f"  - {c}")
    else:
        output.append("✅ Sin conflictos directos")

    if resultados["advertencias"]:
        output.append("\n⚠️ ADVERTENCIAS:")
        for a in resultados["advertencias"]:
            output.append(f"  - {a}")

    if resultados["oportunidades"]:
        output.append("\n💡 OPORTUNIDADES:")
        for o in resultados["oportunidades"]:
            output.append(f"  - {o}")

    if not resultados["conflictos"] and not resultados["advertencias"]:
        output.append("\n✅ Fecha limpia — sin conflictos ni advertencias")

    return "\n".join(output)


conflict_detector_tool = Tool(
    name="ConflictDetector",
    description="""Analiza una fecha propuesta contra feriados mexicanos, eventos confirmados,
    reglas implícitas del calendario y eventos externos. Retorna conflictos, advertencias
    y oportunidades. Input: fecha en formato YYYY-MM-DD.""",
    func=conflict_detector,
)
