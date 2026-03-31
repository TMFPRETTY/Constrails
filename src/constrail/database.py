"""
Database models and session management.
"""

from sqlalchemy import create_engine, Column, String, Text, JSON, Float, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum as PythonEnum
import logging

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


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
    """SQLAlchemy model for audit records."""
    __tablename__ = "audit_records"

    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    tool = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    policy_decision = Column(SQLEnum(Decision), nullable=False)
    final_decision = Column(SQLEnum(Decision), nullable=False)
    approver_id = Column(String, nullable=True)
    sandbox_id = Column(String, nullable=True)
    execution_result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)


class ApprovalRequestModel(Base):
    """Approval requests awaiting human review."""
    __tablename__ = "approval_requests"

    approval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    tool = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    policy_evaluation = Column(JSON, nullable=False)  # serialized PolicyEvaluation
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    approved = Column(Boolean, nullable=True, default=None)  # None = pending, True/False decided
    approver_id = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)


class CapabilityManifestModel(Base):
    """Stored capability manifests."""
    __tablename__ = "capability_manifests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    allowed_tools = Column(JSON, nullable=False)  # list of tool allowances
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    active = Column(Boolean, nullable=False, default=True)


class SandboxExecutionModel(Base):
    """Sandbox execution records."""
    __tablename__ = "sandbox_executions"

    sandbox_id = Column(String, primary_key=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    tool = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    container_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)


# Create engine and session factory
engine = create_engine(settings.database_url, echo=settings.database_echo)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables (for development). In production, use Alembic migrations."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (if not exists).")


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()