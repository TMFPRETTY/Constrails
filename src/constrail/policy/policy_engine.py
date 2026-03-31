"""
Policy engine for Constrail.
Integrates with Open Policy Agent (OPA) for policy evaluation.
"""

import logging
import json
from typing import Dict, Any, Optional
import httpx
from pydantic import BaseModel

from ..models import ActionRequest, RiskAssessment, PolicyEvaluation, Decision

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluates policies against action requests."""
    
    def __init__(self, opa_url: str = "http://localhost:8181", policy_package: str = "constrail"):
        self.opa_url = opa_url
        self.policy_package = policy_package
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def evaluate(self, request: ActionRequest, risk: RiskAssessment) -> PolicyEvaluation:
        """
        Evaluate policy for the given action request and risk assessment.
        Returns a PolicyEvaluation.
        """
        input_data = {
            "request": request.model_dump(mode="json"),
            "risk": risk.model_dump(mode="json"),
        }
        
        # Try OPA first, fallback to simple rules if OPA unavailable
        try:
            return await self._evaluate_opa(input_data)
        except Exception as e:
            logger.warning(f"OPA evaluation failed: {e}, falling back to simple policy")
            return self._evaluate_simple(request, risk)
    
    async def _evaluate_opa(self, input_data: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate using OPA."""
        url = f"{self.opa_url}/v1/data/{self.policy_package}/allow"
        response = await self.client.post(url, json={"input": input_data})
        response.raise_for_status()
        result = response.json()
        
        # OPA returns {"result": {"allow": bool, "decision": str, "message": str, "rule_ids": list}}
        result_data = result.get("result", {})
        allow = result_data.get("allow", False)
        decision_str = result_data.get("decision", "deny")
        message = result_data.get("message")
        rule_ids = result_data.get("rule_ids", [])
        
        # Map to our Decision enum
        decision_map = {
            "allow": Decision.ALLOW,
            "deny": Decision.DENY,
            "approval_required": Decision.APPROVAL_REQUIRED,
            "sandbox": Decision.SANDBOX,
            "quarantine": Decision.QUARANTINE,
        }
        decision = decision_map.get(decision_str.lower(), Decision.DENY)
        
        return PolicyEvaluation(
            decision=decision,
            rule_ids=rule_ids,
            message=message,
        )
    
    def _evaluate_simple(self, request: ActionRequest, risk: RiskAssessment) -> PolicyEvaluation:
        """Simple fallback policy based on tool name and risk level."""
        tool = request.call.tool
        risk_level = risk.level
        
        # Deny high-risk tools
        high_risk_tools = {"exec", "shell", "write_file", "delete_file", "network"}
        if tool in high_risk_tools:
            return PolicyEvaluation(
                decision=Decision.APPROVAL_REQUIRED,
                rule_ids=["simple_fallback_high_risk_tool"],
                message=f"Tool '{tool}' requires approval",
            )
        
        # Deny critical risk
        if risk_level.value == "critical":
            return PolicyEvaluation(
                decision=Decision.DENY,
                rule_ids=["simple_fallback_critical_risk"],
                message="Critical risk level",
            )
        
        # Medium risk -> sandbox
        if risk_level.value == "high":
            return PolicyEvaluation(
                decision=Decision.SANDBOX,
                rule_ids=["simple_fallback_high_risk"],
                message="High risk level, execution in sandbox",
            )
        
        # Low/medium risk -> allow
        return PolicyEvaluation(
            decision=Decision.ALLOW,
            rule_ids=["simple_fallback_allow"],
            message="Allowed by simple policy",
        )
    
    async def close(self):
        await self.client.aclose()


# Default policy engine instance
_default_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the default policy engine."""
    global _default_policy_engine
    if _default_policy_engine is None:
        from ..config import settings
        _default_policy_engine = PolicyEngine(
            opa_url=settings.opa_url,
            policy_package=settings.opa_policy_package,
        )
    return _default_policy_engine