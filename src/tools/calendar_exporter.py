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
            "Code", "Status",
            "1 omschrijving", "2 Tijdstip", "3 Entree", "4 Adres",
            "5 Info post/ FLYER:", "6 flyer moment", "7 contact persoon", "8 Celular",
            "Flyer oleadas", "Flyer resp.",
            "reel na event", "eventbrite", "whats", "inst FB TT", "email", "Texto Socials",
        ],
        "ntbp": "ntbp",
        "nvt": "nvt",
        "cancelled": "geanuleerd",
        "status_pendiente": "open",
        "status_confirmado": "bevestigd",
        "status_cancelado": "geanuleerd",
    },
    "eng": {
        "months": {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December",
        },
        "headers": [
            "Date", "Activity", "Partner", "Location",
            "Code", "Status",
            "1 Description", "2 Time", "3 Entry fee", "4 Address",
            "5 Info post/ FLYER:", "6 Flyer moment", "7 Contact person", "8 Phone",
            "Flyer waves", "Flyer resp.",
            "Reel after event", "Eventbrite", "WhatsApp", "Inst FB TT", "Email", "Social Text",
        ],
        "ntbp": "TBD",
        "nvt": "n/a",
        "cancelled": "cancelled",
        "status_pendiente": "pending",
        "status_confirmado": "confirmed",
        "status_cancelado": "cancelled",
    },
    "spa": {
        "months": {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        },
        "headers": [
            "Fecha", "Actividad", "Socio", "Ubicación",
            "Código", "Estado",
            "1 Descripción", "2 Horario", "3 Entrada", "4 Dirección",
            "5 Info post/ FLYER:", "6 Momento flyer", "7 Persona contacto", "8 Celular",
            "Oleadas flyer", "Resp. flyer",
            "Reel post evento", "Eventbrite", "WhatsApp", "Inst FB TT", "Email", "Texto Social",
        ],
        "ntbp": "por definir",
        "nvt": "n/a",
        "cancelled": "cancelado",
        "status_pendiente": "pendiente",
        "status_confirmado": "confirmado",
        "status_cancelado": "cancelado",
    },
    "por": {
        "months": {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
        },
        "headers": [
            "Data", "Atividade", "Parceiro", "Local",
            "Código", "Estado",
            "1 Descrição", "2 Horário", "3 Entrada", "4 Endereço",
            "5 Info post/ FLYER:", "6 Momento flyer", "7 Pessoa contacto", "8 Telefone",
            "Ondas flyer", "Resp. flyer",
            "Reel pós evento", "Eventbrite", "WhatsApp", "Inst FB TT", "Email", "Texto Social",
        ],
        "ntbp": "a definir",
        "nvt": "n/a",
        "cancelled": "cancelado",
        "status_pendiente": "pendente",
        "status_confirmado": "confirmado",
        "status_cancelado": "cancelado",
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


def _format_phone(tel) -> str:
    """Formats phone with country code prefix. Assumes +52 (Mexico) if no prefix."""
    s = str(tel).strip()
    if not s:
        return ""
    if s.startswith("+"):
        return s  # Already has international prefix
    if s.startswith("52") and len(s) >= 12:
        return f"+{s}"
    return f"+52{s}"


def _resolve_contact(contact_ids: list) -> tuple:
    nombres, telefonos = [], []
    for cid in (contact_ids or []):
        data = _load_json(os.path.join(DATA_DIR, "contactos", f"{cid}.json"))
        nombres.append(data.get("nombre", cid))
        tel = data.get("telefono", "")
        if tel:
            telefonos.append(_format_phone(tel))
    return (
        ", ".join(nombres),
        telefonos[0] if len(telefonos) == 1
        else ", ".join(telefonos) if telefonos
        else "",
    )


def _format_date(fecha_str: str, lang: str = "dut", fecha_exacta: bool = True) -> str:
    try:
        dt = datetime.fromisoformat(fecha_str)
        if not fecha_exacta and dt.day == 1:
            return f"ntbp {dt.month:02d}/{dt.year}"
        return f"{dt.day:02d}/{dt.month:02d}/{dt.year}"
    except (ValueError, TypeError):
        return fecha_str or ""


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
    if isinstance(precio, str):
        return precio  # Keep text descriptions like "100k/200volw"
    if isinstance(precio, dict):
        text = precio.get("texto")
        if text:
            return text
        return precio.get("mxn", 0)
    if isinstance(precio, (int, float)):
        return precio
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
            if val and isinstance(val, str) and val not in ("ntbp", "nvt", "n/a", "TBD", ""):
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


def _event_to_row(evento: dict, lang: str = "dut", code: str = "") -> list:
    """Genera fila B-W (22 columnas) matching formato original."""
    t = TRANSLATIONS.get(lang, TRANSLATIONS["dut"])
    nombre_contacto, tel_contacto = _resolve_contact(evento.get("contacto_ids"))
    canales = evento.get("canales", [])

    nvt = t["nvt"]

    # Col N: flyer oleadas (number or nvt)
    flyer_oleadas = evento.get("flyer_oleadas") or nvt

    # Col O: flyer responsable
    resp = evento.get("flyer_responsable", "")
    if resp == "nv":
        flyer_resp = CONTENT_MANAGER["nombre"]
    elif resp == "proveedor":
        flyer_resp = evento.get("flyer_responsable_nombre", "")
    elif resp == "ninguno":
        flyer_resp = nvt
    else:
        flyer_resp = nvt

    # Cancelled events show "geanuleerd" instead of date
    if evento.get("estado") == "cancelado":
        date_str = t["cancelled"]
    else:
        fecha_exacta = evento.get("fecha_exacta", True)
        date_str = _format_date(evento.get("fecha", evento.get("fecha_inicio", "")), lang, fecha_exacta)

    # hora: nvt for publications, ntbp for pending
    tier = evento.get("tier_promocion", "")
    hora_val = evento.get("hora")
    if hora_val:
        hora_str = hora_val
    elif tier == "publicacion":
        hora_str = nvt
    else:
        hora_str = t["ntbp"]

    # precio: nvt for null (publications, flyer-only), 0 for free events
    precio_raw = evento.get("precio")
    precio_val = nvt if precio_raw is None else _format_precio(precio_raw)

    # flyer_moment: nvt if no flyer needed
    flyer_moment = evento.get("flyer_moment", "") or nvt

    # Translated status
    estado = evento.get("estado", "")
    status_key = f"status_{estado}"
    status_str = t.get(status_key, estado)

    return [
        date_str,
        evento.get("nombre", ""),
        evento.get("partner_nombre") or _resolve_provider(evento.get("partner_id")) or "",
        evento.get("venue_nombre") or _resolve_venue(evento.get("venue_id")) or nvt,
        code or evento.get("id", ""),
        status_str,
        evento.get("descripcion", ""),
        hora_str,
        precio_val,
        _resolve_address(evento, lang),
        evento.get("detalle") or nvt,
        flyer_moment,
        nombre_contacto,
        tel_contacto,
        flyer_oleadas,
        flyer_resp,
        "reel aft" if evento.get("reel_post") else nvt,
        "eventbrite" if evento.get("eventbrite") else nvt,
        "whats" if "whatsapp" in canales else nvt,
        "inst FB TT" if "rrss" in canales else nvt,
        "email" if "email" in canales else nvt,
        evento.get("texto_social", ""),
    ]


def _prepare_calendar_data(
    year: int = 2026,
    filter_status: Optional[str] = None,
    filter_contacto: Optional[str] = None,
    lang: str = "dut",
) -> tuple[list, list, dict] | str:
    """
    Carga JSON, expande recurrentes, ordena, filtra, traduce.
    Retorna (all_events, rec_events, translations) o string de error.
    """
    if lang not in VALID_LANGS:
        return f"Error: Idioma '{lang}' no soportado. Usa: {', '.join(VALID_LANGS)}"

    cal_path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    cal = _load_json(cal_path)
    if not cal:
        return f"Error: No existe calendario para {year}"

    all_events = list(cal.get("eventos", []))

    for rec in cal.get("eventos_recurrentes", []):
        if rec.get("expandir_en_export", True) is False:
            continue
        for instance in rec.get("instancias_2026", []):
            expanded = {**rec, **instance}
            expanded.pop("instancias_2026", None)
            expanded.pop("regla", None)
            expanded["nombre"] = rec.get("nombre_corto", rec.get("nombre", ""))
            expanded["canales"] = []
            expanded["_expanded"] = True
            all_events.append(expanded)

    all_events.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))

    # Filter hidden events
    all_events = [e for e in all_events if e.get("show_in_export", True)]

    if filter_status:
        all_events = [e for e in all_events if e.get("estado") == filter_status]
    if filter_contacto:
        all_events = [e for e in all_events if filter_contacto in (e.get("contacto_ids") or [])]

    if not all_events:
        return "No hay eventos que coincidan con los filtros."

    all_events = _translate_content(all_events, lang)
    rec_events = _translate_content(list(cal.get("eventos_recurrentes", [])[:2]), lang)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["dut"])

    return all_events, rec_events, t


