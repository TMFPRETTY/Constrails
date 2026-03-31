import asyncio
from datetime import datetime, timedelta

import pytest

from constrail.approval import get_approval_service
from constrail.database import init_db
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, ToolCall



def run(coro):
    return asyncio.run(coro)



def setup_module(module):
    init_db()



def test_replay_rejects_expired_approval():
    kernel = ConstrailKernel()
    req = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo expired-approval'}),
        context={'goal': 'approval expiry test'},
    )
    response = run(kernel.process(req))
    approval_id = response.approval_id
    if approval_id is None:
        return

    service = get_approval_service()
    service.decide(approval_id, approved=True, approver_id='tmfpretty', comment='approve for expiry test')

    row = service.get_request(approval_id)
    assert row is not None
    row.expires_at = datetime.utcnow() - timedelta(minutes=1)
    from constrail.database import SessionLocal, ApprovalRequestModel
    db = SessionLocal()
    try:
        stored = db.query(ApprovalRequestModel).filter(ApprovalRequestModel.approval_id == approval_id).first()
        stored.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    with pytest.raises(ValueError, match='expired'):
        run(kernel.replay_approved(approval_id))
