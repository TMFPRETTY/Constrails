from fastapi.testclient import TestClient

from constrail.auth import get_auth_service
from constrail.database import init_db
from constrail.kernel import app


client = TestClient(app)


def test_audit_record_includes_bearer_auth_metadata():
    init_db()
    auth = get_auth_service()
    token = auth.mint_token(
        role='agent',
        subject='audit-agent',
        tenant_id='default',
        namespace='dev',
        agent_id='dev-agent',
    )

    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'audit auth metadata test'},
    }

    action = client.post('/v1/action', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert action.status_code == 200
    request_id = action.json()['request_id']

    audit = client.get(f'/v1/admin/audit/{request_id}', headers={'X-API-Key': 'dev-admin'})
    assert audit.status_code == 200
    body = audit.json()
    assert body['auth_type'] == 'bearer'
    assert body['auth_subject'] == 'dev-agent'
    assert body['auth_token_id'] is not None
    assert body['auth_key_id'] is not None
