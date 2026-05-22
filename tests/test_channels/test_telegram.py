"""Tests for Telegram channel adapter — testing via new src/channels/ path."""
from src.channels.telegram.bot import _split_multi_task, _extract_group_text


class TestSplitMultiTask:
    def test_single_task(self):
        assert _split_multi_task("hello world") == ["hello world"]

    def test_bullets(self):
        text = "cambiar\n*. fecha a 2026-06-01\n*. nombre a Test"
        result = _split_multi_task(text)
        assert len(result) == 2


class TestExtractGroupText:
    def test_mention_at_start(self):
        text = "@kalendbot cambiar fecha"
        result = _extract_group_text(text, "kalendbot")
        assert result == "cambiar fecha"

    def test_no_mention(self):
        text = "just chatting"
        result = _extract_group_text(text, "kalendbot")
        assert result is None

    def test_mention_anywhere(self):
        text = "hey @kalendbot do something"
        result = _extract_group_text(text, "kalendbot")
        assert result is not None
        assert "do something" in result
