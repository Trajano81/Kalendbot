"""Tests for the shared undo handler."""
import asyncio
import json
import os

from src.handlers.registry import CommandContext
from src.handlers.undo import handle_undo, _find_most_recent_snapshot


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _inject_snapshot(data_dir, event_id, snapshot_data):
    """Inject an _undo_snapshot into a test event."""
    cal_path = os.path.join(data_dir, "calendario-2026.json")
    with open(cal_path, "r", encoding="utf-8") as f:
        cal = json.load(f)
    for e in cal.get("eventos", []):
        if e["id"] == event_id:
            e["_undo_snapshot"] = snapshot_data
            break
    with open(cal_path, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)
    return cal


class TestFindMostRecentSnapshot:
    def test_no_snapshots(self, sample_calendar):
        event, snap = _find_most_recent_snapshot(sample_calendar)
        assert event is None
        assert snap is None

    def test_finds_snapshot(self, sample_calendar):
        # Inject a snapshot into the first event
        first_event = sample_calendar["eventos"][0]
        first_event["_undo_snapshot"] = {
            "timestamp": "2026-05-22T10:00:00",
            "user": "test",
            "changes": {"nombre": "Old Name"},
        }
        event, snap = _find_most_recent_snapshot(sample_calendar)
        assert event is first_event
        assert snap["user"] == "test"

    def test_finds_most_recent(self, sample_calendar):
        eventos = sample_calendar["eventos"]
        if len(eventos) >= 2:
            eventos[0]["_undo_snapshot"] = {
                "timestamp": "2026-05-22T09:00:00",
                "user": "old",
                "changes": {"nombre": "A"},
            }
            eventos[1]["_undo_snapshot"] = {
                "timestamp": "2026-05-22T11:00:00",
                "user": "newer",
                "changes": {"nombre": "B"},
            }
            event, snap = _find_most_recent_snapshot(sample_calendar)
            assert snap["user"] == "newer"


class TestHandleUndo:
    def test_with_text_defers_to_agent(self):
        """When user specifies event name, handler returns empty result for agent fallback."""
        ctx = CommandContext(
            contact_id="test", phone="123",
            text="cambios en Koningsdag",
            language="es", channel="whatsapp",
        )
        result = _run(handle_undo(ctx))
        # Empty result signals "defer to agent"
        assert result.text is None
        assert result.error is None

    def test_no_snapshots_returns_error(self, writable_data_dir):
        ctx = CommandContext(
            contact_id="test", phone="123",
            text="", language="es", channel="telegram",
        )
        result = _run(handle_undo(ctx))
        assert result.error is not None
        assert "deshacer" in result.error.lower() or "cambios" in result.error.lower()

    def test_undoes_most_recent_change(self, writable_data_dir):
        # Inject a snapshot
        cal_path = os.path.join(writable_data_dir, "calendario-2026.json")
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)

        target = cal["eventos"][0]
        original_name = target.get("nombre", "original")
        target["nombre"] = "Changed Name"
        target["_undo_snapshot"] = {
            "timestamp": "2026-05-22T10:00:00",
            "user": "test",
            "changes": {"nombre": original_name},
        }
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)

        ctx = CommandContext(
            contact_id="test", phone="123",
            text="", language="es", channel="whatsapp",
        )
        result = _run(handle_undo(ctx))
        assert result.text is not None
        assert "1" in result.text  # 1 field restored
        assert result.error is None

        # Verify the snapshot was removed and value restored
        with open(cal_path, "r", encoding="utf-8") as f:
            cal_after = json.load(f)
        restored = cal_after["eventos"][0]
        assert restored["nombre"] == original_name
        assert "_undo_snapshot" not in restored

    def test_undo_en_language(self, writable_data_dir):
        cal_path = os.path.join(writable_data_dir, "calendario-2026.json")
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
        target = cal["eventos"][0]
        target["nombre"] = "Changed"
        target["_undo_snapshot"] = {
            "timestamp": "2026-05-22T10:00:00",
            "user": "test",
            "changes": {"nombre": "Original"},
        }
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)

        ctx = CommandContext(
            contact_id="test", phone="123",
            text="", language="en", channel="telegram",
        )
        result = _run(handle_undo(ctx))
        assert result.text is not None
        assert "Reverted" in result.text

    def test_undo_nl_language(self, writable_data_dir):
        cal_path = os.path.join(writable_data_dir, "calendario-2026.json")
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
        target = cal["eventos"][0]
        target["nombre"] = "Changed"
        target["_undo_snapshot"] = {
            "timestamp": "2026-05-22T10:00:00",
            "user": "test",
            "changes": {"nombre": "Original"},
        }
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(cal, f, ensure_ascii=False, indent=2)

        ctx = CommandContext(
            contact_id="test", phone="123",
            text="", language="nl", channel="whatsapp",
        )
        result = _run(handle_undo(ctx))
        assert result.text is not None
        assert "Ongedaan" in result.text
