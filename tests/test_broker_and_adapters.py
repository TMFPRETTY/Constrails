import asyncio
from pathlib import Path

from constrail.adapters.filesystem import FilesystemAdapter
from constrail.models import AgentIdentity, Decision, ToolCall
from constrail.tool_broker.broker import ExecutionContext, ToolBroker


def run(coro):
    return asyncio.run(coro)


def test_filesystem_adapter_read_and_write(tmp_path):
    adapter = FilesystemAdapter(base_path=str(tmp_path))

    write_call = ToolCall(
        tool='write_file',
        parameters={'operation': 'write', 'path': 'hello.txt', 'content': 'hi there'},
    )
    write_result = run(adapter.execute(write_call))
    assert write_result.success is True

    read_call = ToolCall(
        tool='read_file',
        parameters={'operation': 'read', 'path': 'hello.txt'},
    )
    read_result = run(adapter.execute(read_call))
    assert read_result.success is True
    assert read_result.data['content'] == 'hi there'


def test_broker_dispatches_registered_adapter(tmp_path):
    broker = ToolBroker()
    broker.register_adapter('read_file', FilesystemAdapter(base_path=str(tmp_path)))

    target = Path(tmp_path) / 'note.txt'
    target.write_text('broker test', encoding='utf-8')

    call = ToolCall(tool='read_file', parameters={'operation': 'read', 'path': 'note.txt'})
    context = ExecutionContext(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        decision=Decision.ALLOW,
        risk_level='low',
        request_id='req-123',
    )

    result = run(broker.execute(call, context))

    assert result.success is True
    assert result.data['content'] == 'broker test'
    assert result.metadata['execution_mode'] == 'direct'
    assert result.metadata['agent_id'] == 'dev-agent'
