"""
Constrail CLI entrypoint.
"""

from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

import click
import uvicorn
from rich.console import Console
from rich.table import Table

from . import __version__
from .approval import get_approval_service
from .approval_models import ApprovalRequestResponse
from .auth import get_auth_service
from .capability_store import get_capability_store
from .config import settings
from .database import AuditRecordModel, SandboxExecutionModel, SessionLocal, init_db
from .rate_limits import get_rate_limit_service
from .kernel_v2 import ConstrailKernel
from .sandbox import get_sandbox_executor, reset_sandbox_executor, sandbox_health
from .audit_verify import get_audit_verifier
from .audit_checkpoint import create_audit_checkpoint
from .db_migrate import current_db, upgrade_db

console = Console()


@click.group(help="Constrail command line interface.")
@click.version_option(version=__version__, prog_name="constrail")
def cli():
    pass

# ... existing commands omitted in this rewrite target for brevity in this patch? no, keep full file

@cli.command("version", help="Show the installed Constrail version.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def version_command(as_json: bool):
    payload = {"name": "constrail", "version": __version__}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"constrail {__version__}")


@cli.command("auth-status", help="Show configured auth roles for current alpha settings.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def auth_status_command(as_json: bool):
    auth = get_auth_service()
    payload = {
        'agent_key_configured': bool(settings.agent_api_key),
        'admin_key_configured': bool(settings.admin_api_key),
        'bearer_tokens_enabled': bool(settings.secret_key),
        'previous_secret_key_configured': bool(settings.previous_secret_key),
        'token_issuer': settings.token_issuer,
        'token_audience': settings.token_audience,
        'token_expire_minutes': settings.token_expire_minutes,
        'agent_role': auth.authenticate(settings.agent_api_key).role if settings.agent_api_key else None,
        'admin_role': auth.authenticate(settings.admin_api_key).role if settings.admin_api_key else None,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    table = Table(title='Constrail Auth Status')
    table.add_column('Setting')
    table.add_column('Value')
    for key, value in payload.items():
        table.add_row(key, str(value))
    console.print(table)


@cli.command("auth-keys", help="Show signing key registry state.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def auth_keys_command(as_json: bool):
    payload = get_auth_service().key_summary()
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("auth-mint-token", help="Mint a local bearer token for testing/operator workflows.")
@click.option("--role", type=click.Choice(["agent", "admin"]), required=True, help="Token role.")
@click.option("--subject", required=True, help="Token subject.")
@click.option("--tenant", "tenant_id", default=None, help="Tenant identifier.")
@click.option("--namespace", default=None, help="Namespace identifier.")
@click.option("--agent-id", default=None, help="Optional agent ID claim.")
@click.option("--expires-minutes", type=int, default=None, help="Override token lifetime.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def auth_mint_token_command(role: str, subject: str, tenant_id: str | None, namespace: str | None, agent_id: str | None, expires_minutes: int | None, as_json: bool):
    auth = get_auth_service()
    token = auth.mint_token(
        role=role,
        subject=subject,
        tenant_id=tenant_id,
        namespace=namespace,
        agent_id=agent_id,
        expires_minutes=expires_minutes,
    )
    payload = {
        'token': token,
        'role': role,
        'subject': subject,
        'tenant_id': tenant_id,
        'namespace': namespace,
        'agent_id': agent_id,
        'expires_minutes': expires_minutes or settings.token_expire_minutes,
        'issuer': settings.token_issuer,
        'audience': settings.token_audience,
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(token)


@cli.command("auth-inspect-token", help="Inspect bearer token claims without verifying the signature.")
@click.argument("token")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def auth_inspect_token_command(token: str, as_json: bool):
    auth = get_auth_service()
    payload = auth.inspect_token(token)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("auth-revoke-token", help="Revoke a bearer token by its signed value.")
@click.argument("token")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def auth_revoke_token_command(token: str, as_json: bool):
    auth = get_auth_service()
    payload = auth.revoke_token(token)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("auth-rotate-secret", help="Rotate the active bearer signing secret and retain the previous secret temporarily.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def auth_rotate_secret_command(as_json: bool):
    auth = get_auth_service()
    payload = auth.rotate_secret()
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("init-db", help="Initialize the Constrail database schema.")
def init_db_command():
    init_db()
    console.print("[green]Database initialized.[/green]")


@cli.command("db-upgrade", help="Apply Alembic migrations up to the requested revision.")
@click.option("--revision", default="head", help="Target Alembic revision (default: head).")
@click.option("--database-url", default=None, help="Optional database URL override for migration commands.")
def db_upgrade_command(revision: str, database_url: str | None):
    upgrade_db(revision, database_url=database_url)
    console.print(f"[green]Database upgraded to {revision}.[/green]")


@cli.command("db-current", help="Show current Alembic revision.")
@click.option("--database-url", default=None, help="Optional database URL override for migration commands.")
def db_current_command(database_url: str | None):
    current_db(verbose=True, database_url=database_url)


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
    sandbox_info = sandbox_health()
    payload = {
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "database_url": settings.database_url,
        "policy_engine": settings.policy_engine,
        "opa_url": settings.opa_url,
        "sandbox_type": settings.sandbox_type,
        "sandbox_mode": settings.sandbox_mode,
        "sandbox_image": settings.sandbox_image,
        "sandbox_executor": executor.__class__.__name__ if executor else None,
        "docker_cli_found": sandbox_info["docker_cli_found"],
        "docker_path": sandbox_info["docker_path"],
        "docker_socket": sandbox_info["docker_socket"],
        "sandbox_image_has_digest": sandbox_info["sandbox_image_has_digest"],
        "sandbox_require_image_digest": sandbox_info["sandbox_require_image_digest"],
        "sandbox_allow_host_network": sandbox_info["sandbox_allow_host_network"],
        "sandbox_workspace_mount_readonly": sandbox_info["sandbox_workspace_mount_readonly"],
        "checks": sandbox_info["checks"],
        "production_ready": sandbox_info["production_ready"],
        "warnings": sandbox_info["warnings"],
        "policy_dir": settings.policy_dir,
        "auth_mode": 'static-keys-plus-bearer-alpha',
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="Constrail Doctor")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    for key, value in payload.items():
        table.add_row(key.replace("_", " ").title(), json.dumps(value) if isinstance(value, list) else str(value))

    console.print(table)
    console.print("\n[bold]Raw config:[/bold]")
    console.print_json(json.dumps(payload))


@cli.command("sandbox-validate", help="Validate whether current sandbox config is production-ready enough for stricter use.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def sandbox_validate_command(as_json: bool):
    payload = sandbox_health()
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    if payload['production_ready']:
        console.print('[green]Sandbox posture looks production-ready.[/green]')
    else:
        console.print('[yellow]Sandbox posture still has warnings.[/yellow]')
    console.print_json(json.dumps(payload))


@cli.command("audit-verify", help="Verify audit hash-chain integrity.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def audit_verify_command(as_json: bool):
    init_db()
    payload = get_audit_verifier().verify()
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("audit-checkpoint", help="Create an audit checkpoint/export summary.")
@click.option("--output", default=None, help="Optional path to write the checkpoint JSON.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def audit_checkpoint_command(output: str | None, as_json: bool):
    init_db()
    payload = create_audit_checkpoint(output)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("audit-list", help="List recent audit records.")
@click.option("--limit", default=10, type=int, help="Maximum number of rows to show.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def audit_list_command(limit: int, as_json: bool):
    init_db()
    db = SessionLocal()
    try:
        rows = db.query(AuditRecordModel).order_by(AuditRecordModel.start_time.desc()).limit(limit).all()
        payload = [{"request_id": str(row.request_id), "tool": row.tool, "decision": row.final_decision.value if hasattr(row.final_decision, 'value') else str(row.final_decision), "agent_id": row.agent_id, "sandbox_id": row.sandbox_id} for row in rows]
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
            table.add_row(row["request_id"], row["tool"], row["decision"], row["agent_id"], row["sandbox_id"] or "-")
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
        rows = db.query(SandboxExecutionModel).order_by(SandboxExecutionModel.created_at.desc()).limit(limit).all()
        payload = [{"sandbox_id": row.sandbox_id, "executor": row.executor, "status": row.status, "tool": row.tool, "approval_id": str(row.approval_id) if row.approval_id else None} for row in rows]
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
            table.add_row(row["sandbox_id"], row["executor"] or "-", row["status"], row["tool"], row["approval_id"] or "-")
        console.print(table)
    finally:
        db.close()


@cli.command("quota-events", help="List persisted quota/rate-limit events.")
@click.option("--agent", "agent_id", default=None, help="Filter by agent ID.")
@click.option("--tenant", "tenant_id", default=None, help="Filter by tenant ID.")
@click.option("--tool", default=None, help="Filter by tool name.")
@click.option("--window-seconds", default=None, type=int, help="Optional recent window filter.")
@click.option("--limit", default=50, type=int, help="Maximum events to return.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def quota_events_command(agent_id: str | None, tenant_id: str | None, tool: str | None, window_seconds: int | None, limit: int, as_json: bool):
    init_db()
    payload = get_rate_limit_service().list_events(agent_id=agent_id, tenant_id=tenant_id, tool=tool, limit_seconds=window_seconds, limit=limit)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("quota-prune", help="Prune old quota/rate-limit events.")
@click.option("--older-than-seconds", required=True, type=int, help="Delete events older than this many seconds.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def quota_prune_command(older_than_seconds: int, as_json: bool):
    init_db()
    payload = get_rate_limit_service().prune_events(older_than_seconds=older_than_seconds)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("quota-summary", help="Show persisted quota/rate-limit event summary.")
@click.option("--agent", "agent_id", default=None, help="Filter by agent ID.")
@click.option("--tenant", "tenant_id", default=None, help="Filter by tenant ID.")
@click.option("--window-seconds", default=None, type=int, help="Optional recent window filter.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def quota_summary_command(agent_id: str | None, tenant_id: str | None, window_seconds: int | None, as_json: bool):
    init_db()
    payload = get_rate_limit_service().summary(agent_id=agent_id, tenant_id=tenant_id, limit_seconds=window_seconds)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("capability-list", help="List stored capability manifests.")
@click.option("--agent", "agent_id", default=None, help="Filter by agent ID.")
@click.option("--active/--all", default=True, help="Filter active manifests only.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def capability_list_command(agent_id: str | None, active: bool, as_json: bool):
    init_db()
    store = get_capability_store()
    rows = store.list_manifests(agent_id=agent_id, active=True if active else None)
    payload = [{"id": row.id, "agent_id": row.agent_id, "tenant_id": row.tenant_id, "namespace": row.namespace, "version": row.version, "active": row.active} for row in rows]
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    table = Table(title="Capability Manifests")
    table.add_column("ID")
    table.add_column("Agent")
    table.add_column("Tenant")
    table.add_column("Namespace")
    table.add_column("Version")
    table.add_column("Active")
    for row in payload:
        table.add_row(str(row["id"]), row["agent_id"], row["tenant_id"] or "-", row["namespace"] or "-", str(row["version"]), str(row["active"]))
    console.print(table)


@cli.command("capability-create", help="Create a capability manifest record.")
@click.option("--agent", "agent_id", required=True, help="Agent identifier.")
@click.option("--tenant", "tenant_id", default=None, help="Tenant identifier.")
@click.option("--namespace", default=None, help="Namespace identifier.")
@click.option("--tool", "tools", multiple=True, required=True, help="Allowed tool name. Repeat for multiple tools.")
@click.option("--activate/--inactive", default=True, help="Whether the new manifest should be active.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def capability_create_command(agent_id: str, tenant_id: str | None, namespace: str | None, tools: tuple[str, ...], activate: bool, as_json: bool):
    init_db()
    store = get_capability_store()
    existing = store.list_manifests(agent_id=agent_id, tenant_id=tenant_id, namespace=namespace)
    next_version = max((row.version for row in existing), default=0) + 1
    row = store.create_manifest(agent_id=agent_id, tenant_id=tenant_id, namespace=namespace, version=next_version, allowed_tools=[{"tool": tool} for tool in tools], active=activate)
    payload = {"id": row.id, "agent_id": row.agent_id, "tenant_id": row.tenant_id, "namespace": row.namespace, "version": row.version, "active": row.active}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"[green]Created capability manifest {row.id} (v{row.version})[/green]")


@cli.command("capability-update-tools", help="Replace the tool set on an existing capability manifest.")
@click.argument("manifest_id", type=int)
@click.option("--tool", "tools", multiple=True, required=True, help="Allowed tool name. Repeat for multiple tools.")
@click.option("--activate", is_flag=True, default=False, help="Activate this manifest after updating tools.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def capability_update_tools_command(manifest_id: int, tools: tuple[str, ...], activate: bool, as_json: bool):
    init_db()
    store = get_capability_store()
    row = store.update_manifest_tools(manifest_id, allowed_tools=[{"tool": tool} for tool in tools], activate=activate)
    if row is None:
        raise click.ClickException("Capability manifest not found")
    payload = {"id": row.id, "agent_id": row.agent_id, "tenant_id": row.tenant_id, "namespace": row.namespace, "version": row.version, "active": row.active, "allowed_tools": row.allowed_tools}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"[green]Updated capability manifest {row.id}[/green]")


@cli.command("capability-activate", help="Activate a capability manifest and deactivate sibling manifests in scope.")
@click.argument("manifest_id", type=int)
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def capability_activate_command(manifest_id: int, as_json: bool):
    init_db()
    store = get_capability_store()
    row = store.activate_manifest(manifest_id)
    if row is None:
        raise click.ClickException("Capability manifest not found")
    payload = {"id": row.id, "agent_id": row.agent_id, "tenant_id": row.tenant_id, "namespace": row.namespace, "version": row.version, "active": row.active}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"[green]Activated capability manifest {row.id}[/green]")


@cli.command("capability-deactivate", help="Deactivate a capability manifest.")
@click.argument("manifest_id", type=int)
def capability_deactivate_command(manifest_id: int):
    init_db()
    store = get_capability_store()
    row = store.deactivate_manifest(manifest_id)
    if row is None:
        raise click.ClickException("Capability manifest not found")
    console.print(f"[yellow]Deactivated capability manifest {row.id}[/yellow]")


@cli.command("capability-bump", help="Create the next version of a capability manifest.")
@click.argument("manifest_id", type=int)
@click.option("--activate/--inactive", default=True, help="Whether the new manifest version should be active.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def capability_bump_command(manifest_id: int, activate: bool, as_json: bool):
    init_db()
    store = get_capability_store()
    row = store.create_next_version(manifest_id, activate=activate)
    if row is None:
        raise click.ClickException("Capability manifest not found")
    payload = {"id": row.id, "agent_id": row.agent_id, "tenant_id": row.tenant_id, "namespace": row.namespace, "version": row.version, "active": row.active}
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"[green]Created capability manifest version {row.version} (id={row.id})[/green]")


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

    payload = [{"approval_id": str(row.approval_id), "tool": row.tool, "agent_id": row.agent_id, "approved": row.approved, "approver_id": row.approver_id, "webhook_delivery_status": getattr(row, 'webhook_delivery_status', 'unknown'), "webhook_delivery_attempts": getattr(row, 'webhook_delivery_attempts', 0)} for row in rows]
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="Approval Requests")
    table.add_column("Approval ID")
    table.add_column("Tool")
    table.add_column("Agent")
    table.add_column("Approved")
    table.add_column("Webhook")
    table.add_column("Attempts")
    for row in payload:
        table.add_row(row["approval_id"], row["tool"], row["agent_id"], str(row["approved"]), row["webhook_delivery_status"], str(row["webhook_delivery_attempts"]))
    console.print(table)


@cli.command("approval-summary", help="Show aggregate approval workflow counts.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_summary_command(as_json: bool):
    init_db()
    service = get_approval_service()
    rows = service.list_requests()
    summary = {
        'total': len(rows),
        'pending': sum(1 for row in rows if row.approved is None),
        'approved': sum(1 for row in rows if row.approved is True),
        'denied': sum(1 for row in rows if row.approved is False),
        'delivered': sum(1 for row in rows if getattr(row, 'webhook_delivery_status', None) == 'delivered'),
        'failed': sum(1 for row in rows if getattr(row, 'webhook_delivery_status', None) == 'failed'),
        'exhausted': sum(1 for row in rows if getattr(row, 'webhook_delivery_status', None) == 'exhausted'),
    }
    if as_json:
        click.echo(json.dumps(summary, indent=2))
        return
    table = Table(title='Approval Summary')
    table.add_column('Metric')
    table.add_column('Count')
    for key, value in summary.items():
        table.add_row(key, str(value))
    console.print(table)


@cli.command("approval-outbox-summary", help="Show approval webhook outbox delivery counts.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_outbox_summary_command(as_json: bool):
    init_db()
    payload = get_approval_service().outbox_summary()
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    table = Table(title='Approval Outbox Summary')
    table.add_column('Metric')
    table.add_column('Count')
    for key, value in payload.items():
        table.add_row(key, str(value))
    console.print(table)


@cli.command("approval-drain-outbox", help="Attempt delivery of pending/failed webhook outbox items.")
@click.option("--limit", default=20, type=int, help="Maximum number of outbox items to process.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_drain_outbox_command(limit: int, as_json: bool):
    init_db()
    payload = get_approval_service().drain_outbox(limit=limit)
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print_json(json.dumps(payload))


@cli.command("approval-run-worker", help="Run a bounded approval outbox worker loop.")
@click.option("--cycles", default=3, type=int, help="Number of polling cycles to run.")
@click.option("--sleep-seconds", default=1.0, type=float, help="Base sleep between cycles.")
@click.option("--limit", default=20, type=int, help="Maximum outbox items to process per cycle.")
@click.option("--backoff-multiplier", default=2.0, type=float, help="Multiplier to apply after idle cycles.")
@click.option("--max-sleep-seconds", default=30.0, type=float, help="Maximum sleep after repeated idle cycles.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_run_worker_command(cycles: int, sleep_seconds: float, limit: int, backoff_multiplier: float, max_sleep_seconds: float, as_json: bool):
    init_db()
    service = get_approval_service()
    totals = service.run_worker(
        cycles=cycles,
        sleep_seconds=sleep_seconds,
        limit=limit,
        backoff_multiplier=backoff_multiplier,
        max_sleep_seconds=max_sleep_seconds,
    )
    if as_json:
        click.echo(json.dumps(totals, indent=2))
        return
    console.print_json(json.dumps(totals))


@cli.command("approval-worker-serve", help="Run the approval outbox worker as a long-running service.")
@click.option("--sleep-seconds", default=1.0, type=float, help="Base sleep between cycles.")
@click.option("--limit", default=20, type=int, help="Maximum outbox items to process per cycle.")
@click.option("--backoff-multiplier", default=2.0, type=float, help="Multiplier applied after idle cycles.")
@click.option("--max-sleep-seconds", default=30.0, type=float, help="Maximum backoff sleep between cycles.")
@click.option("--max-cycles", default=None, type=int, help="Optional max cycles (for testing).")
def approval_worker_serve_command(sleep_seconds: float, limit: int, backoff_multiplier: float, max_sleep_seconds: float, max_cycles: int | None):
    init_db()
    service = get_approval_service()
    cycle = 0
    idle_streak = 0
    current_sleep = sleep_seconds
    console.print("[green]Starting approval worker service. Press Ctrl+C to stop.[/green]")
    try:
        while max_cycles is None or cycle < max_cycles:
            result = service.drain_outbox(limit=limit)
            cycle += 1
            idle = result['idle']
            summary = {
                'cycle': cycle,
                'processed': result['processed'],
                'delivered': result['delivered'],
                'failed': result['failed'],
                'idle': idle,
                'sleep_seconds': round(current_sleep, 2),
            }
            console.print_json(json.dumps(summary))
            if idle:
                idle_streak += 1
                current_sleep = min(max_sleep_seconds, current_sleep * backoff_multiplier if current_sleep else 0)
            else:
                idle_streak = 0
                current_sleep = sleep_seconds
            if current_sleep > 0:
                time.sleep(current_sleep)
    except KeyboardInterrupt:
        console.print("[yellow]Approval worker service stopped.[/yellow]")


@cli.command("approval-show", help="Show a single approval request.")
@click.argument("approval_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_show_command(approval_id: str, as_json: bool):
    init_db()
    service = get_approval_service()
    row = service.get_request(UUID(approval_id))
    if row is None:
        raise click.ClickException("Approval request not found")
    payload = ApprovalRequestResponse.from_db(row).model_dump(mode="json")
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


@cli.command("approval-retry-webhook", help="Retry webhook delivery for an approval request.")
@click.argument("approval_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def approval_retry_webhook_command(approval_id: str, as_json: bool):
    init_db()
    service = get_approval_service()
    row = service.retry_webhook(UUID(approval_id))
    if row is None:
        raise click.ClickException("Approval request not found")
    payload = ApprovalRequestResponse.from_db(row).model_dump(mode="json")
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    console.print(f"[green]Retried webhook for {row.approval_id} ({row.webhook_delivery_status})[/green]")


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
