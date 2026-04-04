from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}


def test_admin_metrics_endpoint():
    response = client.get('/v1/admin/metrics', headers=ADMIN_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert 'approvals' in body
    assert 'quotas_last_hour' in body
    assert 'audit_records_total' in body
    assert 'sandbox_executions_total' in body
    assert 'sandbox_health' in body
