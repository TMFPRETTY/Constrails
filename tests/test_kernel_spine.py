import asyncio
from pathlib import Path

from constrail.database import init_db
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, ToolCall, Decision


def run(coro):
    return asyncio.run(coro)


def setup_module(module):
    init_db()



def test_capability_manager_reload_is_used_by_kernel():
    kernel = ConstrailKernel()
    kernel.capability_manager.reload()
    assert 'read_file' in kernel.capability_manager.get_allowed_tools('dev-agent')


def test_read_file_happy_path():
    kernel = ConstrailKernel()
    req = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='read_file', parameters={'path': 'README.md'}),
        context={'goal': 'test read file'},
    )

    response = run(kernel.process(req))

    assert response.decision == Decision.ALLOW
    assert response.result is not None
    assert response.result['success'] is True
    assert 'Constrails' in response.result['data']['content']


def test_list_directory_happy_path():
    kernel = ConstrailKernel()
    req = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='list_directory', parameters={'path': '.'}),
        context={'goal': 'test list directory'},
    )

    response = run(kernel.process(req))

    assert response.decision == Decision.ALLOW
    assert response.result is not None
    assert response.result['success'] is True
    names = [item['name'] for item in response.result['data']['items']]
    assert 'README.md' in names


def test_missing_manifest_denies_unknown_agent():
    kernel = ConstrailKernel()
    req = ActionRequest(
        agent=AgentIdentity(agent_id='unknown-agent', trust_level=0.8),
        call=ToolCall(tool='read_file', parameters={'path': 'README.md'}),
        context={'goal': 'unknown agent should fail closed'},
    )

    response = run(kernel.process(req))

    assert response.decision == Decision.DENY
    assert response.error == 'Tool not allowed in capability manifest'


def test_exec_requires_approval_or_higher_control():
    kernel = ConstrailKernel()
    req = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo hello'}),
        context={'goal': 'exec should not be directly allowed by simple fallback'},
    )

    response = run(kernel.process(req))

    assert response.decision == Decision.APPROVAL_REQUIRED
    assert response.error == 'Approval required'
