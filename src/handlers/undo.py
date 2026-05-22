"""
Direct /undo handler: reverts the most recent change when no event is specified.
Falls back to the LLM agent when the user targets a specific event by name.
"""
import json
import os
import logging
from datetime import datetime

from src.core.config import settings
from src.handlers.registry import (
    CommandContext, CommandResult, CommandDef, register_command,
)

logger = logging.getLogger("kalendbot.handlers.undo")

DATA_DIR = settings.data_dir

_MESSAGES = {
    "es": {
        "no_snapshot": "No hay cambios recientes para deshacer.",
        "reverted": "Revertido",
        "fields_restored": "campo(s) restaurado(s)",
    },
    "en": {
        "no_snapshot": "No recent changes to undo.",
        "reverted": "Reverted",
        "fields_restored": "field(s) restored",
    },
    "nl": {
        "no_snapshot": "Geen recente wijzigingen om ongedaan te maken.",
        "reverted": "Ongedaan gemaakt",
        "fields_restored": "veld(en) hersteld",
    },
}


def _t(lang: str, key: str) -> str:
    return _MESSAGES.get(lang, _MESSAGES["es"]).get(key, _MESSAGES["es"][key])


def _load_calendar(year: int = 2026) -> dict:
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_calendar(data: dict, year: int = 2026) -> None:
    path = os.path.join(DATA_DIR, f"calendario-{year}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_most_recent_snapshot(cal: dict):
    """Scan all events for the most recent _undo_snapshot. Returns (event, snapshot) or (None, None)."""
    best_event = None
    best_snapshot = None
    best_ts = None

    for event in cal.get("eventos", []):
        snap = event.get("_undo_snapshot")
        if snap:
            ts = snap.get("timestamp", "")
            if best_ts is None or ts > best_ts:
                best_event, best_snapshot, best_ts = event, snap, ts

    for rec in cal.get("eventos_recurrentes", []):
        snap = rec.get("_undo_snapshot")
        if snap:
            ts = snap.get("timestamp", "")
            if best_ts is None or ts > best_ts:
                best_event, best_snapshot, best_ts = rec, snap, ts
        for inst in rec.get("instancias_2026", []):
            snap = inst.get("_undo_snapshot")
            if snap:
                ts = snap.get("timestamp", "")
                if best_ts is None or ts > best_ts:
                    best_event, best_snapshot, best_ts = inst, snap, ts

    return best_event, best_snapshot


def _apply_undo(event: dict, snapshot: dict) -> list[str]:
    """Restore old values from snapshot. Returns list of restored field descriptions."""
    old_changes = snapshot.get("changes", {})
    restored = []
    for field, old_val in old_changes.items():
        if old_val is None:
            event.pop(field, None)
        else:
            event[field] = old_val
        restored.append(f"  {field}: {old_val}")

    if "fecha" in old_changes:
        event.pop("fecha_original", None)

    del event["_undo_snapshot"]
    event["ultima_actualizacion"] = datetime.now().isoformat()
    return restored


async def handle_undo(ctx: CommandContext) -> CommandResult:
    """
    Direct undo: if no arguments, find the most recent snapshot and revert it.
    If the user provides text (event name), return None-result so the caller
    can fall through to the LLM agent for targeted undo.
    """
    # If user specified an event name, let the agent handle it
    if ctx.text.strip():
        return CommandResult(text=None, error=None)

    lang = ctx.language or "es"

    try:
        cal = _load_calendar()
    except FileNotFoundError:
        return CommandResult(error=_t(lang, "no_snapshot"))

    event, snapshot = _find_most_recent_snapshot(cal)
    if not event or not snapshot:
        return CommandResult(error=_t(lang, "no_snapshot"))

    nombre = event.get("nombre", event.get("id", "?"))
    restored = _apply_undo(event, snapshot)
    _save_calendar(cal)

    lines = [f"↩ {_t(lang, 'reverted')} {nombre}: {len(restored)} {_t(lang, 'fields_restored')}"]
    lines.extend(restored)
    return CommandResult(text="\n".join(lines))


register_command(CommandDef(
    name="undo",
    aliases=["deshacer", "ongedaan"],
    handler=handle_undo,
    permission="contacto",
    description={
        "es": "Revertir ultimo cambio",
        "en": "Revert last change",
        "nl": "Laatste wijziging ongedaan maken",
    },
))
