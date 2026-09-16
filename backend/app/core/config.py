from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Vercel request body ceiling is below the historical 8 MiB intake limit.
# 4 MiB stays safely under the platform payload limit after multipart overhead.
DEFAULT_MAX_UPLOAD_BYTES = 4 * 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "VeyraQ"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/veyraq"
    )
    # Comma-separated origins in env (not JSON). NoDecode avoids pydantic-settings
    # attempting json.loads on values like https://app.vercel.app
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_STRUCTURED_OUTPUT_STRICT: bool = True
    MAX_UPLOAD_BYTES: int = DEFAULT_MAX_UPLOAD_BYTES

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            return origins or ["http://localhost:5173"]
        return value

    @field_validator("MAX_UPLOAD_BYTES", mode="before")
    @classmethod
    def parse_max_upload_bytes(cls, value: object) -> object:
        if isinstance(value, str) and value.strip():
            return int(value.strip())
        return value


settings = Settings()
