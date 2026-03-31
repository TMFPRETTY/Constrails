from urllib.error import URLError
from uuid import uuid4

from constrail.approval import ApprovalService
from constrail.config import settings


class _SuccessResponse:
    def __init__(self, status=204):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False



def test_webhook_delivery_success(monkeypatch):
    monkeypatch.setattr(settings, 'approval_webhook_url', 'https://example.test/webhook')
    monkeypatch.setattr('constrail.approval.urlopen', lambda req, timeout=5: _SuccessResponse(status=204))

    service = ApprovalService()
    approval = service.create_request(
        request_id=uuid4(),
        agent_id='dev-agent',
        tool='exec',
        parameters={'command': 'echo webhook'},
        risk_score=0.7,
        risk_level='high',
        policy_evaluation={'decision': 'approval_required'},
    )

    assert approval.webhook_delivery_status == 'delivered'
    assert approval.webhook_delivery_attempts == 1
    assert approval.webhook_last_response_code == 204
    assert approval.webhook_last_error is None

    monkeypatch.setattr(settings, 'approval_webhook_url', None)



def test_webhook_delivery_failure(monkeypatch):
    monkeypatch.setattr(settings, 'approval_webhook_url', 'https://example.test/webhook')

    def _boom(req, timeout=5):
        raise URLError('network down')

    monkeypatch.setattr('constrail.approval.urlopen', _boom)

    service = ApprovalService()
    approval = service.create_request(
        request_id=uuid4(),
        agent_id='dev-agent',
        tool='exec',
        parameters={'command': 'echo webhook'},
        risk_score=0.7,
        risk_level='high',
        policy_evaluation={'decision': 'approval_required'},
    )

    assert approval.webhook_delivery_status == 'failed'
    assert approval.webhook_delivery_attempts == 1
    assert approval.webhook_last_response_code is None
    assert 'network down' in approval.webhook_last_error

    monkeypatch.setattr(settings, 'approval_webhook_url', None)
