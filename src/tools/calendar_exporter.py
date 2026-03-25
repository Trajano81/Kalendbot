"""
Tool 9: CalendarExporter
Exporta el calendario JSON a Excel preservando formato del original.
"""
import json
import os
import shutil
from datetime import datetime
from typing import Optional
from openpyxl import load_workbook
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from src.tools.flyer_manager import CONTENT_MANAGER

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "NV_2026_Jaarkalender V2.0.xlsx")

# Meses en holandés
DUTCH_MONTHS = {
    1: "Januari", 2: "Februari", 3: "Maart", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Augustus",
    9: "September", 10: "Oktober", 11: "November", 12: "December"
}

# Filas reservadas: 1-2 titulo/formulas, 3 headers, 4-5 recurrentes
DATA_START_ROW = 6


def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _resolve_provider(partner_id) -> str:
    if not partner_id or partner_id == "None":
        return ""
    data = _load_json(os.path.join(DATA_DIR, "proveedores", f"{partner_id}.json"))
    return data.get("nombre", partner_id)


def _resolve_contact(contact_ids: list) -> tuple:
    nombres, telefonos = [], []
    for cid in (contact_ids or []):
        data = _load_json(os.path.join(DATA_DIR, "contactos", f"{cid}.json"))
        nombres.append(data.get("nombre", cid))
        tel = data.get("telefono", "")
        if tel:
            try:
                telefonos.append(int(tel))
            except (ValueError, TypeError):
                telefonos.append(tel)
    return ", ".join(nombres), telefonos[0] if len(telefonos) == 1 else ", ".join(str(t) for t in telefonos) if telefonos else ""


def _format_date_nl(fecha_str: str) -> str:
    try:
        dt = datetime.fromisoformat(fecha_str)
        return f"{dt.day} {DUTCH_MONTHS[dt.month]}"
    except (ValueError, TypeError):
        return fecha_str or ""


def _format_hora(hora_str) -> str:
    """Retorna hora en formato 24h o ntbp si no hay."""
    if not hora_str:
        return "ntbp"
    return hora_str


def _resolve_address(evento: dict) -> str:
    """Resuelve dirección: venue_direccion > proveedor dirección > ntbp."""
    addr = evento.get("venue_direccion")
    if addr:
        return addr
    # Intentar obtener dirección del proveedor
    partner_id = evento.get("partner_id")
    if partner_id:
        data = _load_json(os.path.join(DATA_DIR, "proveedores", f"{partner_id}.json"))
        addr = data.get("direccion") or data.get("venue_direccion")
        if addr:
            return addr
    return "ntbp"


def _format_precio(precio):
    """Retorna precio como número (matching original format)."""
    if precio is None:
        return 0
    if isinstance(precio, dict):
        return precio.get("mxn", 0)
    if isinstance(precio, (int, float)):
        return precio
    try:
        return int(precio)
    except (ValueError, TypeError):
        return 0


def _event_to_row(evento: dict) -> list:
    """Genera fila B-U (20 columnas) matching formato original."""
    nombre_contacto, tel_contacto = _resolve_contact(evento.get("contacto_ids"))
    canales = evento.get("canales", [])

    # Col N: flyer oleadas (number or "x")
    flyer_oleadas = evento.get("flyer_oleadas", "x") or "x"

    # Col O: flyer responsable
    resp = evento.get("flyer_responsable", "")
    if resp == "nv":
        flyer_resp = CONTENT_MANAGER["nombre"]
    elif resp == "proveedor":
        flyer_resp = evento.get("flyer_responsable_nombre", "")
    else:
        flyer_resp = ""

    return [
        _format_date_nl(evento.get("fecha", evento.get("fecha_inicio", ""))),
        evento.get("nombre", ""),
        _resolve_provider(evento.get("partner_id")) or evento.get("partner_nombre", ""),
        evento.get("venue_nombre") or evento.get("venue_id") or "nvt",
        evento.get("descripcion", ""),
        _format_hora(evento.get("hora")),
        _format_precio(evento.get("precio")),
        _resolve_address(evento),
        evento.get("detalle", ""),
        evento.get("flyer_moment", ""),
        nombre_contacto,
        tel_contacto,
        flyer_oleadas,
        flyer_resp,
        "reel aft" if evento.get("reel_post") else "x",
        "eventbrite" if evento.get("eventbrite") else "x",
        "whats" if "whatsapp" in canales else "x",
        "inst FB TT" if "rrss" in canales else "x",
        "email" if "email" in canales else "x",
        evento.get("texto_social", ""),
    ]


