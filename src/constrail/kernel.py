"""
Constrail Kernel – the central entry point for agent actions.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from .models import (
    ActionRequest,
    ActionResponse,
    Decision,
    RiskAssessment,
    PolicyEvaluation,
    EnrichedAction,
)
from .config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Constrail Kernel",
    description="Runtime governance and containment platform for AI agents",
    version="0.1.0",
    root_path=settings.api_root_path,
)


def authenticate_request(request: Request) -> str:
    """Extract and validate API key from request headers.
    MVP: simple header check.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    # TODO: validate key against database
    # For now, assume key is agent_id
    return api_key


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/v1/action", response_model=ActionResponse)
async def execute_action(
    request: ActionRequest, auth_token: str = Depends(authenticate_request)
):
    """Main endpoint for agent tool calls."""
    # Enrich with identity (MVP: use auth token as agent_id)
    request.agent.agent_id = auth_token

    # 1. Context enrichment (placeholder)
    # 2. Risk assessment
    risk = await assess_risk(request)
    # 3. Policy evaluation
    policy = await evaluate_policy(request, risk)
    # 4. Capability check
    capability_ok = await check_capability(request)
    # 5. Decision
    enriched = EnrichedAction(
        request=request,
        risk=risk,
        policy=policy,
        capability_check_passed=capability_ok,
    )
    decision = await make_decision(enriched)
    enriched.final_decision = decision

    # 6. Audit logging
    await audit_log(enriched)

    # 7. Execute if allowed, otherwise return appropriate response
    if decision == Decision.ALLOW:
        result = await execute_tool(request.call)
        return ActionResponse(
            request_id=request.request_id,
            decision=decision,
            result=result,
        )
    elif decision == Decision.DENY:
        return ActionResponse(
            request_id=request.request_id,
            decision=decision,
            error="Action denied by policy",
        )
    elif decision == Decision.APPROVAL_REQUIRED:
        approval_id = await create_approval_request(enriched)
        return ActionResponse(
            request_id=request.request_id,
            decision=decision,
            approval_url=f"/approval/{approval_id}",
        )
    elif decision == Decision.SANDBOX:
        sandbox_id = await execute_in_sandbox(request.call)
        return ActionResponse(
            request_id=request.request_id,
            decision=decision,
            sandbox_id=sandbox_id,
            result=await get_sandbox_result(sandbox_id),
        )
    elif decision == Decision.QUARANTINE:
        # Quarantine the agent session
        await quarantine_agent(request.agent.agent_id)
        return ActionResponse(
            request_id=request.request_id,
            decision=decision,
            error="Agent quarantined due to high risk",
        )
    else:
        raise HTTPException(status_code=500, detail="Unexpected decision")


# Stub implementations for MVP
async def assess_risk(request: ActionRequest) -> RiskAssessment:
    """Placeholder risk engine."""
    # TODO: implement real risk scoring
    from .models import RiskLevel
    return RiskAssessment(
        score=0.2,
        level=RiskLevel.LOW,
        factors=["tool is low risk"],
        explanation="MVP stub",
    )


async def evaluate_policy(
    request: ActionRequest, risk: RiskAssessment
) -> PolicyEvaluation:
    """Placeholder policy engine."""
    # TODO: integrate OPA or builtin policy engine
    from .models import Decision
    return PolicyEvaluation(
        decision=Decision.ALLOW,
        rule_ids=["allow_all_mvp"],
        message="MVP stub",
    )


async def check_capability(request: ActionRequest) -> bool:
    """Placeholder capability check."""
    # TODO: query capability manifest
    return True


async def make_decision(enriched: EnrichedAction) -> Decision:
    """Placeholder decision logic."""
    # TODO: combine risk, policy, capability
    return enriched.policy.decision


async def audit_log(enriched: EnrichedAction):
    """Placeholder audit logging."""
    logger.info(
        "Audit: agent=%s tool=%s decision=%s",
        enriched.request.agent.agent_id,
        enriched.request.call.tool,
        enriched.final_decision,
    )


async def execute_tool(call):
    """Placeholder tool execution."""
    # TODO: invoke tool broker
    return {"status": "success", "output": f"Executed {call.tool} with {call.parameters}"}


async def create_approval_request(enriched: EnrichedAction) -> str:
    """Placeholder approval creation."""
    return "approval-123"


async def execute_in_sandbox(call):
    """Placeholder sandbox execution."""
    return "sandbox-456"


async def get_sandbox_result(sandbox_id: str):
    """Placeholder sandbox result."""
    return {"output": "sandbox result stub"}


async def quarantine_agent(agent_id: str):
    """Placeholder quarantine."""
    logger.warning("Agent %s quarantined", agent_id)