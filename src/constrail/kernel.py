"""
Constrail FastAPI application.
Thin API wrapper around the canonical ConstrailKernel implementation.
"""

import logging
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request

from .admin_models import AuditRecordResponse, SandboxExecutionResponse
from .approval import get_approval_service
from .approval_models import ApprovalDecisionRequest, ApprovalRequestResponse
from .config import settings
from .database import AuditRecordModel, SandboxExecutionModel, SessionLocal, init_db
from .kernel_v2 import get_kernel
from .models import ActionRequest, ActionResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Constrail Kernel",
    description="Runtime governance and containment platform for AI agents",
    version="0.1.0",
    root_path=settings.api_root_path,
)


def ensure_runtime_ready():
    init_db()



def authenticate_request(request: Request) -> str:
    """Extract and validate API key from request headers.
    MVP: simple header check where API key maps to agent_id.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    return api_key


@app.get("/health")
async def health():
    ensure_runtime_ready()
    return {"status": "healthy"}


@app.post("/v1/action", response_model=ActionResponse)
async def execute_action(
    request: ActionRequest, auth_token: str = Depends(authenticate_request)
):
    ensure_runtime_ready()
    request.agent.agent_id = auth_token
    kernel = await get_kernel()
    return await kernel.process(request)


@app.get("/v1/approval", response_model=list[ApprovalRequestResponse])
async def list_approvals(auth_token: str = Depends(authenticate_request)):
    ensure_runtime_ready()
    service = get_approval_service()
    return [ApprovalRequestResponse.from_db(row) for row in service.list_requests()]


@app.get("/v1/approval/{approval_id}", response_model=ApprovalRequestResponse)
async def get_approval(approval_id: UUID, auth_token: str = Depends(authenticate_request)):
    ensure_runtime_ready()
    service = get_approval_service()
    row = service.get_request(approval_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalRequestResponse.from_db(row)


@app.post("/v1/approval/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    auth_token: str = Depends(authenticate_request),
):
    ensure_runtime_ready()
    service = get_approval_service()
    row = service.decide(approval_id, approved=True, approver_id=body.approver_id, comment=body.comment)
    if row is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalRequestResponse.from_db(row)


@app.post("/v1/approval/{approval_id}/deny", response_model=ApprovalRequestResponse)
async def deny_request(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    auth_token: str = Depends(authenticate_request),
):
    ensure_runtime_ready()
    service = get_approval_service()
    row = service.decide(approval_id, approved=False, approver_id=body.approver_id, comment=body.comment)
    if row is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalRequestResponse.from_db(row)


@app.post("/v1/approval/{approval_id}/replay", response_model=ActionResponse)
async def replay_approved_request(
    approval_id: UUID,
    auth_token: str = Depends(authenticate_request),
):
    ensure_runtime_ready()
    kernel = await get_kernel()
    try:
        return await kernel.replay_approved(approval_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/admin/audit", response_model=list[AuditRecordResponse])
async def list_audit_records(
    limit: int = 20,
    offset: int = 0,
    agent_id: str | None = None,
    tool: str | None = None,
    decision: str | None = None,
    approval_id: UUID | None = None,
    sandbox_id: str | None = None,
    auth_token: str = Depends(authenticate_request),
):
    ensure_runtime_ready()
    db = SessionLocal()
    try:
        query = db.query(AuditRecordModel)
        if agent_id:
            query = query.filter(AuditRecordModel.agent_id == agent_id)
        if tool:
            query = query.filter(AuditRecordModel.tool == tool)
        if decision:
            query = query.filter(AuditRecordModel.final_decision == decision)
        if approval_id:
            query = query.filter(AuditRecordModel.approval_id == approval_id)
        if sandbox_id:
            query = query.filter(AuditRecordModel.sandbox_id == sandbox_id)

        rows = (
            query.order_by(AuditRecordModel.start_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [AuditRecordResponse.from_db(row) for row in rows]
    finally:
        db.close()


@app.get("/v1/admin/audit/{request_id}", response_model=AuditRecordResponse)
async def get_audit_record(request_id: UUID, auth_token: str = Depends(authenticate_request)):
    ensure_runtime_ready()
    db = SessionLocal()
    try:
        row = (
            db.query(AuditRecordModel)
            .filter(AuditRecordModel.request_id == request_id)
            .order_by(AuditRecordModel.start_time.desc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Audit record not found")
        return AuditRecordResponse.from_db(row)
    finally:
        db.close()


@app.get("/v1/admin/sandbox", response_model=list[SandboxExecutionResponse])
async def list_sandbox_executions(
    limit: int = 20,
    offset: int = 0,
    agent_id: str | None = None,
    tool: str | None = None,
    executor: str | None = None,
    status: str | None = None,
    approval_id: UUID | None = None,
    auth_token: str = Depends(authenticate_request),
):
    ensure_runtime_ready()
    db = SessionLocal()
    try:
        query = db.query(SandboxExecutionModel)
        if agent_id:
            query = query.filter(SandboxExecutionModel.agent_id == agent_id)
        if tool:
            query = query.filter(SandboxExecutionModel.tool == tool)
        if executor:
            query = query.filter(SandboxExecutionModel.executor == executor)
        if status:
            query = query.filter(SandboxExecutionModel.status == status)
        if approval_id:
            query = query.filter(SandboxExecutionModel.approval_id == approval_id)

        rows = (
            query.order_by(SandboxExecutionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [SandboxExecutionResponse.from_db(row) for row in rows]
    finally:
        db.close()


@app.get("/v1/admin/sandbox/{sandbox_id}", response_model=SandboxExecutionResponse)
async def get_sandbox_execution(sandbox_id: str, auth_token: str = Depends(authenticate_request)):
    ensure_runtime_ready()
    db = SessionLocal()
    try:
        row = (
            db.query(SandboxExecutionModel)
            .filter(SandboxExecutionModel.sandbox_id == sandbox_id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Sandbox execution not found")
        return SandboxExecutionResponse.from_db(row)
    finally:
        db.close()
