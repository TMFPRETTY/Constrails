from jose import jwt
from fastapi.testclient import TestClient

from constrail.config import settings
from constrail.kernel import app
from constrail.auth import get_auth_service


client = TestClient(app)


AGENT_HEADERS = {'X-API-Key': 'dev-agent'}
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}
BAD_HEADERS = {'X-API-Key': 'nope'}


def _make_token(role: str, sub: str, tenant_id: str | None = None, namespace: str | None = None, agent_id: str | None = None, issuer: str | None = None, audience: str | None = None) -> str:
    payload = {
        'role': role,
        'sub': sub,
        'iss': issuer or settings.token_issuer,
        'aud': audience or settings.token_audience,
    }
    if agent_id is not None:
        payload['agent_id'] = agent_id
    if tenant_id is not None:
        payload['tenant_id'] = tenant_id
    if namespace is not None:
        payload['namespace'] = namespace
    return jwt.encode(payload, settings.secret_key, algorithm=settings.token_algorithm)



def test_action_endpoint_accepts_agent_key():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'auth test'},
    }
    response = client.post('/v1/action', json=payload, headers=AGENT_HEADERS)
    assert response.status_code == 200



def test_action_endpoint_accepts_agent_bearer_token():
    token = _make_token('agent', 'token-agent', tenant_id='default', namespace='dev', agent_id='dev-agent')
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'bearer auth test'},
    }
    response = client.post('/v1/action', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json()['decision'] == 'allow'



def test_revoked_bearer_token_rejected():
    auth = get_auth_service()
    token = auth.mint_token(role='agent', subject='revoked-agent', tenant_id='default', namespace='dev', agent_id='dev-agent')
    auth.revoke_token(token)
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'revoked bearer auth test'},
    }
    response = client.post('/v1/action', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403



def test_admin_endpoint_rejects_agent_key():
    response = client.get('/v1/admin/audit', headers=AGENT_HEADERS)
    assert response.status_code == 403



def test_admin_endpoint_accepts_admin_key():
    response = client.get('/v1/admin/audit', headers=ADMIN_HEADERS)
    assert response.status_code == 200



def test_admin_endpoint_accepts_admin_bearer_token():
    token = _make_token('admin', 'admin-token', tenant_id='default', namespace='dev')
    response = client.get('/v1/admin/audit', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200



def test_invalid_bearer_token_claims_rejected():
    token = _make_token('admin', 'admin-token', issuer='wrong-issuer')
    response = client.get('/v1/admin/audit', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403



def test_bad_key_rejected():
    response = client.get('/v1/admin/audit', headers=BAD_HEADERS)
    assert response.status_code == 403
