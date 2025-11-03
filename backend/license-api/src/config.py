"""
License API configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """License API settings"""

    database_url: str = Field(
        default="postgresql://flexmon:changeme@timescaledb:5432/flexmon",
        validation_alias="DATABASE_URL"
    )

    api_secret_key: str = Field(
        default="changeme",
        validation_alias="API_SECRET_KEY"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
