import os
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ModelRole = Literal["researcher", "judge", "resolver", "summarizer", "chat"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="DBAD_", extra="ignore", frozen=True
    )

    app_name: str = "dont-be-a-dick"
    debug: bool = False

    tavily_api_key: SecretStr = Field(
        default=SecretStr(""), description="API key for Tavily service"
    )
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""), description="API key for Anthropic/Claude service"
    )

    default_model: str = Field(
        default="claude-haiku-5-5",
        description="Model used by every role that has no override of its own",
    )
    max_concurrent_research: int = Field(
        default=3, ge=1, description="Research agents allowed to run at once, to ease API limits"
    )
    research_max_searches: int = Field(
        default=10, ge=1, description="Web searches one researcher may run per rubric"
    )
    research_max_fetches: int = Field(
        default=5, ge=1, description="Page fetches one researcher may run per rubric"
    )
    anthropic_max_retries: int = Field(
        default=6, ge=0, description="Retries on Anthropic rate limits and server errors"
    )

    researcher_model: str | None = Field(default=None, description="Override for researchers")
    judge_model: str | None = Field(default=None, description="Override for judges")
    resolver_model: str | None = Field(default=None, description="Override for subject resolution")
    summarizer_model: str | None = Field(default=None, description="Override for the summary")
    chat_model: str | None = Field(default=None, description="Override for the /research agent")

    def model_for(self, role: ModelRole) -> str:
        """The role's override, or `default_model` when it has none."""
        return getattr(self, f"{role}_model") or self.default_model


class LangSmithSettings(BaseSettings):
    """LangSmith variables, kept apart from the `DBAD_` app settings.

    LangChain and the LangSmith client read `LANGSMITH_*` straight from the process environment,
    so `export_to_environ` copies what `.env` provides there. Real environment variables win.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="LANGSMITH_", extra="ignore", frozen=True
    )

    tracing: bool = False
    api_key: SecretStr = SecretStr("")
    endpoint: str | None = None
    project: str | None = None
    agent_id: str | None = None
    agent_environment: str | None = None

    def export_to_environ(self) -> None:
        values = {
            "tracing": str(self.tracing).lower(),
            "api_key": self.api_key.get_secret_value() or None,
            "endpoint": self.endpoint,
            "project": self.project,
            "agent_id": self.agent_id,
            "agent_environment": self.agent_environment,
        }
        for name, value in values.items():
            if value is not None:
                os.environ.setdefault(f"LANGSMITH_{name.upper()}", value)


langsmith_settings = LangSmithSettings()
langsmith_settings.export_to_environ()

settings = Settings()
