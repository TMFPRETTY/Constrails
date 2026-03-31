from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)
HEADERS = {'X-API-Key': 'dev-agent'}


def test_approval_request_lifecycle():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'exec', 'parameters': {'command': 'echo hello'}},
        'context': {'goal': 'approval flow test'},
    }

    create_response = client.post('/v1/action', json=payload, headers=HEADERS)
    assert create_response.status_code == 200
    body = create_response.json()
    assert body['decision'] == 'approval_required'
    assert body['approval_id'] is not None

    approval_id = body['approval_id']

    list_response = client.get('/v1/approval', headers=HEADERS)
    assert list_response.status_code == 200
    approvals = list_response.json()
    assert any(row['approval_id'] == approval_id for row in approvals)

    get_response = client.get(f'/v1/approval/{approval_id}', headers=HEADERS)
    assert get_response.status_code == 200
    assert get_response.json()['tool'] == 'exec'

    approve_response = client.post(
        f'/v1/approval/{approval_id}/approve',
        json={'approver_id': 'tmfpretty', 'comment': 'looks good for test'},
        headers=HEADERS,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()['approved'] is True

    replay_response = client.post(f'/v1/approval/{approval_id}/replay', headers=HEADERS)
    assert replay_response.status_code == 200
    replay_body = replay_response.json()
    assert replay_body['decision'] == 'allow'
    assert replay_body['result'] is not None
