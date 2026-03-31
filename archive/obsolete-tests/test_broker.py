#!/usr/bin/env python3
"""Quick test of the tool broker and adapters."""
import sys
sys.path.insert(0, 'src')

from constrail.tool_broker.broker import ToolBroker
from constrail.adapters.filesystem import FilesystemAdapter
from constrail.adapters.http import HTTPAdapter
from constrail.models import ToolCall, ToolResult, ToolResultStatus

def test_broker():
    broker = ToolBroker()
    print(f"Broker adapters: {broker.adapters}")
    
    # Test filesystem adapter
    fs_adapter = FilesystemAdapter()
    broker.register_adapter('filesystem', fs_adapter)
    
    # Create a tool call
    tool_call = ToolCall(
        tool_name='filesystem.read',
        parameters={'path': 'test.txt'}
    )
    
    print(f"Tool call: {tool_call}")
    
    # Execute via broker
    result = broker.execute(tool_call)
    print(f"Result: {result}")
    
    # Test HTTP adapter
    http_adapter = HTTPAdapter()
    broker.register_adapter('http', http_adapter)
    
    http_tool = ToolCall(
        tool_name='http.get',
        parameters={'url': 'https://httpbin.org/get'}
    )
    
    print(f"HTTP tool call: {http_tool}")
    result2 = broker.execute(http_tool)
    print(f"Result: {result2}")

if __name__ == '__main__':
    test_broker()