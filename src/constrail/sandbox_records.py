"""
Persistence helpers for sandbox execution records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .database import SandboxExecutionModel, SessionLocal


class SandboxExecutionService:
    def record_execution(
        self,
        sandbox_id: str,
        request_id: UUID,
        agent_id: str,
        tool: str,
        parameters: dict,
        executor: Optional[str],
        status: str,
        result: Optional[dict],
        error: Optional[str],
        approval_id: Optional[UUID] = None,
        duration_ms: Optional[int] = None,
        container_id: Optional[str] = None,
    ) -> SandboxExecutionModel:
        db = SessionLocal()
        try:
            row = SandboxExecutionModel(
                sandbox_id=sandbox_id,
                request_id=request_id,
                approval_id=approval_id,
                agent_id=agent_id,
                tool=tool,
                parameters=parameters,
                container_id=container_id,
                status=status,
                executor=executor,
                result=result,
                error=error,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_ms=duration_ms,
            )
            persisted = db.merge(row)
            db.commit()
            db.refresh(persisted)
            return persisted
        finally:
            db.close()

    def get_execution(self, sandbox_id: str) -> Optional[SandboxExecutionModel]:
        db = SessionLocal()
        try:
            return (
                db.query(SandboxExecutionModel)
                .filter(SandboxExecutionModel.sandbox_id == sandbox_id)
                .first()
            )
        finally:
            db.close()


_default_sandbox_execution_service: Optional[SandboxExecutionService] = None


def get_sandbox_execution_service() -> SandboxExecutionService:
    global _default_sandbox_execution_service
    if _default_sandbox_execution_service is None:
        _default_sandbox_execution_service = SandboxExecutionService()
    return _default_sandbox_execution_service
