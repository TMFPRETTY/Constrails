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
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo hi'}),
        context={'goal': 'policy fallback test'},
    )
    risk = risk_engine.assess(request)
    result = run(engine.evaluate(request, risk))
    assert result.decision.value == 'approval_required'



def test_policy_engine_explain_local_policy():
    engine = PolicyEngine(opa_url='')
    explanation = engine.explain_local_policy()
    assert explanation['fallback_mode'] is True
    assert explanation['policy_package'] == 'constrail'
