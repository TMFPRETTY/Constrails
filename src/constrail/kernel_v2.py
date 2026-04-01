"""
Constrail Kernel - Core safety kernel for agent action governance.
Implements the full request lifecycle.
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from .approval import get_approval_service
from .capability.manager import get_capability_manager
from .config import settings
from .database import (
    ApprovalRequestModel,
    AuditRecordModel,
    Decision as DBDecision,
    RiskLevel as DBRiskLevel,
    SessionLocal,
)
from .models import ActionRequest, ActionResponse, Decision, RiskLevel, ToolResult
from .policy.policy_engine import get_policy_engine
from .risk.risk_engine import get_risk_engine
from .sandbox_records import get_sandbox_execution_service
from .rate_limits import get_rate_limit_service
from .tool_broker.broker import ExecutionContext

logger = logging.getLogger(__name__)


class ConstrailKernel:
    """Main kernel for agent safety enforcement."""

    def __init__(self):
        self.risk_engine = get_risk_engine()
        self.policy_engine = get_policy_engine()
        self.capability_manager = get_capability_manager()
        self.approval_service = get_approval_service()
        self.sandbox_execution_service = get_sandbox_execution_service()
        self.rate_limit_service = get_rate_limit_service()
        self.tool_broker = None

    async def process(self, request: ActionRequest) -> ActionResponse:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(
            "Processing request %s from agent %s for tool %s",
            request_id,
            request.agent.agent_id,
            request.call.tool,
        )

        if not self.capability_manager.is_tool_allowed(
            request.agent, request.call.tool, request.call.parameters
        ):
            logger.warning(
                "Agent %s attempted disallowed tool %s",
                request.agent.agent_id,
                request.call.tool,
            )
            return self._create_denied_response(
                request, request_id, "Tool not allowed in capability manifest"
            )

        risk_assessment = self.risk_engine.assess(request)
        policy_evaluation = await self.policy_engine.evaluate(request, risk_assessment)
        final_decision = self._determine_final_decision(
            request, policy_evaluation.decision, risk_assessment.level
        )
        if self._rate_limit_exceeded(request):
            final_decision = Decision.QUARANTINE
            duration_ms = int((time.time() - start_time) * 1000)
            await self._log_audit(
                request,
                request_id,
                risk_assessment,
                policy_evaluation,
                final_decision,
                None,
                self._quota_error_message(request),
                None,
                duration_ms,
                approval_id=None,
                approver_id=None,
                replayed_from_approval_id=None,
            )
            return ActionResponse(
                request_id=uuid.UUID(request_id),
                decision=Decision.QUARANTINE,
                result=None,
                error=self._quota_error_message(request),
                approval_id=None,
                sandbox_id=None,
            )

        execution_result = None
        error = None
        sandbox_id = None
        approval_id = None
        approver_id = None
        replayed_from_approval_id = None

        if final_decision == Decision.DENY:
            logger.info("Request %s denied by policy", request_id)
        elif final_decision == Decision.QUARANTINE:
            logger.warning(
                "Request %s triggered quarantine for agent %s",
                request_id,
                request.agent.agent_id,
            )
        elif final_decision == Decision.APPROVAL_REQUIRED:
            logger.info("Request %s requires approval", request_id)
            if settings.approval_auto_approve_low_risk and risk_assessment.level == RiskLevel.LOW:
                final_decision = Decision.ALLOW
                logger.info("Auto-approved low-risk request %s", request_id)
            else:
                approval = self.approval_service.create_request(
                    request_id=uuid.UUID(request_id),
                    agent_id=request.agent.agent_id,
                    tool=request.call.tool,
                    parameters=request.call.parameters,
                    risk_score=risk_assessment.score,
                    risk_level=risk_assessment.level.value,
                    policy_evaluation=policy_evaluation.model_dump(mode="json"),
                )
                approval_id = approval.approval_id
                duration_ms = int((time.time() - start_time) * 1000)
                await self._log_audit(
                    request,
                    request_id,
                    risk_assessment,
                    policy_evaluation,
                    final_decision,
                    execution_result,
                    "Approval required",
                    sandbox_id,
                    duration_ms,
                    approval_id=approval_id,
                    approver_id=None,
                    replayed_from_approval_id=None,
                )
                return ActionResponse(
                    request_id=uuid.UUID(request_id),
                    decision=Decision.APPROVAL_REQUIRED,
                    result=None,
                    error="Approval required",
                    approval_id=approval_id,
                    approval_url=f"/v1/approval/{approval_id}",
                    sandbox_id=None,
                )

        if final_decision in {Decision.ALLOW, Decision.SANDBOX}:
            execution_result = await self._execute_tool(
                request, final_decision, request_id, risk_assessment.level.value
            )
            if execution_result is not None:
                sandbox_id = execution_result.metadata.get("sandbox_id")
            if not execution_result.success:
                error = execution_result.error

        duration_ms = int((time.time() - start_time) * 1000)
        await self._log_audit(
            request,
            request_id,
            risk_assessment,
            policy_evaluation,
            final_decision,
            execution_result,
            error,
            sandbox_id,
            duration_ms,
            approval_id=approval_id,
            approver_id=approver_id,
            replayed_from_approval_id=replayed_from_approval_id,
        )

        if final_decision == Decision.QUARANTINE and error is None:
            error = 'Rate limit exceeded'

        return ActionResponse(
            request_id=uuid.UUID(request_id),
            decision=final_decision,
            result=execution_result.model_dump() if execution_result else None,
            error=error,
            approval_id=approval_id,
            sandbox_id=sandbox_id,
        )

    def _rate_limit_exceeded(self, request: ActionRequest) -> bool:
        if not settings.anomaly_detection_enabled:
            return False
        result = self.rate_limit_service.record_and_check(
            agent_id=request.agent.agent_id,
            tenant_id=request.agent.tenant_id,
            tool=request.call.tool,
            event_type='action',
        )
        request.context['quota'] = result
        return result['blocked']

    def _quota_error_message(self, request: ActionRequest) -> str:
        quota = request.context.get('quota', {}) if isinstance(request.context, dict) else {}
        if not quota:
            return 'Rate limit exceeded'
        return (
            f"Rate limit exceeded ({quota.get('threshold_scope')} threshold {quota.get('effective_threshold')}, "
            f"agent_count={quota.get('agent_count')}, tool_count={quota.get('tool_count')})"
        )

    def _determine_final_decision(
        self,
        request: ActionRequest,
        policy_decision: Decision,
        risk_level: RiskLevel,
    ) -> Decision:
        if policy_decision == Decision.ALLOW and risk_level == RiskLevel.CRITICAL:
            return Decision.APPROVAL_REQUIRED

        if policy_decision == Decision.SANDBOX and settings.sandbox_type == "none":
            return Decision.APPROVAL_REQUIRED

        tool = request.call.tool
        if tool in {"http_request", "write_file", "delete_file"}:
            return Decision.APPROVAL_REQUIRED
        if tool == "exec":
            return Decision.APPROVAL_REQUIRED

        return policy_decision

    async def _execute_tool(
        self,
        request: ActionRequest,
        decision: Decision,
        request_id: str,
        risk_level: str,
    ) -> Optional[ToolResult]:
        if self.tool_broker is None:
            from .tool_broker.broker import ToolBroker
            from .adapters.exec import ExecAdapter
            from .adapters.filesystem import FilesystemAdapter
            from .adapters.http import HTTPAdapter
            from .sandbox import get_sandbox_executor

            broker = ToolBroker()
            broker.register_adapter_class("read_file", FilesystemAdapter, base_path=".")
            broker.register_adapter_class("write_file", FilesystemAdapter, base_path=".")
            broker.register_adapter_class("delete_file", FilesystemAdapter, base_path=".")
            broker.register_adapter_class("list_directory", FilesystemAdapter, base_path=".")
            broker.register_adapter_class("http_request", HTTPAdapter)
            broker.register_adapter_class("exec", ExecAdapter, sandbox_executor=get_sandbox_executor())
            self.tool_broker = broker

        context = ExecutionContext(
            agent=request.agent,
            decision=decision,
            risk_level=risk_level,
            request_id=request_id,
            sandbox_id=None,
        )

        try:
            normalized_call = self._normalize_call(request)
            return await self.tool_broker.execute(normalized_call, context)
        except Exception as e:
            logger.exception("Tool execution failed: %s", e)
            return ToolResult(
                success=False,
                error=f"Execution failed: {e}",
                data=None,
                metadata={"error": str(e)},
            )

    def _normalize_call(self, request: ActionRequest):
        call = request.call.model_copy(deep=True)
        if call.tool == "read_file":
            call.parameters.setdefault("operation", "read")
        elif call.tool == "write_file":
            call.parameters.setdefault("operation", "write")
        elif call.tool == "delete_file":
            call.parameters.setdefault("operation", "delete")
        elif call.tool == "list_directory":
            call.parameters.setdefault("operation", "list")
        return call

    async def replay_approved(self, approval_id):
        db = SessionLocal()
        try:
            approval = (
                db.query(self.approval_service.get_request(approval_id).__class__)
                .filter_by(approval_id=approval_id)
                .first()
            )
        finally:
            db.close()
        if approval is None:
            raise ValueError("Approval request not found")
        if approval.approved is not True:
            raise ValueError("Approval request is not approved")
        if approval.expires_at is not None and approval.expires_at <= datetime.utcnow():
            raise ValueError("Approval request expired")

        request = ActionRequest(
            agent={"agent_id": approval.agent_id, "trust_level": 0.8},
            call={"tool": approval.tool, "parameters": approval.parameters},
            context={"approval_replay": True, "approval_id": str(approval_id)},
        )

        request_id = str(uuid.uuid4())
        start_time = time.time()
        risk_assessment = self.risk_engine.assess(request)
        policy_evaluation = await self.policy_engine.evaluate(request, risk_assessment)
        forced_decision = Decision.SANDBOX if approval.tool == "exec" else Decision.ALLOW
        execution_result = await self._execute_tool(
            request,
            forced_decision,
            request_id,
            risk_assessment.level.value,
        )
        sandbox_id = execution_result.metadata.get("sandbox_id") if execution_result else None
        error = None if execution_result.success else execution_result.error
        duration_ms = int((time.time() - start_time) * 1000)

        if sandbox_id and execution_result is not None:
            self.sandbox_execution_service.record_execution(
                sandbox_id=sandbox_id,
                request_id=uuid.UUID(request_id),
                approval_id=approval_id,
                agent_id=request.agent.agent_id,
                tool=request.call.tool,
                parameters=request.call.parameters,
                executor=execution_result.metadata.get("sandbox_executor"),
                status="completed" if execution_result.success else "failed",
                result=execution_result.model_dump(mode="json"),
                error=error,
                duration_ms=duration_ms,
            )

        await self._log_audit(
            request,
            request_id,
            risk_assessment,
            policy_evaluation,
            forced_decision,
            execution_result,
            error,
            sandbox_id,
            duration_ms,
            approval_id=approval_id,
            approver_id=approval.approver_id,
            replayed_from_approval_id=approval_id,
        )

        return ActionResponse(
            request_id=uuid.UUID(request_id),
            decision=Decision.ALLOW,
            result=execution_result.model_dump() if execution_result else None,
            error=error,
            approval_id=approval_id,
            sandbox_id=sandbox_id,
        )

    def _compute_audit_chain_hash(
        self,
        *,
        prev_hash: str | None,
        request: ActionRequest,
        request_id: str,
        risk_assessment,
        policy_evaluation,
        final_decision: Decision,
        error: Optional[str],
        approval_id,
        replayed_from_approval_id,
        sandbox_id: Optional[str],
        auth_context: dict,
    ) -> str:
        payload = {
            'prev_hash': prev_hash,
            'request_id': request_id,
            'agent_id': request.agent.agent_id,
            'tool': request.call.tool,
            'parameters': request.call.parameters,
            'risk_score': risk_assessment.score,
            'risk_level': risk_assessment.level.value,
            'policy_decision': policy_evaluation.decision.value,
            'final_decision': final_decision.value,
            'approval_id': str(approval_id) if approval_id else None,
            'replayed_from_approval_id': str(replayed_from_approval_id) if replayed_from_approval_id else None,
            'sandbox_id': sandbox_id,
            'error': error,
            'auth_type': auth_context.get('auth_type'),
            'auth_subject': auth_context.get('auth_subject'),
            'auth_token_id': auth_context.get('auth_token_id'),
            'auth_key_id': auth_context.get('auth_key_id'),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def _normalize_uuidish(self, value):
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError(f"Unsupported UUID value: {value!r} ({type(value).__name__})")

    async def _log_audit(
        self,
        request: ActionRequest,
        request_id: str,
        risk_assessment,
        policy_evaluation,
        final_decision: Decision,
        execution_result,
        error: Optional[str],
        sandbox_id: Optional[str],
        duration_ms: int,
        approval_id=None,
        approver_id: Optional[str] = None,
        replayed_from_approval_id=None,
    ):
        auth_context = request.context.get('auth', {}) if isinstance(request.context, dict) else {}
        try:
            normalized_request_id = self._normalize_uuidish(request_id)
            normalized_approval_id = self._normalize_uuidish(approval_id)
            normalized_replayed_from_approval_id = self._normalize_uuidish(replayed_from_approval_id)
        except Exception:
            logger.exception(
                "Audit UUID normalization failed request_id=%r approval_id=%r replayed_from_approval_id=%r",
                request_id,
                approval_id,
                replayed_from_approval_id,
            )
            raise
        logger.debug(
            "Audit UUIDs request_id=%r(%s) approval_id=%r(%s) replayed_from_approval_id=%r(%s)",
            normalized_request_id,
            type(normalized_request_id).__name__,
            normalized_approval_id,
            type(normalized_approval_id).__name__ if normalized_approval_id is not None else 'None',
            normalized_replayed_from_approval_id,
            type(normalized_replayed_from_approval_id).__name__ if normalized_replayed_from_approval_id is not None else 'None',
        )
        audit_record = AuditRecordModel(
            request_id=normalized_request_id,
            agent_id=request.agent.agent_id,
            tool=request.call.tool,
            parameters=request.call.parameters,
            risk_score=risk_assessment.score,
            risk_level=DBRiskLevel(risk_assessment.level.value),
            policy_decision=DBDecision(policy_evaluation.decision.value),
            final_decision=DBDecision(final_decision.value),
            approver_id=approver_id,
            approval_id=normalized_approval_id,
            replayed_from_approval_id=normalized_replayed_from_approval_id,
            auth_type=auth_context.get('auth_type'),
            auth_subject=auth_context.get('auth_subject'),
            auth_token_id=auth_context.get('auth_token_id'),
            auth_key_id=auth_context.get('auth_key_id'),
            sandbox_id=sandbox_id,
            execution_result=execution_result.model_dump(mode="json") if execution_result else None,
            error=error,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=duration_ms,
        )

        db = None
        try:
            db = SessionLocal()
            previous_hash_rows = db.query(AuditRecordModel.chain_hash).order_by(AuditRecordModel.start_time.asc()).all()
            prev_hash = previous_hash_rows[-1][0] if previous_hash_rows else None
            audit_record.chain_prev_hash = prev_hash
            audit_record.chain_hash = self._compute_audit_chain_hash(
                prev_hash=prev_hash,
                request=request,
                request_id=str(normalized_request_id),
                risk_assessment=risk_assessment,
                policy_evaluation=policy_evaluation,
                final_decision=final_decision,
                error=error,
                approval_id=normalized_approval_id,
                replayed_from_approval_id=normalized_replayed_from_approval_id,
                sandbox_id=sandbox_id,
                auth_context=auth_context,
            )
            db.add(audit_record)
            db.commit()
            logger.debug("Audit record saved for request %s", request_id)
        except Exception as e:
            logger.error("Failed to save audit record: %s", e)
            if db is not None:
                db.rollback()
        finally:
            if db is not None:
                db.close()

    def _create_denied_response(
        self, request: ActionRequest, request_id: str, reason: str
    ) -> ActionResponse:
        return ActionResponse(
            request_id=uuid.UUID(request_id),
            decision=Decision.DENY,
            result=None,
            error=reason,
        )


_default_kernel: Optional[ConstrailKernel] = None


async def get_kernel() -> ConstrailKernel:
    global _default_kernel
    if _default_kernel is None:
        _default_kernel = ConstrailKernel()
    return _default_kernel
