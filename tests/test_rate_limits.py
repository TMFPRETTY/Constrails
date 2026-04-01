import asyncio
import time

from constrail.config import settings
from constrail.database import QuotaEventModel, SessionLocal, init_db
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, Decision, ToolCall


class TempSetting:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.original = getattr(settings, name)

    def __enter__(self):
        setattr(settings, self.name, self.value)

    def __exit__(self, exc_type, exc, tb):
        setattr(settings, self.name, self.original)


def run(coro):
    return asyncio.run(coro)


def test_rate_limit_blocks_bursting_agent():
    init_db()
    db = SessionLocal()
    try:
        db.query(QuotaEventModel).filter(QuotaEventModel.agent_id == 'dev-agent').delete()
        db.commit()
    finally:
        db.close()

    kernel = ConstrailKernel()
    with (
        TempSetting('anomaly_detection_enabled', True),
        TempSetting('anomaly_burst_threshold', 2),
    ):
        req = ActionRequest(
            agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
            call=ToolCall(tool='read_file', parameters={'path': 'README.md'}),
            context={'goal': 'rate limit test'},
        )
        first = run(kernel.process(req))
        second = run(kernel.process(req))
        third = run(kernel.process(req))

        assert first.decision == Decision.ALLOW
        assert second.decision == Decision.ALLOW
        assert third.decision == Decision.QUARANTINE
        assert third.error == 'Rate limit exceeded'
