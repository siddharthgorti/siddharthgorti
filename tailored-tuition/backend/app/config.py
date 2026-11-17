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
    # "auto": Claude if ANTHROPIC_API_KEY is set, else a local Ollama model if
    # Ollama is running, else canned offline demo replies.
    llm_mode: str = "auto"  # "auto" | "anthropic" | "ollama" | "offline"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    # Chat runs on every student message, so it favours speed; quiz generation
    # is rarer and a wrong answer key is the costliest error, so it favours
    # accuracy. See README "Choosing models".
    chat_model: str = "claude-sonnet-5-5"
    chat_effort: str = "low"
    quiz_model: str = "claude-opus-5-5"
    quiz_effort: str = "medium"
    enable_refusal_fallbacks: bool = True

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'tuition.db'}"
    data_dir: Path = BACKEND_DIR / "data"
    max_upload_mb: int = 20

    # Accounts, email and security (see docs/API.md "Configuration").
    app_env: str = "development"  # "development" | "production"
    public_url: str = "http://localhost:3000"
    email_backend: str = "console"  # "console" | "smtp"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    cookie_secure: bool = False
    admin_emails: str = ""  # comma-separated
    privacy_policy_version: str = "2026-11-17"
    guardian_session_days: int = 14
    student_session_days: int = 30
    max_messages_per_day: int = 200
    max_sessions_per_day: int = 30
    max_quizzes_per_day: int = 20
    seed_demo_accounts: bool = False

    cors_origins: list[str] = ["http://localhost:3000"]

    default_board: str = "CBSE"
    default_grade: int = 11
    subject: str = "Mathematics"

    max_turns_per_session: int = 50
    history_turns_in_prompt: int = 12  # recent messages sent to the LLM
    rag_top_k: int = 4

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def dev_links_enabled(self) -> bool:
        """Return verification/reset links in API responses: local development only."""
        return self.app_env == "development" and self.email_backend == "console"

    def production_problems(self) -> list[str]:
        """Settings that would be unsafe in production (empty list = OK)."""
        if self.app_env != "production":
            return []
        problems = []
        if self.email_backend != "smtp":
            problems.append("EMAIL_BACKEND must be 'smtp'")
        elif not (self.smtp_host and self.smtp_from):
            problems.append("SMTP_HOST and SMTP_FROM must be set")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true")
        if not self.public_url.startswith("https://"):
            problems.append("PUBLIC_URL must start with https://")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL must be Postgres, not SQLite")
        if self.seed_demo_accounts:
            problems.append("SEED_DEMO_ACCOUNTS must be false")
        return problems

    @property
    def resolved_llm_mode(self) -> str:
        if self.llm_mode in ("anthropic", "ollama", "offline"):
            return self.llm_mode
        if self.anthropic_api_key:
            return "anthropic"
        from app.llm.ollama import ollama_available

        return "ollama" if ollama_available(self.ollama_url) else "offline"


@lru_cache
def get_settings() -> Settings:
    return Settings()
