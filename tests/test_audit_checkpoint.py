from pathlib import Path

from click.testing import CliRunner
from fastapi.testclient import TestClient

from constrail.audit_checkpoint import create_audit_checkpoint
from constrail.cli import cli
from constrail.database import init_db
from constrail.kernel import app


client = TestClient(app)
runner = CliRunner()


def _seed():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'checkpoint seed'},
    }
    response = client.post('/v1/action', json=payload, headers={'X-API-Key': 'dev-agent'})
    assert response.status_code == 200


def test_create_audit_checkpoint_and_cli(tmp_path):
    init_db()
    _seed()

    checkpoint_path = tmp_path / 'audit-checkpoint.json'
    payload = create_audit_checkpoint(str(checkpoint_path))
    assert payload['records'] >= 1
    assert checkpoint_path.exists()

    result = runner.invoke(cli, ['audit-checkpoint', '--json'])
    assert result.exit_code == 0
    assert '"checkpoint_hash"' in result.output
