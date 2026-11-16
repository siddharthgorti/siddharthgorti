"""Application settings, loaded from environment variables / `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # LLM. With no API key the app runs in "offline" mode (deterministic stub
    # responses) so the whole stack can be developed and tested without spend.
    anthropic_api_key: str | None = None
    llm_mode: str = "auto"  # "auto" | "anthropic" | "offline"
    default_model: str = "claude-sonnet-5-5"
    chat_effort: str = "low"  # tutoring turns: latency-sensitive
    quiz_effort: str = "medium"  # answer keys must be correct: think more
    enable_refusal_fallbacks: bool = True

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'tuition.db'}"
    upload_dir: Path = BACKEND_DIR / "data" / "uploads"
    max_upload_mb: int = 20

    cors_origins: list[str] = ["http://localhost:3000"]

    default_board: str = "CBSE"
    default_grade: int = 11
    subject: str = "Mathematics"

    max_turns_per_session: int = 50
    history_turns_in_prompt: int = 12  # recent messages sent to the LLM
    rag_top_k: int = 4

    @property
    def resolved_llm_mode(self) -> str:
        if self.llm_mode in ("anthropic", "offline"):
            return self.llm_mode
        return "anthropic" if self.anthropic_api_key else "offline"


@lru_cache
def get_settings() -> Settings:
    return Settings()
