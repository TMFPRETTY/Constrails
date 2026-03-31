import asyncio

from constrail.models import ActionRequest, AgentIdentity, ToolCall
from constrail.policy.policy_engine import PolicyEngine
from constrail.risk.risk_engine import get_risk_engine


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload



def run(coro):
    return asyncio.run(coro)



def test_policy_engine_uses_opa_result_contract_for_sandbox(monkeypatch):
    engine = PolicyEngine(opa_url='http://opa.test', policy_package='constrail')

    async def _fake_post(url, json):
        assert url == 'http://opa.test/v1/data/constrail/allow'
        assert 'input' in json
        return _FakeResponse(
            {
                'result': {
                    'decision': 'sandbox',
                    'message': 'OPA says sandbox this request',
                    'rule_ids': ['opa_sandbox_rule'],
                }
            }
        )

    monkeypatch.setattr(engine.client, 'post', _fake_post)

    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='http_request', parameters={'url': 'http://example.com'}),
        context={'goal': 'opa contract test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))

    assert result.decision.value == 'sandbox'
    assert result.message == 'OPA says sandbox this request'
    assert result.rule_ids == ['opa_sandbox_rule']

    run(engine.close())



def test_policy_engine_uses_opa_result_contract_for_approval(monkeypatch):
    engine = PolicyEngine(opa_url='http://opa.test', policy_package='constrail')

    async def _fake_post(url, json):
        return _FakeResponse(
            {
                'result': {
                    'decision': 'approval_required',
                    'message': 'OPA wants approval',
                    'rule_ids': ['opa_approval_rule'],
                }
            }
        )

    monkeypatch.setattr(engine.client, 'post', _fake_post)

    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo hi'}),
        context={'goal': 'opa approval test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))

    assert result.decision.value == 'approval_required'
    assert result.rule_ids == ['opa_approval_rule']

    run(engine.close())



def test_policy_engine_uses_opa_result_contract_for_deny(monkeypatch):
    engine = PolicyEngine(opa_url='http://opa.test', policy_package='constrail')

    async def _fake_post(url, json):
        return _FakeResponse(
            {
                'result': {
                    'decision': 'deny',
                    'message': 'OPA denies this request',
                    'rule_ids': ['opa_deny_rule'],
                }
            }
        )

    monkeypatch.setattr(engine.client, 'post', _fake_post)

    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='delete_file', parameters={'path': '/etc/passwd'}),
        context={'goal': 'opa deny test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))

    assert result.decision.value == 'deny'
    assert result.rule_ids == ['opa_deny_rule']

    run(engine.close())



def test_policy_engine_falls_back_when_opa_call_fails(monkeypatch):
    engine = PolicyEngine(opa_url='http://opa.test', policy_package='constrail')

    async def _fake_post(url, json):
        raise RuntimeError('opa unavailable')

    monkeypatch.setattr(engine.client, 'post', _fake_post)

    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo hi'}),
        context={'goal': 'opa fallback test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))

    assert result.decision.value == 'sandbox'
    assert 'degraded_policy_unavailable_high_risk' in result.rule_ids

    run(engine.close())
