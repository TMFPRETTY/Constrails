"""
Tool broker for Constrail.
Routes tool calls to appropriate adapters and handles execution modes.
"""

import logging
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass

from ..adapters.base import ToolAdapter
from ..models import ToolCall, ToolResult, AgentIdentity, Decision
from ..config import settings

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
        self._sandbox_executor = None
        self._http_adapter = None
        self._exec_adapter = None
    
    def register_adapter(self, tool_name: str, adapter: ToolAdapter):
        """Register an adapter for a tool name."""
        self.adapters[tool_name] = adapter
        logger.info(f"Registered adapter for tool '{tool_name}'")
    
    def register_adapter_class(self, tool_name: str, adapter_class: Type[ToolAdapter], **kwargs):
        """Register an adapter class for a tool name."""
        adapter = adapter_class(**kwargs)
        self.register_adapter(tool_name, adapter)
    
    async def execute(self, call: ToolCall, context: ExecutionContext) -> ToolResult:
        """
        Execute a tool call based on decision.
        
        Handles:
        - ALLOW: direct execution via adapter
        - SANDBOX: execution in sandbox environment
        - APPROVAL_REQUIRED: should have been resolved before reaching here
        - DENY: returns error result
        - QUARANTINE: returns error and triggers quarantine procedures
        """
        if context.decision == Decision.DENY:
            return ToolResult(
                success=False,
                error="Tool execution denied by policy",
                data=None,
                metadata={"decision": "deny"},
            )
        
        if context.decision == Decision.QUARANTINE:
            # Trigger quarantine procedures (TODO)
            logger.warning(f"Agent {context.agent.agent_id} quarantined due to tool {call.tool}")
            return ToolResult(
                success=False,
                error="Agent quarantined",
                data=None,
                metadata={"decision": "quarantine"},
            )
        
        if context.decision == Decision.APPROVAL_REQUIRED:
            # Should have been approved before reaching here
            # If not approved, treat as denied
            return ToolResult(
                success=False,
                error="Approval required but not granted",
                data=None,
                metadata={"decision": "approval_required"},
            )
        
        # Determine execution mode
        if context.decision == Decision.SANDBOX:
            return await self._execute_sandbox(call, context)
        else:  # ALLOW
            return await self._execute_direct(call, context)
    
    async def _execute_direct(self, call: ToolCall, context: ExecutionContext) -> ToolResult:
        """Execute tool directly via adapter."""
        adapter = self.adapters.get(call.tool)
        if adapter is None:
            logger.error(f"No adapter registered for tool '{call.tool}'")
            return ToolResult(
                success=False,
                error=f"Tool '{call.tool}' not supported",
                data=None,
                metadata={"decision": "no_adapter"},
            )
        
        try:
            logger.info(f"Executing tool '{call.tool}' directly for agent {context.agent.agent_id}")
            result = await adapter.execute(call.parameters)
            # Enrich metadata
            result.metadata = {
                **result.metadata,
                "execution_mode": "direct",
                "request_id": context.request_id,
                "agent_id": context.agent.agent_id,
            }
            return result
        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {e}",
                data=None,
                metadata={"decision": "execution_error"},
            )
    
    async def _execute_sandbox(self, call: ToolCall, context: ExecutionContext) -> ToolResult:
        """Execute tool in sandbox environment."""
        # TODO: Integrate with sandbox executor
        # For now, just log and execute directly with sandbox metadata
        logger.warning(f"Sandbox execution not yet implemented for tool '{call.tool}', falling back to direct")
        result = await self._execute_direct(call, context)
        result.metadata["sandbox_fallback"] = True
        return result
    
    def get_available_tools(self) -> list:
        """Return list of tools that have adapters registered."""
        return list(self.adapters.keys())


# Default tool broker instance
_default_tool_broker: Optional[ToolBroker] = None


def get_tool_broker() -> ToolBroker:
    """Get or create the default tool broker."""
    global _default_tool_broker
    if _default_tool_broker is None:
        broker = ToolBroker()
        # Register built-in adapters
        from ..adapters.filesystem import FilesystemAdapter
        broker.register_adapter_class("read_file", FilesystemAdapter)
        broker.register_adapter_class("write_file", FilesystemAdapter)
        broker.register_adapter_class("delete_file", FilesystemAdapter)
        # TODO: register HTTP adapter, exec adapter
        _default_tool_broker = broker
    return _default_tool_broker