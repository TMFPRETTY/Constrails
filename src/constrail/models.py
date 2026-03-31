"""
Data models for Constrail.
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AgentIdentity(BaseModel):
    """Identity of the agent making a request."""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    session_id: Optional[str] = Field(None, description="Session within the agent")
    capability_hash: Optional[str] = Field(
        None, description="Hash of the capability manifest"
    )
    trust_level: float = Field(
        0.5, ge=0.0, le=1.0, description="Trust score (0=untrusted, 1=fully trusted)"
    )


class ToolCall(BaseModel):
    """A request to execute a tool."""
    tool: str = Field(..., description="Name of the tool (e.g., 'read_file')")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool-specific parameters"
    )
    call_id: UUID = Field(default_factory=uuid4, description="Unique ID for this call")


class ActionRequest(BaseModel):
    """Incoming request from an agent."""
    agent: AgentIdentity
    call: ToolCall
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g., conversation history, task goal)",
    )
    request_id: UUID = Field(default_factory=uuid4, description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"
    SANDBOX = "sandbox"
    QUARANTINE = "quarantine"


class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


class ToolResult(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: ToolResultStatus = ToolResultStatus.SUCCESS


class RiskAssessment(BaseModel):
    """Output of the risk engine."""
    score: float = Field(0.0, ge=0.0, le=1.0)
    level: RiskLevel = RiskLevel.LOW
    factors: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class PolicyEvaluation(BaseModel):
    """Output of the policy engine."""
    decision: Decision
    rule_ids: List[str] = Field(default_factory=list)
    message: Optional[str] = None


class EnrichedAction(BaseModel):
    """Action request enriched with security context."""
    request: ActionRequest
    risk: RiskAssessment
    policy: PolicyEvaluation
    capability_check_passed: bool = False
    final_decision: Optional[Decision] = None
    sandbox_id: Optional[str] = None
    approval_id: Optional[UUID] = None


class ActionResponse(BaseModel):
    """Response returned to the agent."""
    request_id: UUID
    decision: Decision
    result: Optional[Dict[str, Any]] = Field(
        None, description="Tool execution result (if allowed)"
    )
    error: Optional[str] = Field(None, description="Error message (if denied/failed)")
    approval_id: Optional[UUID] = Field(
        None, description="Approval request ID (if decision=APPROVAL_REQUIRED)"
    )
    approval_url: Optional[str] = Field(
        None, description="URL for human approval (if decision=APPROVAL_REQUIRED)"
    )
    sandbox_id: Optional[str] = Field(
        None, description="ID of the sandbox where execution occurred"
    )


class AuditRecord(BaseModel):
    """Immutable record for audit logging."""
    audit_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    agent_id: str
    tool: str
    parameters: Dict[str, Any]
    risk_score: float
    risk_level: RiskLevel
    policy_decision: Decision
    final_decision: Decision
    approver_id: Optional[str] = None
    sandbox_id: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None

    model_config = ConfigDict(frozen=True)


class CapabilityManifest(BaseModel):
    """Defines what an agent is allowed to do."""
    agent_id: str
    allowed_tools: List[Dict[str, Any]] = Field(
        ..., description="List of tool allowances with constraints"
    )
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None