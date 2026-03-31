"""
Policy engine for Constrail.
Integrates with Open Policy Agent (OPA) for policy evaluation.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

from ..models import ActionRequest, RiskAssessment, PolicyEvaluation, Decision
from ..config import settings

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluates policies against action requests."""

    def __init__(self, opa_url: str = "http://localhost:8181", policy_package: str = "constrail"):
        self.opa_url = opa_url.rstrip("/")
        self.policy_package = policy_package
        self.client = httpx.AsyncClient(timeout=5.0)

    async def evaluate(self, request: ActionRequest, risk: RiskAssessment) -> PolicyEvaluation:
        input_data = {
            "request": request.model_dump(mode="json"),
            "risk": risk.model_dump(mode="json"),
        }

        if self._opa_enabled():
            try:
                return await self._evaluate_opa(input_data)
            except Exception as e:
                mode = settings.policy_availability_mode
                logger.warning("OPA evaluation failed: %s, mode=%s", e, mode)
                if mode == 'strict':
                    return PolicyEvaluation(
                        decision=Decision.DENY,
                        rule_ids=['strict_policy_unavailable'],
                        message='OPA unavailable in strict mode',
                    )
                if mode == 'degraded' and request.call.tool in {'exec', 'delete_file', 'http_request'}:
                    return PolicyEvaluation(
                        decision=Decision.SANDBOX,
                        rule_ids=['degraded_policy_unavailable_high_risk'],
                        message='OPA unavailable, high-risk action forced into sandbox/degraded mode',
                    )

        return self._evaluate_simple(request, risk)

    def _opa_enabled(self) -> bool:
        return bool(self.opa_url)

    async def _evaluate_opa(self, input_data: Dict[str, Any]) -> PolicyEvaluation:
        url = f"{self.opa_url}/v1/data/{self.policy_package}/allow"
        response = await self.client.post(url, json={"input": input_data})
        response.raise_for_status()
        result = response.json()

        result_data = result.get("result", {})
        decision_str = result_data.get("decision", "deny")
        message = result_data.get("message")
        rule_ids = result_data.get("rule_ids", [])

        decision_map = {
            "allow": Decision.ALLOW,
            "deny": Decision.DENY,
            "approval_required": Decision.APPROVAL_REQUIRED,
            "sandbox": Decision.SANDBOX,
            "quarantine": Decision.QUARANTINE,
        }
        decision = decision_map.get(str(decision_str).lower(), Decision.DENY)

        return PolicyEvaluation(
            decision=decision,
            rule_ids=rule_ids,
            message=message,
        )

    def _evaluate_simple(self, request: ActionRequest, risk: RiskAssessment) -> PolicyEvaluation:
        tool = request.call.tool
        risk_level = risk.level.value
        tenant_id = request.agent.tenant_id
        params = request.call.parameters or {}

        if not tenant_id:
            return PolicyEvaluation(
                decision=Decision.DENY,
                rule_ids=["simple_missing_tenant_scope"],
                message="Tenant scope required",
            )

        if risk_level == "critical":
            return PolicyEvaluation(
                decision=Decision.DENY,
                rule_ids=["simple_fallback_critical_risk"],
                message="Critical risk level",
            )

        if tool == "delete_file":
            path = str(params.get("path", ""))
            if path.startswith("/") and not path.startswith("/tmp/"):
                return PolicyEvaluation(
                    decision=Decision.DENY,
                    rule_ids=["simple_deny_destructive_target"],
                    message="Deleting non-temporary absolute paths is denied",
                )
            return PolicyEvaluation(
                decision=Decision.APPROVAL_REQUIRED,
                rule_ids=["simple_delete_requires_approval"],
                message="Delete operations require approval",
            )

        if tool in {"exec", "shell", "network", "write_file"}:
            return PolicyEvaluation(
                decision=Decision.APPROVAL_REQUIRED,
                rule_ids=["simple_fallback_high_risk_tool"],
                message=f"Tool '{tool}' requires approval",
            )

        if tool == "http_request":
            url = str(params.get("url", ""))
            if url.startswith("http://"):
                return PolicyEvaluation(
                    decision=Decision.SANDBOX,
                    rule_ids=["simple_http_requires_sandbox"],
                    message="Plain HTTP requests require sandboxing",
                )
            if url.startswith("https://"):
                return PolicyEvaluation(
                    decision=Decision.ALLOW,
                    rule_ids=["simple_allow_https_request"],
                    message="HTTPS request allowed",
                )
            return PolicyEvaluation(
                decision=Decision.APPROVAL_REQUIRED,
                rule_ids=["simple_http_unknown_scheme"],
                message="Unrecognized HTTP target requires approval",
            )

        if risk_level == "high":
            return PolicyEvaluation(
                decision=Decision.SANDBOX,
                rule_ids=["simple_fallback_high_risk"],
                message="High risk level, execution in sandbox",
            )

        return PolicyEvaluation(
            decision=Decision.ALLOW,
            rule_ids=["simple_fallback_allow"],
            message="Allowed by simple policy",
        )

    async def close(self):
        await self.client.aclose()

    def explain_local_policy(self) -> dict[str, Any]:
        policy_dir = Path("./policies")
        rego_files = [str(p) for p in policy_dir.rglob("*.rego")] if policy_dir.exists() else []
        return {
            "opa_url": self.opa_url,
            "policy_package": self.policy_package,
            "policy_availability_mode": settings.policy_availability_mode,
            "rego_files": rego_files,
            "fallback_mode": True,
            "policy_features": [
                "tenant_scope_required",
                "critical_risk_denial",
                "approval_for_high_risk_tools",
                "sandbox_for_high_risk_execution",
                "https_allowance",
                "destructive_path_guardrails",
            ],
        }


_default_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _default_policy_engine
    if _default_policy_engine is None:
        _default_policy_engine = PolicyEngine(
            opa_url=settings.opa_url,
            policy_package=settings.opa_policy_package,
        )
    return _default_policy_engine
