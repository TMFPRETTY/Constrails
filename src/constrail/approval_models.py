"""
Pydantic models for approval API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel


class ApprovalDecisionRequest(BaseModel):
    approver_id: str
    comment: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    approval_id: UUID
    request_id: UUID
    agent_id: str
    tool: str
    parameters: dict[str, Any]
    risk_score: float
    risk_level: str
    policy_evaluation: dict[str, Any]
    created_at: datetime
    approved: Optional[bool] = None
    approver_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    replay_url: Optional[str] = None
    status: str

    @classmethod
    def from_db(cls, row):
        if row.approved is True:
            status = 'approved'
        elif row.approved is False:
            status = 'denied'
        else:
            status = 'pending'
        return cls(
            approval_id=row.approval_id,
            request_id=row.request_id,
            agent_id=row.agent_id,
            tool=row.tool,
            parameters=row.parameters,
            risk_score=row.risk_score,
            risk_level=row.risk_level.value if hasattr(row.risk_level, 'value') else str(row.risk_level),
            policy_evaluation=row.policy_evaluation,
            created_at=row.created_at,
            approved=row.approved,
            approver_id=row.approver_id,
            reviewed_at=row.reviewed_at,
            review_comment=row.review_comment,
            replay_url=f"/v1/approval/{row.approval_id}/replay" if row.approved is True else None,
            status=status,
        )
