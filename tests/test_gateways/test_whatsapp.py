"""Tests for WhatsApp gateway components."""
import pytest
from unittest.mock import MagicMock

from src.gateways.whatsapp_provider import normalize_phone, phone_to_chat_id, WAHAProvider


class TestPhoneUtils:
    def test_phone_to_chat_id(self):
        assert phone_to_chat_id("521234567890") == "521234567890@c.us"

    def test_phone_to_chat_id_with_plus(self):
        assert phone_to_chat_id("+521234567890") == "521234567890@c.us"

    def test_phone_to_chat_id_already_formatted(self):
        assert phone_to_chat_id("521234567890@c.us") == "521234567890@c.us"


class TestWAHAProvider:
    def test_mock_mode_without_api_key(self):
        provider = WAHAProvider()
        provider.api_key = ""
        assert provider._is_mock()

    def test_send_text_mock_mode(self):
        provider = WAHAProvider()
        provider.api_key = ""
        result = provider.send_text("12345@c.us", "hello")
        assert result["status"] == "mock"

    def test_get_session_status_mock(self):
        provider = WAHAProvider()
        provider.api_key = ""
        assert provider.get_session_status() == "MOCK"

    def test_parse_webhook_valid_message(self):
        provider = WAHAProvider()
        data = {
            "event": "message",
            "payload": {
                "from": "521234567890@c.us",
                "body": "Hello bot",
                "fromMe": False,
            },
        }
        result = provider.parse_webhook(data)
        assert result is not None
        assert result["sender_phone"] == "521234567890"
        assert result["message_text"] == "Hello bot"
        assert result["is_group"] is False

    def test_parse_webhook_group_message(self):
        provider = WAHAProvider()
        data = {
            "event": "message",
            "payload": {
                "from": "120363xxxxx@g.us",
                "body": "Group message",
                "fromMe": False,
                "participant": "521234567890@c.us",
            },
        }
        result = provider.parse_webhook(data)
        assert result is not None
        assert result["is_group"] is True
        assert result["sender_phone"] == "521234567890"
        assert result["group_id"] == "120363xxxxx@g.us"

    def test_parse_webhook_ignores_from_me(self):
        provider = WAHAProvider()
        data = {
            "event": "message",
            "payload": {
                "from": "521234567890@c.us",
                "body": "My own message",
                "fromMe": True,
            },
        }
        result = provider.parse_webhook(data)
        assert result is None

    def test_parse_webhook_ignores_empty_body(self):
        provider = WAHAProvider()
        data = {
            "event": "message",
            "payload": {
                "from": "521234567890@c.us",
                "body": "",
                "fromMe": False,
            },
        }
        result = provider.parse_webhook(data)
        assert result is None

    def test_parse_webhook_ignores_non_message_event(self):
        provider = WAHAProvider()
        data = {"event": "session.status", "payload": {"status": "CONNECTED"}}
        result = provider.parse_webhook(data)
        assert result is None


class TestBotTriggerDetection:
    def test_slash_trigger(self):
        from src.gateways.whatsapp_bot import _is_bot_triggered
        parsed = {
            "message_text": "/pendientes",
            "mentioned_jids": [],
        }
        triggered, text = _is_bot_triggered(parsed)
        assert triggered is True
        assert text == "pendientes"

    def test_no_trigger(self):
        from src.gateways.whatsapp_bot import _is_bot_triggered
        parsed = {
            "message_text": "just chatting",
            "mentioned_jids": [],
        }
        triggered, text = _is_bot_triggered(parsed)
        assert triggered is False

    def test_empty_slash_not_triggered(self):
        from src.gateways.whatsapp_bot import _is_bot_triggered
        parsed = {
            "message_text": "/",
            "mentioned_jids": [],
        }
        triggered, text = _is_bot_triggered(parsed)
        assert triggered is False


class TestMarkdownConversion:
    def test_bold_conversion(self):
        from src.gateways.whatsapp_bot import _convert_markdown_to_whatsapp
        assert _convert_markdown_to_whatsapp("**bold**") == "*bold*"

    def test_no_change_for_plain_text(self):
        from src.gateways.whatsapp_bot import _convert_markdown_to_whatsapp
        assert _convert_markdown_to_whatsapp("plain text") == "plain text"
