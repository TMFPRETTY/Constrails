#!/usr/bin/env python3
"""Test the Constrail kernel_v2 implementation."""
import asyncio
import sys
sys.path.insert(0, 'src')

from constrail.kernel_v2 import Kernel
from constrail.models import ToolCall, AgentIdentity

async def test_kernel():
    print("Testing Constrail Kernel...")
    
    # Create kernel instance
    kernel = Kernel()
    
    # Create a simple agent identity
    agent = AgentIdentity(
        agent_id="test-agent-1",
        agent_name="Test Agent",
        runtime="openclaw",
        capabilities=["filesystem.read", "http.get"]
    )
    
    # Create a tool call
    tool_call = ToolCall(
        tool_name="filesystem.read",
        parameters={"path": "README.md"},
        agent_identity=agent
    )
    
    print(f"Tool call: {tool_call.tool_name} with params: {tool_call.parameters}")
    
    # Process the tool call
    result = await kernel.process(tool_call)
    
    print(f"Result: {result}")
    print(f"Status: {result.status}")
    print(f"Output: {result.output}")
    print(f"Metadata: {result.metadata}")
    
    # Test a blocked tool call (maybe exec)
    tool_call2 = ToolCall(
        tool_name="filesystem.write",
        parameters={"path": "/etc/passwd", "content": "malicious"},
        agent_identity=agent
    )
    
    print(f"\nBlocked tool call: {tool_call2.tool_name}")
    result2 = await kernel.process(tool_call2)
    print(f"Result: {result2}")
    
    # Test HTTP adapter
    tool_call3 = ToolCall(
        tool_name="http.get",
        parameters={"url": "https://httpbin.org/get"},
        agent_identity=agent
    )
    
    print(f"\nHTTP tool call: {tool_call3.tool_name}")
    result3 = await kernel.process(tool_call3)
    print(f"Result status: {result3.status}")
    if result3.output:
        print(f"Response keys: {list(result3.output.keys())}")

if __name__ == "__main__":
    asyncio.run(test_kernel())