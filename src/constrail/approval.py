"""
Approval workflow support for Constrail.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional
from uuid import UUID
from urllib.request import Request, urlopen

from .config import settings
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
            self._emit_webhook(
                {
                    "event": "approval.created",
                    "approval_id": str(approval.approval_id),
                    "request_id": str(approval.request_id),
                    "agent_id": approval.agent_id,
                    "tool": approval.tool,
                    "risk_score": approval.risk_score,
                    "risk_level": approval.risk_level.value if hasattr(approval.risk_level, 'value') else str(approval.risk_level),
                }
            )
            return approval
        finally:
            db.close()

    def list_requests(
        self,
        approved: Optional[bool] = None,
        agent_id: Optional[str] = None,
        tool: Optional[str] = None,
    ) -> list[ApprovalRequestModel]:
        db = SessionLocal()
        try:
            query = db.query(ApprovalRequestModel)
            if approved is not None:
                query = query.filter(ApprovalRequestModel.approved == approved)
            if agent_id is not None:
                query = query.filter(ApprovalRequestModel.agent_id == agent_id)
            if tool is not None:
                query = query.filter(ApprovalRequestModel.tool == tool)
            return query.order_by(ApprovalRequestModel.created_at.desc()).all()
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
            self._emit_webhook(
                {
                    "event": "approval.approved" if approved else "approval.denied",
                    "approval_id": str(approval.approval_id),
                    "request_id": str(approval.request_id),
                    "agent_id": approval.agent_id,
                    "tool": approval.tool,
                    "approver_id": approval.approver_id,
                    "review_comment": approval.review_comment,
                }
            )
            return approval
        finally:
            db.close()

    def get_approver_id(self, approval_id: UUID) -> Optional[str]:
        approval = self.get_request(approval_id)
        if approval is None:
            return None
        return approval.approver_id

    def _emit_webhook(self, payload: dict):
        if not settings.approval_webhook_url:
            return
        req = Request(
            settings.approval_webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlopen(req, timeout=5):
                pass
        except Exception:
            # Best-effort only for now; approval flow should not fail on webhook delivery.
            pass


_default_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    global _default_approval_service
    if _default_approval_service is None:
        _default_approval_service = ApprovalService()
    return _default_approval_service
