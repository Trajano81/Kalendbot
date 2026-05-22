"""
Centralized configuration for KalendBot.
Validates all environment variables at startup using Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Core
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    data_dir: str = Field(default="./kalendbot-data", alias="KALENDBOT_DATA_DIR")
    webhook_port: int = Field(default=8000, alias="KALENDBOT_WEBHOOK_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")  # "text" or "json"

    # Telegram
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_group_chat_id: str = Field(default="", alias="TELEGRAM_GROUP_CHAT_ID")

    # WhatsApp
    whatsapp_provider: str = Field(default="waha", alias="WHATSAPP_PROVIDER")
    whatsapp_group_chat_id: str = Field(default="", alias="WHATSAPP_GROUP_CHAT_ID")
    whatsapp_bot_jid: str = Field(default="", alias="WHATSAPP_BOT_JID")

    # WAHA
    waha_api_url: str = Field(default="", alias="WAHA_API_URL")
    waha_api_key: str = Field(default="", alias="WAHA_API_KEY")
    waha_session_name: str = Field(default="kalendbot", alias="WAHA_SESSION_NAME")
    waha_dashboard_username: str = Field(default="admin", alias="WAHA_DASHBOARD_USERNAME")
    waha_dashboard_password: str = Field(default="", alias="WAHA_DASHBOARD_PASSWORD")

    # LangSmith (optional)
    langchain_tracing_v2: str = Field(default="false", alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="kalendbot", alias="LANGCHAIN_PROJECT")

    # Sentry (optional)
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }


settings = Settings()
