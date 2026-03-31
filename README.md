# Constrails

![Alpha](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-57%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

Constrails is an **Agent Safety System**: an external runtime governance and containment layer for AI agents.

Instead of trusting an agent to self-regulate, Constrails routes meaningful actions through a safety kernel that can:

- identify the agent
- validate capabilities
- score risk
- evaluate policy
- allow, deny, require approval, sandbox, or quarantine
- broker tool execution
- record auditable outcomes

## Current Status

Constrails currently provides a working **development MVP spine** for governed agent execution.

Available today:
- canonical kernel path (`kernel_v2.py`) behind FastAPI (`kernel.py`)
- capability-based allow/deny checks with tenant/namespace-aware manifest lookup
- capability manifest persistence, versioning, activation/deactivation, mutation, and CLI lifecycle commands
- heuristic risk scoring with bootstrap risk profiles
- policy evaluation with built-in fallback when OPA is unavailable
- expanded starter OPA policy bundle plus OPA-response contract tests
- tool broker with filesystem, HTTP, and exec adapters
- approval request lifecycle, status model, replay flow, webhook delivery tracking, and retry hooks
- local SQLite-backed audit, approval, sandbox execution, and capability persistence for development
- path, domain, and command constraints in capability manifests
- sandbox-first exec behavior with a development sandbox executor
- Docker sandbox path hardened with clearer production-posture reporting
- a first-class `constrail` CLI entrypoint
- read-only admin inspection endpoints for audit, sandbox, and capability history
- filtered admin queries and scoped admin semantics for operational workflows
- basic admin/agent auth separation with dual static keys for alpha use
- deployment examples for Docker Compose + OPA sidecar flow
- automated test coverage for the current MVP spine

Still under active development:
- production-grade approval UX and durable delivery guarantees
- verified production-grade containerized sandbox execution defaults across broader deployment targets
- stronger identity/auth primitives beyond static alpha keys
- deeper OPA integration coverage against live policy services
- broader package distribution ergonomics

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
- `src/constrail/risk/risk_engine.py` - heuristic risk scoring
- `src/constrail/policy/policy_engine.py` - OPA integration with built-in fallback
- `src/constrail/approval.py` - approval persistence, status, webhook delivery tracking, and retry helpers
- `src/constrail/auth.py` - alpha auth principal and role helpers
- `src/constrail/sandbox.py` - sandbox executor abstraction, posture reporting, and implementations
- `src/constrail/sandbox_records.py` - sandbox execution persistence helpers
- `src/constrail/database.py` - development database models and session management
- `src/constrail/cli.py` - CLI entrypoint for local operations

## Repository Layout

```text
src/constrail/           application code
policies/                bootstrap capability profiles, risk profiles, and OPA policy assets
deploy/                  deployment examples and environment templates
tests/                   supported automated tests
archive/obsolete-tests/  archived scratch tests kept for reference
examples/                reserved for future examples
scripts/                 reserved for future tooling
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
python -m pip install -e .
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
python -m pip install fastapi uvicorn httpx sqlalchemy psycopg2-binary pydantic pydantic-settings click rich pytest pytest-asyncio
export PYTHONPATH=src
```

Then run the CLI module directly:

```bash
python -m constrail.cli --help
```

### Container build

A basic application image can be built from the included Dockerfile:

```bash
docker build -t constrails:alpha .
```

Run it:

```bash
docker run --rm -p 8000:8000 constrails:alpha
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
- auth mode: dual static keys for alpha (`agent_api_key`, `admin_api_key`)
- approval webhooks: optional, with delivery tracking and manual retry support

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

Use `constrail doctor --json` to inspect whether the current sandbox posture looks production-ready.

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
constrail auth-status
constrail auth-status --json
```

`doctor --json` now exposes sandbox posture fields such as:
- `sandbox_mode`
- `sandbox_image_has_digest`
- `sandbox_require_image_digest`
- `sandbox_allow_host_network`
- `sandbox_workspace_mount_readonly`
- `production_ready`
- `warnings`

### Approval management

```bash
constrail approval-list --limit 10
constrail approval-list --limit 10 --json
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

### Audit and sandbox inspection

```bash
constrail audit-list --limit 10 --json
constrail sandbox-list --limit 10 --json
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

These endpoints expose read-only visibility into:
- recent audit records
- replay provenance
- approval linkage
- sandbox execution history
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
- approval request lifecycle, webhook delivery tracking, and auth boundaries
- capability constraints and lifecycle management
- exec adapter sandbox behavior
- sandbox executor selection, posture reporting, and replay flow
- audit and sandbox provenance linkage
- admin inspection endpoints
- CLI command surface and JSON output
- policy engine fallback, explanation behavior, and OPA-response contract coverage

## Changelog

See `CHANGELOG.md` for milestone history.

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

Current development defaults are intentionally permissive enough to enable local bring-up. Do not mistake the dev SQLite path, local filesystem base path, fallback policy mode, or dual static auth keys for the intended final production deployment posture.

## License

See `LICENSE`.
