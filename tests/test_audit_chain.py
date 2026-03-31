from fastapi.testclient import TestClient

from constrail.database import init_db, SessionLocal, AuditRecordModel
from constrail.kernel import app


client = TestClient(app)
AGENT_HEADERS = {'X-API-Key': 'dev-agent'}
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}


def test_audit_records_form_hash_chain():
    init_db()

    first_payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'first chain event'},
    }
    second_payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'list_directory', 'parameters': {'path': '.'}},
        'context': {'goal': 'second chain event'},
    }

    first = client.post('/v1/action', json=first_payload, headers=AGENT_HEADERS)
    second = client.post('/v1/action', json=second_payload, headers=AGENT_HEADERS)
    assert first.status_code == 200
    assert second.status_code == 200

    db = SessionLocal()
    try:
        rows = db.query(AuditRecordModel).order_by(AuditRecordModel.start_time.asc()).all()
        assert len(rows) >= 2
        assert rows[-2].chain_hash is not None
        assert rows[-1].chain_prev_hash == rows[-2].chain_hash
        assert rows[-1].chain_hash is not None
    finally:
        db.close()

    audit = client.get('/v1/admin/audit?limit=2', headers=ADMIN_HEADERS)
    assert audit.status_code == 200
    body = audit.json()
    assert 'chain_hash' in body[0]
