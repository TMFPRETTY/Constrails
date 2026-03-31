from click.testing import CliRunner

from constrail.cli import cli


runner = CliRunner()


def test_doctor_command():
    result = runner.invoke(cli, ['doctor'])
    assert result.exit_code == 0
    assert 'Constrail Doctor' in result.output
    assert 'Sandbox Type' in result.output


def test_doctor_json_command():
    result = runner.invoke(cli, ['doctor', '--json'])
    assert result.exit_code == 0
    assert '"sandbox_type"' in result.output


def test_init_db_command():
    result = runner.invoke(cli, ['init-db'])
    assert result.exit_code == 0
    assert 'Database initialized.' in result.output
