import hashlib
import hmac
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
    monkeypatch.setattr(settings, 'approval_webhook_secret', 'super-secret')
    monkeypatch.setattr(settings, 'approval_webhook_max_attempts', 3)

    captured = {}

    def _ok(req, timeout=5):
        captured['signature'] = req.headers.get('X-constrails-signature')
        captured['body'] = req.data
        return _SuccessResponse(status=204)

    monkeypatch.setattr('constrail.approval.urlopen', _ok)

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
    expected = 'sha256=' + hmac.new(b'super-secret', captured['body'], hashlib.sha256).hexdigest()
    assert captured['signature'] == expected

    monkeypatch.setattr(settings, 'approval_webhook_url', None)
    monkeypatch.setattr(settings, 'approval_webhook_secret', None)



def test_webhook_delivery_failure_exhaustion_and_manual_retry(monkeypatch):
    monkeypatch.setattr(settings, 'approval_webhook_url', 'https://example.test/webhook')
    monkeypatch.setattr(settings, 'approval_webhook_secret', 'super-secret')
    monkeypatch.setattr(settings, 'approval_webhook_max_attempts', 2)

    attempts = {'count': 0}

    def _flaky(req, timeout=5):
        attempts['count'] += 1
        if attempts['count'] < 3:
            raise URLError('network down')
        return _SuccessResponse(status=202)

    monkeypatch.setattr('constrail.approval.urlopen', _flaky)

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

    second = service.retry_webhook(approval.approval_id)
    assert second is not None
    assert second.webhook_delivery_status == 'failed'
    assert second.webhook_delivery_attempts == 2

    third = service.retry_webhook(approval.approval_id)
    assert third is not None
    assert third.webhook_delivery_status == 'delivered'
    assert third.webhook_delivery_attempts == 3
    assert third.webhook_last_response_code == 202
    assert third.webhook_last_error is None

    monkeypatch.setattr(settings, 'approval_webhook_url', None)
