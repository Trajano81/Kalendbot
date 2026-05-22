"""Tests for WhatsApp channel adapter — testing via new src/channels/ path."""
from src.channels.whatsapp.bot import _is_bot_triggered, _convert_markdown_to_whatsapp


class TestBotTriggerDetection:
    def test_slash_trigger(self):
        parsed = {"message_text": "/pendientes", "mentioned_jids": []}
        triggered, text = _is_bot_triggered(parsed)
        assert triggered is True
        assert text == "pendientes"

    def test_no_trigger(self):
        parsed = {"message_text": "just chatting", "mentioned_jids": []}
        triggered, text = _is_bot_triggered(parsed)
        assert triggered is False

    def test_empty_slash_not_triggered(self):
        parsed = {"message_text": "/", "mentioned_jids": []}
        triggered, text = _is_bot_triggered(parsed)
        assert triggered is False


class TestMarkdownConversion:
    def test_bold_conversion(self):
        assert _convert_markdown_to_whatsapp("**bold**") == "*bold*"

    def test_no_change_for_plain_text(self):
        assert _convert_markdown_to_whatsapp("plain text") == "plain text"
