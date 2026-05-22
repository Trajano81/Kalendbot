"""Tests for contacts gateway utilities."""
import os
import json
import pytest

from src.gateways.contacts import (
    normalize_phone,
    load_contact,
    identify_by_phone,
    identify_by_telegram_id,
    get_contact_language,
    set_contact_language,
    create_contact_json,
    strip_markdown,
    SUPPORTED_LANGUAGES,
)


class TestNormalizePhone:
    def test_strips_plus(self):
        assert normalize_phone("+521234567890") == "521234567890"

    def test_strips_spaces(self):
        assert normalize_phone("52 123 456 7890") == "521234567890"

    def test_strips_dashes(self):
        assert normalize_phone("52-123-456-7890") == "521234567890"

    def test_strips_parens(self):
        assert normalize_phone("(52)1234567890") == "521234567890"

    def test_combined(self):
        assert normalize_phone("+52 (123) 456-7890") == "521234567890"

    def test_already_clean(self):
        assert normalize_phone("521234567890") == "521234567890"


class TestLoadContact:
    def test_load_existing_contact(self, fixtures_dir):
        contact = load_contact("hanna-test")
        assert contact is not None
        assert contact["id"] == "hanna-test"

    def test_load_nonexistent_contact(self):
        contact = load_contact("does-not-exist-xyz")
        assert contact is None


class TestIdentifyByPhone:
    def test_find_by_exact_phone(self, fixtures_dir):
        # Check what phone number the test contact has
        contact = load_contact("hanna-test")
        if contact and contact.get("telefono"):
            cid, path = identify_by_phone(contact["telefono"])
            assert cid == "hanna-test"

    def test_not_found(self, fixtures_dir):
        cid, path = identify_by_phone("0000000000")
        assert cid is None
        assert path is None


class TestIdentifyByTelegramId:
    def test_find_by_telegram_id(self, fixtures_dir):
        contact = load_contact("hanna-test")
        if contact and contact.get("telegram_id"):
            cid = identify_by_telegram_id(contact["telegram_id"])
            assert cid == "hanna-test"

    def test_not_found(self, fixtures_dir):
        cid = identify_by_telegram_id(99999999999)
        assert cid is None


class TestLanguage:
    def test_get_default_language(self, fixtures_dir):
        lang = get_contact_language("nonexistent")
        assert lang == "es"

    def test_get_contact_language(self, fixtures_dir):
        lang = get_contact_language("hanna-test")
        assert lang in SUPPORTED_LANGUAGES

    def test_set_language(self, writable_data_dir):
        from src.gateways import contacts as contacts_mod
        from src import config as config_mod
        # writable_data_dir fixture already patches DATA_DIR
        assert set_contact_language("hanna-test", "nl")
        assert get_contact_language("hanna-test") == "nl"

    def test_set_invalid_language(self, writable_data_dir):
        assert not set_contact_language("hanna-test", "xx")


class TestCreateContact:
    def test_create_new_contact(self, writable_data_dir):
        cid = create_contact_json(
            nombre="Test User",
            telefono="+521234567890",
        )
        assert cid == "test-user"
        filepath = os.path.join(writable_data_dir, "contactos", f"{cid}.json")
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert data["rol_kalendbot"] == "readonly"
        assert data["telefono"] == "+521234567890"


class TestStripMarkdown:
    def test_strips_bold(self):
        assert strip_markdown("**hello**") == "hello"

    def test_strips_italic(self):
        assert strip_markdown("*hello*") == "hello"

    def test_plain_text_unchanged(self):
        assert strip_markdown("hello world") == "hello world"
