from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .config import settings
from .database import QuotaEventModel, SessionLocal


class RateLimitService:
    def record_and_check(
        self,
        *,
        agent_id: str,
        tenant_id: Optional[str],
        tool: str,
        event_type: str = 'action',
    ) -> dict:
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=settings.rate_limit_window_seconds)
        db = SessionLocal()
        try:
            row = QuotaEventModel(
                agent_id=agent_id,
                tenant_id=tenant_id,
                tool=tool,
                event_type=event_type,
                created_at=now,
            )
            db.add(row)
            db.commit()

            scoped_count = (
                db.query(QuotaEventModel)
                .filter(QuotaEventModel.agent_id == agent_id)
                .filter(QuotaEventModel.created_at >= window_start)
                .count()
            )
            tool_count = (
                db.query(QuotaEventModel)
                .filter(QuotaEventModel.agent_id == agent_id)
                .filter(QuotaEventModel.tool == tool)
                .filter(QuotaEventModel.created_at >= window_start)
                .count()
            )
            return {
                'agent_id': agent_id,
                'tenant_id': tenant_id,
                'tool': tool,
                'event_type': event_type,
                'window_seconds': settings.rate_limit_window_seconds,
                'agent_count': scoped_count,
                'tool_count': tool_count,
                'blocked': scoped_count > settings.anomaly_burst_threshold,
            }
        finally:
            db.close()

    def summary(self, *, agent_id: Optional[str] = None, tenant_id: Optional[str] = None, limit_seconds: Optional[int] = None) -> dict:
        db = SessionLocal()
        try:
            query = db.query(QuotaEventModel)
            if agent_id:
                query = query.filter(QuotaEventModel.agent_id == agent_id)
            if tenant_id:
                query = query.filter(QuotaEventModel.tenant_id == tenant_id)
            if limit_seconds:
                window_start = datetime.utcnow() - timedelta(seconds=limit_seconds)
                query = query.filter(QuotaEventModel.created_at >= window_start)
            rows = query.all()
            per_tool = {}
            per_tenant = {}
            for row in rows:
                per_tool[row.tool] = per_tool.get(row.tool, 0) + 1
                key = row.tenant_id or 'default'
                per_tenant[key] = per_tenant.get(key, 0) + 1
            return {
                'total_events': len(rows),
                'agents': sorted({row.agent_id for row in rows}),
                'tools': sorted({row.tool for row in rows}),
                'per_tool': per_tool,
                'per_tenant': per_tenant,
            }
        finally:
            db.close()


_default_rate_limit_service: RateLimitService | None = None


def get_rate_limit_service() -> RateLimitService:
    global _default_rate_limit_service
    if _default_rate_limit_service is None:
        _default_rate_limit_service = RateLimitService()
    return _default_rate_limit_service