def export_calendar(year: int = 2026, filter_status: Optional[str] = None, filter_contacto: Optional[str] = None) -> str:
    """Exporta calendario JSON a Excel usando template original."""
    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    cal = _load_json(cal_path)
    if not cal:
        return f"Error: No existe calendario para {year}"

    template = os.path.normpath(TEMPLATE_PATH)
    if not os.path.exists(template):
        return f"Error: No se encuentra template Excel en {template}"

    # Recopilar eventos regulares (no recurrentes — esos quedan en rows 4-5)
    all_events = list(cal.get("eventos", []))

    # Ordenar por fecha
    all_events.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))

    # Filtros opcionales
    if filter_status:
        all_events = [e for e in all_events if e.get("estado") == filter_status]
    if filter_contacto:
        all_events = [e for e in all_events if filter_contacto in (e.get("contacto_ids") or [])]

    if not all_events:
        return "No hay eventos que coincidan con los filtros."

    # Copiar template al output
    output_path = os.path.join(DATA_DIR, f"NV_{year}_Jaarkalender_UPDATED.xlsx")
    shutil.copy2(template, output_path)

    wb = load_workbook(output_path)
    ws = wb.active

    # Actualizar rows 4-5 (eventos recurrentes) desde JSON
    for idx, rec in enumerate(cal.get("eventos_recurrentes", [])[:2]):
        row_num = 4 + idx
        row_data = _event_to_row(rec)
        # Solo sobreescribir columnas que tenemos datos (preservar regla en col B)
        row_data[0] = rec.get("regla", ws.cell(row=row_num, column=2).value)
        for col_offset, value in enumerate(row_data):
            ws.cell(row=row_num, column=2 + col_offset, value=value)

    # Limpiar filas de datos (6+), preservar rows 1-3
    for row in range(DATA_START_ROW, ws.max_row + 1):
        for col in range(2, 22):  # B-T
            ws.cell(row=row, column=col).value = None

    # Escribir eventos en filas 6+
    for idx, evento in enumerate(all_events):
        row_num = DATA_START_ROW + idx
        row_data = _event_to_row(evento)
        for col_offset, value in enumerate(row_data):
            ws.cell(row=row_num, column=2 + col_offset, value=value)

    wb.save(output_path)
    return output_path


class CalendarExporterInput(BaseModel):
    year: int = Field(default=2026, description="Año del calendario a exportar")
    filter_status: Optional[str] = Field(default=None, description="Filtrar por estado: confirmado, pendiente, cancelado")
    filter_contacto: Optional[str] = Field(default=None, description="Filtrar por contacto_id responsable")
    role: Optional[str] = Field(default=None, description="Rol del usuario: admin, tester, contacto, readonly")


def calendar_exporter(
    year: int = 2026,
    filter_status: Optional[str] = None,
    filter_contacto: Optional[str] = None,
    role: Optional[str] = None,
) -> str:
    """Exporta el calendario a Excel. Wrapper para LangChain tool."""
    if role == "readonly":
        return "No tienes permisos para exportar. Contacta al administrador."
    path = export_calendar(year=year, filter_status=filter_status, filter_contacto=filter_contacto)
    if path.startswith("Error") or path.startswith("No hay"):
        return path
    return f"Calendario exportado exitosamente: {path}"


calendar_exporter_tool = StructuredTool.from_function(
    name="CalendarExporter",
    description="Exporta el calendario de eventos a Excel (.xlsx). Permite filtrar por año, estado o contacto responsable. El archivo se genera en kalendbot-data/.",
    func=calendar_exporter,
    args_schema=CalendarExporterInput,
)


if __name__ == "__main__":
    import sys
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    result = export_calendar(year=yr)
    print(result)
