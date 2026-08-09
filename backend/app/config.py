"""Central runtime settings, loaded from environment variables / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider
    anthropic_api_key: str = ""
    persona_model: str = "claude-sonnet-5"
    structured_model: str = "claude-sonnet-5"

    # evidence-server search backend
    serper_api_key: str = ""

    # debate bounds (overridable per debate at intake time, these are defaults)
    min_rounds: int = 2
    max_rounds: int = 6

    # checkpointer
    checkpoint_db_path: str = "expert_panel.sqlite3"


settings = Settings()
