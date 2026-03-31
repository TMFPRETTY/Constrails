"""
Constrail Kernel - Core safety kernel for agent action governance.
Implements the full request lifecycle.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from .approval import get_approval_service
from .capability.manager import get_capability_manager
from .config import settings
from .database import (
    AuditRecordModel,
    Decision as DBDecision,
    RiskLevel as DBRiskLevel,
    SessionLocal,
)
from .models import ActionRequest, ActionResponse, Decision, RiskLevel, ToolResult
from .policy.policy_engine import get_policy_engine
from .risk.risk_engine import get_risk_engine
from .tool_broker.broker import ExecutionContext

logger = logging.getLogger(__name__)


class ConstrailKernel:
    """Main kernel for agent safety enforcement."""

    def __init__(self):
        self.risk_engine = get_risk_engine()
        self.policy_engine = get_policy_engine()
        self.capability_manager = get_capability_manager()
        self.approval_service = get_approval_service()
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

        execution_result = None
        error = None
        sandbox_id = None
        approval_id = None

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
        )

        return ActionResponse(
            request_id=uuid.UUID(request_id),
            decision=final_decision,
            result=execution_result.model_dump() if execution_result else None,
            error=error,
            approval_id=approval_id,
            sandbox_id=sandbox_id,
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
        if tool in {"exec", "http_request", "write_file", "delete_file"}:
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
            from .tool_broker.broker import get_tool_broker

            self.tool_broker = get_tool_broker()

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
        approval = self.approval_service.get_request(approval_id)
        if approval is None:
            raise ValueError("Approval request not found")
        if approval.approved is not True:
            raise ValueError("Approval request is not approved")

        request = ActionRequest(
            agent={"agent_id": approval.agent_id, "trust_level": 0.8},
            call={"tool": approval.tool, "parameters": approval.parameters},
            context={"approval_replay": True, "approval_id": str(approval_id)},
        )

        risk_assessment = self.risk_engine.assess(request)
        policy_evaluation = await self.policy_engine.evaluate(request, risk_assessment)
        execution_result = await self._execute_tool(
            request,
            Decision.ALLOW,
            str(uuid.uuid4()),
            risk_assessment.level.value,
        )
        error = None if execution_result.success else execution_result.error
        return ActionResponse(
            request_id=uuid.uuid4(),
            decision=Decision.ALLOW,
            result=execution_result.model_dump() if execution_result else None,
            error=error,
            approval_id=approval_id,
            sandbox_id=None,
        )

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
    ):
        audit_record = AuditRecordModel(
            request_id=uuid.UUID(request_id),
            agent_id=request.agent.agent_id,
            tool=request.call.tool,
            parameters=request.call.parameters,
            risk_score=risk_assessment.score,
            risk_level=DBRiskLevel(risk_assessment.level.value),
            policy_decision=DBDecision(policy_evaluation.decision.value),
            final_decision=DBDecision(final_decision.value),
            approver_id=None,
            sandbox_id=sandbox_id,
            execution_result=execution_result.model_dump() if execution_result else None,
            error=error,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=duration_ms,
        )

        db = None
        try:
            db = SessionLocal()
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
