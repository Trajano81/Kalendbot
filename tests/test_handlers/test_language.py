"""Tests for the shared language handler."""
import asyncio
from src.handlers.registry import CommandContext
from src.handlers.language import handle_language


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestHandleLanguage:
    def test_no_contact_id(self):
        ctx = CommandContext(contact_id=None, phone="123", text="", language="es", channel="whatsapp")
        result = _run(handle_language(ctx))
        assert result.error == "No estás identificado."

    def test_show_options_when_no_arg(self, writable_data_dir):
        ctx = CommandContext(contact_id="kmilo-aparicio", phone="123", text="", language="es", channel="telegram")
        result = _run(handle_language(ctx))
        assert result.text is not None
        assert "es" in result.text
        assert "en" in result.text
        assert "nl" in result.text

    def test_set_language_directly(self, writable_data_dir):
        ctx = CommandContext(contact_id="kmilo-aparicio", phone="123", text="en", language="es", channel="whatsapp")
        result = _run(handle_language(ctx))
        assert result.text is not None
        assert "Language set to" in result.text or "English" in result.text
