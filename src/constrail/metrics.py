from __future__ import annotations

from .approval import get_approval_service
from .database import SessionLocal, AuditRecordModel, SandboxExecutionModel, QuotaEventModel
from .rate_limits import get_rate_limit_service
from .sandbox import sandbox_health


def get_metrics_snapshot() -> dict:
    db = SessionLocal()
    try:
        approval_summary = get_approval_service().outbox_summary()
        quota_summary = get_rate_limit_service().summary(limit_seconds=3600)
        audit_count = db.query(AuditRecordModel).count()
        sandbox_count = db.query(SandboxExecutionModel).count()
        quota_total = db.query(QuotaEventModel).count()
        return {
            'approvals': approval_summary,
            'quotas_last_hour': quota_summary,
            'quota_events_total': quota_total,
            'audit_records_total': audit_count,
            'sandbox_executions_total': sandbox_count,
            'sandbox_health': sandbox_health(),
        }
    finally:
        db.close()


def render_prometheus_metrics() -> str:
    snapshot = get_metrics_snapshot()
    lines = [
        '# HELP constrail_approval_outbox_total Total approval outbox items',
        '# TYPE constrail_approval_outbox_total gauge',
        f"constrail_approval_outbox_total {snapshot['approvals']['total']}",
        f"constrail_approval_outbox_pending {snapshot['approvals']['pending']}",
        f"constrail_approval_outbox_failed {snapshot['approvals']['failed']}",
        f"constrail_approval_outbox_delivered {snapshot['approvals']['delivered']}",
        '# HELP constrail_quota_events_total Total quota events persisted',
        '# TYPE constrail_quota_events_total gauge',
        f"constrail_quota_events_total {snapshot['quota_events_total']}",
        '# HELP constrail_audit_records_total Total audit records persisted',
        '# TYPE constrail_audit_records_total gauge',
        f"constrail_audit_records_total {snapshot['audit_records_total']}",
        '# HELP constrail_sandbox_executions_total Total sandbox executions persisted',
        '# TYPE constrail_sandbox_executions_total gauge',
        f"constrail_sandbox_executions_total {snapshot['sandbox_executions_total']}",
        '# HELP constrail_sandbox_production_ready Whether sandbox posture is production ready',
        '# TYPE constrail_sandbox_production_ready gauge',
        f"constrail_sandbox_production_ready {1 if snapshot['sandbox_health']['production_ready'] else 0}",
    ]
    return '\n'.join(lines) + '\n'
