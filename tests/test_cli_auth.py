from click.testing import CliRunner

from constrail.cli import cli


runner = CliRunner()


def test_auth_status_command():
    result = runner.invoke(cli, ['auth-status'])
    assert result.exit_code == 0
    assert 'Constrail Auth Status' in result.output



def test_auth_status_json_command():
    result = runner.invoke(cli, ['auth-status', '--json'])
    assert result.exit_code == 0
    assert '"agent_role": "agent"' in result.output
    assert '"admin_role": "admin"' in result.output
