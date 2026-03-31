"""
Pydantic models for audit and sandbox inspection APIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditRecordResponse(BaseModel):
    audit_id: UUID
    request_id: UUID
    agent_id: str
    tool: str
    parameters: dict[str, Any]
    risk_score: float
    risk_level: str
    policy_decision: str
    final_decision: str
    approver_id: Optional[str] = None
    approval_id: Optional[UUID] = None
    replayed_from_approval_id: Optional[UUID] = None
    sandbox_id: Optional[str] = None
    execution_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None

    @classmethod
    def from_db(cls, row):
        return cls(
            audit_id=row.audit_id,
            request_id=row.request_id,
            agent_id=row.agent_id,
            tool=row.tool,
            parameters=row.parameters,
            risk_score=row.risk_score,
            risk_level=row.risk_level.value if hasattr(row.risk_level, 'value') else str(row.risk_level),
            policy_decision=row.policy_decision.value if hasattr(row.policy_decision, 'value') else str(row.policy_decision),
            final_decision=row.final_decision.value if hasattr(row.final_decision, 'value') else str(row.final_decision),
            approver_id=row.approver_id,
            approval_id=row.approval_id,
            replayed_from_approval_id=row.replayed_from_approval_id,
            sandbox_id=row.sandbox_id,
            execution_result=row.execution_result,
            error=row.error,
            start_time=row.start_time,
            end_time=row.end_time,
            duration_ms=row.duration_ms,
        )


class SandboxExecutionResponse(BaseModel):
    sandbox_id: str
    request_id: UUID
    approval_id: Optional[UUID] = None
    agent_id: str
    tool: str
    parameters: dict[str, Any]
    container_id: Optional[str] = None
    status: str
    executor: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    @classmethod
    def from_db(cls, row):
        return cls(
            sandbox_id=row.sandbox_id,
            request_id=row.request_id,
            approval_id=row.approval_id,
            agent_id=row.agent_id,
            tool=row.tool,
            parameters=row.parameters,
            container_id=row.container_id,
            status=row.status,
            executor=row.executor,
            result=row.result,
            error=row.error,
            created_at=row.created_at,
            completed_at=row.completed_at,
            duration_ms=row.duration_ms,
        )


class CapabilityManifestResponse(BaseModel):
    id: int
    agent_id: str
    tenant_id: Optional[str] = None
    namespace: Optional[str] = None
    version: int
    allowed_tools: list[dict[str, Any]]
    created_at: datetime
    expires_at: Optional[datetime] = None
    active: bool

    @classmethod
    def from_db(cls, row):
        return cls(
            id=row.id,
            agent_id=row.agent_id,
            tenant_id=getattr(row, 'tenant_id', None),
            namespace=getattr(row, 'namespace', None),
            version=row.version,
            allowed_tools=row.allowed_tools,
            created_at=row.created_at,
            expires_at=row.expires_at,
            active=row.active,
        )
