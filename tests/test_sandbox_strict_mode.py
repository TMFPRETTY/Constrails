import asyncio

from constrail.config import settings
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, Decision, ToolCall
from constrail.tool_broker.broker import get_tool_broker


class TempSetting:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.original = getattr(settings, name)

    def __enter__(self):
        setattr(settings, self.name, self.value)

    def __exit__(self, exc_type, exc, tb):
        setattr(settings, self.name, self.original)


def run(coro):
    return asyncio.run(coro)


def test_replay_exec_blocked_when_strict_sandbox_posture_is_unready():
    kernel = ConstrailKernel()
    broker = get_tool_broker()
    broker._sandbox_executor = None
    exec_adapter = broker.adapters['exec']
    original_executor = exec_adapter.sandbox_executor
    try:
        with TempSetting('sandbox_strict_mode', True):
            exec_adapter.sandbox_executor = original_executor
            req = ActionRequest(
                agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
                call=ToolCall(tool='exec', parameters={'command': 'echo strict-block'}),
                context={'goal': 'strict sandbox block test'},
            )
            initial = run(kernel.process(req))
            assert initial.decision == Decision.APPROVAL_REQUIRED
            assert initial.approval_id is not None

            kernel.approval_service.decide(
                initial.approval_id,
                approved=True,
                approver_id='tmfpretty',
                comment='strict sandbox test',
            )

            replayed = run(kernel.replay_approved(initial.approval_id))
            assert replayed.result is not None
            assert replayed.result['success'] is False
            assert replayed.result['data']['sandbox_strict_mode'] is True
            assert 'Strict sandbox mode blocked' in replayed.result['error']
    finally:
        exec_adapter.sandbox_executor = original_executor
