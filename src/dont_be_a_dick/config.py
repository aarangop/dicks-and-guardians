from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    researcher_model: str = Field(default="claude-sonnet-5-5", description="Model for researchers")
    judge_model: str = Field(default="claude-sonnet-5-5", description="Model for judges")
    resolver_model: str = Field(
        default="claude-haiku-4-5-20251001", description="Model for subject resolution"
    )
    summarizer_model: str = Field(
        default="claude-haiku-4-5-20251001", description="Model for the final summary"
    )


settings = Settings()
