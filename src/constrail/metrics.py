from __future__ import annotations

from .approval import get_approval_service
from .database import SessionLocal, AuditRecordModel, SandboxExecutionModel
from .rate_limits import get_rate_limit_service
from .sandbox import sandbox_health


def get_metrics_snapshot() -> dict:
    db = SessionLocal()
    try:
        approval_summary = get_approval_service().outbox_summary()
        quota_summary = get_rate_limit_service().summary(limit_seconds=3600)
        audit_count = db.query(AuditRecordModel).count()
        sandbox_count = db.query(SandboxExecutionModel).count()
        return {
            'approvals': approval_summary,
            'quotas_last_hour': quota_summary,
            'audit_records_total': audit_count,
            'sandbox_executions_total': sandbox_count,
            'sandbox_health': sandbox_health(),
        }
    finally:
        db.close()
