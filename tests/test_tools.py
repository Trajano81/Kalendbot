"""
Unit tests for KalendBot's 9 tools.
Story 7.1: Test Suite Fundacional — FR24
"""
import json
from unittest.mock import patch


# ========================================================================
# CalendarManager
# ========================================================================

class TestCalendarManager:
    def test_list_all(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_all")
        assert "Koningsdag" in result
        assert "Sinterklaas" in result
        assert "Pub Quiz" in result

    def test_get_event(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="get_event", event_id="koningsdag-2026")
        assert "Koningsdag" in result
        assert "2026-04-27" in result

    def test_get_event_not_found(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="get_event", event_id="no-existe")
        assert "no encontr" in result.lower() or "not found" in result.lower() or "no existe" in result.lower()

    def test_list_pending(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_pending")
        # Should include future pending events
        assert "Sinterklaas" in result or "pendiente" in result.lower()

    def test_list_by_contact(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_by_contact", contact_id="hanna-test")
        assert "Koningsdag" in result
        assert "Sinterklaas" in result

    def test_list_by_status(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_by_status", status="confirmado")
        assert "Koningsdag" in result
        # Cancelled event should NOT appear
        assert "Evento Oculto" not in result

    def test_update_status(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="update_status",
            event_id="sinterklaas-2026",
            status="confirmado",
            role="admin"
        )
        assert "confirmado" in result.lower()
        # Verify persisted
        verify = calendar_manager(action="get_event", event_id="sinterklaas-2026")
        assert "confirmado" in verify.lower()

    def test_update_status_invalid(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="update_status",
            event_id="sinterklaas-2026",
            status="inventado",
            role="admin"
        )
        assert "pendiente" in result.lower() or "confirmado" in result.lower() or "error" in result.lower()

    def test_invalid_action(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="accion_inexistente")
        assert "error" in result.lower() or "no reconocida" in result.lower() or "desconocida" in result.lower()


# ========================================================================
# ContactManager
# ========================================================================

class TestContactManager:
    def test_list_all(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("list_all")
        assert "Hanna" in result
        assert "Koen" in result
        assert "Christian" in result

    def test_get_by_id(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("hanna-test")
        assert "Hanna van Rijsse" in result
        assert "+528120264857" in result

    def test_search_partial_name(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("search:Koen")
        assert "Koen" in result or "koen-test" in result

    def test_search_case_insensitive(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("search:hanna")
        assert "Hanna" in result

    def test_search_no_results(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("search:zzzznotexist")
        assert "no" in result.lower()

    def test_not_found(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("persona-inexistente")
        assert "no" in result.lower()


# ========================================================================
# ProviderManager
# ========================================================================

class TestProviderManager:
    def test_list_all(self, writable_data_dir):
        from src.tools.provider_manager import provider_manager
        result = provider_manager("list_all")
        assert "Holland Wafels" in result
        assert "NV Mexico" in result

    def test_get_by_id(self, writable_data_dir):
        from src.tools.provider_manager import provider_manager
        result = provider_manager("holland-wafels")
        assert "Holland Wafels" in result
        assert "venue" in result.lower()

    def test_not_found(self, writable_data_dir):
        from src.tools.provider_manager import provider_manager
        result = provider_manager("proveedor-inexistente")
        assert "no" in result.lower()


# ========================================================================
# ConflictDetector
# ========================================================================

class TestConflictDetector:
    def test_holiday_conflict(self, writable_data_dir):
        from src.tools.conflict_detector import conflict_detector
        result = conflict_detector("2026-01-01")  # Ano Nuevo
        assert "Ano Nuevo" in result or "feriado" in result.lower() or "holiday" in result.lower()

    def test_clear_date(self, writable_data_dir):
        from src.tools.conflict_detector import conflict_detector
        result = conflict_detector("2026-08-15")  # Random clear date
        assert "conflicto" in result.lower() or "disponible" in result.lower() or "libre" in result.lower() or "sin" in result.lower()

    def test_date_with_existing_event(self, writable_data_dir):
        from src.tools.conflict_detector import conflict_detector
        result = conflict_detector("2026-04-27")  # Koningsdag (confirmado)
        assert "Koningsdag" in result or "evento" in result.lower()

    def test_invalid_date_format(self, writable_data_dir):
        from src.tools.conflict_detector import conflict_detector
        result = conflict_detector("27-04-2026")  # Wrong format
        assert "error" in result.lower() or "formato" in result.lower() or "YYYY-MM-DD" in result


# ========================================================================
# DateLocker
# ========================================================================

class TestDateLocker:
    def test_check_date(self, writable_data_dir):
        from src.tools.date_locker import date_locker
        # check excludes the event itself, so koningsdag's own date shows as available
        result = date_locker(action="check", event_id="koningsdag-2026", fecha="2026-04-27")
        assert "disponible" in result.lower() or "libre" in result.lower()

    def test_lock_date(self, writable_data_dir):
        from src.tools.date_locker import date_locker
        result = date_locker(
            action="lock",
            event_id="sinterklaas-2026",
            fecha="2026-12-05",
            role="admin"
        )
        assert "confirmado" in result.lower() or "lock" in result.lower() or "bloqueada" in result.lower()

    def test_unlock_date(self, writable_data_dir):
        from src.tools.date_locker import date_locker
        result = date_locker(
            action="unlock",
            event_id="koningsdag-2026",
            fecha="2026-04-27",
            role="admin"
        )
        assert "pendiente" in result.lower() or "unlock" in result.lower() or "desbloqueada" in result.lower()

    def test_readonly_cannot_lock(self, writable_data_dir):
        from src.tools.date_locker import date_locker
        result = date_locker(
            action="lock",
            event_id="sinterklaas-2026",
            fecha="2026-12-05",
            role="readonly"
        )
        assert "permiso" in result.lower() or "readonly" in result.lower() or "no" in result.lower()


# ========================================================================
# FlyerManager
# ========================================================================

class TestFlyerManager:
    def test_check_responsibility(self, writable_data_dir):
        from src.tools.flyer_manager import flyer_manager
        result = flyer_manager(action="check_responsibility", event_id="koningsdag-2026")
        assert "nv" in result.lower() or "responsab" in result.lower()

    def test_get_status(self, writable_data_dir):
        from src.tools.flyer_manager import flyer_manager
        result = flyer_manager(action="get_status", event_id="koningsdag-2026")
        assert "solicitado" in result.lower()

    def test_request_flyer(self, writable_data_dir):
        from src.tools.flyer_manager import flyer_manager
        result = flyer_manager(
            action="request_flyer",
            event_id="sinterklaas-2026",
            role="admin"
        )
        assert "solicitado" in result.lower() or "request" in result.lower()

    def test_readonly_cannot_request(self, writable_data_dir):
        from src.tools.flyer_manager import flyer_manager
        result = flyer_manager(
            action="request_flyer",
            event_id="sinterklaas-2026",
            role="readonly"
        )
        assert "permiso" in result.lower() or "readonly" in result.lower() or "no" in result.lower()


# ========================================================================
# GroupNotifier
# ========================================================================

class TestGroupNotifier:
    @patch("src.gateways.dispatcher.send_to_group", return_value=True)
    def test_send_message(self, mock_send, writable_data_dir):
        from src.tools.group_notifier import group_notifier
        result = group_notifier(message="Test notification", role="admin")
        assert "enviado" in result.lower() or "publicado" in result.lower() or "ok" in result.lower()

    def test_readonly_cannot_notify(self, writable_data_dir):
        from src.tools.group_notifier import group_notifier
        result = group_notifier(message="Test", role="readonly")
        assert "permiso" in result.lower() or "readonly" in result.lower() or "no" in result.lower()

    def test_empty_message(self, writable_data_dir):
        from src.tools.group_notifier import group_notifier
        result = group_notifier(message="", role="admin")
        assert "vac" in result.lower() or "empty" in result.lower() or "error" in result.lower()


# ========================================================================
# RulesEngine
# ========================================================================

class TestRulesEngine:
    def test_tiers(self, writable_data_dir):
        from src.tools.rules_engine import rules_engine
        result = rules_engine("tiers")
        assert "grande" in result.lower() or "Grande" in result

    def test_restricciones(self, writable_data_dir):
        from src.tools.rules_engine import rules_engine
        result = rules_engine("restricciones")
        assert "Ano Nuevo" in result or "feriado" in result.lower()

    def test_all_query(self, writable_data_dir):
        from src.tools.rules_engine import rules_engine
        result = rules_engine("all")
        # Should return a summary without infinite recursion
        assert len(result) > 0

    def test_unknown_query(self, writable_data_dir):
        from src.tools.rules_engine import rules_engine
        result = rules_engine("query_inexistente")
        assert len(result) > 0  # Should return something (help text or error)


# ========================================================================
# CalendarExporter (smoke test only — needs template/Chromium for full test)
# ========================================================================

class TestCalendarExporter:
    def test_readonly_cannot_export(self, writable_data_dir):
        from src.tools.calendar_exporter import calendar_exporter
        result = calendar_exporter(role="readonly")
        assert "permiso" in result.lower() or "readonly" in result.lower() or "no" in result.lower()
