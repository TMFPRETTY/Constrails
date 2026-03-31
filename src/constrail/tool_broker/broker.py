"""
Tool broker for Constrail.
Routes tool calls to appropriate adapters and handles execution modes.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Type

from ..adapters.base import ToolAdapter
from ..models import AgentIdentity, Decision, ToolCall, ToolResult
from ..sandbox import SandboxEnforcementError, enforce_sandbox_posture, get_sandbox_executor

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for tool execution."""

    agent: AgentIdentity
    decision: Decision
    risk_level: str
    request_id: str
    sandbox_id: Optional[str] = None


class ToolBroker:
    """Brokers tool execution to adapters."""

    def __init__(self):
        self.adapters: Dict[str, ToolAdapter] = {}
        self._sandbox_executor = get_sandbox_executor()

    def register_adapter(self, tool_name: str, adapter: ToolAdapter):
        self.adapters[tool_name] = adapter
        logger.info("Registered adapter for tool '%s'", tool_name)

    def register_adapter_class(self, tool_name: str, adapter_class: Type[ToolAdapter], **kwargs):
        adapter = adapter_class(**kwargs)
        self.register_adapter(tool_name, adapter)

    async def execute(self, call: ToolCall, context: ExecutionContext) -> ToolResult:
        if context.decision == Decision.DENY:
            return ToolResult(success=False, error="Tool execution denied by policy", data=None, metadata={"decision": "deny"})

        if context.decision == Decision.QUARANTINE:
            logger.warning("Agent %s quarantined due to tool %s", context.agent.agent_id, call.tool)
            return ToolResult(success=False, error="Agent quarantined", data=None, metadata={"decision": "quarantine"})

        if context.decision == Decision.APPROVAL_REQUIRED:
            return ToolResult(success=False, error="Approval required but not granted", data=None, metadata={"decision": "approval_required"})

        if context.decision == Decision.SANDBOX:
            return await self._execute_sandbox(call, context)

        return await self._execute_direct(call, context)

    async def _execute_direct(self, call: ToolCall, context: ExecutionContext) -> ToolResult:
        adapter = self.adapters.get(call.tool)
        if adapter is None:
            logger.error("No adapter registered for tool '%s'", call.tool)
            return ToolResult(success=False, error=f"Tool '{call.tool}' not supported", data=None, metadata={"decision": "no_adapter"})

        try:
            logger.info("Executing tool '%s' directly for agent %s", call.tool, context.agent.agent_id)
            result = await adapter.execute(call)
            sandbox_id = result.metadata.get('sandbox_id') if result.metadata else None
            result.metadata = {
                **result.metadata,
                "execution_mode": "direct",
                "request_id": context.request_id,
                "agent_id": context.agent.agent_id,
                "sandbox_id": sandbox_id,
            }
            return result
        except Exception as e:
            logger.exception("Tool execution failed: %s", e)
            return ToolResult(success=False, error=f"Tool execution failed: {e}", data=None, metadata={"decision": "execution_error"})

    async def _execute_sandbox(self, call: ToolCall, context: ExecutionContext) -> ToolResult:
        try:
            enforce_sandbox_posture(operation=f"sandboxed tool '{call.tool}'")
        except SandboxEnforcementError as exc:
            return ToolResult(
                success=False,
                error=str(exc),
                data={"sandbox_strict_mode": True, "sandbox_required": True},
                metadata={
                    "decision": "sandbox_blocked",
                    "request_id": context.request_id,
                    "agent_id": context.agent.agent_id,
                },
            )
        result = await self._execute_direct(call, context)
        result.metadata["execution_mode"] = "sandbox"
        return result

    def get_available_tools(self) -> list[str]:
        return list(self.adapters.keys())


_default_tool_broker: Optional[ToolBroker] = None


def get_tool_broker() -> ToolBroker:
    global _default_tool_broker
    if _default_tool_broker is None:
        from ..adapters.exec import ExecAdapter
        from ..adapters.filesystem import FilesystemAdapter
        from ..adapters.http import HTTPAdapter

        broker = ToolBroker()
        broker.register_adapter_class("read_file", FilesystemAdapter, base_path=".")
        broker.register_adapter_class("write_file", FilesystemAdapter, base_path=".")
        broker.register_adapter_class("delete_file", FilesystemAdapter, base_path=".")
        broker.register_adapter_class("list_directory", FilesystemAdapter, base_path=".")
        broker.register_adapter_class("http_request", HTTPAdapter)
        broker.register_adapter_class("exec", ExecAdapter, sandbox_executor=broker._sandbox_executor)
        _default_tool_broker = broker
    return _default_tool_broker
