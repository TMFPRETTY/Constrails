from fastapi.testclient import TestClient

from constrail.kernel import app


client = TestClient(app)
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}


def test_prometheus_metrics_endpoint():
    response = client.get('/metrics', headers=ADMIN_HEADERS)
    assert response.status_code == 200
    text = response.text
    assert 'constrail_approval_outbox_total' in text
    assert 'constrail_quota_events_total' in text
    assert 'constrail_audit_records_total' in text
    assert 'constrail_sandbox_production_ready' in text
