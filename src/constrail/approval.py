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
                webhook_delivery_status='not_configured' if not settings.approval_webhook_url else 'pending',
                webhook_delivery_attempts=0,
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)
            self._emit_webhook(
                approval.approval_id,
                self._build_event_payload(approval, 'approval.created'),
            )
            return self.get_request(approval.approval_id)
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
                approval.approval_id,
                self._build_event_payload(
                    approval,
                    'approval.approved' if approved else 'approval.denied',
                ),
            )
            return self.get_request(approval.approval_id)
        finally:
            db.close()

    def retry_webhook(self, approval_id: UUID) -> Optional[ApprovalRequestModel]:
        approval = self.get_request(approval_id)
        if approval is None:
            return None
        self._emit_webhook(approval.approval_id, self._build_retry_payload(approval), allow_exhausted=True)
        return self.get_request(approval.approval_id)

    def get_approver_id(self, approval_id: UUID) -> Optional[str]:
        approval = self.get_request(approval_id)
        if approval is None:
            return None
        return approval.approver_id

    def _build_event_payload(self, approval: ApprovalRequestModel, event: str) -> dict:
        payload = {
            'event': event,
            'approval_id': str(approval.approval_id),
            'request_id': str(approval.request_id),
            'agent_id': approval.agent_id,
            'tool': approval.tool,
            'status': self._status_for(approval),
            'webhook_delivery_attempts': approval.webhook_delivery_attempts or 0,
        }
        if event == 'approval.created':
            payload['risk_score'] = approval.risk_score
            payload['risk_level'] = approval.risk_level.value if hasattr(approval.risk_level, 'value') else str(approval.risk_level)
        if approval.approver_id:
            payload['approver_id'] = approval.approver_id
        if approval.review_comment:
            payload['review_comment'] = approval.review_comment
        return payload

    def _build_retry_payload(self, approval: ApprovalRequestModel) -> dict:
        payload = self._build_event_payload(approval, 'approval.retry')
        payload['last_webhook_delivery_status'] = approval.webhook_delivery_status
        payload['last_webhook_last_error'] = approval.webhook_last_error
        return payload

    def _status_for(self, approval: ApprovalRequestModel) -> str:
        if approval.approved is True:
            return 'approved'
        if approval.approved is False:
            return 'denied'
        return 'pending'

    def _record_webhook_delivery(
        self,
        approval_id: UUID,
        *,
        status: str,
        response_code: int | None = None,
        error: str | None = None,
    ):
        db = SessionLocal()
        try:
            approval = (
                db.query(ApprovalRequestModel)
                .filter(ApprovalRequestModel.approval_id == approval_id)
                .first()
            )
            if approval is None:
                return
            approval.webhook_delivery_status = status
            approval.webhook_delivery_attempts = (approval.webhook_delivery_attempts or 0) + 1
            approval.webhook_last_attempt_at = datetime.utcnow()
            approval.webhook_last_response_code = response_code
            approval.webhook_last_error = error
            db.commit()
        finally:
            db.close()

    def _emit_webhook(self, approval_id: UUID, payload: dict, allow_exhausted: bool = False):
        if not settings.approval_webhook_url:
            return
        approval = self.get_request(approval_id)
        if approval is None:
            return
        attempts = approval.webhook_delivery_attempts or 0
        if attempts >= settings.approval_webhook_max_attempts and not allow_exhausted:
            approval.webhook_delivery_status = 'exhausted'
            db = SessionLocal()
            try:
                row = (
                    db.query(ApprovalRequestModel)
                    .filter(ApprovalRequestModel.approval_id == approval_id)
                    .first()
                )
                if row is not None:
                    row.webhook_delivery_status = 'exhausted'
                    row.webhook_last_error = row.webhook_last_error or 'max webhook attempts reached'
                    db.commit()
            finally:
                db.close()
            return
        req = Request(
            settings.approval_webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlopen(req, timeout=5) as response:
                self._record_webhook_delivery(
                    approval_id,
                    status='delivered',
                    response_code=getattr(response, 'status', None),
                    error=None,
                )
        except Exception as exc:
            next_attempt = attempts + 1
            if allow_exhausted:
                status = 'failed'
            else:
                status = 'failed' if next_attempt < settings.approval_webhook_max_attempts else 'exhausted'
            self._record_webhook_delivery(
                approval_id,
                status=status,
                response_code=None,
                error=str(exc),
            )


_default_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    global _default_approval_service
    if _default_approval_service is None:
        _default_approval_service = ApprovalService()
    return _default_approval_service
