"""Tests for the shared help handler."""
import asyncio
from src.handlers.registry import CommandContext
from src.handlers.help import handle_help


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestHandleHelp:
    def test_help_es(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="es", channel="telegram")
        result = _run(handle_help(ctx))
        assert result.text is not None
        assert "/cambiar" in result.text
        assert "/exportar_excel" in result.text

    def test_help_en(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="en", channel="telegram")
        result = _run(handle_help(ctx))
        assert result.text is not None
        assert "/change" in result.text
        assert "/export_excel" in result.text

    def test_help_nl(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="nl", channel="telegram")
        result = _run(handle_help(ctx))
        assert result.text is not None
        assert "Beschikbare" in result.text

    def test_help_unknown_lang_defaults_es(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="xx", channel="whatsapp")
        result = _run(handle_help(ctx))
        assert result.text is not None
        assert "/cambiar" in result.text

    def test_help_no_error(self):
        ctx = CommandContext(contact_id="test", phone="123", text="", language="es", channel="whatsapp")
        result = _run(handle_help(ctx))
        assert result.error is None
