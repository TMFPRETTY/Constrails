import asyncio

from constrail.database import AuditRecordModel, SessionLocal, SandboxExecutionModel
from constrail.kernel_v2 import ConstrailKernel
from constrail.models import ActionRequest, AgentIdentity, Decision, ToolCall


def run(coro):
    return asyncio.run(coro)


def test_exec_replay_runs_through_sandbox_after_approval():
    kernel = ConstrailKernel()

    create_request = ActionRequest(
        agent=AgentIdentity(agent_id='dev-agent', trust_level=0.8),
        call=ToolCall(tool='exec', parameters={'command': 'echo sandboxed'}),
        context={'goal': 'sandbox replay test'},
    )

    initial = run(kernel.process(create_request))
    assert initial.decision == Decision.APPROVAL_REQUIRED
    assert initial.approval_id is not None

    approval = kernel.approval_service.decide(
        initial.approval_id,
        approved=True,
        approver_id='tmfpretty',
        comment='test approval',
    )
    assert approval is not None
    assert approval.approved is True

    replayed = run(kernel.replay_approved(initial.approval_id))
    assert replayed.decision == Decision.ALLOW
    assert replayed.result is not None
    assert replayed.result['success'] is True
    assert replayed.sandbox_id is not None
    assert replayed.result['metadata']['execution_mode'] == 'sandbox'
    assert replayed.result['metadata']['sandbox_executor'] == 'dev'
    assert 'sandboxed' in replayed.result['data']['stdout']

    db = SessionLocal()
    try:
        sandbox_row = (
            db.query(SandboxExecutionModel)
            .filter(SandboxExecutionModel.sandbox_id == replayed.sandbox_id)
            .first()
        )
        assert sandbox_row is not None
        assert sandbox_row.approval_id == initial.approval_id
        assert sandbox_row.executor == 'dev'
        assert sandbox_row.status == 'completed'

        audit_row = (
            db.query(AuditRecordModel)
            .filter(AuditRecordModel.replayed_from_approval_id == initial.approval_id)
            .order_by(AuditRecordModel.start_time.desc())
            .first()
        )
        assert audit_row is not None
        assert audit_row.approval_id == initial.approval_id
        assert audit_row.approver_id == 'tmfpretty'
        assert audit_row.sandbox_id == replayed.sandbox_id
    finally:
        db.close()
