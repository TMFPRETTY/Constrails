"""
Database models and session management.
"""

import logging
import uuid
from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, Integer, JSON, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import CHAR, TypeDecorator

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(str(value))


class Decision(PythonEnum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"
    SANDBOX = "sandbox"
    QUARANTINE = "quarantine"


class RiskLevel(PythonEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditRecordModel(Base):
    __tablename__ = "audit_records"

    audit_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    request_id = Column(GUID(), nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    tool = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    policy_decision = Column(SQLEnum(Decision), nullable=False)
    final_decision = Column(SQLEnum(Decision), nullable=False)
    approver_id = Column(String, nullable=True)
    approval_id = Column(GUID(), nullable=True, index=True)
    replayed_from_approval_id = Column(GUID(), nullable=True, index=True)
    auth_type = Column(String, nullable=True)
    auth_subject = Column(String, nullable=True)
    auth_token_id = Column(String, nullable=True, index=True)
    auth_key_id = Column(String, nullable=True)
    chain_prev_hash = Column(String, nullable=True)
    chain_hash = Column(String, nullable=True, index=True)
    sandbox_id = Column(String, nullable=True)
    execution_result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"

    approval_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    request_id = Column(GUID(), nullable=False, unique=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    tool = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    policy_evaluation = Column(JSON, nullable=False)
    capability_fingerprint = Column(String, nullable=True)
    policy_mode = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    approved = Column(Boolean, nullable=True, default=None)
    approver_id = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)
    webhook_delivery_status = Column(String, nullable=False, default="not_configured")
    webhook_delivery_attempts = Column(Integer, nullable=False, default=0)
    webhook_last_attempt_at = Column(DateTime, nullable=True)
    webhook_last_response_code = Column(Integer, nullable=True)
    webhook_last_error = Column(Text, nullable=True)


class ApprovalWebhookOutboxModel(Base):
    __tablename__ = "approval_webhook_outbox"

    outbox_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    approval_id = Column(GUID(), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    delivery_status = Column(String, nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)


class QuotaEventModel(Base):
    __tablename__ = "quota_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    tool = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class RevokedTokenModel(Base):
    __tablename__ = "revoked_tokens"

    token_id = Column(String, primary_key=True)
    subject = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    revoked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class SigningKeyModel(Base):
    __tablename__ = "signing_keys"

    key_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    retired_at = Column(DateTime, nullable=True)


class CapabilityManifestModel(Base):
    __tablename__ = "capability_manifests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=True, index=True)
    namespace = Column(String, nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    allowed_tools = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    active = Column(Boolean, nullable=False, default=True)


class SandboxExecutionModel(Base):
    __tablename__ = "sandbox_executions"

    sandbox_id = Column(String, primary_key=True)
    request_id = Column(GUID(), nullable=False, index=True)
    approval_id = Column(GUID(), nullable=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    tool = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    container_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    executor = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)


def _build_database_url() -> str:
    if settings.database_url:
        return settings.database_url
    return "sqlite:///./constrail-dev.db"


DATABASE_URL = _build_database_url()
engine = create_engine(DATABASE_URL, echo=settings.database_echo)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (if not exists).")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
