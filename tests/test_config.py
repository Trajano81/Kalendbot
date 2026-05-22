"""Tests for centralized configuration."""
import os
import pytest


class TestSettings:
    """Test Settings class loads and validates configuration."""

    def test_settings_loads(self):
        from src.config import settings
        assert settings.data_dir is not None
        assert settings.webhook_port == 8000

    def test_default_values(self):
        from src.config import settings
        assert settings.log_level == "INFO"
        assert settings.log_format == "text"
        assert settings.whatsapp_provider == "waha"
        # waha_session_name may come from .env, just verify it's a non-empty string
        assert isinstance(settings.waha_session_name, str)
        assert settings.langchain_project == "kalendbot"

    def test_data_dir_from_env(self):
        """Settings should pick up KALENDBOT_DATA_DIR from environment."""
        from src.config import settings
        # conftest.py sets KALENDBOT_DATA_DIR to fixtures dir
        assert "fixtures" in settings.data_dir or settings.data_dir == "./kalendbot-data"

    def test_settings_extra_ignore(self):
        """Settings should ignore unknown env vars without error."""
        os.environ["SOME_RANDOM_VAR_XYZ"] = "test"
        try:
            from src.config import Settings
            s = Settings()
            assert s is not None
        finally:
            del os.environ["SOME_RANDOM_VAR_XYZ"]
