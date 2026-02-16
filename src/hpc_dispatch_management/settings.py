from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    DATABASE_URL: str = "sqlite:///./hpc_dispatch.db"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    JWT_SECRET: str
    JWT_ALGO: str = "HS256"
    MOCK_AUTH_ENABLED: bool = False

    NOTIFICATION_SERVICE_URL: HttpUrl
    HPC_USER_SERVICE_URL: HttpUrl
    HPC_DRIVE_SERVICE_URL: HttpUrl

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
