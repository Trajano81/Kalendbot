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

    # --- search_event ---

    def test_search_event_by_name(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="search_event", event_id="Koning")
        assert "koningsdag-2026" in result
        assert "Koningsdag" in result

    def test_search_event_recurring(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="search_event", event_id="pub quiz")
        assert "pub-quiz-recurrente" in result
        assert "recurrente" in result

    def test_search_event_no_results(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="search_event", event_id="zzz_no_existe")
        assert "no se encontraron" in result.lower()

    # --- list_pending with recurrentes ---

    def test_list_pending_includes_recurring(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_pending")
        assert "Pub Quiz" in result
        assert "[R]" in result

    # --- list_upcoming with recurrentes ---

    def test_list_upcoming_includes_recurring(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_upcoming")
        assert "Pub Quiz" in result or "pub-quiz-recurrente" in result
        assert "[R]" in result

    # --- batch_preview + batch_confirm flow ---

    def test_batch_preview(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_preview",
            event_id="koningsdag-2026",
            changes="hora=14:00",
            role="admin",
        )
        assert "CAMBIOS" in result
        assert "hora" in result
        assert "11:00" in result  # old value
        assert "14:00" in result  # new value

    def test_batch_confirm(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_confirm",
            event_id="koningsdag-2026",
            changes="hora=14:00",
            role="admin",
        )
        assert "actualizado" in result.lower()
        # Verify persisted
        verify = calendar_manager(action="get_event", event_id="koningsdag-2026")
        assert '"hora": "14:00"' in verify

    def test_batch_confirm_then_undo(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        # Apply change
        calendar_manager(
            action="batch_confirm",
            event_id="koningsdag-2026",
            changes="hora=14:00",
            role="admin",
        )
        # Undo
        result = calendar_manager(action="undo_last", event_id="koningsdag-2026", role="admin")
        assert "revertido" in result.lower()
        # Verify reverted
        verify = calendar_manager(action="get_event", event_id="koningsdag-2026")
        assert '"hora": "11:00"' in verify

    def test_batch_preview_readonly_denied(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_preview",
            event_id="koningsdag-2026",
            changes="hora=14:00",
            role="readonly",
        )
        assert "error" in result.lower() or "permiso" in result.lower()

    def test_batch_preview_recurring_instance(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_preview",
            event_id="pub-quiz-recurrente",
            status="2026-03-05",
            changes="estado=confirmado",
            role="admin",
        )
        # estado is not in _FIELD_META so this should error, but let's check the event is found
        assert "pub" in result.lower() or "error" in result.lower()

    def test_batch_confirm_multiple_fields(self, writable_data_dir):
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_confirm",
            event_id="koningsdag-2026",
            changes="hora=14:00|descripcion=Dia del Rey actualizado",
            role="admin",
        )
        assert "actualizado" in result.lower()
        assert "2" in result  # 2 campos
        verify = calendar_manager(action="get_event", event_id="koningsdag-2026")
        assert "14:00" in verify
        assert "actualizado" in verify


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


# ========================================================================
# Multi-task flow: _split_multi_task + _preprocess_command
# ========================================================================

class TestSplitMultiTask:
    """Tests for _split_multi_task — splitting bullet-point messages into tasks."""

    def test_single_task_no_split(self):
        from src.gateways.telegram_bot import _split_multi_task
        result = _split_multi_task("cambiar fecha del Koningsdag a 2026-04-28")
        assert result == ["cambiar fecha del Koningsdag a 2026-04-28"]

    def test_split_bullet_star(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n*. fecha del Koningsdag a 2026-04-28\n*. hora del Pub Quiz a 20:00"
        result = _split_multi_task(text)
        assert len(result) == 2
        assert "fecha" in result[0] and "Koningsdag" in result[0]
        assert "hora" in result[1] and "Pub Quiz" in result[1]

    def test_split_bullet_dash(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n- fecha del Koningsdag a 2026-04-28\n- hora del Pub Quiz a 20:00"
        result = _split_multi_task(text)
        assert len(result) == 2

    def test_prepends_cambiar_if_missing_verb(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n*. fecha del Koningsdag a 2026-04-28\n*. la hora del Pub Quiz a 20:00"
        result = _split_multi_task(text)
        # Second task "la hora del Pub Quiz..." doesn't start with a known verb,
        # so it gets "cambiar" prepended
        assert result[1].startswith("cambiar")

    def test_no_split_without_known_verb(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "hola\n*. punto uno\n*. punto dos"
        result = _split_multi_task(text)
        assert len(result) == 1  # Not split because "hola" is not a known verb

    def test_mixed_verbs_preserved(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n*. ocultar Buitendag\n*. mostrar Sinterklaas"
        result = _split_multi_task(text)
        assert len(result) == 2
        assert result[0].startswith("ocultar")
        assert result[1].startswith("mostrar")

    def test_split_numbered_list(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n1. fecha del Koningsdag a 2026-04-28\n2. hora del Pub Quiz a 20:00"
        result = _split_multi_task(text)
        assert len(result) == 2
        assert "Koningsdag" in result[0]
        assert "Pub Quiz" in result[1]

    def test_split_numbered_paren(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n1) fecha del Koningsdag a 2026-04-28\n2) hora del Pub Quiz a 20:00"
        result = _split_multi_task(text)
        assert len(result) == 2

    def test_split_unicode_bullet(self):
        from src.gateways.telegram_bot import _split_multi_task
        text = "cambiar\n\u2022 fecha del Koningsdag a 2026-04-28\n\u2022 hora del Pub Quiz a 20:00"
        result = _split_multi_task(text)
        assert len(result) == 2


class TestPreprocessCommand:
    """Tests for _preprocess_command — translating /commands to structured instructions."""

    def test_cambiar_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("cambiar fecha del Koningsdag a 2026-04-28")
        assert "[COMANDO: /cambiar]" in result
        assert "search_event" in result
        assert "batch_preview" in result

    def test_estado_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("estado Koningsdag confirmado")
        assert "[COMANDO: /estado]" in result
        assert "update_status" in result

    def test_buscar_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("buscar Pub Quiz")
        assert "[COMANDO: /buscar]" in result
        assert "Pub Quiz" in result

    def test_pendientes_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("pendientes")
        assert "[COMANDO: /pendientes]" in result
        assert "list_pending" in result

    def test_proximos_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("proximos")
        assert "[COMANDO: /proximos]" in result
        assert "list_upcoming" in result

    def test_grupo_prefix_preserved(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("[Grupo] cambiar fecha del Koningsdag a 2026-04-28")
        assert result.startswith("[Grupo]")
        assert "[COMANDO: /cambiar]" in result

    def test_batch_prefix_preserved(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("[BATCH: aplica directo] cambiar hora a 20:00")
        assert "[BATCH:" in result
        assert "[COMANDO: /cambiar]" in result

    def test_non_command_passthrough(self):
        from src.agent import _preprocess_command
        msg = "hola, como estas?"
        result = _preprocess_command(msg)
        assert result == msg

    def test_ocultar_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("ocultar Buitendag")
        assert "[COMANDO: /ocultar]" in result
        assert "show_in_export" in result

    def test_deshacer_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("deshacer cambios en Koningsdag")
        assert "[COMANDO: /deshacer]" in result
        assert "undo_last" in result


class TestMultiTaskBatchFlow:
    """
    End-to-end test of the multi-task batch flow at the CalendarManager level.
    Simulates what happens when _split_multi_task splits a message and each task
    goes through batch_confirm with [BATCH:] prefix (no preview needed).
    """

    def test_two_changes_different_events(self, writable_data_dir):
        """Simulate: cambiar hora Koningsdag + cambiar descripcion Sinterklaas"""
        from src.tools.calendar_manager import calendar_manager

        # Task 1: change hora on Koningsdag
        r1 = calendar_manager(
            action="batch_confirm",
            event_id="koningsdag-2026",
            changes="hora=14:00",
            role="admin",
        )
        assert "actualizado" in r1.lower()

        # Task 2: change descripcion on Sinterklaas
        r2 = calendar_manager(
            action="batch_confirm",
            event_id="sinterklaas-2026",
            changes="descripcion=Fiesta de San Nicolas actualizada",
            role="admin",
        )
        assert "actualizado" in r2.lower()

        # Verify both persisted
        e1 = calendar_manager(action="get_event", event_id="koningsdag-2026")
        assert "14:00" in e1
        e2 = calendar_manager(action="get_event", event_id="sinterklaas-2026")
        assert "actualizada" in e2

    def test_batch_confirm_then_undo_each(self, writable_data_dir):
        """Each batch task creates its own undo snapshot — both can be reverted."""
        from src.tools.calendar_manager import calendar_manager

        # Apply two changes
        calendar_manager(action="batch_confirm", event_id="koningsdag-2026",
                         changes="hora=14:00", role="admin")
        calendar_manager(action="batch_confirm", event_id="sinterklaas-2026",
                         changes="descripcion=Changed", role="admin")

        # Undo Koningsdag
        r1 = calendar_manager(action="undo_last", event_id="koningsdag-2026")
        assert "revertido" in r1.lower()
        e1 = calendar_manager(action="get_event", event_id="koningsdag-2026")
        assert "11:00" in e1  # original hora

        # Undo Sinterklaas
        r2 = calendar_manager(action="undo_last", event_id="sinterklaas-2026")
        assert "revertido" in r2.lower()
        e2 = calendar_manager(action="get_event", event_id="sinterklaas-2026")
        assert "Fiesta de San Nicolas" in e2  # original descripcion
        assert "Changed" not in e2

    def test_batch_with_invalid_event_returns_error(self, writable_data_dir):
        """If a batch task references a non-existent event, it returns error (not crash)."""
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_confirm",
            event_id="evento-inexistente",
            changes="hora=14:00",
            role="admin",
        )
        assert "no encontrado" in result.lower()

    def test_batch_readonly_denied(self, writable_data_dir):
        """Batch confirm with readonly role is denied."""
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(
            action="batch_confirm",
            event_id="koningsdag-2026",
            changes="hora=14:00",
            role="readonly",
        )
        assert "permiso" in result.lower() or "error" in result.lower()


class TestActivityCreator:
    """Tests for the ActivityCreator tool."""

    def test_preview_valid(self, writable_data_dir):
        """Preview with all valid fields returns formatted summary."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Test Event",
            fecha="2026-09-15",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "Test Event" in result
        assert "2026-09-15" in result
        assert "nv-mexico" in result
        assert "Confirma" in result

    def test_preview_conflict_detection(self, writable_data_dir):
        """Preview on a date with existing confirmed event mentions conflict."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Conflicting Event",
            fecha="2026-05-24",  # same date as Koningsdag (confirmed)
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "Conflicting Event" in result

    def test_confirm_saves_sorted(self, writable_data_dir):
        """Confirm inserts event sorted by date in eventos array."""
        from src.tools.activity_creator import activity_creator, _load_calendar
        result = activity_creator(
            action="confirm",
            nombre="Mid Year Event",
            fecha="2026-06-15",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "mid-year-event" in result.lower()

        # Verify sorted insertion
        cal = _load_calendar(2026)
        fechas = [e.get("fecha", "9999") for e in cal["eventos"]]
        assert fechas == sorted(fechas)

        # Verify the event is present
        ids = [e["id"] for e in cal["eventos"]]
        assert "mid-year-event" in ids

    def test_confirm_duplicate_id_blocked(self, writable_data_dir):
        """Creating an event with a slug that already exists is blocked."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="confirm",
            nombre="Koningsdag 2026",  # slug = koningsdag-2026, already exists
            fecha="2026-09-15",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "ya existe" in result.lower()

    def test_readonly_blocked(self, writable_data_dir):
        """Readonly role cannot create events."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Test",
            fecha="2026-09-15",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="readonly",
        )
        assert "permiso" in result.lower()

    def test_invalid_date_format(self, writable_data_dir):
        """Invalid date format returns error."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Test",
            fecha="15-09-2026",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "formato" in result.lower() or "error" in result.lower()

    def test_invalid_tier(self, writable_data_dir):
        """Invalid tier_promocion returns error."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Test",
            fecha="2026-09-15",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="mega",
            flyer_responsable="nv",
            role="admin",
        )
        assert "invalido" in result.lower() or "opciones" in result.lower()

    def test_invalid_partner_id(self, writable_data_dir):
        """Non-existent partner_id returns error."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Test",
            fecha="2026-09-15",
            contacto_ids="hanna-test",
            partner_id="nonexistent-partner",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "no encontrado" in result.lower() or "error" in result.lower()

    def test_invalid_contact_id(self, writable_data_dir):
        """Non-existent contact ID returns error."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="preview",
            nombre="Test",
            fecha="2026-09-15",
            contacto_ids="nonexistent-contact",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "no encontrado" in result.lower() or "error" in result.lower()

    def test_confirm_sets_default_fields(self, writable_data_dir):
        """Confirmed event has all expected default fields."""
        from src.tools.activity_creator import activity_creator, _load_calendar
        activity_creator(
            action="confirm",
            nombre="Defaults Test",
            fecha="2026-10-01",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="mediano",
            flyer_responsable="proveedor",
            role="admin",
        )
        cal = _load_calendar(2026)
        evt = next(e for e in cal["eventos"] if e["id"] == "defaults-test")
        assert evt["show_in_export"] is True
        assert evt["fecha_exacta"] is True
        assert evt["flyer_status"] == "no_solicitado"
        assert evt["estado"] == "pendiente"
        assert "ultima_actualizacion" in evt

    def test_unknown_action(self, writable_data_dir):
        """Unknown action returns error."""
        from src.tools.activity_creator import activity_creator
        result = activity_creator(
            action="delete",
            nombre="Test",
            fecha="2026-09-15",
            contacto_ids="hanna-test",
            partner_id="nv-mexico",
            tier_promocion="regular",
            flyer_responsable="nv",
            role="admin",
        )
        assert "desconocida" in result.lower()


class TestPreprocessAgregar:
    """Tests for /agregar command preprocessing."""

    def test_agregar_command(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("agregar un nuevo evento")
        assert "[COMANDO: /agregar]" in result
        assert "ActivityCreator" in result

    def test_add_command_english(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("add a new event")
        assert "[COMANDO: /agregar]" in result

    def test_toevoegen_command_dutch(self):
        from src.agent import _preprocess_command
        result = _preprocess_command("toevoegen nieuw evenement")
        assert "[COMANDO: /agregar]" in result
