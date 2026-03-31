from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'healthy'}


def test_action_endpoint_read_file():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'api read file test'},
    }

    response = client.post('/v1/action', json=payload, headers={'X-API-Key': 'dev-agent'})
    assert response.status_code == 200

    body = response.json()
    assert body['decision'] == 'allow'
    assert body['result']['success'] is True
    assert 'Constrails' in body['result']['data']['content']
