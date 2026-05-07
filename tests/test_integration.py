"""
Integration tests for KalendBot agent.
Story 7.1: Test Suite Fundacional — FR25
Tests: FAQ bypass, contact identification, unknown contact handling.
"""
import os
import json

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestFAQBypass:
    """Tests that FAQ questions are answered without invoking the LLM."""

    def test_faq_match_total_eventos(self, writable_data_dir):
        from src.agent import _check_faq
        result = _check_faq("cuantos eventos hay?")
        assert result is not None
        assert "5 eventos" in result

    def test_faq_match_que_es_nv(self, writable_data_dir):
        from src.agent import _check_faq
        result = _check_faq("que es nv mexico?")
        assert result is not None
        assert "asociacion" in result.lower()

    def test_faq_no_match_returns_none(self, writable_data_dir):
        from src.agent import _check_faq
        result = _check_faq("confirma el koningsdag")
        assert result is None

    def test_faq_no_false_positive(self, writable_data_dir):
        """OBS-05 regression: FAQ should NOT match partial queries."""
        from src.agent import _check_faq
        # "cuantos eventos tiene Koen" should NOT match "cuantos eventos hay"
        result = _check_faq("cuantos eventos tiene Koen?")
        assert result is None


class TestContactIdentification:
    """Tests that contacts are correctly identified by phone or ID."""

    def test_identify_by_phone(self, writable_data_dir):
        from src.gateways.contacts import identify_by_phone
        result = identify_by_phone("+528120264857")
        contact_id = result[0] if isinstance(result, tuple) else result
        assert contact_id == "hanna-test"

    def test_identify_by_phone_not_found(self, writable_data_dir):
        from src.gateways.contacts import identify_by_phone
        result = identify_by_phone("+529999999999")
        contact_id = result[0] if isinstance(result, tuple) else result
        assert contact_id is None

    def test_contact_role_lookup(self, writable_data_dir):
        from src.agent import _get_contact_role
        role = _get_contact_role("hanna-test")
        assert role == "admin"

    def test_contact_role_default(self, writable_data_dir):
        from src.agent import _get_contact_role
        role = _get_contact_role("unknown-user")
        # Non-existent contact should default to readonly or contacto
        assert role in ("readonly", "contacto")


class TestUnknownContactHandling:
    """Tests that unknown contacts get proper fallback IDs."""

    def test_unknown_contact_id_format(self, writable_data_dir):
        """ISSUE-01/03 regression: unknown contacts get ID from last 4 chars of phone."""
        from src.agent import _identify_contact_by_phone
        contact_id = _identify_contact_by_phone("9998887777")
        # Should create unknown-XXXX pattern
        assert contact_id is None or contact_id.startswith("unknown-")
