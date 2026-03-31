"""
Tool 9: CalendarExporter
Exporta el calendario JSON a Excel preservando formato del original.
Soporta multi-idioma: dut (default), eng, spa, por.
"""
import copy
import json
import os
import shutil
from datetime import datetime
from typing import Optional
from openpyxl import load_workbook
from openpyxl.drawing.spreadsheet_drawing import TwoCellAnchor
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from src.tools.flyer_manager import CONTENT_MANAGER

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "NV_2026_Jaarkalender V3.0.xlsx")

# Filas reservadas: 1-2 titulo/formulas, 3 headers, 4-5 recurrentes
DATA_START_ROW = 6

VALID_LANGS = ("dut", "eng", "spa", "por")

# --- Static translation dictionaries ---
TRANSLATIONS = {
    "dut": {
        "months": {
            1: "Januari", 2: "Februari", 3: "Maart", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Augustus",
            9: "September", 10: "Oktober", 11: "November", 12: "December",
        },
        "headers": [
            "Datum", "Activiteit", "Partner", "Locatie",
            "1 omschrijving", "2 Tijdstip", "3 Entree", "4 Adres",
            "5 Info post/ FLYER:", "6 flyer moment", "7 contact persoon", "8 Celular",
            "Flyer oleadas", "Flyer resp.",
            "reel na event", "eventbrite", "whats", "inst FB TT", "email", "Texto Socials",
        ],
        "ntbp": "ntbp",
        "nvt": "nvt",
    },
    "eng": {
        "months": {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December",
        },
        "headers": [
            "Date", "Activity", "Partner", "Location",
            "1 Description", "2 Time", "3 Entry fee", "4 Address",
            "5 Info post/ FLYER:", "6 Flyer moment", "7 Contact person", "8 Phone",
            "Flyer waves", "Flyer resp.",
            "Reel after event", "Eventbrite", "WhatsApp", "Inst FB TT", "Email", "Social Text",
        ],
        "ntbp": "TBD",
        "nvt": "n/a",
    },
    "spa": {
        "months": {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        },
        "headers": [
            "Fecha", "Actividad", "Socio", "Ubicación",
            "1 Descripción", "2 Horario", "3 Entrada", "4 Dirección",
            "5 Info post/ FLYER:", "6 Momento flyer", "7 Persona contacto", "8 Celular",
            "Oleadas flyer", "Resp. flyer",
            "Reel post evento", "Eventbrite", "WhatsApp", "Inst FB TT", "Email", "Texto Social",
        ],
        "ntbp": "por definir",
        "nvt": "n/a",
    },
    "por": {
        "months": {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
        },
        "headers": [
            "Data", "Atividade", "Parceiro", "Local",
            "1 Descrição", "2 Horário", "3 Entrada", "4 Endereço",
            "5 Info post/ FLYER:", "6 Momento flyer", "7 Pessoa contacto", "8 Telefone",
            "Ondas flyer", "Resp. flyer",
            "Reel pós evento", "Eventbrite", "WhatsApp", "Inst FB TT", "Email", "Texto Social",
        ],
        "ntbp": "a definir",
        "nvt": "n/a",
    },
}


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
    return data.get("partner_display", data.get("nombre", partner_id))


def _resolve_venue(venue_id) -> str:
    """Resuelve venue_id a nombre legible desde proveedores JSON."""
    if not venue_id or venue_id == "None":
        return ""
    data = _load_json(os.path.join(DATA_DIR, "proveedores", f"{venue_id}.json"))
    return data.get("venue_nombre", data.get("nombre", venue_id))


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
    return (
        ", ".join(nombres),
        telefonos[0] if len(telefonos) == 1
        else ", ".join(str(t) for t in telefonos) if telefonos
        else "",
    )


def _format_date(fecha_str: str, lang: str = "dut") -> str:
    months = TRANSLATIONS.get(lang, TRANSLATIONS["dut"])["months"]
    try:
        dt = datetime.fromisoformat(fecha_str)
        return f"{dt.day} {months[dt.month]}"
    except (ValueError, TypeError):
        return fecha_str or ""


def _format_hora(hora_str, lang: str = "dut") -> str:
    if not hora_str:
        return TRANSLATIONS.get(lang, TRANSLATIONS["dut"])["ntbp"]
    return hora_str


def _resolve_address(evento: dict, lang: str = "dut") -> str:
    addr = evento.get("venue_direccion")
    if addr:
        return addr
    partner_id = evento.get("partner_id")
    if partner_id:
        data = _load_json(os.path.join(DATA_DIR, "proveedores", f"{partner_id}.json"))
        addr = data.get("direccion") or data.get("venue_direccion")
        if addr:
            return addr
    return TRANSLATIONS.get(lang, TRANSLATIONS["dut"])["ntbp"]


