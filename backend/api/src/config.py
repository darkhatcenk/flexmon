"""
FlexMON API Configuration
Loads settings from environment variables and Docker secrets
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


def read_secret(secret_name: str) -> Optional[str]:
    """Read secret from Docker secrets or fallback to env var"""
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        return secret_path.read_text().strip()
    return None


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    app_name: str = "FlexMON API"
    api_version: str = "v1"
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Database Configuration
    database_url: str = Field(
        default="postgresql://flexmon:changeme@timescaledb:5432/flexmon",
        validation_alias="DATABASE_URL"
    )

    # Elasticsearch Configuration
    elasticsearch_url: str = Field(
        default="http://elasticsearch:9200",
        validation_alias="ELASTICSEARCH_URL"
    )
    elasticsearch_user: str = Field(default="elastic", validation_alias="ELASTICSEARCH_USER")

    @property
    def elasticsearch_password(self) -> str:
        """Get Elasticsearch password from secret or env"""
        return (
            read_secret("elastic_password") or
            os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
        )

    # XMPP Configuration
    xmpp_host: str = Field(default="xmpp", validation_alias="XMPP_HOST")
    xmpp_port: int = Field(default=5222, validation_alias="XMPP_PORT")
    xmpp_domain: str = Field(default="localhost", validation_alias="XMPP_DOMAIN")

    # License API Configuration
    license_api_url: str = Field(
        default="http://license-api:8001",
        validation_alias="LICENSE_API_URL"
    )
    license_check_interval_hours: int = Field(
        default=24,
        validation_alias="LICENSE_CHECK_INTERVAL_HOURS"
    )
    license_grace_period_days: int = Field(
        default=7,
        validation_alias="LICENSE_GRACE_PERIOD_DAYS"
    )

    # AI Service Configuration
    ai_api_url: str = Field(
        default="https://ai.cloudflex.tr",
        validation_alias="AI_API_URL"
    )

    @property
    def ai_api_token(self) -> Optional[str]:
        """Get AI API token from secret or env"""
        return read_secret("ai_token") or os.getenv("AI_API_TOKEN")

    # Security Configuration
    @property
    def api_secret_key(self) -> str:
        """Get API secret key from secret or env"""
        return (
            read_secret("api_secret") or
            os.getenv("API_SECRET_KEY", "changeme-insecure-secret-key-change-in-production")
        )

    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(default=60, validation_alias="JWT_EXPIRATION_MINUTES")

    # TLS Configuration
    tls_cert_path: Optional[str] = Field(
        default="/app/certs/server.crt",
        validation_alias="TLS_CERT_PATH"
    )
    tls_key_path: Optional[str] = Field(
        default="/app/certs/server.key",
        validation_alias="TLS_KEY_PATH"
    )
    enable_mtls: bool = Field(default=False, validation_alias="ENABLE_MTLS")
    ca_cert_path: Optional[str] = Field(
        default="/app/certs/ca.crt",
        validation_alias="CA_CERT_PATH"
    )

    # Rate Limiting
    api_rate_limit_per_min: int = Field(
        default=1000,
        validation_alias="API_RATE_LIMIT_PER_MIN"
    )
    metrics_batch_max_size_mb: int = Field(
        default=15,
        validation_alias="METRICS_BATCH_MAX_SIZE_MB"
    )
    metrics_batch_max_records: int = Field(
        default=3000,
        validation_alias="METRICS_BATCH_MAX_RECORDS"
    )

    # Alert Configuration
    alert_dedup_minutes: int = Field(
        default=15,
        validation_alias="ALERT_DEDUP_MINUTES"
    )
    alert_batch_size: int = Field(
        default=100,
        validation_alias="ALERT_BATCH_SIZE"
    )

    # Agent Configuration
    agent_default_interval_sec: int = Field(
        default=30,
        validation_alias="AGENT_DEFAULT_INTERVAL_SEC"
    )
    agent_min_interval_sec: int = Field(
        default=10,
        validation_alias="AGENT_MIN_INTERVAL_SEC"
    )
    agent_max_interval_sec: int = Field(
        default=300,
        validation_alias="AGENT_MAX_INTERVAL_SEC"
    )

    # Retention Configuration
    metrics_raw_retention_days: int = Field(
        default=7,
        validation_alias="METRICS_RAW_RETENTION_DAYS"
    )
    metrics_5min_retention_days: int = Field(
        default=30,
        validation_alias="METRICS_5MIN_RETENTION_DAYS"
    )
    metrics_1h_retention_days: int = Field(
        default=365,
        validation_alias="METRICS_1H_RETENTION_DAYS"
    )
    logs_hot_retention_days: int = Field(
        default=1,
        validation_alias="LOGS_HOT_RETENTION_DAYS"
    )
    logs_warm_retention_days: int = Field(
        default=7,
        validation_alias="LOGS_WARM_RETENTION_DAYS"
    )
    logs_total_retention_days: int = Field(
        default=90,
        validation_alias="LOGS_TOTAL_RETENTION_DAYS"
    )

    # S3 Backup Configuration
    s3_endpoint: Optional[str] = Field(default=None, validation_alias="S3_ENDPOINT")
    s3_bucket: Optional[str] = Field(default=None, validation_alias="S3_BUCKET")
    s3_access_key: Optional[str] = Field(default=None, validation_alias="S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = Field(default=None, validation_alias="S3_SECRET_KEY")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        validation_alias="CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
