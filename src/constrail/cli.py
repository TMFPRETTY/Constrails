"""
Constrail CLI entrypoint.
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import click
import uvicorn
from rich.console import Console
from rich.table import Table

from . import __version__
from .approval import get_approval_service
from .config import settings
from .database import AuditRecordModel, SandboxExecutionModel, SessionLocal, init_db
from .kernel_v2 import ConstrailKernel
from .sandbox import get_sandbox_executor, reset_sandbox_executor

console = Console()


@click.group(help="Constrail command line interface.")
@click.version_option(version=__version__, prog_name="constrail")
def cli():
    pass


@cli.command("version", help="Show the installed Constrail version.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def version_command(as_json: bool):
    payload = {"name": "constrail", "version": __version__}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"constrail {__version__}")


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
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def doctor_command(as_json: bool):
    reset_sandbox_executor()
    executor = get_sandbox_executor()
    payload = {
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "database_url": settings.database_url,
        "policy_engine": settings.policy_engine,
        "opa_url": settings.opa_url,
        "sandbox_type": settings.sandbox_type,
        "sandbox_executor": executor.__class__.__name__ if executor else None,
        "policy_dir": settings.policy_dir,
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="Constrail Doctor")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    for key, value in payload.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)
    console.print("\n[bold]Raw config:[/bold]")
    console.print_json(json.dumps(payload))


@cli.command("audit-list", help="List recent audit records.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def audit_list_command(limit: int, as_json: bool):
    init_db()
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditRecordModel)
            .order_by(AuditRecordModel.start_time.desc())
            .limit(limit)
            .all()
        )
        payload = [
            {
                "request_id": str(row.request_id),
                "tool": row.tool,
                "decision": row.final_decision.value if hasattr(row.final_decision, 'value') else str(row.final_decision),
                "agent_id": row.agent_id,
                "sandbox_id": row.sandbox_id,
            }
            for row in rows
        ]
        if as_json:
            click.echo(json.dumps(payload, indent=2))
            return

        table = Table(title="Audit Records")
        table.add_column("Request ID")
        table.add_column("Tool")
        table.add_column("Decision")
        table.add_column("Agent")
        table.add_column("Sandbox")
        for row in payload:
            table.add_row(
                row["request_id"],
                row["tool"],
                row["decision"],
                row["agent_id"],
                row["sandbox_id"] or "-",
            )
        console.print(table)
    finally:
        db.close()


@cli.command("sandbox-list", help="List recent sandbox executions.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def sandbox_list_command(limit: int, as_json: bool):
    init_db()
    db = SessionLocal()
    try:
        rows = (
            db.query(SandboxExecutionModel)
            .order_by(SandboxExecutionModel.created_at.desc())
            .limit(limit)
            .all()
        )
        payload = [
            {
                "sandbox_id": row.sandbox_id,
                "executor": row.executor,
                "status": row.status,
                "tool": row.tool,
                "approval_id": str(row.approval_id) if row.approval_id else None,
            }
            for row in rows
        ]
        if as_json:
            click.echo(json.dumps(payload, indent=2))
            return

        table = Table(title="Sandbox Executions")
        table.add_column("Sandbox ID")
        table.add_column("Executor")
        table.add_column("Status")
        table.add_column("Tool")
        table.add_column("Approval ID")
        for row in payload:
            table.add_row(
                row["sandbox_id"],
                row["executor"] or "-",
                row["status"],
                row["tool"],
                row["approval_id"] or "-",
            )
        console.print(table)
    finally:
        db.close()


@cli.command("approval-list", help="List recent approval requests.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
@click.option("--approved", type=click.Choice(["true", "false", "pending"]), default=None, help="Filter by approval state.")
@click.option("--agent", "agent_id", default=None, help="Filter by agent ID.")
@click.option("--tool", default=None, help="Filter by tool name.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_list_command(limit: int, approved: str | None, agent_id: str | None, tool: str | None, as_json: bool):
    init_db()
    service = get_approval_service()
    approved_filter = None
    if approved == "true":
        approved_filter = True
    elif approved == "false":
        approved_filter = False
    elif approved == "pending":
        approved_filter = None

    rows = service.list_requests(approved=approved_filter, agent_id=agent_id, tool=tool)[:limit]
    if approved == "pending":
        rows = [row for row in rows if row.approved is None]

    payload = [
        {
            "approval_id": str(row.approval_id),
            "tool": row.tool,
            "agent_id": row.agent_id,
            "approved": row.approved,
            "approver_id": row.approver_id,
        }
        for row in rows
    ]
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="Approval Requests")
    table.add_column("Approval ID")
    table.add_column("Tool")
    table.add_column("Agent")
    table.add_column("Approved")
    table.add_column("Approver")
    for row in payload:
        table.add_row(
            row["approval_id"],
            row["tool"],
            row["agent_id"],
            str(row["approved"]),
            row["approver_id"] or "-",
        )
    console.print(table)


@cli.command("approval-show", help="Show a single approval request.")
@click.argument("approval_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_show_command(approval_id: str, as_json: bool):
    init_db()
    service = get_approval_service()
    row = service.get_request(UUID(approval_id))
    if row is None:
        raise click.ClickException("Approval request not found")
    payload = {
        "approval_id": str(row.approval_id),
        "request_id": str(row.request_id),
        "agent_id": row.agent_id,
        "tool": row.tool,
        "parameters": row.parameters,
        "approved": row.approved,
        "approver_id": row.approver_id,
        "review_comment": row.review_comment,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


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


@cli.command("approval-replay", help="Replay an already approved request.")
@click.argument("approval_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_replay_command(approval_id: str, as_json: bool):
    init_db()
    kernel = ConstrailKernel()
    response = asyncio.run(kernel.replay_approved(UUID(approval_id)))
    payload = response.model_dump(mode="json")
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


if __name__ == "__main__":
    cli()
