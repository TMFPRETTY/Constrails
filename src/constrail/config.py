"""
Configuration management for Constrail.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_root_path: str = ""
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./constrail-dev.db"
    database_pool_size: int = 5
    database_echo: bool = False

    # Redis (for approval notifications and caching)
    redis_url: Optional[str] = None

    # Security
    secret_key: str = "change-me-in-production"
    token_algorithm: str = "HS256"
    token_expire_minutes: int = 30

    # Sandbox
    sandbox_type: str = "dev"  # dev, docker, gvisor, none
    docker_socket: Optional[str] = None  # defaults to /var/run/docker.sock
    sandbox_timeout_seconds: int = 300
    sandbox_memory_limit_mb: int = 512
    sandbox_cpu_shares: int = 512

    # Policy
    policy_engine: str = "opa"  # opa, builtin
    opa_url: str = "http://localhost:8181"
    opa_policy_package: str = "constrail"
    policy_dir: str = "./policies"

    # Risk engine
    risk_threshold_medium: float = 0.3
    risk_threshold_high: float = 0.7
    risk_threshold_critical: float = 0.9

    # Audit
    audit_log_dir: str = "./audit"
    audit_sign_logs: bool = False
    audit_signing_key: Optional[str] = None

    # Approval
    approval_webhook_url: Optional[str] = None
    approval_auto_approve_low_risk: bool = False

    # Anomaly detection
    anomaly_detection_enabled: bool = True
    anomaly_burst_threshold: int = 100  # calls per minute
    anomaly_new_tool_alert: bool = True


def get_settings() -> Settings:
    """Return the settings singleton."""
    return Settings()


# Global settings instance
settings = get_settings()