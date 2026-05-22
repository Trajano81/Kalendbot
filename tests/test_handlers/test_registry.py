"""Tests for the shared command registry."""
import pytest

from src.handlers.registry import (
    find_command, get_all_commands, get_commands_for_menu,
    check_permission, CommandContext, CommandResult,
)


class TestCommandRegistry:
    def test_all_commands_registered(self):
        """All expected commands should be registered."""
        # Import handler modules to trigger registration
        import src.handlers.exports  # noqa: F401
        import src.handlers.visibility  # noqa: F401
        import src.handlers.help  # noqa: F401
        import src.handlers.language  # noqa: F401
        import src.handlers.status  # noqa: F401

        commands = get_all_commands()
        names = {cmd.name for cmd in commands}
        assert "export_excel" in names
        assert "export_jpeg" in names
        assert "export_jpeg_codes" in names
        assert "export_instructions" in names
        assert "ocultar" in names
        assert "mostrar" in names
        assert "help" in names
        assert "idioma" in names
        assert "status" in names

    def test_find_command_by_name(self):
        cmd = find_command("help")
        assert cmd is not None
        assert cmd.name == "help"

    def test_find_command_by_alias(self):
        cmd = find_command("ayuda")
        assert cmd is not None
        assert cmd.name == "help"

    def test_find_command_by_alias_export(self):
        cmd = find_command("export")
        assert cmd is not None
        assert cmd.name == "export_excel"

    def test_find_command_not_found(self):
        cmd = find_command("nonexistent_command")
        assert cmd is None

    def test_find_command_hide_aliases(self):
        cmd = find_command("hide")
        assert cmd is not None
        assert cmd.name == "ocultar"

    def test_find_command_verbergen(self):
        cmd = find_command("verbergen")
        assert cmd is not None
        assert cmd.name == "ocultar"

    def test_find_command_show_aliases(self):
        cmd = find_command("show")
        assert cmd is not None
        assert cmd.name == "mostrar"

    def test_find_command_tonen(self):
        cmd = find_command("tonen")
        assert cmd is not None
        assert cmd.name == "mostrar"

    def test_find_command_estado(self):
        cmd = find_command("estado")
        assert cmd is not None
        assert cmd.name == "status"

    def test_find_command_language(self):
        cmd = find_command("language")
        assert cmd is not None
        assert cmd.name == "idioma"

    def test_get_commands_for_menu_es(self):
        menu = get_commands_for_menu("es")
        assert len(menu) > 0
        names = [name for name, desc in menu]
        assert "help" in names

    def test_get_commands_for_menu_en(self):
        menu = get_commands_for_menu("en")
        for name, desc in menu:
            if name == "help":
                assert "Show" in desc or "available" in desc

    def test_get_commands_for_menu_nl(self):
        menu = get_commands_for_menu("nl")
        for name, desc in menu:
            if name == "help":
                assert "commando" in desc.lower() or "hulp" in desc.lower() or "Beschikbare" in desc


class TestCheckPermission:
    def test_admin_can_do_anything(self):
        assert check_permission("admin", "readonly") is True
        assert check_permission("admin", "contacto") is True
        assert check_permission("admin", "tester") is True
        assert check_permission("admin", "admin") is True

    def test_readonly_limited(self):
        assert check_permission("readonly", "readonly") is True
        assert check_permission("readonly", "contacto") is False
        assert check_permission("readonly", "admin") is False

    def test_contacto_mid_tier(self):
        assert check_permission("contacto", "readonly") is True
        assert check_permission("contacto", "contacto") is True
        assert check_permission("contacto", "admin") is False

    def test_unknown_role(self):
        assert check_permission("unknown", "readonly") is True
        assert check_permission("unknown", "admin") is False


class TestCommandContext:
    def test_creation(self):
        ctx = CommandContext(
            contact_id="test-user",
            phone="1234",
            text="some args",
            language="es",
            channel="telegram",
        )
        assert ctx.contact_id == "test-user"
        assert ctx.language == "es"
        assert ctx.channel == "telegram"


class TestCommandResult:
    def test_text_result(self):
        r = CommandResult(text="hello")
        assert r.text == "hello"
        assert r.error is None
        assert r.file_path is None

    def test_error_result(self):
        r = CommandResult(error="not allowed")
        assert r.error == "not allowed"
        assert r.text is None

    def test_file_result(self):
        r = CommandResult(file_path="/tmp/test.xlsx", text="caption")
        assert r.file_path == "/tmp/test.xlsx"
        assert r.text == "caption"
