"""
Constrail Kernel - Core safety kernel for agent action governance.
Implements the full request lifecycle.
"""

import logging
import uuid
import time
from typing import Optional
from datetime import datetime

from .models import ActionRequest, ActionResponse, ToolCall, ToolResult, Decision, RiskLevel
from .risk.risk_engine import get_risk_engine
from .policy.policy_engine import get_policy_engine
from .capability.manager import get_capability_manager
from .tool_broker.broker import ToolBroker, ExecutionContext
from .database import AuditRecordModel, SessionLocal, Decision as DBDecision, RiskLevel as DBRiskLevel
from .config import settings

logger = logging.getLogger(__name__)


class ConstrailKernel:
    """Main kernel for agent safety enforcement."""
    
    def __init__(self):
        self.risk_engine = get_risk_engine()
        self.policy_engine = get_policy_engine()
        self.capability_manager = get_capability_manager()
        self.tool_broker = None  # Lazy initialization
    
    async def process(self, request: ActionRequest) -> ActionResponse:
        """
        Process an agent action request through the full safety pipeline.
        
        Steps:
        1. Generate request ID
        2. Validate capability (tool allowance)
        3. Assess risk
        4. Evaluate policy
        5. Make final decision (incorporating approvals if needed)
        6. Execute (or deny/sandbox/quarantine)
        7. Log audit record
        8. Return response
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Processing request {request_id} from agent {request.agent.agent_id} for tool {request.call.tool}")
        
        # 1. Capability validation
        if not self.capability_manager.is_tool_allowed(request.agent, request.call.tool, request.call.parameters):
            logger.warning(f"Agent {request.agent.agent_id} attempted disallowed tool {request.call.tool}")
            return self._create_denied_response(
                request, request_id, "Tool not allowed in capability manifest"
            )
        
        # 2. Risk assessment
        risk_assessment = self.risk_engine.assess(request)
        logger.debug(f"Risk assessment: score={risk_assessment.score}, level={risk_assessment.level}")
        
        # 3. Policy evaluation
        policy_evaluation = await self.policy_engine.evaluate(request, risk_assessment)
        logger.debug(f"Policy decision: {policy_evaluation.decision}")
        
        # 4. Determine final decision (may require approval)
        final_decision = self._determine_final_decision(policy_evaluation.decision, risk_assessment.level)
        
        # 5. Execute based on decision
        execution_result = None
        error = None
        sandbox_id = None
        
        if final_decision == Decision.DENY:
            logger.info(f"Request {request_id} denied by policy")
        elif final_decision == Decision.QUARANTINE:
            logger.warning(f"Request {request_id} triggered quarantine for agent {request.agent.agent_id}")
            # TODO: Implement quarantine procedures
        elif final_decision == Decision.APPROVAL_REQUIRED:
            logger.info(f"Request {request_id} requires approval")
            # For MVP, treat as denied unless auto-approval configured
            if not settings.auto_approve_medium_risk:
                return self._create_approval_required_response(request, request_id, policy_evaluation)
            else:
                final_decision = Decision.ALLOW
                logger.info(f"Auto-approved request {request_id}")
        else:  # ALLOW or SANDBOX
            execution_result = await self._execute_tool(request, final_decision, request_id)
            if not execution_result.success:
                error = execution_result.error
        
        # 6. Create audit record
        duration_ms = int((time.time() - start_time) * 1000)
        await self._log_audit(
            request, request_id, risk_assessment, policy_evaluation,
            final_decision, execution_result, error, sandbox_id, duration_ms
        )
        
        # 7. Return response
        return ActionResponse(
            request_id=request_id,
            decision=final_decision,
            risk_assessment=risk_assessment,
            policy_evaluation=policy_evaluation,
            result=execution_result,
            error=error,
            sandbox_id=sandbox_id,
        )
    
    def _determine_final_decision(self, policy_decision: Decision, risk_level: RiskLevel) -> Decision:
        """Determine final decision considering risk level and configuration."""
        # For MVP, simple mapping
        if policy_decision == Decision.ALLOW and risk_level == RiskLevel.CRITICAL:
            # Override ALLOW to APPROVAL_REQUIRED for critical risk
            return Decision.APPROVAL_REQUIRED
        
        if policy_decision == Decision.SANDBOX and not settings.sandbox_enabled:
            # Fallback to APPROVAL_REQUIRED if sandbox disabled
            return Decision.APPROVAL_REQUIRED
        
        return policy_decision
    
    async def _execute_tool(self, request: ActionRequest, decision: Decision, request_id: str) -> Optional[ToolResult]:
        """Execute tool through broker."""
        if self.tool_broker is None:
            from .tool_broker.broker import get_tool_broker
            self.tool_broker = get_tool_broker()
        
        context = ExecutionContext(
            agent=request.agent,
            decision=decision,
            risk_level=request.risk_level if hasattr(request, 'risk_level') else "unknown",
            request_id=request_id,
            sandbox_id=None,  # TODO: generate sandbox ID if sandbox execution
        )
        
        try:
            return await self.tool_broker.execute(request.call, context)
        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                error=f"Execution failed: {e}",
                data=None,
                metadata={"error": str(e)},
            )
    
    async def _log_audit(self, request: ActionRequest, request_id: str, risk_assessment,
                        policy_evaluation, final_decision: Decision, execution_result,
                        error: Optional[str], sandbox_id: Optional[str], duration_ms: int):
        """Log audit record to database."""
        audit_record = AuditRecordModel(
            request_id=uuid.UUID(request_id),
            agent_id=request.agent.agent_id,
            tool=request.call.tool,
            parameters=request.call.parameters,
            risk_score=risk_assessment.score,
            risk_level=DBRiskLevel(risk_assessment.level.value),
            policy_decision=DBDecision(policy_evaluation.decision.value),
            final_decision=DBDecision(final_decision.value),
            approver_id=None,  # TODO: approval system
            sandbox_id=sandbox_id,
            execution_result=execution_result.model_dump() if execution_result else None,
            error=error,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=duration_ms,
        )
        
        try:
            db = SessionLocal()
            db.add(audit_record)
            db.commit()
            db.close()
            logger.debug(f"Audit record saved for request {request_id}")
        except Exception as e:
            logger.error(f"Failed to save audit record: {e}")
    
    def _create_denied_response(self, request: ActionRequest, request_id: str, reason: str) -> ActionResponse:
        """Create a denied response."""
        # Create minimal risk assessment for denial
        from .models import RiskAssessment, RiskLevel, PolicyEvaluation
        
        risk = RiskAssessment(
            score=1.0,
            level=RiskLevel.CRITICAL,
            factors=["capability_denied"],
            explanation=reason,
        )
        
        policy = PolicyEvaluation(
            decision=Decision.DENY,
            rule_ids=["capability_check"],
            message=reason,
        )
        
        return ActionResponse(
            request_id=request_id,
            decision=Decision.DENY,
            risk_assessment=risk,
            policy_evaluation=policy,
            result=None,
            error=reason,
            sandbox_id=None,
        )
    
    def _create_approval_required_response(self, request: ActionRequest, request_id: str,
                                          policy_evaluation) -> ActionResponse:
        """Create an approval required response."""
        # For MVP, just return the response
        # TODO: Create approval request in database
        from .risk.risk_engine import get_risk_engine
        
        risk = get_risk_engine().assess(request)
        
        return ActionResponse(
            request_id=request_id,
            decision=Decision.APPROVAL_REQUIRED,
            risk_assessment=risk,
            policy_evaluation=policy_evaluation,
            result=None,
            error="Approval required",
            sandbox_id=None,
        )


# Default kernel instance
_default_kernel: Optional[ConstrailKernel] = None


async def get_kernel() -> ConstrailKernel:
    """Get or create the default kernel."""
    global _default_kernel
    if _default_kernel is None:
        _default_kernel = ConstrailKernel()
    return _default_kernel