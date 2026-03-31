from click.testing import CliRunner

from constrail.cli import cli


runner = CliRunner()


def test_doctor_command():
    result = runner.invoke(cli, ['doctor'])
    assert result.exit_code == 0
    assert 'Constrail Doctor' in result.output
    assert 'Sandbox type' in result.output


def test_init_db_command():
    result = runner.invoke(cli, ['init-db'])
    assert result.exit_code == 0
    assert 'Database initialized.' in result.output
