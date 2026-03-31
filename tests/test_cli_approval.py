import asyncio
from click.testing import CliRunner

from constrail.cli import cli
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, ToolCall


runner = CliRunner()


def run(coro):
    return asyncio.run(coro)



def test_approval_management_commands():
    kernel = ConstrailKernel()
    req = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo cli-approval'}),
        context={'goal': 'approval cli test'},
    )
    response = run(kernel.process(req))
    approval_id = str(response.approval_id)

    list_result = runner.invoke(cli, ['approval-list', '--limit', '5', '--approved', 'pending'])
    assert list_result.exit_code == 0
    assert 'Approval Requests' in list_result.output

    show_result = runner.invoke(cli, ['approval-show', approval_id, '--json'])
    assert show_result.exit_code == 0
    assert approval_id in show_result.output
    assert '"webhook_delivery_status"' in show_result.output

    approve_result = runner.invoke(
        cli,
        ['approval-approve', approval_id, '--approver', 'tmfpretty', '--comment', 'cli approve'],
    )
    assert approve_result.exit_code == 0
    assert 'Approved' in approve_result.output

    replay_result = runner.invoke(cli, ['approval-replay', approval_id, '--json'])
    assert replay_result.exit_code == 0
    assert '"decision": "allow"' in replay_result.output

    deny_result = runner.invoke(
        cli,
        ['approval-deny', approval_id, '--approver', 'tmfpretty', '--comment', 'cli deny'],
    )
    assert deny_result.exit_code == 0
    assert 'Denied' in deny_result.output
