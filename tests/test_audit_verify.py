from click.testing import CliRunner
from fastapi.testclient import TestClient

from constrail.audit_verify import get_audit_verifier
from constrail.cli import cli
from constrail.database import AuditRecordModel, SessionLocal, init_db
from constrail.kernel import app


client = TestClient(app)
runner = CliRunner()


def _seed_audit_chain():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'audit verify seed'},
    }
    response = client.post('/v1/action', json=payload, headers={'X-API-Key': 'dev-agent'})
    assert response.status_code == 200


def test_audit_verify_reports_ok_for_valid_chain():
    init_db()
    _seed_audit_chain()
    result = get_audit_verifier().verify()
    assert result['ok'] is True
    assert result['checked'] >= 1


def test_audit_verify_detects_tampering():
    init_db()
    _seed_audit_chain()
    db = SessionLocal()
    try:
        row = db.query(AuditRecordModel).order_by(AuditRecordModel.start_time.desc()).first()
        row.chain_hash = 'tampered'
        db.commit()
    finally:
        db.close()

    result = get_audit_verifier().verify()
    assert result['ok'] is False
    assert result['error'] == 'chain_hash mismatch'


def test_audit_verify_cli_json():
    init_db()
    _seed_audit_chain()
    result = runner.invoke(cli, ['audit-verify', '--json'])
    assert result.exit_code == 0
    assert '"ok"' in result.output
