from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Mail Intelligence"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_origin: str = "http://127.0.0.1:5173"
    database_url: str = "sqlite:///./data/mail_intelligence.db"
    google_credentials_path: str = "./secrets/credentials.json"
    google_token_path: str = "./secrets/token.json"
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_chat_model: str = ""
    lmstudio_embedding_model: str = ""
    lmstudio_timeout_seconds: int = 120
    max_email_body_chars: int = 18000
    default_sync_days: int = 90

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
