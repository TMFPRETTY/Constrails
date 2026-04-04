import asyncio
from urllib.error import URLError
from click.testing import CliRunner

from constrail.cli import cli
from constrail.config import settings
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, ToolCall


runner = CliRunner()


def run(coro):
    return asyncio.run(coro)



def test_approval_management_commands(monkeypatch):
    monkeypatch.setattr(settings, 'approval_webhook_url', 'https://example.test/webhook')

    def _boom(req, timeout=5):
        raise URLError('retry me')

    monkeypatch.setattr('constrail.approval.urlopen', _boom)

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

    summary_result = runner.invoke(cli, ['approval-summary', '--json'])
    assert summary_result.exit_code == 0
    assert '"total"' in summary_result.output
    assert '"pending"' in summary_result.output

    outbox_result = runner.invoke(cli, ['approval-outbox-summary', '--json'])
    assert outbox_result.exit_code == 0
    assert '"total"' in outbox_result.output

    drain_result = runner.invoke(cli, ['approval-drain-outbox', '--limit', '5', '--json'])
    assert drain_result.exit_code == 0
    assert '"processed"' in drain_result.output

    worker_result = runner.invoke(cli, ['approval-run-worker', '--cycles', '2', '--sleep-seconds', '0', '--limit', '5', '--backoff-multiplier', '2', '--max-sleep-seconds', '1', '--json'])
    assert worker_result.exit_code == 0
    assert '"cycles": 2' in worker_result.output
    assert '"cycle_results"' in worker_result.output

    serve_result = runner.invoke(
        cli,
        [
            'approval-worker-serve',
            '--sleep-seconds', '0',
            '--limit', '5',
            '--backoff-multiplier', '2',
            '--max-sleep-seconds', '1',
            '--max-cycles', '2',
        ],
    )
    assert serve_result.exit_code == 0
    assert '"cycle": 1' in serve_result.output
    assert '"cycle": 2' in serve_result.output

    list_json_result = runner.invoke(cli, ['approval-list', '--limit', '5', '--json'])
    assert list_json_result.exit_code == 0
    assert '"webhook_delivery_status"' in list_json_result.output

    show_result = runner.invoke(cli, ['approval-show', approval_id, '--json'])
    assert show_result.exit_code == 0
    assert approval_id in show_result.output
    assert '"webhook_delivery_status": "failed"' in show_result.output

    retry_result = runner.invoke(cli, ['approval-retry-webhook', approval_id, '--json'])
    assert retry_result.exit_code == 0
    assert '"webhook_delivery_attempts": 2' in retry_result.output

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

    monkeypatch.setattr(settings, 'approval_webhook_url', None)
