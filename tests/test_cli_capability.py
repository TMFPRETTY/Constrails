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



def test_capability_create_bump_update_activate_and_deactivate_commands():
    create_result = runner.invoke(
        cli,
        ['capability-create', '--agent', 'managed-agent', '--tenant', 'tenant-a', '--namespace', 'ns-a', '--tool', 'read_file', '--tool', 'list_directory', '--json'],
    )
    assert create_result.exit_code == 0
    assert '"agent_id": "managed-agent"' in create_result.output

    list_result = runner.invoke(cli, ['capability-list', '--agent', 'managed-agent', '--json'])
    assert list_result.exit_code == 0

    store = get_capability_store()
    rows = store.list_manifests(agent_id='managed-agent', tenant_id='tenant-a', namespace='ns-a')
    manifest_id = rows[0].id
    current_version = rows[0].version

    update_result = runner.invoke(cli, ['capability-update-tools', str(manifest_id), '--tool', 'read_file', '--tool', 'http_request', '--json'])
    assert update_result.exit_code == 0
    assert '"http_request"' in update_result.output

    bump_result = runner.invoke(cli, ['capability-bump', str(manifest_id), '--json', '--inactive'])
    assert bump_result.exit_code == 0
    assert f'"version": {current_version + 1}' in bump_result.output

    bumped_rows = store.list_manifests(agent_id='managed-agent', tenant_id='tenant-a', namespace='ns-a')
    bumped_id = bumped_rows[0].id

    activate_result = runner.invoke(cli, ['capability-activate', str(bumped_id), '--json'])
    assert activate_result.exit_code == 0
    assert '"active": true' in activate_result.output

    deactivate_result = runner.invoke(cli, ['capability-deactivate', str(bumped_id)])
    assert deactivate_result.exit_code == 0
    assert 'Deactivated capability manifest' in deactivate_result.output
