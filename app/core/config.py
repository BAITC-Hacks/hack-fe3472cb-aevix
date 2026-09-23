import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HackAlem AI Career Quest"
    environment: str = "development"
    dataset_dir: str = str((Path(__file__).resolve().parents[2] / "career_quest_dataset" / "case_1" / "career_quest_dataset").resolve())
    database_url: str = "sqlite:///./career_quest.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-6-astra"
    hr_username: str = "hr"
    hr_password_hash: str | None = None
    hr_session_hours: int = 8
    hr_cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.allowed_origins.split(",") if origin.strip() and origin.strip() != "*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def dataset_path(self) -> Path:
        return Path(self.dataset_dir).resolve()


settings = Settings()
if os.getenv("DATASET_DIR"):
    settings.dataset_dir = os.getenv("DATASET_DIR")
