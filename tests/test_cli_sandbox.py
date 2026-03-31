from click.testing import CliRunner

from constrail.cli import cli


runner = CliRunner()



def test_doctor_json_includes_sandbox_details():
    result = runner.invoke(cli, ['doctor', '--json'])
    assert result.exit_code == 0
    assert '"sandbox_image"' in result.output
    assert '"docker_cli_found"' in result.output
    assert '"production_ready"' in result.output
    assert '"warnings"' in result.output
    assert '"checks"' in result.output



def test_sandbox_validate_json_command():
    result = runner.invoke(cli, ['sandbox-validate', '--json'])
    assert result.exit_code == 0
    assert '"production_ready"' in result.output
    assert '"checks"' in result.output
