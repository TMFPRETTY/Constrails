from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)
HEADERS = {'X-API-Key': 'dev-agent'}


def test_admin_audit_and_sandbox_endpoints():
    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'exec', 'parameters': {'command': 'echo audit-me'}},
        'context': {'goal': 'exercise admin endpoints'},
    }

    create_response = client.post('/v1/action', json=payload, headers=HEADERS)
    assert create_response.status_code == 200
    approval_id = create_response.json()['approval_id']

    approve_response = client.post(
        f'/v1/approval/{approval_id}/approve',
        json={'approver_id': 'tmfpretty', 'comment': 'admin endpoint test'},
        headers=HEADERS,
    )
    assert approve_response.status_code == 200

    replay_response = client.post(f'/v1/approval/{approval_id}/replay', headers=HEADERS)
    assert replay_response.status_code == 200
    replay_body = replay_response.json()
    request_id = replay_body['request_id']
    sandbox_id = replay_body['sandbox_id']

    audit_list = client.get('/v1/admin/audit?limit=5&agent_id=dev-agent&tool=exec', headers=HEADERS)
    assert audit_list.status_code == 200
    assert any(row['request_id'] == request_id for row in audit_list.json())

    audit_get = client.get(f'/v1/admin/audit/{request_id}', headers=HEADERS)
    assert audit_get.status_code == 200
    assert audit_get.json()['sandbox_id'] == sandbox_id

    sandbox_list = client.get('/v1/admin/sandbox?limit=5&agent_id=dev-agent&executor=dev&status=completed', headers=HEADERS)
    assert sandbox_list.status_code == 200
    assert any(row['sandbox_id'] == sandbox_id for row in sandbox_list.json())

    sandbox_get = client.get(f'/v1/admin/sandbox/{sandbox_id}', headers=HEADERS)
    assert sandbox_get.status_code == 200
    assert sandbox_get.json()['status'] == 'completed'
