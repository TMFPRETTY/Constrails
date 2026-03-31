# Constrails

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
- tool broker with filesystem, HTTP, and exec adapters
- approval request lifecycle and approval API endpoints
- local SQLite-backed audit, approval, and sandbox execution persistence for development
- path, domain, and command constraints in capability manifests
- sandbox-first exec behavior with a development sandbox executor
- opt-in Docker sandbox executor path
- automated test coverage for the current MVP spine

Still under active development:
- production-grade approval UX
- verified production-grade containerized sandbox execution
- richer multi-tenant capability lifecycle management
- live OPA policy bundle management
- polished package/CLI distribution workflow

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
- `src/constrail/database.py` - development database models and session management

## Repository Layout

```text
src/constrail/           application code
policies/                bootstrap capability and risk profiles
tests/                   supported automated tests
archive/obsolete-tests/  archived scratch tests kept for reference
examples/                reserved for future examples
scripts/                 reserved for future tooling
```

## Installation

## Prerequisites

Recommended:
- Python 3.10+
- a virtual environment
- Docker (optional, for future/opt-in container sandbox execution)

## Option 1: Run from a local checkout

```bash
git clone https://github.com/TMFPRETTY/Constrails.git
cd Constrails
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn httpx sqlalchemy psycopg2-binary pydantic pydantic-settings pytest pytest-asyncio
```

Because the packaging/CLI workflow is still being polished, the most reliable current launch path is module-based:

```bash
PYTHONPATH=src python -m uvicorn constrail.kernel:app --host 127.0.0.1 --port 8011
```

## Option 2: Editable install

Editable install may work depending on your local Python packaging toolchain.
If your environment supports modern `pyproject.toml` editable installs, try:

```bash
python -m pip install -e .
```

If that fails on an older system Python, use **Option 1** for now.

## CLI and service startup

Constrails does **not** yet ship a polished standalone CLI binary or console script.

For now, professional/reliable usage is:
- run the API server with `python -m uvicorn`
- interact with it over HTTP
- run tests with `pytest`

Current launch command:

```bash
PYTHONPATH=src python -m uvicorn constrail.kernel:app --host 127.0.0.1 --port 8011
```

## Configuration

Current development defaults:
- database: `sqlite:///./constrail-dev.db`
- policy fallback: built-in simple policy if OPA is unavailable
- sandbox type: `dev`
- filesystem adapter base path: current repository working directory

These defaults are intentionally optimized for local bring-up, not for final production deployment.

### Optional sandbox selection

Development default is `dev`.

If Docker becomes available, you can opt in before starting the API:

```bash
export SANDBOX_TYPE=docker
# optional if Docker is on a non-default socket
export DOCKER_SOCKET=unix:///var/run/docker.sock
```

If Docker is not running or not reachable, keep the default dev sandbox.

## Bootstrap policy files

Included bootstrap files:
- `policies/capabilities/dev-agent.json`
- `policies/tool_risk_profiles.json`

The included `dev-agent` manifest supports local development and demonstrates:
- scoped filesystem access
- constrained HTTP destinations
- constrained command execution
- approval-required handling for risky tools

## Quick Start

### 1. Initialize the development database

```bash
PYTHONPATH=src python - <<'PY'
from constrail.database import init_db
init_db()
print('db initialized')
PY
```

### 2. Start the API

```bash
PYTHONPATH=src python -m uvicorn constrail.kernel:app --host 127.0.0.1 --port 8011
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

## Safety Note

Current development defaults are intentionally permissive enough to enable local bring-up.
Do not mistake the dev SQLite path, local filesystem base path, fallback policy mode, or dev sandbox executor for the intended final production deployment posture.

## License

See `LICENSE`.
