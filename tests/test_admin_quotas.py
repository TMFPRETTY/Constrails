from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)
AGENT_HEADERS = {'X-API-Key': 'dev-agent'}
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}


def test_admin_quota_summary_endpoint():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'quota summary seed'},
    }
    response = client.post('/v1/action', json=payload, headers=AGENT_HEADERS)
    assert response.status_code == 200

    summary = client.get('/v1/admin/quotas?agent_id=dev-agent&window_seconds=300', headers=ADMIN_HEADERS)
    assert summary.status_code == 200
    body = summary.json()
    assert body['total_events'] >= 1
    assert 'read_file' in body['per_tool']