def _format_precio(precio):
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


def _translate_content(events: list, lang: str) -> list:
    """Traduce contenido de eventos usando Claude. Solo para exports no-Dutch."""
    if lang == "dut":
        return events

    lang_names = {"eng": "English", "spa": "Spanish", "por": "Portuguese"}
    target = lang_names.get(lang, "English")

    # Recopilar textos únicos para traducir en batch
    texts_to_translate = {}
    fields = ["nombre", "descripcion", "detalle", "texto_social"]
    for evento in events:
        for field in fields:
            val = evento.get(field)
            if val and isinstance(val, str) and val not in ("x", "ntbp", "nvt", ""):
                texts_to_translate[val] = None  # placeholder

    if not texts_to_translate:
        return events

    # Batch translate via Claude
    try:
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0, max_tokens=4096)

        # Build translation prompt
        text_list = list(texts_to_translate.keys())
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(text_list))

        prompt = (
            f"Translate the following Dutch texts to {target}. "
            f"Keep proper nouns, event names, and emojis unchanged. "
            f"Return ONLY a JSON array of translated strings in the same order.\n\n"
            f"{numbered}"
        )

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Parse JSON array from response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        translated = json.loads(content)

        if len(translated) == len(text_list):
            for orig, trans in zip(text_list, translated):
                texts_to_translate[orig] = trans
    except Exception:
        # Fallback: keep original Dutch text
        pass

    # Apply translations
    translated_events = []
    for evento in events:
        ev = dict(evento)
        for field in fields:
            val = ev.get(field)
            if val and val in texts_to_translate and texts_to_translate[val]:
                ev[field] = texts_to_translate[val]
        translated_events.append(ev)

    return translated_events


def _event_to_row(evento: dict, lang: str = "dut") -> list:
    """Genera fila B-U (20 columnas) matching formato original."""
    t = TRANSLATIONS.get(lang, TRANSLATIONS["dut"])
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
        _format_date(evento.get("fecha", evento.get("fecha_inicio", "")), lang),
        evento.get("nombre", ""),
        evento.get("partner_nombre") or _resolve_provider(evento.get("partner_id")) or "",
        evento.get("venue_nombre") or _resolve_venue(evento.get("venue_id")) or t["nvt"],
        evento.get("descripcion", ""),
        _format_hora(evento.get("hora"), lang),
        _format_precio(evento.get("precio")),
        _resolve_address(evento, lang),
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


