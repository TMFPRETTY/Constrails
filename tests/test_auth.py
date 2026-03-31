from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)


AGENT_HEADERS = {'X-API-Key': 'dev-agent'}
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}
BAD_HEADERS = {'X-API-Key': 'nope'}


def test_action_endpoint_accepts_agent_key():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'auth test'},
    }
    response = client.post('/v1/action', json=payload, headers=AGENT_HEADERS)
    assert response.status_code == 200



def test_admin_endpoint_rejects_agent_key():
    response = client.get('/v1/admin/audit', headers=AGENT_HEADERS)
    assert response.status_code == 403



def test_admin_endpoint_accepts_admin_key():
    response = client.get('/v1/admin/audit', headers=ADMIN_HEADERS)
    assert response.status_code == 200



def test_bad_key_rejected():
    response = client.get('/v1/admin/audit', headers=BAD_HEADERS)
    assert response.status_code == 403
