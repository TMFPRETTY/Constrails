"""
Constrail CLI entrypoint.
"""

from __future__ import annotations

import json
from uuid import UUID

import click
import uvicorn
from rich.console import Console
from rich.table import Table

from .approval import get_approval_service
from .config import settings
from .database import AuditRecordModel, SandboxExecutionModel, SessionLocal, init_db
from .sandbox import get_sandbox_executor, reset_sandbox_executor

console = Console()


@click.group(help="Constrail command line interface.")
def cli():
    pass


@cli.command("init-db", help="Initialize the Constrail database schema.")
def init_db_command():
    init_db()
    console.print("[green]Database initialized.[/green]")


@cli.command("serve", help="Run the Constrail API server.")
@click.option("--host", default=None, help="Bind host. Defaults to configured api_host.")
@click.option("--port", default=None, type=int, help="Bind port. Defaults to configured api_port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development.")
def serve_command(host: str | None, port: int | None, reload: bool):
    uvicorn.run(
        "constrail.kernel:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
        reload=reload,
    )


@cli.command("doctor", help="Show current runtime configuration and dependency posture.")
def doctor_command():
    reset_sandbox_executor()
    executor = get_sandbox_executor()

    table = Table(title="Constrail Doctor")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("API host", settings.api_host)
    table.add_row("API port", str(settings.api_port))
    table.add_row("Database URL", settings.database_url)
    table.add_row("Policy engine", settings.policy_engine)
    table.add_row("OPA URL", settings.opa_url)
    table.add_row("Sandbox type", settings.sandbox_type)
    table.add_row("Sandbox executor", executor.__class__.__name__ if executor else "None")
    table.add_row("Policy dir", settings.policy_dir)

    console.print(table)
    console.print("\n[bold]Raw config:[/bold]")
    console.print_json(json.dumps({
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "database_url": settings.database_url,
        "policy_engine": settings.policy_engine,
        "opa_url": settings.opa_url,
        "sandbox_type": settings.sandbox_type,
        "policy_dir": settings.policy_dir,
    }))


@cli.command("audit-list", help="List recent audit records.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
def audit_list_command(limit: int):
    init_db()
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditRecordModel)
            .order_by(AuditRecordModel.start_time.desc())
            .limit(limit)
            .all()
        )
        table = Table(title="Audit Records")
        table.add_column("Request ID")
        table.add_column("Tool")
        table.add_column("Decision")
        table.add_column("Agent")
        table.add_column("Sandbox")
        for row in rows:
            table.add_row(
                str(row.request_id),
                row.tool,
                row.final_decision.value if hasattr(row.final_decision, 'value') else str(row.final_decision),
                row.agent_id,
                row.sandbox_id or "-",
            )
        console.print(table)
    finally:
        db.close()


@cli.command("sandbox-list", help="List recent sandbox executions.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
def sandbox_list_command(limit: int):
    init_db()
    db = SessionLocal()
    try:
        rows = (
            db.query(SandboxExecutionModel)
            .order_by(SandboxExecutionModel.created_at.desc())
            .limit(limit)
            .all()
        )
        table = Table(title="Sandbox Executions")
        table.add_column("Sandbox ID")
        table.add_column("Executor")
        table.add_column("Status")
        table.add_column("Tool")
        table.add_column("Approval ID")
        for row in rows:
            table.add_row(
                row.sandbox_id,
                row.executor or "-",
                row.status,
                row.tool,
                str(row.approval_id) if row.approval_id else "-",
            )
        console.print(table)
    finally:
        db.close()


@cli.command("approval-list", help="List recent approval requests.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
def approval_list_command(limit: int):
    init_db()
    service = get_approval_service()
    rows = service.list_requests()[:limit]
    table = Table(title="Approval Requests")
    table.add_column("Approval ID")
    table.add_column("Tool")
    table.add_column("Agent")
    table.add_column("Approved")
    table.add_column("Approver")
    for row in rows:
        table.add_row(
            str(row.approval_id),
            row.tool,
            row.agent_id,
            str(row.approved),
            row.approver_id or "-",
        )
    console.print(table)


@cli.command("approval-show", help="Show a single approval request.")
@click.argument("approval_id")
def approval_show_command(approval_id: str):
    init_db()
    service = get_approval_service()
    row = service.get_request(UUID(approval_id))
    if row is None:
        raise click.ClickException("Approval request not found")
    console.print_json(json.dumps({
        "approval_id": str(row.approval_id),
        "request_id": str(row.request_id),
        "agent_id": row.agent_id,
        "tool": row.tool,
        "parameters": row.parameters,
        "approved": row.approved,
        "approver_id": row.approver_id,
        "review_comment": row.review_comment,
    }))


@cli.command("approval-approve", help="Approve an approval request.")
@click.argument("approval_id")
@click.option("--approver", required=True, help="Approver identifier.")
@click.option("--comment", default=None, help="Optional approval comment.")
def approval_approve_command(approval_id: str, approver: str, comment: str | None):
    init_db()
    service = get_approval_service()
    row = service.decide(UUID(approval_id), approved=True, approver_id=approver, comment=comment)
    if row is None:
        raise click.ClickException("Approval request not found")
    console.print(f"[green]Approved {row.approval_id}[/green]")


@cli.command("approval-deny", help="Deny an approval request.")
@click.argument("approval_id")
@click.option("--approver", required=True, help="Approver identifier.")
@click.option("--comment", default=None, help="Optional denial comment.")
def approval_deny_command(approval_id: str, approver: str, comment: str | None):
    init_db()
    service = get_approval_service()
    row = service.decide(UUID(approval_id), approved=False, approver_id=approver, comment=comment)
    if row is None:
        raise click.ClickException("Approval request not found")
    console.print(f"[yellow]Denied {row.approval_id}[/yellow]")


if __name__ == "__main__":
    cli()