def export_calendar(
    year: int = 2026,
    filter_status: Optional[str] = None,
    filter_contacto: Optional[str] = None,
    lang: str = "dut",
) -> str:
    """Exporta calendario JSON a Excel usando template original."""
    result = _prepare_calendar_data(year, filter_status, filter_contacto, lang)
    if isinstance(result, str):
        return result
    all_events, rec_events, t = result

    template = os.path.normpath(TEMPLATE_PATH)
    if not os.path.exists(template):
        return f"Error: No se encuentra template Excel en {template}"

    # Copiar template al output
    output_path = os.path.join(DATA_DIR, f"NV_{year}_Jaarkalender_UPDATED_{lang}.xlsx")
    shutil.copy2(template, output_path)

    wb = load_workbook(output_path)
    ws = wb.active

    # Escribir headers traducidos en row 3 (B3-W3)
    for col_offset, header in enumerate(t["headers"]):
        ws.cell(row=3, column=2 + col_offset, value=header)

    # Actualizar rows 4-5 (eventos recurrentes) desde JSON
    for idx, rec in enumerate(rec_events[:2]):
        row_num = 4 + idx
        rec_code = f"R{idx + 1}"
        row_data = _event_to_row(rec, lang, code=rec_code)
        row_data[0] = rec.get("regla", ws.cell(row=row_num, column=2).value)
        for col_offset, value in enumerate(row_data):
            ws.cell(row=row_num, column=2 + col_offset, value=value)

    # Limpiar filas de datos (6+), preservar rows 1-3
    for row in range(DATA_START_ROW, ws.max_row + 1):
        for col in range(2, 24):  # B-W
            ws.cell(row=row, column=col).value = None

    # Copiar formato de row 6 (referencia) para filas que excedan el template
    template_max_row = ws.max_row
    ref_styles = {}
    for col in range(2, 24):
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
        event_code = str(idx + 1)
        row_data = _event_to_row(evento, lang, code=event_code)
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


