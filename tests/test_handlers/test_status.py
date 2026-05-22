"""Tests for the shared status handler."""
import asyncio
from src.handlers.registry import CommandContext
from src.handlers.status import handle_status


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestHandleStatus:
    def test_status_returns_text(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="es", channel="telegram")
        result = _run(handle_status(ctx))
        assert result.text is not None or result.error is not None

    def test_status_no_file_or_image(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="es", channel="whatsapp")
        result = _run(handle_status(ctx))
        assert result.file_path is None
        assert result.image_path is None
