#!/usr/bin/env python3
"""Integration test for KernelV2 with ToolBroker."""

import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock
sys.path.insert(0, '.')

from src.constrail.kernel_v2 import KernelV2
from src.constrail.tool_broker.broker import ToolBroker
from src.constrail.adapters.base import ToolAdapter
from src.constrail.models import ToolCall, ToolResult, ToolResultStatus, RiskLevel, Decision


class MockAdapter(ToolAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, name="mock"):
        self.name = name
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Return a successful mock result."""
        return ToolResult(
            success=True,
            data={"message": f"Mock execution of {tool_call.tool_name}"},
            status=ToolResultStatus.SUCCESS
        )
    
    def can_handle(self, tool_call: ToolCall) -> bool:
        """Handle all tools for testing."""
        return True


async def test_kernel_integration():
    """Test basic kernel flow with mock adapter."""
    # Create kernel
    kernel = KernelV2()
    
    # Create tool broker with mock adapter
    broker = ToolBroker()
    adapter = MockAdapter()
    broker.register_adapter(adapter)
    
    # Set broker on kernel
    kernel.set_tool_broker(broker)
    
    # Create a simple tool call
    tool_call = ToolCall(
        tool_name="test_tool",
        tool_args={"arg1": "value1"},
        agent_id="test_agent",
        session_id="test_session"
    )
    
    # Process the tool call through kernel
    result = await kernel.process(tool_call)
    
    print(f"Process result: {result}")
    print(f"Risk assessment: {result.risk_assessment}")
    print(f"Policy decision: {result.policy_decision}")
    print(f"Tool result: {result.tool_result}")
    
    # Basic assertions
    assert result.risk_assessment is not None
    assert result.policy_decision is not None
    assert result.tool_result is not None
    assert result.tool_result.success == True
    
    print("Integration test passed!")
    return True


def test_sync():
    """Run async test in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_kernel_integration())
    finally:
        loop.close()


if __name__ == "__main__":
    success = test_sync()
    sys.exit(0 if success else 1)