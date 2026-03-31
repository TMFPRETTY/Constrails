from uuid import UUID

from constrail.database import init_db, SessionLocal, AuditRecordModel, Decision as DBDecision, RiskLevel as DBRiskLevel
from constrail.models import ActionRequest, AgentIdentity, ToolCall
from constrail.risk.risk_engine import RiskEngine


def test_http_request_gets_extra_risk_after_recent_file_read():
    init_db()
    db = SessionLocal()
    try:
        db.add(
            AuditRecordModel(
                request_id=UUID('11111111-1111-1111-1111-111111111111'),
                agent_id='dev-agent',
                tool='read_file',
                parameters={'path': 'README.md'},
                risk_score=0.1,
                risk_level=DBRiskLevel.LOW,
                policy_decision=DBDecision.ALLOW,
                final_decision=DBDecision.ALLOW,
            )
        )
        db.commit()
    finally:
        db.close()

    engine = RiskEngine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='http_request', parameters={'url': 'https://example.com/upload'}),
        context={'goal': 'send data outward'},
    )
    risk = engine.assess(request)
    assert any(f.startswith('chain_risk:') for f in risk.factors)
    assert risk.score > 0.3


def test_http_request_without_recent_read_has_no_chain_factor():
    init_db()
    engine = RiskEngine()
    request = ActionRequest(
        agent=AgentIdentity(agent_id='clean-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='http_request', parameters={'url': 'https://example.com/upload'}),
        context={'goal': 'plain network call'},
    )
    risk = engine.assess(request)
    assert not any(f.startswith('chain_risk:') for f in risk.factors)
