"""
Approval workflow support for Constrail.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from .database import ApprovalRequestModel, SessionLocal


class ApprovalService:
    """Persistence and state transitions for approval-required actions."""

    def create_request(
        self,
        request_id: UUID,
        agent_id: str,
        tool: str,
        parameters: dict,
        risk_score: float,
        risk_level: str,
        policy_evaluation: dict,
    ) -> ApprovalRequestModel:
        db = SessionLocal()
        try:
            existing = (
                db.query(ApprovalRequestModel)
                .filter(ApprovalRequestModel.request_id == request_id)
                .first()
            )
            if existing is not None:
                return existing

            approval = ApprovalRequestModel(
                request_id=request_id,
                agent_id=agent_id,
                tool=tool,
                parameters=parameters,
                risk_score=risk_score,
                risk_level=risk_level.upper(),
                policy_evaluation=policy_evaluation,
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)
            return approval
        finally:
            db.close()

    def list_requests(self) -> list[ApprovalRequestModel]:
        db = SessionLocal()
        try:
            return (
                db.query(ApprovalRequestModel)
                .order_by(ApprovalRequestModel.created_at.desc())
                .all()
            )
        finally:
            db.close()

    def get_request(self, approval_id: UUID) -> Optional[ApprovalRequestModel]:
        db = SessionLocal()
        try:
            return (
                db.query(ApprovalRequestModel)
                .filter(ApprovalRequestModel.approval_id == approval_id)
                .first()
            )
        finally:
            db.close()

    def decide(
        self,
        approval_id: UUID,
        approved: bool,
        approver_id: str,
        comment: Optional[str] = None,
    ) -> Optional[ApprovalRequestModel]:
        db = SessionLocal()
        try:
            approval = (
                db.query(ApprovalRequestModel)
                .filter(ApprovalRequestModel.approval_id == approval_id)
                .first()
            )
            if approval is None:
                return None

            approval.approved = approved
            approval.approver_id = approver_id
            approval.reviewed_at = datetime.utcnow()
            approval.review_comment = comment
            db.commit()
            db.refresh(approval)
            return approval
        finally:
            db.close()


_default_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    global _default_approval_service
    if _default_approval_service is None:
        _default_approval_service = ApprovalService()
    return _default_approval_service
