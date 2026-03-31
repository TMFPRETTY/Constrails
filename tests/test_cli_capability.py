from click.testing import CliRunner

from constrail.capability_store import get_capability_store
from constrail.cli import cli
from constrail.database import init_db


runner = CliRunner()


def setup_module(module):
    init_db()
    store = get_capability_store()
    store.create_manifest(
        agent_id='cli-agent',
        tenant_id='tenant-cli',
        namespace='ns-cli',
        version=1,
        allowed_tools=[{'tool': 'read_file'}],
        active=True,
    )



def test_capability_list_command():
    result = runner.invoke(cli, ['capability-list', '--agent', 'cli-agent'])
    assert result.exit_code == 0
    assert 'Capability Manifests' in result.output
    assert 'cli-agent' in result.output



def test_capability_list_json_command():
    result = runner.invoke(cli, ['capability-list', '--agent', 'cli-agent', '--json'])
    assert result.exit_code == 0
    assert '"agent_id": "cli-agent"' in result.output
