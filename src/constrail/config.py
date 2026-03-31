"""
Configuration management for Constrail.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_root_path: str = ""
    debug: bool = False

    database_url: str = "sqlite:///./constrail-dev.db"
    database_pool_size: int = 5
    database_echo: bool = False

    redis_url: Optional[str] = None

    secret_key: str = "change-me-in-production"
    previous_secret_key: Optional[str] = None
    token_algorithm: str = "HS256"
    token_expire_minutes: int = 30
    token_issuer: str = "constrails"
    token_audience: str = "constrails-api"
    agent_api_key: str = "dev-agent"
    admin_api_key: str = "dev-admin"
    agent_tenant_id: str = "default"
    agent_namespace: str = "dev"
    admin_tenant_id: Optional[str] = None
    admin_namespace: Optional[str] = None

    sandbox_type: str = "dev"
    sandbox_mode: str = "development"
    sandbox_strict_mode: bool = False
    docker_socket: Optional[str] = None
    sandbox_image: str = "python:3.11-alpine"
    sandbox_timeout_seconds: int = 300
    sandbox_memory_limit_mb: int = 512
    sandbox_cpu_shares: int = 512
    sandbox_require_image_digest: bool = False
    sandbox_allow_host_network: bool = False
    sandbox_workspace_mount_readonly: bool = True
    sandbox_tmpfs_size_mb: int = 64

    policy_engine: str = "opa"
    policy_availability_mode: str = "degraded"
    opa_url: str = "http://localhost:8181"
    opa_policy_package: str = "constrail"
    policy_dir: str = "./policies"

    risk_threshold_medium: float = 0.3
    risk_threshold_high: float = 0.7
    risk_threshold_critical: float = 0.9

    audit_log_dir: str = "./audit"
    audit_sign_logs: bool = False
    audit_signing_key: Optional[str] = None

    approval_webhook_url: Optional[str] = None
    approval_webhook_secret: Optional[str] = None
    approval_auto_approve_low_risk: bool = False
    approval_webhook_max_attempts: int = 3
    approval_outbox_auto_drain: bool = False
    approval_outbox_auto_drain_limit: int = 20
    approval_expire_minutes: int = 60

    anomaly_detection_enabled: bool = True
    anomaly_burst_threshold: int = 100
    anomaly_new_tool_alert: bool = True


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