def export_calendar(
    year: int = 2026,
    filter_status: Optional[str] = None,
    filter_contacto: Optional[str] = None,
    lang: str = "dut",
) -> str:
    """Exporta calendario JSON a Excel usando template original."""
    if lang not in VALID_LANGS:
        return f"Error: Idioma '{lang}' no soportado. Usa: {', '.join(VALID_LANGS)}"

    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    cal = _load_json(cal_path)
    if not cal:
        return f"Error: No existe calendario para {year}"

    template = os.path.normpath(TEMPLATE_PATH)
    if not os.path.exists(template):
        return f"Error: No se encuentra template Excel en {template}"

    # Recopilar eventos regulares
    all_events = list(cal.get("eventos", []))

    # Expandir eventos recurrentes en instancias individuales
    for rec in cal.get("eventos_recurrentes", []):
        if rec.get("expandir_en_export", True) is False:
            continue
        for instance in rec.get("instancias_2026", []):
            expanded = {**rec, **instance}
            expanded.pop("instancias_2026", None)
            expanded.pop("regla", None)
            all_events.append(expanded)

    # Ordenar por fecha
    all_events.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))

    # Filtros opcionales
    if filter_status:
        all_events = [e for e in all_events if e.get("estado") == filter_status]
    if filter_contacto:
        all_events = [e for e in all_events if filter_contacto in (e.get("contacto_ids") or [])]

    if not all_events:
        return "No hay eventos que coincidan con los filtros."

    # Traducir contenido si idioma != Dutch
    all_events = _translate_content(all_events, lang)
    rec_events = _translate_content(list(cal.get("eventos_recurrentes", [])[:2]), lang)

    # Copiar template al output
    output_path = os.path.join(DATA_DIR, f"NV_{year}_Jaarkalender_UPDATED_{lang}.xlsx")
    shutil.copy2(template, output_path)

    wb = load_workbook(output_path)
    ws = wb.active

    t = TRANSLATIONS.get(lang, TRANSLATIONS["dut"])

    # Escribir headers traducidos en row 3 (B3-U3)
    for col_offset, header in enumerate(t["headers"]):
        ws.cell(row=3, column=2 + col_offset, value=header)

    # Actualizar rows 4-5 (eventos recurrentes) desde JSON
    for idx, rec in enumerate(rec_events[:2]):
        row_num = 4 + idx
        row_data = _event_to_row(rec, lang)
        row_data[0] = rec.get("regla", ws.cell(row=row_num, column=2).value)
        for col_offset, value in enumerate(row_data):
            ws.cell(row=row_num, column=2 + col_offset, value=value)

    # Limpiar filas de datos (6+), preservar rows 1-3
    for row in range(DATA_START_ROW, ws.max_row + 1):
        for col in range(2, 22):  # B-U
            ws.cell(row=row, column=col).value = None

    # Copiar formato de row 6 (referencia) para filas que excedan el template
    template_max_row = ws.max_row
    ref_styles = {}
    for col in range(2, 22):
        ref_cell = ws.cell(row=DATA_START_ROW, column=col)
        ref_styles[col] = {
            "font": copy.copy(ref_cell.font),
            "fill": copy.copy(ref_cell.fill),
            "border": copy.copy(ref_cell.border),
            "alignment": copy.copy(ref_cell.alignment),
            "number_format": ref_cell.number_format,
        }

    # Escribir eventos en filas 6+
    for idx, evento in enumerate(all_events):
        row_num = DATA_START_ROW + idx
        row_data = _event_to_row(evento, lang)
        for col_offset, value in enumerate(row_data):
            cell = ws.cell(row=row_num, column=2 + col_offset, value=value)
            # Aplicar formato a filas que exceden el template original
            if row_num > template_max_row:
                style = ref_styles.get(2 + col_offset)
                if style:
                    cell.font = style["font"]
                    cell.fill = style["fill"]
                    cell.border = style["border"]
                    cell.alignment = style["alignment"]
                    cell.number_format = style["number_format"]

    last_data_row = DATA_START_ROW + len(all_events)

    # Reubicar imágenes del footer debajo de la última fila de datos
    footer_gap = 2  # filas de espacio entre datos y logos
    for img in ws._images:
        anchor = img.anchor
        if isinstance(anchor, TwoCellAnchor) and anchor._from.row >= 30:
            # Calcular offset relativo al inicio original del footer
            original_footer_start = 34  # row donde empezaban las imgs en V3
            row_offset = anchor._from.row - original_footer_start
            new_start = last_data_row + footer_gap + row_offset
            to_offset = anchor.to.row - anchor._from.row
            anchor._from.row = new_start
            anchor.to.row = new_start + to_offset

    wb.save(output_path)
    return output_path


class CalendarExporterInput(BaseModel):
    year: int = Field(default=2026, description="Año del calendario a exportar")
    filter_status: Optional[str] = Field(default=None, description="Filtrar por estado: confirmado, pendiente, cancelado")
    filter_contacto: Optional[str] = Field(default=None, description="Filtrar por contacto_id responsable")
    lang: str = Field(default="dut", description="Idioma: dut (holandés), eng (inglés), spa (español), por (portugués)")
    role: Optional[str] = Field(default=None, description="Rol del usuario: admin, tester, contacto, readonly")


def calendar_exporter(
    year: int = 2026,
    filter_status: Optional[str] = None,
    filter_contacto: Optional[str] = None,
    lang: str = "dut",
    role: Optional[str] = None,
) -> str:
    """Exporta el calendario a Excel. Wrapper para LangChain tool."""
    if role == "readonly":
        return "No tienes permisos para exportar. Contacta al administrador."
    path = export_calendar(year=year, filter_status=filter_status, filter_contacto=filter_contacto, lang=lang)
    if path.startswith("Error") or path.startswith("No hay"):
        return path
    return f"Calendario exportado exitosamente: {path}"


calendar_exporter_tool = StructuredTool.from_function(
    name="CalendarExporter",
    description=(
        "Exporta el calendario de eventos a Excel (.xlsx). "
        "Permite filtrar por año, estado o contacto responsable. "
        "Soporta idiomas: dut (holandés, default), eng (inglés), spa (español), por (portugués). "
        "El archivo se genera en kalendbot-data/ con sufijo de idioma."
    ),
    func=calendar_exporter,
    args_schema=CalendarExporterInput,
)


if __name__ == "__main__":
    import sys
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    lang = sys.argv[2] if len(sys.argv) > 2 else "dut"
    result = export_calendar(year=yr, lang=lang)
    print(result)
