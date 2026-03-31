from fastapi.testclient import TestClient

from constrail.kernel import app
from constrail.config import settings


client = TestClient(app)
AGENT_HEADERS = {'X-API-Key': 'dev-agent'}
ADMIN_HEADERS = {'X-API-Key': 'dev-admin'}


def test_scoped_admin_cannot_query_other_agent_records(monkeypatch):
    monkeypatch.setattr(settings, 'admin_tenant_id', 'default')
    monkeypatch.setattr(settings, 'admin_namespace', 'dev')

    payload = {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'exec', 'parameters': {'command': 'echo scoped-admin'}},
        'context': {'goal': 'create scoped records'},
    }

    create_response = client.post('/v1/action', json=payload, headers=AGENT_HEADERS)
    assert create_response.status_code == 200

    forbidden_audit = client.get('/v1/admin/audit?agent_id=other-agent', headers=ADMIN_HEADERS)
    assert forbidden_audit.status_code == 403

    forbidden_sandbox = client.get('/v1/admin/sandbox?agent_id=other-agent', headers=ADMIN_HEADERS)
    assert forbidden_sandbox.status_code == 403

    forbidden_caps = client.get('/v1/admin/capabilities?agent_id=other-agent', headers=ADMIN_HEADERS)
    assert forbidden_caps.status_code == 403

    monkeypatch.setattr(settings, 'admin_tenant_id', None)
    monkeypatch.setattr(settings, 'admin_namespace', None)


def test_scoped_admin_can_query_in_scope_agent_records(monkeypatch):
    monkeypatch.setattr(settings, 'admin_tenant_id', 'default')
    monkeypatch.setattr(settings, 'admin_namespace', 'dev')

    audit_response = client.get('/v1/admin/audit?agent_id=dev-agent', headers=ADMIN_HEADERS)
    assert audit_response.status_code == 200

    sandbox_response = client.get('/v1/admin/sandbox?agent_id=dev-agent', headers=ADMIN_HEADERS)
    assert sandbox_response.status_code == 200

    capability_response = client.get('/v1/admin/capabilities?agent_id=dev-agent', headers=ADMIN_HEADERS)
    assert capability_response.status_code == 200

    monkeypatch.setattr(settings, 'admin_tenant_id', None)
    monkeypatch.setattr(settings, 'admin_namespace', None)
