import asyncio

from constrail.adapters.exec import ExecAdapter
from constrail.models import ToolCall, ToolResultStatus
from constrail.sandbox import DevSandboxExecutor


class FakeSandbox:
    async def execute(self, command: str, cwd=None, env=None, timeout=None):
        class Result:
            sandbox_id = 'fake-sandbox-123'
            exit_code = 0
            stdout = f'ran: {command}'
            stderr = ''
            timeout = False
            executor = 'fake'

            def to_dict(self):
                return {
                    'sandbox_id': self.sandbox_id,
                    'exit_code': self.exit_code,
                    'stdout': self.stdout,
                    'stderr': self.stderr,
                    'timeout': self.timeout,
                    'executor': self.executor,
                }

        return Result()


def run(coro):
    return asyncio.run(coro)


def test_exec_adapter_blocks_unsandboxed_execution_by_default():
    adapter = ExecAdapter()
    call = ToolCall(tool='exec', parameters={'command': 'echo hello'})
    result = run(adapter.execute(call))
    assert result.success is False
    assert result.status == ToolResultStatus.BLOCKED
    assert result.data['sandbox_required'] is True


def test_exec_adapter_uses_sandbox_when_available():
    adapter = ExecAdapter(sandbox_executor=FakeSandbox())
    call = ToolCall(tool='exec', parameters={'command': 'echo hello'})
    result = run(adapter.execute(call))
    assert result.success is True
    assert result.status == ToolResultStatus.SUCCESS
    assert result.data['stdout'] == 'ran: echo hello'
    assert result.metadata['sandbox_id'] == 'fake-sandbox-123'


def test_dev_sandbox_executor_runs_simple_command():
    executor = DevSandboxExecutor()
    result = run(executor.execute('echo sandbox-ok'))
    assert result.exit_code == 0
    assert 'sandbox-ok' in result.stdout
    assert result.executor == 'dev'
