"""
Shared pytest configuration for KalendBot tests.
Sets KALENDBOT_DATA_DIR to tests/fixtures/ BEFORE any src imports.
"""
import os
import sys
import json
import shutil

# --- Set test data dir BEFORE any src imports ---
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
os.environ["KALENDBOT_DATA_DIR"] = FIXTURES_DIR
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key")

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture
def fixtures_dir():
    """Path to the test fixtures directory (read-only data)."""
    return FIXTURES_DIR


@pytest.fixture
def writable_data_dir(tmp_path, monkeypatch):
    """
    Copy fixtures to a temp dir for tests that write data.
    Patches DATA_DIR in all tool modules that use it.
    """
    # Copy all fixtures to temp dir
    shutil.copytree(FIXTURES_DIR, tmp_path / "data", dirs_exist_ok=True)
    data_dir = str(tmp_path / "data")

    # Patch DATA_DIR in all modules that use it
    from src.tools import calendar_manager, contact_manager, provider_manager
    from src.tools import conflict_detector, date_locker, flyer_manager
    from src.tools import rules_engine, calendar_exporter
    from src.gateways import contacts as contacts_mod
    from src.handlers import undo as undo_mod
    from src import config as config_mod

    # Patch settings.data_dir for any code that reads it at runtime
    monkeypatch.setattr(config_mod.settings, "data_dir", data_dir)

    for mod in [calendar_manager, contact_manager, provider_manager,
                conflict_detector, date_locker, flyer_manager,
                rules_engine, calendar_exporter, contacts_mod, undo_mod]:
        monkeypatch.setattr(mod, "DATA_DIR", data_dir)

    # Also patch derived paths
    monkeypatch.setattr(contact_manager, "CONTACTS_DIR", os.path.join(data_dir, "contactos"))
    monkeypatch.setattr(provider_manager, "PROVIDERS_DIR", os.path.join(data_dir, "proveedores"))
    monkeypatch.setattr(rules_engine, "CONFIG_DIR", os.path.join(data_dir, "config"))

    return data_dir


@pytest.fixture
def sample_calendar():
    """Load the test calendar data."""
    cal_path = os.path.join(FIXTURES_DIR, "calendario-2026.json")
    with open(cal_path, "r", encoding="utf-8") as f:
        return json.load(f)
