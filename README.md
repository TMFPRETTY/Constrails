# Constrails

![Alpha](https://img.shields.io/badge/status-alpha-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-33%20passing-brightgreen)
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
- capability-based allow/deny checks
- heuristic risk scoring with bootstrap risk profiles
- policy evaluation with built-in fallback when OPA is unavailable
- sample OPA policy assets and package layout under `policies/rego/`
- tool broker with filesystem, HTTP, and exec adapters
- approval request lifecycle and approval API endpoints
- local SQLite-backed audit, approval, and sandbox execution persistence for development
- path, domain, and command constraints in capability manifests
- sandbox-first exec behavior with a development sandbox executor
- Docker sandbox path verified on host and hardened for safer execution defaults
- a first-class `constrail` CLI entrypoint
- read-only admin inspection endpoints for audit and sandbox history
- filtered admin queries and JSON CLI output for operational workflows
- deployment examples for Docker Compose + OPA sidecar flow
- automated test coverage for the current MVP spine

Still under active development:
- production-grade approval UX
- verified production-grade containerized sandbox execution defaults for broader deployment targets
- richer multi-tenant capability lifecycle management
- deeper OPA policy coverage beyond the sample bundle
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
- `src/constrail/risk/risk_engine.py` - heuristic risk scoring
- `src/constrail/policy/policy_engine.py` - OPA integration with built-in fallback
- `src/constrail/approval.py` - approval persistence and state transitions
- `src/constrail/sandbox.py` - sandbox executor abstraction and implementations
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
- filesystem adapter base path: current repository working directory

These defaults are intentionally optimized for local bring-up, not for final production deployment.

### Optional sandbox selection

Development default is `dev`.

If Docker is available, you can opt in before starting the API:

```bash
export SANDBOX_TYPE=docker
# optional if Docker is on a non-default socket
export DOCKER_SOCKET=unix:///var/run/docker.sock
```

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

For development reload:

```bash
constrail serve --host 127.0.0.1 --port 8011 --reload
```

### Inspect runtime configuration

```bash
constrail doctor
constrail doctor --json
```

### Approval management

```bash
constrail approval-list --limit 10
constrail approval-list --limit 10 --json
constrail approval-show <approval_id>
constrail approval-approve <approval_id> --approver tmfpretty --comment "approved"
constrail approval-deny <approval_id> --approver tmfpretty --comment "denied"
```

### Audit and sandbox inspection

```bash
constrail audit-list --limit 10
constrail audit-list --limit 10 --json
constrail sandbox-list --limit 10
constrail sandbox-list --limit 10 --json
```

If you are running without editable install, use the module form:

```bash
PYTHONPATH=src python -m constrail.cli doctor --json
PYTHONPATH=src python -m constrail.cli init-db
PYTHONPATH=src python -m constrail.cli approval-list --limit 10 --json
PYTHONPATH=src python -m constrail.cli audit-list --limit 10 --json
PYTHONPATH=src python -m constrail.cli sandbox-list --limit 10 --json
PYTHONPATH=src python -m constrail.cli serve --host 127.0.0.1 --port 8011
```

## Bootstrap policy files

Included bootstrap files:
- `policies/capabilities/dev-agent.json`
- `policies/tool_risk_profiles.json`
- `policies/rego/constrail/allow.rego`
- `policies/examples/input-example.json`

The included assets demonstrate:
- scoped filesystem access
- constrained HTTP destinations
- constrained command execution
- approval-required handling for risky tools
- a sample OPA package layout and input shape

## Operator workflow example

A typical local development workflow looks like this:

1. initialize the database
2. start the API
3. submit a request that requires approval
4. inspect pending approvals
5. approve or deny the request
6. inspect audit history and sandbox execution history

Example:

```bash
constrail init-db
constrail serve --host 127.0.0.1 --port 8011
# in another shell:
constrail approval-list --limit 10 --json
constrail audit-list --limit 10 --json
constrail sandbox-list --limit 10 --json
```

## Quick Start

### 1. Initialize the development database

```bash
constrail init-db
```

### 2. Start the API

```bash
constrail serve --host 127.0.0.1 --port 8011
```

### 3. Smoke test the API

```bash
python - <<'PY'
import json, urllib.request

payload = {
    'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
    'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
    'context': {'goal': 'smoke test'}
}
req = urllib.request.Request(
    'http://127.0.0.1:8011/v1/action',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-agent'}
)
with urllib.request.urlopen(req) as r:
    print(r.read().decode())
PY
```

## API Overview

### Health

- `GET /health`

### Action execution

- `POST /v1/action`

Example request:

```json
{
  "agent": {"agent_id": "placeholder", "trust_level": 0.8},
  "call": {"tool": "read_file", "parameters": {"path": "README.md"}},
  "context": {"goal": "read the project README"}
}
```

### Approval flow

- `GET /v1/approval`
- `GET /v1/approval/{approval_id}`
- `POST /v1/approval/{approval_id}/approve`
- `POST /v1/approval/{approval_id}/deny`
- `POST /v1/approval/{approval_id}/replay`

Example approval-triggering request:

```json
{
  "agent": {"agent_id": "placeholder", "trust_level": 0.8},
  "call": {"tool": "exec", "parameters": {"command": "echo hello"}},
  "context": {"goal": "test approval path"}
}
```

Example approve payload:

```json
{
  "approver_id": "tmfpretty",
  "comment": "approved for development test"
}
```

### Admin inspection

- `GET /v1/admin/audit`
- `GET /v1/admin/audit/{request_id}`
- `GET /v1/admin/sandbox`
- `GET /v1/admin/sandbox/{sandbox_id}`

Supported audit query parameters:
- `limit`
- `offset`
- `agent_id`
- `tool`
- `decision`
- `approval_id`
- `sandbox_id`

Supported sandbox query parameters:
- `limit`
- `offset`
- `agent_id`
- `tool`
- `executor`
- `status`
- `approval_id`

These endpoints expose read-only visibility into:
- recent audit records
- replay provenance
- approval linkage
- sandbox execution history

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
- FastAPI smoke path
- approval request lifecycle
- capability constraints
- exec adapter sandbox behavior
- sandbox executor selection and replay flow
- audit and sandbox provenance linkage for approved replays
- admin inspection endpoints
- CLI command surface
- approval management CLI
- JSON CLI output
- policy engine fallback and local explanation behavior

## Changelog

See `CHANGELOG.md` for milestone history.

## Contributing

See `CONTRIBUTING.md`.

## Security

See `SECURITY.md`.

## Safety Note

Current development defaults are intentionally permissive enough to enable local bring-up.
Do not mistake the dev SQLite path, local filesystem base path, fallback policy mode, or dev sandbox executor for the intended final production deployment posture.

## License

See `LICENSE`.
