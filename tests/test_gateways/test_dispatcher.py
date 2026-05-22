"""Tests for the dispatcher module."""
import pytest
from unittest.mock import patch, MagicMock

from src.gateways.dispatcher import send_dm, send_to_group


class TestSendDm:
    def test_unknown_contact_returns_false(self):
        assert send_dm("nonexistent-contact-xyz", message="hello") is False

    def test_no_message_returns_false(self):
        with patch("src.gateways.dispatcher.load_contact", return_value={"canal_preferido": "telegram"}):
            assert send_dm("test", message=None) is False


class TestSendToGroup:
    @patch("src.gateways.dispatcher.settings")
    def test_no_group_ids_returns_false(self, mock_settings):
        mock_settings.telegram_group_chat_id = ""
        mock_settings.whatsapp_group_chat_id = ""
        mock_settings.telegram_bot_token = ""
        result = send_to_group("test message", channel="both")
        assert result is False

    @patch("src.gateways.dispatcher._send_telegram_message", return_value=True)
    @patch("src.gateways.dispatcher.settings")
    def test_telegram_only(self, mock_settings, mock_send):
        mock_settings.telegram_group_chat_id = "12345"
        mock_settings.telegram_bot_token = "fake-token"
        result = send_to_group("test message", channel="telegram")
        assert result is True
        mock_send.assert_called_once_with("12345", "test message")
