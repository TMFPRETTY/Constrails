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


if __name__ == "__main__":
    cli()
