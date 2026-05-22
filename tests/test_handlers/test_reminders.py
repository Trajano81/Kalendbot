"""Tests for the shared reminder utilities."""
import pytest
from src.handlers.reminders import (
    parse_flyer_moment,
    load_reminder_config,
    load_sent_reminders,
)


class TestParseFlyer:
    def test_normal(self):
        assert parse_flyer_moment("-60,-30,-7 dagen") == [60, 30, 7]

    def test_single(self):
        assert parse_flyer_moment("-14 dagen") == [14]

    def test_x_returns_empty(self):
        assert parse_flyer_moment("x") == []
        assert parse_flyer_moment("X") == []

    def test_empty(self):
        assert parse_flyer_moment("") == []
        assert parse_flyer_moment(None) == []

    def test_mixed(self):
        assert parse_flyer_moment("-30, -7 days") == [30, 7]


class TestLoadConfig:
    def test_load_config(self, fixtures_dir):
        config = load_reminder_config()
        assert isinstance(config, dict)

    def test_load_sent_reminders(self, fixtures_dir):
        sent = load_sent_reminders()
        assert isinstance(sent, dict)
