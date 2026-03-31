"""
Risk engine for Constrail.
Computes risk scores and levels for action requests.
"""

import logging
from typing import Dict, Any
import json
import os

from ..models import ActionRequest, RiskAssessment, RiskLevel
from ..config import settings
from ..database import AuditRecordModel, SessionLocal

logger = logging.getLogger(__name__)


class RiskEngine:
    """Evaluates risk of an action request."""

    def __init__(self):
        self.tool_risk_profiles = self._load_tool_risk_profiles()

    def _load_tool_risk_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load tool risk profiles from JSON file."""
        default_profiles = {
            "read_file": {"base_risk": 0.1, "category": "filesystem"},
            "write_file": {"base_risk": 0.6, "category": "filesystem"},
            "delete_file": {"base_risk": 0.8, "category": "filesystem"},
            "exec": {"base_risk": 0.9, "category": "execution"},
            "shell": {"base_risk": 1.0, "category": "execution"},
            "network_request": {"base_risk": 0.5, "category": "network"},
            "database_query": {"base_risk": 0.4, "category": "data_access"},
            "send_message": {"base_risk": 0.3, "category": "communication"},
        }

        profiles_path = os.path.join(settings.policy_dir, "tool_risk_profiles.json")
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, "r") as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    default_profiles.update(loaded)
                    logger.info(f"Loaded tool risk profiles from {profiles_path}")
            except Exception as e:
                logger.warning(f"Failed to load tool risk profiles: {e}")

        return default_profiles

    def _recent_agent_tools(self, agent_id: str) -> list[str]:
        db = SessionLocal()
        try:
            rows = (
                db.query(AuditRecordModel.tool)
                .filter(AuditRecordModel.agent_id == agent_id)
                .order_by(AuditRecordModel.start_time.desc())
                .limit(settings.exfiltration_lookback_limit)
                .all()
            )
            return [row[0] for row in rows]
        except Exception as e:
            logger.warning(f"Failed to load recent audit history for exfiltration checks: {e}")
            return []
        finally:
            db.close()

    def assess(self, request: ActionRequest) -> RiskAssessment:
        """
        Assess risk of an action request.
        Returns a RiskAssessment with score, level, and factors.
        """
        factors = []
        score = 0.0

        # 1. Base tool risk
        tool = request.call.tool
        tool_profile = self.tool_risk_profiles.get(tool, {"base_risk": 0.5, "category": "unknown"})
        base_risk = tool_profile["base_risk"]
        score += base_risk * 0.4  # 40% weight
        factors.append(f"tool_{tool}_base_risk:{base_risk}")

        # 2. Agent trust level (inverse)
        agent_trust = request.agent.trust_level
        trust_factor = 1.0 - agent_trust  # lower trust -> higher risk
        score += trust_factor * 0.3  # 30% weight
        factors.append(f"agent_trust:{agent_trust}")

        # 3. Parameter sensitivity (simple heuristics)
        param_risk = self._assess_parameters(request.call.parameters, tool_profile.get("category"))
        score += param_risk * 0.2  # 20% weight
        factors.append(f"parameter_risk:{param_risk:.2f}")

        # 4. Contextual risk (if context contains sensitive keywords)
        context_risk = self._assess_context(request.context)
        score += context_risk * 0.1  # 10% weight
        if context_risk > 0:
            factors.append("context_sensitive")

        # 5. Cross-request exfiltration chaining heuristics
        chain_risk = self._assess_request_chain(request)
        score += chain_risk
        if chain_risk > 0:
            factors.append(f"chain_risk:{chain_risk:.2f}")

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine risk level
        level = RiskLevel.LOW
        if score >= settings.risk_threshold_critical:
            level = RiskLevel.CRITICAL
        elif score >= settings.risk_threshold_high:
            level = RiskLevel.HIGH
        elif score >= settings.risk_threshold_medium:
            level = RiskLevel.MEDIUM

        explanation = (
            f"Risk score {score:.2f} derived from tool '{tool}' (base {base_risk}), "
            f"agent trust {agent_trust}, parameter risk {param_risk:.2f}."
        )

        return RiskAssessment(
            score=score,
            level=level,
            factors=factors,
            explanation=explanation,
        )

    def _assess_parameters(self, parameters: Dict[str, Any], category: str) -> float:
        """Assess risk based on tool parameters."""
        risk = 0.0

        if category == "filesystem":
            # Path traversal risk
            for value in parameters.values():
                if isinstance(value, str) and (".." in value or "/" in value or "\\" in value):
                    risk += 0.3
                    break

        elif category == "execution":
            # Command injection risk
            for value in parameters.values():
                if isinstance(value, str) and ("|" in value or "&" in value or ";" in value):
                    risk += 0.5
                    break

        elif category == "network":
            # External network calls
            for value in parameters.values():
                if isinstance(value, str) and ("http://" in value or "https://" in value):
                    risk += 0.2
                    break

        # Additional parameter checks
        # e.g., sensitive data in parameters
        sensitive_keywords = ["password", "secret", "key", "token"]
        for key, value in parameters.items():
            if any(kw in key.lower() for kw in sensitive_keywords):
                risk += 0.4
                break

        return min(risk, 1.0)

    def _assess_request_chain(self, request: ActionRequest) -> float:
        if not settings.exfiltration_read_then_network_enabled:
            return 0.0
        if request.call.tool != 'http_request':
            return 0.0
        recent_tools = self._recent_agent_tools(request.agent.agent_id)
        if any(tool in {'read_file', 'list_directory'} for tool in recent_tools):
            return 0.35
        return 0.0

    def _assess_context(self, context: Dict[str, Any]) -> float:
        """Assess risk based on context."""
        # Simple keyword detection in context JSON string
        context_str = str(context).lower()
        sensitive_phrases = ["delete", "destroy", "exfiltrate", "steal", "hack", "bypass"]
        for phrase in sensitive_phrases:
            if phrase in context_str:
                return 0.5
        return 0.0


# Default risk engine instance
_default_risk_engine: RiskEngine = None


def get_risk_engine() -> RiskEngine:
    """Get or create the default risk engine."""
    global _default_risk_engine
    if _default_risk_engine is None:
        _default_risk_engine = RiskEngine()
    return _default_risk_engine