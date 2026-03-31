#!/usr/bin/env python3
"""Quick test of the tool broker and adapters."""
import sys
sys.path.insert(0, 'src')

from constrail.tool_broker.broker import ToolBroker
from constrail.adapters.filesystem import FilesystemAdapter
from constrail.models import ToolCall

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
    
    # Test with a file that exists
    tool_call2 = ToolCall(
        tool_name='filesystem.read',
        parameters={'path': 'README.md'}
    )
    
    result2 = broker.execute(tool_call2)
    print(f"Result for README.md: {result2}")

if __name__ == '__main__':
    test_broker()