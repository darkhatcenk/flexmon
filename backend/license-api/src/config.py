"""
License API configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
import urllib.parse
import re


class Settings(BaseSettings):
    """License API settings"""

    # Database connection - can be full URL or discrete parts
    database_url: Optional[str] = Field(
        default=None,
        validation_alias="DATABASE_URL"
    )

    db_host: str = Field(default="timescaledb", validation_alias="DB_HOST")
    db_port: str = Field(default="5432", validation_alias="DB_PORT")  # String for validation
    db_user: str = Field(default="flexmon", validation_alias="POSTGRES_USER")
    db_password: str = Field(default="changeme", validation_alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="flexmon", validation_alias="POSTGRES_DB")

    api_secret_key: str = Field(
        default="changeme",
        validation_alias="API_SECRET_KEY"
    )

    @field_validator("db_port")
    @classmethod
    def validate_db_port(cls, v):
        """Validate and coerce port to string"""
        try:
            port = int(v)
            if not (1 <= port <= 65535):
                print(f"WARNING: Invalid DB_PORT {v}, using default 5432")
                return "5432"
            return str(port)
        except (ValueError, TypeError):
            print(f"WARNING: Invalid DB_PORT {v}, using default 5432")
            return "5432"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_database_url(self) -> str:
        """Get the database URL, building from parts if needed"""
        if self.database_url:
            return self.database_url
        # Build DSN with URL-encoded password
        encoded_password = urllib.parse.quote_plus(self.db_password)
        return f"postgresql://{self.db_user}:{encoded_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_redacted_database_url(self) -> str:
        """Get database URL with password masked for logging"""
        url = self.get_database_url()
        # Mask password: show first 2 and last 2 chars
        return re.sub(r':([^:@]{2})[^@]*([^@]{2})@', r':\1****\2@', url)


settings = Settings()
