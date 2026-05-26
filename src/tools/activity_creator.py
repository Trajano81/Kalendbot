"""
Tool: ActivityCreator
Creates new events in the calendar with validation, conflict detection,
and sorted insertion by date.
"""
import json
import os
import re
import logging
import unicodedata
from datetime import datetime
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger("kalendbot.activity_creator")

DATA_DIR = settings.data_dir
PROVIDERS_DIR = os.path.join(DATA_DIR, "proveedores")
CONTACTS_DIR = os.path.join(DATA_DIR, "contactos")

VALID_STATUSES = {"pendiente", "confirmado"}
VALID_TIERS = {"regular", "mediano", "grande", "delegado", "publicacion", "ninguno"}
VALID_FLYER_RESP = {"nv", "proveedor", "ninguno"}


def _load_calendar(year: int = 2026) -> dict:
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_calendar(data: dict, year: int = 2026):
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _slugify(text: str) -> str:
    """Generate a slug ID from event name."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _validate_fields(
    nombre: str,
    fecha: str,
    estado: str,
    contacto_ids_str: str,
    partner_id: str,
    tier_promocion: str,
    flyer_responsable: str,
    role: str | None,
    contact_id: str | None,
    cal: dict,
) -> tuple[list[str], str, list[str]]:
    """
    Validate all fields for a new event.
    Returns (errors, generated_slug, parsed_contacto_ids).
    """
    errors = []

    # Permission check
    if role == "readonly":
        errors.append("No tienes permisos para crear eventos")
        return errors, "", []

    # Nombre
    if not nombre or not nombre.strip():
        errors.append("El nombre del evento es obligatorio")

    # Slug
    slug = _slugify(nombre) if nombre else ""
    if slug:
        existing_ids = {e["id"] for e in cal.get("eventos", [])}
        existing_ids.update(e["id"] for e in cal.get("eventos_recurrentes", []))
        if slug in existing_ids:
            errors.append(f"Ya existe un evento con ID '{slug}'. Usa un nombre diferente")

    # Fecha
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        if fecha_dt.date() < datetime.now().date():
            if role in ("admin", "tester"):
                pass  # admin gets warning in preview, not blocked
            else:
                errors.append("No se pueden crear eventos en fechas pasadas")
    except ValueError:
        errors.append(f"Formato de fecha invalido '{fecha}'. Usa YYYY-MM-DD")

    # Estado
    if estado not in VALID_STATUSES:
        errors.append(f"Estado invalido '{estado}'. Opciones: {', '.join(sorted(VALID_STATUSES))}")

    # Tier
    if tier_promocion not in VALID_TIERS:
        errors.append(f"Tier invalido '{tier_promocion}'. Opciones: {', '.join(sorted(VALID_TIERS))}")

    # Flyer responsable
    if flyer_responsable not in VALID_FLYER_RESP:
        errors.append(f"Flyer responsable invalido '{flyer_responsable}'. Opciones: {', '.join(sorted(VALID_FLYER_RESP))}")

    # Partner
    if partner_id:
        partner_path = os.path.join(PROVIDERS_DIR, f"{partner_id}.json")
        if not os.path.exists(partner_path):
            errors.append(f"Proveedor '{partner_id}' no encontrado en proveedores/")

    # Contactos
    parsed_contacts = [c.strip() for c in contacto_ids_str.split(",") if c.strip()]
    if not parsed_contacts:
        errors.append("Se requiere al menos un contacto responsable")
    else:
        for cid in parsed_contacts:
            contact_path = os.path.join(CONTACTS_DIR, f"{cid}.json")
            if not os.path.exists(contact_path):
                errors.append(f"Contacto '{cid}' no encontrado en contactos/")

    # Contacto role check
    if role == "contacto" and contact_id and contact_id not in parsed_contacts:
        errors.append("Como contacto, debes estar incluido en los responsables del evento")

    return errors, slug, parsed_contacts


def activity_creator(
    action: str,
    nombre: str,
    fecha: str,
    contacto_ids: str,
    partner_id: str,
    tier_promocion: str,
    flyer_responsable: str,
    estado: str = "pendiente",
    year: int = 2026,
    role: Optional[str] = None,
    contact_id: Optional[str] = None,
) -> str:
    """Create a new event in the calendar. Actions: preview, confirm."""
    cal = _load_calendar(year)

    # Validate
    errors, slug, parsed_contacts = _validate_fields(
        nombre, fecha, estado, contacto_ids, partner_id,
        tier_promocion, flyer_responsable, role, contact_id, cal,
    )

    if errors:
        return "Error al crear evento:\n" + "\n".join(f"  - {e}" for e in errors)

    if action == "preview":
        # Build preview
        lines = [f"=== NUEVO EVENTO: {nombre} ==="]
        lines.append(f"  ID: {slug}")
        lines.append(f"  Fecha: {fecha}")
        lines.append(f"  Estado: {estado}")
        lines.append(f"  Contactos: {', '.join(parsed_contacts)}")
        lines.append(f"  Proveedor: {partner_id}")
        lines.append(f"  Tier: {tier_promocion}")
        lines.append(f"  Flyer responsable: {flyer_responsable}")

        # Past date warning for admin
        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
            if fecha_dt.date() < datetime.now().date() and role in ("admin", "tester"):
                lines.append(f"  Advertencia: la fecha {fecha} ya paso")
        except ValueError:
            pass

        # Conflict detection
        try:
            from src.tools.conflict_detector import conflict_detector
            conflict_result = conflict_detector(fecha)
            if "CONFLICTOS:" in conflict_result or "ADVERTENCIAS:" in conflict_result:
                lines.append("")
                lines.append(conflict_result)
            else:
                lines.append(f"  Fecha {fecha}: sin conflictos")
        except Exception as e:
            logger.warning(f"ConflictDetector error: {e}")

        lines.append("")
        lines.append("Confirma para crear el evento.")
        return "\n".join(lines)

    elif action == "confirm":
        # Build event
        new_event = {
            "id": slug,
            "nombre": nombre,
            "fecha": fecha,
            "estado": estado,
            "contacto_ids": parsed_contacts,
            "partner_id": partner_id,
            "tier_promocion": tier_promocion,
            "flyer_responsable": flyer_responsable,
            "flyer_status": "no_solicitado",
            "show_in_export": True,
            "fecha_exacta": True,
            "ultima_actualizacion": datetime.now().isoformat(),
        }

        # Insert sorted by date
        eventos = cal.get("eventos", [])
        eventos.append(new_event)
        eventos.sort(key=lambda e: e.get("fecha", e.get("fecha_inicio", "9999-12-31")))
        cal["eventos"] = eventos

        _save_calendar(cal, year)

        lines = [f"Evento '{nombre}' creado con ID '{slug}'"]
        lines.append(f"  Fecha: {fecha}")
        lines.append(f"  Estado: {estado}")
        lines.append(f"  Contactos: {', '.join(parsed_contacts)}")
        lines.append(f"  Proveedor: {partner_id}")
        lines.append(f"  Tier: {tier_promocion}")
        lines.append(f"  Flyer responsable: {flyer_responsable}")
        lines.append(f"Usa /cambiar para editar campos adicionales (hora, venue, precio, etc.).")
        return "\n".join(lines)

    else:
        return f"Accion desconocida: {action}. Opciones: preview, confirm"


class ActivityCreatorInput(BaseModel):
    action: str = Field(
        description="Accion: preview (validar y mostrar resumen), confirm (guardar el evento)"
    )
    nombre: str = Field(description="Nombre del evento")
    fecha: str = Field(description="Fecha del evento en formato YYYY-MM-DD")
    contacto_ids: str = Field(
        description="IDs de contactos responsables separados por coma (ej: 'rocco-van-velzen,hanna-van-rijsse')"
    )
    partner_id: str = Field(description="ID del proveedor/partner (ej: 'holland-wafels')")
    tier_promocion: str = Field(
        description="Tier de promocion: regular, mediano, grande, delegado, publicacion, ninguno"
    )
    flyer_responsable: str = Field(
        description="Responsable del flyer: nv, proveedor, ninguno"
    )
    estado: str = Field(
        default="pendiente",
        description="Estado del evento: pendiente, confirmado"
    )
    year: int = Field(default=2026, description="Ano del calendario")
    role: Optional[str] = Field(
        default=None, description="Rol del usuario: admin, tester, contacto, readonly"
    )
    contact_id: Optional[str] = Field(
        default=None, description="ID del contacto que ejecuta la accion"
    )


activity_creator_tool = StructuredTool.from_function(
    name="ActivityCreator",
    description=(
        "Crea nuevos eventos en el calendario. Acciones: "
        "preview (validar campos y mostrar resumen con deteccion de conflictos), "
        "confirm (guardar el evento en el calendario, insertado en orden por fecha). "
        "Campos requeridos: nombre, fecha, contacto_ids, partner_id, tier_promocion, "
        "flyer_responsable. Estado por defecto: pendiente."
    ),
    func=activity_creator,
    args_schema=ActivityCreatorInput,
)
