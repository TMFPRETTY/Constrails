from click.testing import CliRunner

from constrail.cli import cli
from constrail.database import init_db
from constrail.rate_limits import get_rate_limit_service


runner = CliRunner()


def test_quota_summary_json_command():
    init_db()
    service = get_rate_limit_service()
    service.record_and_check(agent_id='dev-agent', tenant_id='default', tool='read_file')

    result = runner.invoke(cli, ['quota-summary', '--json'])
    assert result.exit_code == 0
    assert '"total_events"' in result.output
    assert '"dev-agent"' in result.output
