from click.testing import CliRunner
from fastapi.testclient import TestClient

from constrail.cli import cli
from constrail.database import init_db
from constrail.kernel import app
from constrail.rate_limits import get_rate_limit_service


runner = CliRunner()
client = TestClient(app)
AGENT_HEADERS = {'X-API-Key': 'dev-agent'}
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}


def test_quota_events_cli_and_prune():
    init_db()
    service = get_rate_limit_service()
    service.record_and_check(agent_id='dev-agent', tenant_id='default', tool='read_file')

    events = runner.invoke(cli, ['quota-events', '--json'])
    assert events.exit_code == 0
    assert '"agent_id": "dev-agent"' in events.output

    pruned = runner.invoke(cli, ['quota-prune', '--older-than-seconds', '0', '--json'])
    assert pruned.exit_code == 0
    assert '"deleted"' in pruned.output


def test_admin_quota_events_endpoint():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'quota events seed'},
    }
    response = client.post('/v1/action', json=payload, headers=AGENT_HEADERS)
    assert response.status_code == 200

    events = client.get('/v1/admin/quota-events?agent_id=dev-agent&window_seconds=300', headers=ADMIN_HEADERS)
    assert events.status_code == 200
    body = events.json()
    assert len(body) >= 1
    assert body[0]['agent_id'] == 'dev-agent'
