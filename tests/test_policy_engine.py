import asyncio

from constrail.models import ActionRequest, AgentIdentity, ToolCall
from constrail.policy.policy_engine import PolicyEngine
from constrail.risk.risk_engine import get_risk_engine



def run(coro):
    return asyncio.run(coro)



def test_policy_engine_simple_fallback_for_high_risk_tool():
    engine = PolicyEngine(opa_url='')
    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo hi'}),
        context={'goal': 'policy fallback test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))
    assert result.decision.value == 'approval_required'
    assert 'simple_fallback_high_risk_tool' in result.rule_ids



def test_policy_engine_denies_missing_tenant_scope():
    engine = PolicyEngine(opa_url='')
    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='read_file', parameters={'path': 'README.md'}),
        context={'goal': 'missing tenant scope test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))
    assert result.decision.value == 'deny'
    assert 'simple_missing_tenant_scope' in result.rule_ids



def test_policy_engine_sandboxes_plain_http_requests():
    engine = PolicyEngine(opa_url='')
    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='http_request', parameters={'url': 'http://example.com'}),
        context={'goal': 'plain http test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))
    assert result.decision.value == 'sandbox'
    assert 'simple_http_requires_sandbox' in result.rule_ids



def test_policy_engine_allows_https_requests_in_scope():
    engine = PolicyEngine(opa_url='')
    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='http_request', parameters={'url': 'https://example.com'}),
        context={'goal': 'https allow test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))
    assert result.decision.value == 'allow'
    assert 'simple_allow_https_request' in result.rule_ids



def test_policy_engine_denies_destructive_absolute_delete():
    engine = PolicyEngine(opa_url='')
    risk_engine = get_risk_engine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='delete_file', parameters={'path': '/etc/passwd'}),
        context={'goal': 'destructive delete test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))
    assert result.decision.value == 'deny'
    assert 'simple_deny_destructive_target' in result.rule_ids



def test_policy_engine_explain_local_policy():
    engine = PolicyEngine(opa_url='')
    explanation = engine.explain_local_policy()
    assert explanation['fallback_mode'] is True
    assert explanation['policy_package'] == 'constrail'
    assert 'tenant_scope_required' in explanation['policy_features']
    assert any(path.endswith('allow.rego') for path in explanation['rego_files'])
    assert any(path.endswith('approval.rego') for path in explanation['rego_files'])
    assert any(path.endswith('sandbox.rego') for path in explanation['rego_files'])
    assert any(path.endswith('deny.rego') for path in explanation['rego_files'])
