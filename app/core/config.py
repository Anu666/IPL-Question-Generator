# Core configuration module
# Loads environment variables from .env using Pydantic BaseSettings.
# Access settings anywhere via: from app.core.config import settings

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application metadata
    APP_NAME: str = "IPL Question Generator API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        # Read values from the .env file at project root
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single shared instance — import this throughout the app
settings = Settings()
