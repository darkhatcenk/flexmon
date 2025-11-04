"""
License API configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional


class Settings(BaseSettings):
    """License API settings"""

    # Database connection - can be full URL or discrete parts
    database_url: Optional[str] = Field(
        default=None,
        validation_alias="DATABASE_URL"
    )

    db_host: str = Field(default="timescaledb")
    db_port: int = Field(default=5432)
    db_user: str = Field(default="flexmon", validation_alias="POSTGRES_USER")
    db_password: str = Field(default="changeme", validation_alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="flexmon", validation_alias="POSTGRES_DB")

    api_secret_key: str = Field(
        default="changeme",
        validation_alias="API_SECRET_KEY"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_database_url(self) -> str:
        """Get the database URL, building from parts if needed"""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
