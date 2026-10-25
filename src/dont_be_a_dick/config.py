import os
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
"""The checkout root, so `.env` and the database are found wherever the server is started from."""

ModelRole = Literal["researcher", "judge", "resolver", "summarizer", "chat"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_prefix="DBAD_", extra="ignore", frozen=True
    )

    app_name: str = "dont-be-a-dick"
    debug: bool = False

    tavily_api_key: SecretStr = Field(
        default=SecretStr(""), description="API key for Tavily service"
    )
    openrouter_api_key: SecretStr = Field(
        default=SecretStr(""), description="API key for OpenRouter service"
    )

    default_model: str = Field(
        default="anthropic/claude-haiku-5.5",
        description="Model used by every role that has no override of its own",
    )
    max_concurrent_research: int = Field(
        default=3, ge=1, description="Research agents allowed to run at once, to ease API limits"
    )
    db_path: Path = Field(
        default=PROJECT_ROOT / "data" / "results.json",
        description="TinyDB file holding stored scoring runs. Single-process only.",
    )
    research_max_searches: int = Field(
        default=10, ge=1, description="Web searches one researcher may run per rubric"
    )
    research_max_fetches: int = Field(
        default=5, ge=1, description="Page fetches one researcher may run per rubric"
    )
    llm_max_retries: int = Field(
        default=1,
        ge=0,
        description=(
            "OpenRouter retry budget. Each unit allows ~150 s of backoff (SDK max_elapsed_time), "
            "not one attempt."
        ),
    )

    researcher_model: str | None = Field(default=None, description="Override for researchers")
    judge_model: str | None = Field(default=None, description="Override for judges")
    resolver_model: str | None = Field(default=None, description="Override for subject resolution")
    summarizer_model: str | None = Field(default=None, description="Override for the summary")
    chat_model: str | None = Field(default=None, description="Override for the /research agent")

    def model_for(self, role: ModelRole) -> str:
        """The role's override, or `default_model` when it has none."""
        return getattr(self, f"{role}_model") or self.default_model


class LangfuseSettings(BaseSettings):
    """Langfuse variables, kept apart from the `DBAD_` app settings.

    The Langfuse client reads `LANGFUSE_*` straight from the process environment, so
    `export_to_environ` copies what `.env` provides there. Real environment variables win.
    Tracing stays off unless it is enabled and both keys are present.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_prefix="LANGFUSE_", extra="ignore", frozen=True
    )

    tracing_enabled: bool = False
    public_key: str = ""
    secret_key: SecretStr = SecretStr("")
    base_url: str = "http://localhost:3000"
    tracing_environment: str | None = None

    @property
    def active(self) -> bool:
        return bool(self.tracing_enabled and self.public_key and self.secret_key.get_secret_value())

    def export_to_environ(self) -> None:
        values = {
            "tracing_enabled": str(self.tracing_enabled).lower(),
            "public_key": self.public_key or None,
            "secret_key": self.secret_key.get_secret_value() or None,
            "base_url": self.base_url,
            "tracing_environment": self.tracing_environment,
        }
        for name, value in values.items():
            if value is not None:
                os.environ.setdefault(f"LANGFUSE_{name.upper()}", value)


langfuse_settings = LangfuseSettings()
langfuse_settings.export_to_environ()

settings = Settings()
