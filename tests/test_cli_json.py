from click.testing import CliRunner

from constrail.cli import cli


runner = CliRunner()


def test_audit_list_json_command():
    result = runner.invoke(cli, ['audit-list', '--limit', '3', '--json'])
    assert result.exit_code == 0
    assert result.output.strip().startswith('[')



def test_sandbox_list_json_command():
    result = runner.invoke(cli, ['sandbox-list', '--limit', '3', '--json'])
    assert result.exit_code == 0
    assert result.output.strip().startswith('[')



def test_approval_list_json_command():
    result = runner.invoke(cli, ['approval-list', '--limit', '3', '--json'])
    assert result.exit_code == 0
    assert result.output.strip().startswith('[')
