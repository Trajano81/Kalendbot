"""Tests for security module."""
import time
import pytest

from src.security import RateLimiter, sanitize_message, validate_webhook_api_key


class TestRateLimiter:
    def test_allows_normal_usage(self):
        limiter = RateLimiter(max_requests=5, window=60)
        for _ in range(5):
            assert limiter.is_allowed("user1")

    def test_blocks_after_limit(self):
        limiter = RateLimiter(max_requests=3, window=60)
        for _ in range(3):
            assert limiter.is_allowed("user1")
        assert not limiter.is_allowed("user1")

    def test_different_keys_independent(self):
        limiter = RateLimiter(max_requests=2, window=60)
        assert limiter.is_allowed("user1")
        assert limiter.is_allowed("user1")
        assert not limiter.is_allowed("user1")
        # user2 should still be allowed
        assert limiter.is_allowed("user2")

    def test_window_expires(self):
        limiter = RateLimiter(max_requests=1, window=1)
        assert limiter.is_allowed("user1")
        assert not limiter.is_allowed("user1")
        time.sleep(1.1)
        assert limiter.is_allowed("user1")


class TestSanitizeMessage:
    def test_normal_text_unchanged(self):
        assert sanitize_message("Hello world") == "Hello world"

    def test_strips_control_chars(self):
        assert sanitize_message("Hello\x00world") == "Helloworld"

    def test_preserves_newlines(self):
        assert sanitize_message("line1\nline2") == "line1\nline2"

    def test_preserves_tabs(self):
        assert sanitize_message("col1\tcol2") == "col1\tcol2"

    def test_truncates_long_messages(self):
        long_msg = "x" * 3000
        result = sanitize_message(long_msg)
        assert len(result) == 2000

    def test_strips_whitespace(self):
        assert sanitize_message("  hello  ") == "hello"

    def test_empty_string(self):
        assert sanitize_message("") == ""

    def test_unicode_preserved(self):
        assert sanitize_message("Hola amigos! Koningsdag") == "Hola amigos! Koningsdag"


class TestWebhookValidation:
    def test_valid_key(self):
        assert validate_webhook_api_key("secret123", "secret123")

    def test_invalid_key(self):
        assert not validate_webhook_api_key("wrong", "secret123")

    def test_no_key_configured(self):
        assert validate_webhook_api_key("anything", "")

    def test_empty_provided_key(self):
        assert not validate_webhook_api_key("", "secret123")
