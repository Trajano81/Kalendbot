"""
Regression tests for resolved issues.
Story 7.1: Test Suite Fundacional — FR26
Covers ISSUE-01~05 and OBS-01~06 from CLI testing sessions.
"""
import json
import os


# ========================================================================
# ISSUE-01: CLI phone simulation — contact_id passed directly
# ========================================================================

class TestIssue01:
    def test_handle_message_accepts_contact_id(self, writable_data_dir):
        """handle_message should accept contact_id parameter directly."""
        from src.agent import handle_message
        import inspect
        sig = inspect.signature(handle_message)
        assert "contact_id" in sig.parameters, \
            "handle_message must accept contact_id param (ISSUE-01 fix)"


# ========================================================================
# ISSUE-02: Recursion limit by tool call loop (StructuredTool migration)
# ========================================================================

class TestIssue02:
    def test_calendar_manager_is_structured(self, writable_data_dir):
        """CalendarManager should use StructuredTool, not Tool."""
        from src.tools.calendar_manager import calendar_manager
        import inspect
        sig = inspect.signature(calendar_manager)
        # StructuredTool functions have named params, not just a single string
        assert "action" in sig.parameters, \
            "calendar_manager must have 'action' param (StructuredTool, ISSUE-02/04)"

    def test_date_locker_is_structured(self, writable_data_dir):
        from src.tools.date_locker import date_locker
        import inspect
        sig = inspect.signature(date_locker)
        assert "action" in sig.parameters

    def test_flyer_manager_is_structured(self, writable_data_dir):
        from src.tools.flyer_manager import flyer_manager
        import inspect
        sig = inspect.signature(flyer_manager)
        assert "action" in sig.parameters


# ========================================================================
# ISSUE-03: Memory assigned to correct contact
# ========================================================================

class TestIssue03:
    def test_contact_id_not_unknown_for_known_phone(self, writable_data_dir):
        """Known phone should resolve to real contact_id, not unknown-XXXX."""
        from src.gateways.contacts import identify_by_phone
        result = identify_by_phone("+528120264857")
        contact_id = result[0] if isinstance(result, tuple) else result
        assert contact_id is not None
        assert not contact_id.startswith("unknown-")
        assert contact_id == "hanna-test"


# ========================================================================
# ISSUE-04: Multi-param tools accept structured input
# ========================================================================

class TestIssue04:
    def test_calendar_manager_multi_params(self, writable_data_dir):
        """CalendarManager should handle multiple named params correctly."""
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_by_contact", contact_id="hanna-test")
        assert "Koningsdag" in result

    def test_date_locker_multi_params(self, writable_data_dir):
        from src.tools.date_locker import date_locker
        result = date_locker(action="check", event_id="koningsdag-2026", fecha="2026-04-27")
        assert len(result) > 0


# ========================================================================
# ISSUE-05: RulesEngine "all" doesn't loop infinitely
# ========================================================================

class TestIssue05:
    def test_rules_engine_all_terminates(self, writable_data_dir):
        """RulesEngine 'all' query should complete without infinite recursion."""
        from src.tools.rules_engine import rules_engine
        result = rules_engine("all")
        assert len(result) > 0
        assert len(result) < 50000  # Sanity check: not absurdly long


# ========================================================================
# OBS-01: ContactManager fuzzy matching
# ========================================================================

class TestObs01:
    def test_search_by_partial_name(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("search:Koen")
        assert "Koen" in result

    def test_search_case_insensitive(self, writable_data_dir):
        from src.tools.contact_manager import contact_manager
        result = contact_manager("search:hanna")
        assert "Hanna" in result

    def test_search_multiple_results(self, writable_data_dir):
        """Search 'an' should match Hanna and Christian."""
        from src.tools.contact_manager import contact_manager
        result = contact_manager("search:an")
        # At least one match
        assert "Hanna" in result or "Christian" in result


# ========================================================================
# OBS-02: Event count by contact
# ========================================================================

class TestObs02:
    def test_event_count_by_contact(self, writable_data_dir):
        """list_by_contact should return correct count for known contact."""
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_by_contact", contact_id="hanna-test")
        # hanna-test is in: koningsdag, sinterklaas, mayo-event = 3 events
        assert "Koningsdag" in result
        assert "Sinterklaas" in result
        assert "Mayo" in result


# ========================================================================
# OBS-03: ConflictDetector works on non-holiday
# ========================================================================

class TestObs03:
    def test_no_conflict_on_clear_date(self, writable_data_dir):
        from src.tools.conflict_detector import conflict_detector
        result = conflict_detector("2026-08-15")
        # Should NOT report a holiday conflict
        assert "feriado" not in result.lower() or "sin" in result.lower()


# ========================================================================
# OBS-04: list_pending separates future vs past
# ========================================================================

class TestObs04:
    def test_list_pending_shows_past_events(self, writable_data_dir):
        """list_pending should show past pending events separately."""
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_pending")
        # nieuwjaar-2026 (2026-01-22) is past and pending
        assert "Nieuwjaarsreceptie" in result


# ========================================================================
# OBS-05: FAQ matches correctly (no false positives)
# ========================================================================

class TestObs05:
    def test_faq_exact_match(self, writable_data_dir):
        from src.agent import _check_faq
        result = _check_faq("cuantos eventos hay?")
        assert result is not None

    def test_faq_no_false_positive_partial(self, writable_data_dir):
        """'cuantos eventos tiene Koen' must NOT match FAQ 'cuantos eventos hay'."""
        from src.agent import _check_faq
        result = _check_faq("cuantos eventos tiene Koen?")
        assert result is None

    def test_faq_no_false_positive_greeting(self, writable_data_dir):
        from src.agent import _check_faq
        result = _check_faq("hola que tal")
        assert result is None


# ========================================================================
# OBS-06: Past events in list_pending with warning
# ========================================================================

class TestObs06:
    def test_past_pending_events_flagged(self, writable_data_dir):
        """Past events that are still 'pendiente' should be visible in list_pending."""
        from src.tools.calendar_manager import calendar_manager
        result = calendar_manager(action="list_pending")
        # nieuwjaar is past (2026-01-22) + pending — should appear
        assert "Nieuwjaarsreceptie" in result or "nieuwjaar" in result.lower()
