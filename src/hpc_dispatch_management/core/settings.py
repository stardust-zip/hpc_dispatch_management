from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


# By inherting BaseSettings, Pydantic knows that every atrtibute
# defined inside this class should be populated by an environtment varibale
# matching it's name.
class Settings(BaseSettings):
    # local or production
    APP_ENV: str

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    DATABASE_URL: str
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://103.126.161.228:3001",
        "http://103.126.161.228",
        "http://hethongdientu.khoacongnghethongtinhpc.io.vn",
        "https://hethongdientu.khoacongnghethongtinhpc.io.vn",
        "http://hethongdientu.khoacongnghethongtinhpc.io.vn:3001",
        "https://hethongdientu.khoacongnghethongtinhpc.io.vn:3001",
    ]

    METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    HEADERS: list[str] = ["Content-Type", "Authorization", "Accept"]

    JWT_SECRET: str
    JWT_ALGO: str

    NOTIFICATION_SERVICE_URL: HttpUrl
    HPC_USER_SERVICE_URL: HttpUrl
    HPC_DRIVE_SERVICE_URL: HttpUrl

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore any extra env variable that wasn't defined in settings.py
    )


# At this moment as Python instantiates the class,
# Pydantic parses the .env file, reads the system env varibles,
# vidates all data types, applies defaults, and sotre everything insde
# settings object.
# With this, other files can import and and safely use the varibles with
# full autocomplete and type-safety, knwoing that validation has already passed
settings = Settings()
