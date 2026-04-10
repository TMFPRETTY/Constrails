# Constrails

![GA](https://img.shields.io/badge/status-ga-success)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-100%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

Constrails is a **general-availability Agent Safety System**: an external runtime governance and containment layer for AI agents.

Instead of trusting an agent to self-regulate, Constrails routes meaningful actions through a safety kernel that can:

- identify the agent
- validate capabilities
- score risk
- evaluate policy
- allow, deny, require approval, sandbox, or quarantine
- broker tool execution
- record auditable outcomes

## Current Status

Constrails now provides a **GA baseline** for governed agent execution with documented production deployment, operations, and support posture.

Available today:
- canonical kernel path (`kernel_v2.py`) behind FastAPI (`kernel.py`)
- capability-based allow/deny checks with tenant/namespace-aware manifest lookup
- capability manifest persistence, versioning, activation/deactivation, mutation, and CLI lifecycle commands
- heuristic risk scoring with bootstrap risk profiles, cross-request exfiltration chain heuristics, durable quota event tracking, scoped quota thresholds, quota enforcement modes, and burst-rate controls
- policy evaluation with explicit degraded/strict availability modes when OPA is unavailable
- expanded starter OPA policy bundle plus OPA-response contract tests and local/CI compose smoke coverage
- tool broker with filesystem, HTTP, and exec adapters
- approval request lifecycle, status model, replay flow, webhook delivery tracking, retry hooks, attempt exhaustion tracking, an approval webhook outbox model, optional in-process auto-drain controls, and a bounded worker mode with richer summaries/backoff behavior
- local SQLite-backed audit, approval, sandbox execution, token revocation, capability, and quota-event persistence for development, with cross-dialect GUID handling for safer SQLite portability
- path, domain, and command constraints in capability manifests
- sandbox-first exec behavior with a development sandbox executor
- Docker sandbox path hardened with clearer production-posture reporting and local compose smoke validation
- a first-class `constrail` CLI entrypoint
- read-only admin inspection endpoints for audit, sandbox, capability history, quota visibility/event inspection, and metrics
- filtered admin queries and scoped admin semantics for operational workflows
- basic admin/agent auth separation with legacy static keys plus a stricter bearer-token auth path with issuer/audience validation, token revocation, key registry visibility, and a basic secret-rotation bridge
- deployment examples for Docker Compose + OPA sidecar flow, including a serialized local smoke script
- automated test coverage for the current MVP spine

## Current limitations and next hardening areas

Constrails is now GA, but GA does not mean every surrounding operational concern is fully maximized. These areas still have room to mature:

- **Approval operations:** an outbox model, drain command, optional in-process auto-drain, signed delivery, and a bounded worker mode with richer idle/backoff summaries now exist, but this is still not a full standalone asynchronous worker/service.
- **Sandbox validation breadth:** Docker posture and local smoke coverage are stronger, but broader validation across more deployment targets is still warranted.
- **Identity/auth lifecycle:** bearer tokens now support issuer/audience validation, revocation, and a basic rotation bridge, but stronger issuance and key-management lifecycle controls can still mature further.
- **OPA live integration depth:** local and CI live-path smoke coverage exists, but richer live-policy assertions across more decision classes can still deepen confidence.
- **Distribution ergonomics:** install and release flows are better than they were, but broader packaging/distribution polish is still possible.
- **Storage/migrations:** Alembic baseline migrations and DB operator commands now exist, CI validates migrations against Postgres, and production backup/restore and upgrade guidance now exist, but broader multi-version upgrade validation can still mature further.

## Why Constrails

Prompting alone is not a sufficient safety boundary for autonomous systems. Constrails moves control into infrastructure by enforcing policy at execution time.

This project is designed around a few core principles:
- external enforcement over prompt-based trust
- least privilege and explicit capabilities
- fail-closed defaults where practical
- auditable actions and replayable decisions
- no direct tool access outside the broker

## Architecture Overview

Request flow:

`Agent -> Kernel -> Capability Check -> Risk -> Policy -> Decision -> Broker -> Audit`

Core components in this repository:

- `src/constrail/kernel_v2.py` - canonical request lifecycle
- `src/constrail/kernel.py` - FastAPI API wrapper
- `src/constrail/tool_broker/broker.py` - tool dispatch and execution modes
- `src/constrail/capability/manager.py` - capability manifest loading and checks
- `src/constrail/capability_store.py` - capability manifest persistence and lifecycle helpers
- `src/constrail/risk/risk_engine.py` - heuristic risk scoring, exfiltration-chain detection, and quota/burst anomaly hooks
- `src/constrail/policy/policy_engine.py` - OPA integration with built-in fallback
- `src/constrail/approval.py` - approval persistence, status, signed webhook delivery tracking, retry, exhaustion, outbox helpers, optional auto-drain hooks, and bounded worker-mode helpers
- `src/constrail/auth.py` - auth principal model, static-key auth, bearer-token helpers, revocation support, key registry visibility, and secret-rotation bridging
- `src/constrail/sandbox.py` - sandbox executor abstraction, posture reporting, and implementations
- `src/constrail/sandbox_records.py` - sandbox execution persistence helpers
- `src/constrail/database.py` - development database models, cross-dialect GUID persistence, quota event storage, and session management
- `src/constrail/cli.py` - CLI entrypoint for local operations, audit verification, and quota inspection/pruning

## Repository Layout

```text
src/constrail/           application code
policies/                bootstrap capability profiles, risk profiles, and OPA policy assets
deploy/                  deployment examples and environment templates
tests/                   supported automated tests
archive/obsolete-tests/  archived scratch tests kept for reference
examples/                reserved for future examples
scripts/                 local smoke and helper tooling
.github/workflows/       CI workflow definitions
```

## Installation

### Prerequisites

Recommended:
- Python 3.10+
- a virtual environment
- Docker (optional, for sandboxed command execution and Compose deployment)
- OPA (optional, for live policy evaluation)

### Option 1: Local checkout with editable install

```bash
git clone https://github.com/TMFPRETTY/Constrails.git
cd Constrails
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
```

After installation, the CLI should be available as:

```bash
constrail --help
```

### Option 2: Local checkout without editable install

If editable install is not available in your environment yet, install runtime dependencies directly and use the module path:

```bash
git clone https://github.com/TMFPRETTY/Constrails.git
cd Constrails
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn httpx sqlalchemy psycopg2-binary pydantic pydantic-settings click rich pytest pytest-asyncio python-jose[cryptography]
export PYTHONPATH=src
```

Then run the CLI module directly:

```bash
python -m constrail.cli --help
```

### Container build

A basic application image can be built from the included Dockerfile:

```bash
docker build -t constrails:1.0.0 .
```

Run it:

```bash
docker run --rm -p 8000:8000 constrails:1.0.0
```

## Configuration

A sample environment file is included at:

- `.env.example`

Copy it to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

Current development defaults:
- database: `sqlite:///./constrail-dev.db`
- policy fallback: built-in simple policy if OPA is unavailable
- sandbox type: `dev`
- sandbox mode: `development`
- filesystem adapter base path: current repository working directory
- auth mode: legacy static keys plus a stricter bearer-token path (`agent_api_key`, `admin_api_key`, `Authorization: Bearer ...`)
- approval webhooks: optional, with delivery tracking, retry support, outbox state, auto-drain controls, bounded worker-mode support, attempt limits, and HMAC signing
- quotas: persisted quota events, scoped thresholds, configurable enforcement mode, summary/event inspection, and prune controls
- observability: admin metrics snapshot, Prometheus-style `/metrics`, and audit checkpoint/export summaries

These defaults are intentionally optimized for local bring-up, not for final production deployment.

### Optional sandbox selection

Development default is `dev`.

If Docker is available, you can opt in before starting the API:

```bash
export SANDBOX_TYPE=docker
export SANDBOX_MODE=production
export SANDBOX_REQUIRE_IMAGE_DIGEST=true
export DOCKER_SOCKET=unix:///var/run/docker.sock
```

Use `constrail doctor --json` or `constrail sandbox-validate --json` to inspect whether the current sandbox posture looks production-ready.

### Optional OPA selection

If OPA is available, you can point Constrails at a live policy server:

```bash
export OPA_URL=http://localhost:8181
export OPA_POLICY_PACKAGE=constrail
opa run --server ./policies/rego
```

If OPA is not available, Constrails falls back to its built-in development policy logic.

## Deployment examples

A starter deployment example is included under:

- `deploy/compose/docker-compose.yml`

This stack demonstrates:
- Constrails API service
- OPA sidecar service
- Compose-based environment configuration via `deploy/compose/.env.example`

Quick start:

```bash
cd deploy/compose
cp .env.example .env
docker compose up --build
```

For a serialized local smoke run that brings the stack up, validates the live Constrails → OPA path, and tears the stack down cleanly:

```bash
bash scripts/run_compose_opa_smoke.sh
```

See `deploy/README.md` for details.

## CLI Usage

Constrails provides a CLI for local development and basic operational workflows.

### Initialize the database

```bash
constrail init-db
```

### Run the API server

```bash
constrail serve --host 127.0.0.1 --port 8011
```

### Inspect runtime and auth configuration

```bash
constrail doctor
constrail doctor --json
constrail sandbox-validate --json
constrail auth-status
constrail auth-status --json
constrail auth-keys --json
```

Agent and admin requests can still use `X-API-Key`, and bearer tokens are also supported via `Authorization: Bearer <token>`.

### Local bearer token workflows

```bash
constrail auth-mint-token --role agent --subject local-agent --tenant default --namespace dev --agent-id dev-agent --json
constrail auth-inspect-token <token> --json
constrail auth-revoke-token <token> --json
constrail auth-rotate-secret --json
constrail audit-verify --json
constrail audit-checkpoint --json
constrail quota-summary --json
constrail quota-events --json
constrail quota-prune --older-than-seconds 86400 --json
```

`doctor --json` and `sandbox-validate --json` expose sandbox posture fields such as:
- `sandbox_mode`
- `sandbox_image_has_digest`
- `sandbox_require_image_digest`
- `sandbox_allow_host_network`
- `sandbox_workspace_mount_readonly`
- `checks`
- `production_ready`
- `warnings`

### Approval management

```bash
constrail approval-list --limit 10
constrail approval-list --limit 10 --json
constrail approval-summary --json
constrail approval-outbox-summary --json
constrail approval-drain-outbox --limit 20 --json
constrail approval-run-worker --cycles 3 --sleep-seconds 1 --limit 20 --backoff-multiplier 2 --max-sleep-seconds 30 --json
constrail approval-show <approval_id> --json
constrail approval-approve <approval_id> --approver tmfpretty --comment "approved"
constrail approval-deny <approval_id> --approver tmfpretty --comment "denied"
constrail approval-retry-webhook <approval_id> --json
constrail approval-replay <approval_id> --json
```

`approval-show` and `approval-list --json` expose delivery visibility, including:
- `webhook_delivery_status`
- `webhook_delivery_attempts`
- `webhook_last_attempt_at`
- `webhook_last_response_code`
- `webhook_last_error`

### Capability lifecycle management

```bash
constrail capability-list --json
constrail capability-create --agent demo --tenant default --namespace dev --tool read_file --tool list_directory --json
constrail capability-update-tools 1 --tool read_file --tool http_request --json
constrail capability-bump 1 --inactive --json
constrail capability-activate 2 --json
constrail capability-deactivate 2
```

### Audit, sandbox, and quota inspection

```bash
constrail audit-list --limit 10 --json
constrail audit-verify --json
constrail audit-checkpoint --json
constrail sandbox-list --limit 10 --json
constrail quota-summary --json
constrail quota-events --limit 20 --json
constrail quota-prune --older-than-seconds 86400 --json
```

## API Overview

### Health
- `GET /health`

### Action execution
- `POST /v1/action`

### Approval flow
- `GET /v1/approval`
- `GET /v1/approval/{approval_id}`
- `POST /v1/approval/{approval_id}/approve`
- `POST /v1/approval/{approval_id}/deny`
- `POST /v1/approval/{approval_id}/replay`

Approval responses include delivery visibility for webhook-backed operator notifications.

### Admin inspection
- `GET /v1/admin/audit`
- `GET /v1/admin/audit/{request_id}`
- `GET /v1/admin/sandbox`
- `GET /v1/admin/sandbox/{sandbox_id}`
- `GET /v1/admin/capabilities`
- `GET /v1/admin/metrics`
- `GET /metrics`
- `GET /v1/admin/quotas`
- `GET /v1/admin/quota-events`

These endpoints expose read-only visibility into:
- recent audit records
- replay provenance
- approval linkage
- auth correlation metadata
- audit hash-chain fields
- sandbox execution history
- quota summaries and raw quota event inspection
- stored capability manifest records

## Bootstrap policy files

Included bootstrap files:
- `policies/capabilities/dev-agent.json`
- `policies/tool_risk_profiles.json`
- `policies/rego/constrail/allow.rego`
- `policies/examples/input-example.json`

## Testing

Run the supported suite with the project virtualenv if present:

```bash
.venv/bin/python -m pytest -q tests
```

Current test coverage includes:
- kernel happy paths
- fail-closed behavior
- broker dispatch
- filesystem adapter behavior
- approval request lifecycle, signed webhook delivery tracking, retry, exhaustion behavior, outbox operator flows, optional auto-drain controls, and bounded worker-mode behavior
- capability constraints and lifecycle management
- exec adapter sandbox behavior
- sandbox executor selection, posture reporting, and replay flow
- audit and sandbox provenance linkage
- audit auth-correlation metadata and hash-chain linkage
- exfiltration-chain heuristics, durable quota tracking, scoped thresholds, quota enforcement modes, and quota inspection/pruning
- admin inspection endpoints
- CLI command surface and JSON output
- policy engine fallback, explanation behavior, richer OPA-response contract coverage, and compose-based live OPA smoke coverage

## Changelog

See `CHANGELOG.md` for milestone history.

## Production readiness references

For operator-facing production guidance, see:
- `docs/production-deployment.md`
- `docs/operations-guide.md`
- `docs/support-matrix.md`
- `docs/known-limitations.md`
- `docs/ga-checklist.md`
- `SECURITY-AUDIT.md`
- `docs/security-roadmap.md`
- `RELEASE.md`

## Contributing

See `CONTRIBUTING.md`.

## Security

See `SECURITY.md`.

## Alpha release

A draft alpha release note is included at:

- `.github/release-notes/0.1.0-alpha.md`

Suggested tag:

- `v0.1.0-alpha`

See `RELEASE.md` and `.github/release-checklist.md` for release workflow guidance.

## Safety Note

Current development defaults are intentionally permissive enough to enable local bring-up. Do not mistake the dev SQLite path, local filesystem base path, fallback policy mode, or dev bearer/static auth paths for the intended final production deployment posture.

## License

See `LICENSE`.
