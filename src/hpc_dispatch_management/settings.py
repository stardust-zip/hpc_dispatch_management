from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # This will automatically look for an environment variable named
    # NOTIFICATION_SERVICE_URL.
    # The default value is set for local development.
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8080/api/v1/events/publish"

    # DATABSE URL CONFIGURATION (DB/TEST/PROD)
    # It will look for DATABASE_URL environment variable.
    # If it's not found, it defaults to SQLite db for local development.
    DATABASE_URL: str = "sqlite:///./hpc_dispatch.db"

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Create a single, reusable instance of the settings
settings = Settings()