# ---------------------------------------------------------------------------
# JPEG Export
# ---------------------------------------------------------------------------

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logos")

JPEG_TITLES = {
    "dut": "Voorlopige Jaarplanning NV Mexico {year}",
    "eng": "Annual Calendar NV Mexico {year}",
    "spa": "Planificación Anual NV Mexico {year}",
    "por": "Planejamento Anual NV Mexico {year}",
}

# Column indices in _event_to_row() output to show in JPEG
JPEG_COL_INDICES = [0, 1, 2, 3]  # Datum, Activiteit, Partner, Locatie
JPEG_CODES_COL_INDICES = [4, 0, 1, 2, 3]  # Code, Datum, Activiteit, Partner, Locatie


def _img_to_data_uri(path: str) -> str:
    """Encode image file as base64 data URI for HTML embedding."""
    import base64
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    return f"data:{mime};base64,{data}"


def _build_calendar_html(
    rows: list[list[str]],
    headers: list[str],
    title: str,
) -> str:
    """Build self-contained HTML matching the reference JPEG layout."""
    from html import escape

    nv_logo = _img_to_data_uri(os.path.join(ASSETS_DIR, "nv-mexico-logo.png"))
    ips_logo = _img_to_data_uri(os.path.join(ASSETS_DIR, "ips-logo.png"))
    hw_logo = _img_to_data_uri(os.path.join(ASSETS_DIR, "holland-wafels-logo.jpeg"))
    nl_logo = _img_to_data_uri(os.path.join(ASSETS_DIR, "netherlands-coat-of-arms.png"))

    tbody = "\n".join(
        "<tr>" + "".join(f"<td>{escape(v)}</td>" for v in row) + "</tr>"
        for row in rows
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: 906px;
    font-family: Calibri, 'Segoe UI', Arial, Helvetica, sans-serif;
    background: white;
    -webkit-font-smoothing: antialiased;
}}
.header {{
    display: flex;
    align-items: center;
    height: 80px;
    padding: 3px 3px 0 3px;
}}
.logo-nv {{ height: 72px; margin-right: 10px; }}
.title {{ flex: 1; text-align: center; font-size: 22px; font-weight: bold; }}
table {{
    width: 900px;
    margin: 0 3px;
    border-collapse: collapse;
    table-layout: fixed;
    border: 1px solid #999;
}}
col.c0 {{ width: 140px; }}
col.c1 {{ width: 260px; }}
col.c2 {{ width: 230px; }}
col.c3 {{ width: 270px; }}
th {{
    background: #b0b0b0;
    font-size: 10pt;
    font-weight: bold;
    padding: 3px 5px;
    text-align: left;
    border: 1px solid #999;
}}
td {{
    font-size: 9pt;
    padding: 2px 5px;
    border-bottom: 1px solid #d0d0d0;
    border-right: 1px solid #d0d0d0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
td:last-child {{ border-right: none; }}
.footer {{
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 15px 40px;
    height: 120px;
}}
.footer img {{ max-height: 95px; }}
</style></head>
<body>
<div class="header">
    <img src="{nv_logo}" class="logo-nv">
    <div class="title">{escape(title)}</div>
</div>
<table>
    <colgroup><col class="c0"><col class="c1"><col class="c2"><col class="c3"></colgroup>
    <thead><tr><th>{escape(headers[0])}</th><th>{escape(headers[1])}</th><th>{escape(headers[2])}</th><th>{escape(headers[3])}</th></tr></thead>
    <tbody>{tbody}</tbody>
</table>
<div class="footer">
    <img src="{ips_logo}">
    <img src="{hw_logo}">
    <img src="{nl_logo}">
</div>
</body></html>"""


def export_calendar_as_jpeg(
    year: int = 2026,
    filter_status: Optional[str] = None,
    lang: str = "dut",
) -> str:
    """Genera JPEG del calendario via HTML+Chrome headless rendering."""
    result = _prepare_calendar_data(year, filter_status, lang=lang)
    if isinstance(result, str):
        return result
    all_events, rec_events, t = result

    # Build table rows
    rows = []
    for idx, rec in enumerate(rec_events[:2]):
        row = _event_to_row(rec, lang, code=f"R{idx+1}")
        row[0] = rec.get("regla", "")
        rows.append([str(row[i]) if row[i] is not None else "" for i in JPEG_COL_INDICES])
    for idx, evento in enumerate(all_events):
        row = _event_to_row(evento, lang, code=str(idx + 1))
        rows.append([str(row[i]) if row[i] is not None else "" for i in JPEG_COL_INDICES])

    headers = [t["headers"][i] for i in JPEG_COL_INDICES]
    title = JPEG_TITLES.get(lang, JPEG_TITLES["dut"]).format(year=year)
    html = _build_calendar_html(rows, headers, title)

    # Viewport height: generous to avoid clipping
    viewport_h = 80 + 22 + len(rows) * 20 + 130 + 80

    from html2image import Html2Image
    from PIL import Image, ImageChops

    hti = Html2Image(
        output_path=DATA_DIR,
        size=(906, viewport_h),
        custom_flags=["--no-sandbox", "--disable-gpu", "--hide-scrollbars"],
    )
    temp_png = f"_temp_{year}_{lang}.png"
    hti.screenshot(html_str=html, save_as=temp_png)

    # Trim bottom whitespace and convert to JPEG
    png_path = os.path.join(DATA_DIR, temp_png)
    img = Image.open(png_path)
    bg = Image.new(img.mode, img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        img = img.crop((0, 0, img.width, bbox[3] + 8))

    output_path = os.path.join(DATA_DIR, f"NV_{year}_Jaarplanning_{lang}.jpeg")
    img.convert("RGB").save(output_path, "JPEG", quality=92)

    try:
        os.remove(png_path)
    except OSError:
        pass
    return output_path


def export_calendar_as_jpeg_codes(
    year: int = 2026,
    filter_status: Optional[str] = None,
    lang: str = "dut",
) -> str:
    """Genera JPEG del calendario con columna de códigos de actividad."""
    result = _prepare_calendar_data(year, filter_status, lang=lang)
    if isinstance(result, str):
        return result
    all_events, rec_events, t = result

    rows = []
    for idx, rec in enumerate(rec_events[:2]):
        row = _event_to_row(rec, lang, code=f"R{idx+1}")
        row[0] = rec.get("regla", "")
        rows.append([str(row[i]) if row[i] is not None else "" for i in JPEG_CODES_COL_INDICES])
    for idx, evento in enumerate(all_events):
        row = _event_to_row(evento, lang, code=str(idx + 1))
        rows.append([str(row[i]) if row[i] is not None else "" for i in JPEG_CODES_COL_INDICES])

    headers = [t["headers"][i] for i in JPEG_CODES_COL_INDICES]
    title = JPEG_TITLES.get(lang, JPEG_TITLES["dut"]).format(year=year) + " — Codes"
    html = _build_calendar_html(rows, headers, title)

    viewport_h = 80 + 22 + len(rows) * 20 + 130 + 80

    from html2image import Html2Image
    from PIL import Image, ImageChops

    hti = Html2Image(
        output_path=DATA_DIR,
        size=(960, viewport_h),
        custom_flags=["--no-sandbox", "--disable-gpu", "--hide-scrollbars"],
    )
    temp_png = f"_temp_{year}_{lang}_codes.png"
    hti.screenshot(html_str=html, save_as=temp_png)

    png_path = os.path.join(DATA_DIR, temp_png)
    img = Image.open(png_path)
    bg = Image.new(img.mode, img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        img = img.crop((0, 0, img.width, bbox[3] + 8))

    output_path = os.path.join(DATA_DIR, f"NV_{year}_Codes_{lang}.jpeg")
    img.convert("RGB").save(output_path, "JPEG", quality=92)

    try:
        os.remove(png_path)
    except OSError:
        pass
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
    fmt = sys.argv[3] if len(sys.argv) > 3 else "xlsx"
    if fmt == "jpeg":
        result = export_calendar_as_jpeg(year=yr, lang=lang)
    else:
        result = export_calendar(year=yr, lang=lang)
    print(result)
