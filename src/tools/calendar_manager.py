"""
Tool 1: CalendarManager
Lee, actualiza y edita el calendario de eventos (JSON).
Soporta edición batch con preview, confirmación y undo.
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger("kalendbot.calendar_manager")

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")

VALID_STATUSES = {"pendiente", "confirmado", "cancelado"}

# Field metadata: field → (type, validation, permission, impact_categories)
# permission: "owner" = admin + contacto who owns event, "admin" = admin/tester only
_FIELD_META = {
    "fecha":                    ("date",   None, "owner", ["recordatorios", "conflictos", "flyers", "grupo", "export"]),
    "fecha_inicio":             ("date",   None, "owner", ["recordatorios", "export"]),
    "fecha_fin":                ("date",   None, "owner", ["export"]),
    "fecha_exacta":             ("bool",   None, "owner", ["export"]),
    "nota_fecha":               ("str",    None, "owner", []),
    "nombre":                   ("str",    None, "owner", ["recordatorios", "grupo", "export"]),
    "hora":                     ("str",    None, "owner", ["export"]),
    "hora_detalle":             ("str",    None, "owner", ["export"]),
    "venue_nombre":             ("str",    None, "owner", ["export"]),
    "venue_direccion":          ("str",    None, "owner", ["export"]),
    "partner_nombre":           ("str",    None, "owner", ["export"]),
    "precio":                   ("precio", None, "owner", ["export"]),
    "descripcion":              ("str",    None, "owner", ["export"]),
    "detalle":                  ("str",    None, "owner", ["grupo", "export"]),
    "tier_promocion":           ("enum",   {"regular", "mediano", "grande", "delegado", "publicacion", "ninguno"}, "admin", ["flyers", "export"]),
    "flyer_responsable":        ("enum",   {"nv", "proveedor", "ninguno"}, "admin", ["flyers"]),
    "flyer_responsable_nombre": ("str",    None, "admin", ["flyers"]),
    "flyer_oleadas":            ("int",    None, "admin", ["flyers", "export"]),
    "flyer_moment":             ("str",    None, "admin", ["flyers", "recordatorios"]),
    "reel_post":                ("bool",   None, "owner", ["export"]),
    "eventbrite":               ("bool",   None, "owner", ["export"]),
    "delegado":                 ("bool",   None, "admin", []),
}

_IMPACT_LABELS = {
    "recordatorios": "recordatorios",
    "conflictos": "conflictos de fecha",
    "flyers": "flujo de flyers",
    "grupo": "notificación al grupo",
    "export": "export (Excel/JPEG)",
}


def _load_calendar(year: int = 2026) -> dict:
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_calendar(data: dict, year: int = 2026):
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Batch editing helpers ---

def _parse_changes(changes_str: str) -> list[tuple[str, str]]:
    """Parse 'campo1=val1|campo2=val2' into list of (field, raw_value)."""
    if not changes_str:
        return []
    result = []
    for pair in changes_str.split("|"):
        pair = pair.strip()
        if "=" not in pair:
            continue
        field, value = pair.split("=", 1)
        result.append((field.strip(), value.strip()))
    return result


def _parse_field_value(raw: str, field_type: str, validation=None):
    """Convert string to correct Python type. Returns (value, error_msg)."""
    if field_type == "date":
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw, None
        except ValueError:
            return None, f"Formato inválido '{raw}', usa YYYY-MM-DD"
    elif field_type == "bool":
        if raw.lower() in ("true", "si", "sí", "verdadero", "1"):
            return True, None
        if raw.lower() in ("false", "no", "falso", "0"):
            return False, None
        return None, f"Valor booleano inválido '{raw}', usa true/false o si/no"
    elif field_type == "int":
        try:
            return int(raw), None
        except ValueError:
            return None, f"Valor numérico inválido '{raw}'"
    elif field_type == "enum":
        if raw.lower() in validation:
            return raw.lower(), None
        return None, f"Valor '{raw}' no válido. Opciones: {', '.join(sorted(validation))}"
    elif field_type == "precio":
        low = raw.lower().strip()
        if low in ("na", "nvt", "null", "ninguno"):
            return None, None
        if low in ("0", "gratis", "free"):
            return 0, None
        try:
            return {"mxn": int(raw)}, None
        except ValueError:
            try:
                return {"mxn": float(raw)}, None
            except ValueError:
                return raw, None  # text-based pricing like "100k/200volw"
    # str
    return raw, None


def _find_event(cal: dict, event_id: str, instance_fecha: str = None):
    """Find event in eventos or recurrentes. Returns (parent, target, is_instance)."""
    for e in cal.get("eventos", []):
        if e["id"] == event_id:
            return e, e, False
    for rec in cal.get("eventos_recurrentes", []):
        if rec["id"] == event_id:
            if instance_fecha:
                for inst in rec.get("instancias_2026", []):
                    if inst.get("fecha") == instance_fecha:
                        return rec, inst, True
                return rec, None, True  # instance not found
            return rec, rec, False
    return None, None, False


def _check_field_permission(field_name: str, role: str, contact_id: str, event: dict) -> str | None:
    """Check if role can edit field on event. Returns error message or None."""
    if role == "readonly":
        return "No tienes permisos para editar eventos"
    meta = _FIELD_META.get(field_name)
    if not meta:
        valid = ", ".join(sorted(_FIELD_META.keys()))
        return f"Campo '{field_name}' no es editable. Campos válidos: {valid}"
    _, _, perm, _ = meta
    if perm == "admin" and role not in ("admin", "tester"):
        return f"Campo '{field_name}' solo editable por admin"
    if role == "contacto" and contact_id not in event.get("contacto_ids", []):
        return "No tienes permisos sobre este evento"
    return None


def _check_past_date_change(target: dict, parsed_changes: list[tuple[str, str]], role: str) -> str | None:
    """Block date changes on past events for non-admin roles."""
    if role in ("admin", "tester"):
        return None

    date_fields = {"fecha", "fecha_inicio", "fecha_fin"}
    date_changes = [(f, v) for f, v in parsed_changes if f in date_fields]
    if not date_changes:
        return None

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Check 1: Is the event's current date in the past?
    event_date = target.get("fecha") or target.get("fecha_inicio")
    if event_date:
        try:
            event_dt = datetime.strptime(event_date, "%Y-%m-%d")
            if event_dt < today:
                return (
                    "No se puede cambiar la fecha de un evento pasado. "
                    f"El evento tiene fecha {event_date} que ya ocurrió. "
                    "Contacta al administrador para autorización."
                )
        except ValueError:
            pass

    # Check 2: Is the new date in the past?
    for field, new_date in date_changes:
        try:
            new_dt = datetime.strptime(new_date, "%Y-%m-%d")
            if new_dt < today:
                return (
                    f"No se puede asignar una fecha pasada ({new_date}) a un evento. "
                    f"Hoy es {today.strftime('%Y-%m-%d')}. "
                    "Contacta al administrador para autorización."
                )
        except ValueError:
            pass

    return None


def _build_compact_diagnostics(changed_fields: list[str]) -> str:
    """Build aggregated impact one-liner from changed fields."""
    categories = set()
    for field in changed_fields:
        meta = _FIELD_META.get(field)
        if meta:
            categories.update(meta[3])
    if not categories:
        return ""
    labels = [_IMPACT_LABELS.get(c, c) for c in sorted(categories)]
    return "⚠️ Impacto: " + ", ".join(labels)


def _format_value(val) -> str:
    """Format a value for display in diff output."""
    if val is None:
        return "null"
    if isinstance(val, dict):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


# --- Schema ---

class CalendarManagerInput(BaseModel):
    action: str = Field(
        description="Acción: list_all, get_event, search_event, list_by_status, list_by_contact, "
                    "list_pending, list_upcoming, update_status, update_show_export, "
                    "batch_preview, batch_confirm, undo_last"
    )
    year: int = Field(default=2026, description="Año del calendario")
    event_id: Optional[str] = Field(default=None, description="ID del evento")
    status: Optional[str] = Field(
        default=None,
        description="Estado (para list_by_status, update_status). "
                    "También fecha YYYY-MM-DD de instancia recurrente "
                    "(para update_show_export, batch_preview, batch_confirm, undo_last)"
    )
    contact_id: Optional[str] = Field(default=None, description="ID del contacto")
    show_in_export: Optional[bool] = Field(default=None, description="Mostrar en exports (para update_show_export)")
    changes: Optional[str] = Field(
        default=None,
        description="Cambios en formato 'campo=valor|campo2=valor2' (para batch_preview, batch_confirm). "
                    "Campos editables: fecha, nombre, hora, venue_nombre, venue_direccion, partner_nombre, "
                    "precio, descripcion, detalle, tier_promocion, flyer_responsable, flyer_oleadas, "
                    "flyer_moment, reel_post, eventbrite, delegado, fecha_exacta, nota_fecha, hora_detalle, "
                    "flyer_responsable_nombre, fecha_inicio, fecha_fin"
    )
    role: Optional[str] = Field(default=None, description="Rol del usuario: admin, tester, contacto, readonly")


def calendar_manager(
    action: str,
    year: int = 2026,
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    contact_id: Optional[str] = None,
    show_in_export: Optional[bool] = None,
    changes: Optional[str] = None,
    role: Optional[str] = None,
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

    elif action == "search_event":
        if not event_id:
            return "Error: Falta event_id (texto de búsqueda)"
        query = event_id.lower()
        results = []
        for e in all_events:
            if query in e["id"].lower() or query in e.get("nombre", "").lower() or query in e.get("nombre_corto", "").lower():
                fecha = e.get("fecha", e.get("fecha_inicio", "sin fecha"))
                results.append(f"{e['id']}: {e.get('nombre', '')} — {fecha} [{e.get('estado', '')}]")
        for rec in recurrentes:
            if query in rec["id"].lower() or query in rec.get("nombre", "").lower() or query in rec.get("nombre_corto", "").lower():
                instancias = rec.get("instancias_2026", [])
                fechas = ", ".join(inst.get("fecha", "?") for inst in instancias[:6])
                results.append(f"{rec['id']}: {rec.get('nombre', '')} (recurrente) — fechas: {fechas}")
        if not results:
            return f"No se encontraron eventos que coincidan con '{event_id}'"
        return "\n".join(results)

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
        # Collect pending from regular events
        pending = [e for e in all_events if e.get("estado") == "pendiente"]
        # Also collect pending instances from recurring events
        for rec in recurrentes:
            for inst in rec.get("instancias_2026", []):
                if inst.get("estado") == "pendiente":
                    pending.append({
                        "id": rec["id"],
                        "nombre": rec.get("nombre_corto", rec.get("nombre", rec["id"])),
                        "fecha": inst.get("fecha"),
                        "contacto_ids": rec.get("contacto_ids", []),
                        "fecha_exacta": inst.get("fecha_exacta", True),
                        "_recurrente": True,
                    })
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
                rec_tag = " [R]" if e.get("_recurrente") else ""
                lines.append(f"{e.get('fecha', e.get('fecha_inicio', 'sin fecha'))}{exacta} | {e['id']}: {e['nombre']}{rec_tag} | {contactos}")
        if past:
            lines.append(f"\n═══ PENDIENTES PASADOS — requieren actualización ({len(past)}) ═══")
            for e in past:
                contactos = ", ".join(e.get("contacto_ids", []))
                rec_tag = " [R]" if e.get("_recurrente") else ""
                lines.append(f"⚠️ {e.get('fecha', 'sin fecha')} | {e['id']}: {e['nombre']}{rec_tag} | {contactos}")

        if not lines:
            return "No hay eventos pendientes"
        return "\n".join(lines)

    elif action == "list_upcoming":
        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = [e for e in all_events if e.get("fecha", e.get("fecha_inicio", "0000-01-01")) >= today and e.get("estado") != "cancelado"]
        for rec in recurrentes:
            for inst in rec.get("instancias_2026", []):
                if inst.get("fecha", "0000-01-01") >= today and inst.get("estado") != "cancelado":
                    upcoming.append({
                        "id": rec["id"],
                        "nombre": rec.get("nombre_corto", rec.get("nombre", rec["id"])),
                        "fecha": inst.get("fecha"),
                        "estado": inst.get("estado", "pendiente"),
                        "fecha_exacta": inst.get("fecha_exacta", True),
                        "_recurrente": True,
                    })
        upcoming.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))
        if not upcoming:
            return "No hay eventos próximos"
        lines = []
        for e in upcoming:
            estado = e.get("estado", "desconocido").upper()
            exacta = "" if e.get("fecha_exacta", True) else " (aprox)"
            rec_tag = " [R]" if e.get("_recurrente") else ""
            lines.append(f"[{estado}] {e.get('fecha', e.get('fecha_inicio', 'sin fecha'))}{exacta} | {e['id']}: {e['nombre']}{rec_tag}")
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
        for e in all_events:
            if e["id"] == event_id:
                old_val = e.get("show_in_export", True)
                e["show_in_export"] = show_in_export
                e["ultima_actualizacion"] = datetime.now().isoformat()
                _save_calendar(cal, year)
                return f"Evento '{event_id}' show_in_export: {old_val} → {show_in_export}"
        for rec in recurrentes:
            if rec["id"] == event_id:
                if status:
                    for inst in rec.get("instancias_2026", []):
                        if inst.get("fecha") == status:
                            old_val = inst.get("show_in_export", True)
                            inst["show_in_export"] = show_in_export
                            _save_calendar(cal, year)
                            return f"Instancia '{event_id}' fecha {status} show_in_export: {old_val} → {show_in_export}"
                    return f"Instancia con fecha '{status}' no encontrada en '{event_id}'"
                else:
                    old_val = rec.get("show_in_export", True)
                    rec["show_in_export"] = show_in_export
                    _save_calendar(cal, year)
                    return f"Evento recurrente '{event_id}' show_in_export: {old_val} → {show_in_export}"
        return f"Evento '{event_id}' no encontrado"

    elif action == "batch_preview":
        if not event_id or not changes:
            return "Error: Faltan event_id y/o changes (formato: campo=valor|campo2=valor2)"
        parsed_changes = _parse_changes(changes)
        if not parsed_changes:
            return "Error: No se encontraron cambios válidos en formato campo=valor"

        instance_fecha = status if status and len(status) == 10 else None
        parent, target, is_instance = _find_event(cal, event_id, instance_fecha)
        if not parent:
            return f"Evento '{event_id}' no encontrado"
        if is_instance and target is None:
            return f"Instancia con fecha '{instance_fecha}' no encontrada en '{event_id}'"

        # Block date changes on past finalized events
        past_err = _check_past_date_change(target, parsed_changes, role or "readonly")
        if past_err:
            return past_err

        errors = []
        diffs = []
        changed_fields = []
        for field, raw_val in parsed_changes:
            perm_err = _check_field_permission(field, role or "readonly", contact_id or "", parent)
            if perm_err:
                errors.append(f"  {field}: {perm_err}")
                continue
            meta = _FIELD_META[field]
            parsed_val, parse_err = _parse_field_value(raw_val, meta[0], meta[1])
            if parse_err:
                errors.append(f"  {field}: {parse_err}")
                continue
            old_val = target.get(field)
            diffs.append(f"  {field}: {_format_value(old_val)} → {_format_value(parsed_val)}")
            changed_fields.append(field)

        if errors:
            return "Error en cambios:\n" + "\n".join(errors)

        nombre = parent.get("nombre", event_id)
        inst_label = f" (instancia {instance_fecha})" if is_instance else ""
        lines = [f"═══ CAMBIOS: {nombre}{inst_label} ═══"]
        lines.extend(diffs)

        diag = _build_compact_diagnostics(changed_fields)
        if diag:
            lines.append(diag)

        # Conflict detection for date fields
        date_fields = {"fecha", "fecha_inicio", "fecha_fin"}
        for field, raw_val in parsed_changes:
            if field in date_fields and field in changed_fields:
                try:
                    from src.tools.conflict_detector import conflict_detector
                    conflict_result = conflict_detector(raw_val)
                    if "CONFLICTOS:" in conflict_result or "ADVERTENCIAS:" in conflict_result:
                        lines.append(conflict_result)
                    else:
                        lines.append(f"✅ Fecha {raw_val}: sin conflictos")
                except Exception as e:
                    logger.warning(f"ConflictDetector error: {e}")

        lines.append("Puedes deshacer después de aplicar.")
        return "\n".join(lines)

    elif action == "batch_confirm":
        if not event_id or not changes:
            return "Error: Faltan event_id y/o changes"
        parsed_changes = _parse_changes(changes)
        if not parsed_changes:
            return "Error: No se encontraron cambios válidos"

        instance_fecha = status if status and len(status) == 10 else None
        parent, target, is_instance = _find_event(cal, event_id, instance_fecha)
        if not parent:
            return f"Evento '{event_id}' no encontrado"
        if is_instance and target is None:
            return f"Instancia con fecha '{instance_fecha}' no encontrada en '{event_id}'"

        # Block date changes on past finalized events
        past_err = _check_past_date_change(target, parsed_changes, role or "readonly")
        if past_err:
            return past_err

        # Validate all changes first
        to_apply = []
        errors = []
        for field, raw_val in parsed_changes:
            perm_err = _check_field_permission(field, role or "readonly", contact_id or "", parent)
            if perm_err:
                errors.append(f"  {field}: {perm_err}")
                continue
            meta = _FIELD_META[field]
            parsed_val, parse_err = _parse_field_value(raw_val, meta[0], meta[1])
            if parse_err:
                errors.append(f"  {field}: {parse_err}")
                continue
            to_apply.append((field, parsed_val))

        if errors:
            return "Error en cambios:\n" + "\n".join(errors)

        # Build undo snapshot (store old values)
        undo = {}
        for field, _ in to_apply:
            undo[field] = target.get(field)
        target["_undo_snapshot"] = {
            "timestamp": datetime.now().isoformat(),
            "user": contact_id or "unknown",
            "changes": undo,
        }

        # Apply all changes
        diffs = []
        for field, new_val in to_apply:
            old_val = target.get(field)
            target[field] = new_val
            diffs.append(f"  {field}: {_format_value(old_val)} → {_format_value(new_val)}")
            if field == "fecha" and old_val is not None:
                target["fecha_original"] = old_val

        target["ultima_actualizacion"] = datetime.now().isoformat()
        _save_calendar(cal, year)

        nombre = parent.get("nombre", event_id)
        lines = [f"✓ {nombre}: {len(to_apply)} campo(s) actualizado(s)"]
        lines.extend(diffs)
        lines.append(f'Escribe "deshacer cambios en {nombre}" para revertir.')
        return "\n".join(lines)

    elif action == "undo_last":
        if not event_id:
            return "Error: Falta event_id"

        instance_fecha = status if status and len(status) == 10 else None
        parent, target, is_instance = _find_event(cal, event_id, instance_fecha)
        if not parent:
            return f"Evento '{event_id}' no encontrado"
        if is_instance and target is None:
            return f"Instancia con fecha '{instance_fecha}' no encontrada en '{event_id}'"

        snapshot = target.get("_undo_snapshot")
        if not snapshot:
            return f"No hay cambios para deshacer en '{event_id}'"

        old_changes = snapshot.get("changes", {})
        restored = []
        for field, old_val in old_changes.items():
            if old_val is None:
                target.pop(field, None)
            else:
                target[field] = old_val
            restored.append(f"  {field}: {_format_value(old_val)}")

        if "fecha" in old_changes:
            target.pop("fecha_original", None)

        del target["_undo_snapshot"]
        target["ultima_actualizacion"] = datetime.now().isoformat()
        _save_calendar(cal, year)

        nombre = parent.get("nombre", event_id)
        lines = [f"↩ {nombre}: {len(restored)} campo(s) revertido(s)"]
        lines.extend(restored)
        return "\n".join(lines)

    else:
        return (
            f"Acción desconocida: {action}. Opciones: list_all, get_event, search_event, "
            "list_by_status, list_by_contact, list_pending, list_upcoming, update_status, "
            "update_show_export, batch_preview, batch_confirm, undo_last"
        )


calendar_manager_tool = StructuredTool.from_function(
    name="CalendarManager",
    description=(
        "Gestiona el calendario de eventos de NV Mexico. Acciones: "
        "list_all, get_event, search_event (buscar por nombre parcial, usa event_id como texto de búsqueda), "
        "list_by_status, list_by_contact, "
        "list_pending (pendientes futuros/pasados, incluye recurrentes), list_upcoming (futuros no cancelados), "
        "update_status (pendiente/confirmado/cancelado), "
        "update_show_export (mostrar/ocultar en exports), "
        "batch_preview (preview de cambios con diagnóstico de impacto), "
        "batch_confirm (aplicar cambios con opción de undo), "
        "undo_last (deshacer último cambio). "
        "Para editar campos: changes='campo=valor|campo2=valor2'. "
        "Para instancias recurrentes: status=YYYY-MM-DD."
    ),
    func=calendar_manager,
    args_schema=CalendarManagerInput,
)
