from click.testing import CliRunner

from constrail.cli import cli
from constrail.database import init_db


runner = CliRunner()


def setup_module(module):
    init_db()



def test_audit_list_command_runs():
    result = runner.invoke(cli, ['audit-list', '--limit', '5'])
    assert result.exit_code == 0
    assert 'Audit Records' in result.output



def test_sandbox_list_command_runs():
    result = runner.invoke(cli, ['sandbox-list', '--limit', '5'])
    assert result.exit_code == 0
    assert 'Sandbox Executions' in result.output
