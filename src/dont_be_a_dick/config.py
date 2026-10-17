from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DBAD_", extra="ignore")

    app_name: str = "dont-be-a-dick"
    debug: bool = False


settings = Settings()
