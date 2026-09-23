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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def dataset_path(self) -> Path:
        return Path(self.dataset_dir).resolve()


settings = Settings()
if os.getenv("DATASET_DIR"):
    settings.dataset_dir = os.getenv("DATASET_DIR")
