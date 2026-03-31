# Constrails

Constrails is an **Agent Safety System**: an external runtime governance and containment layer for AI agents.

Instead of trusting an agent to self-regulate, Constrails forces meaningful actions through a safety kernel that can:

- identify the agent
- validate capabilities
- score risk
- evaluate policy
- allow, deny, require approval, sandbox, or quarantine
- broker tool execution
- record auditable outcomes

## Current Status

This repository now contains a working **development MVP spine**.

Working today:
- canonical kernel path (`kernel_v2.py`) behind FastAPI (`kernel.py`)
- capability-based allow/deny checks
- risk scoring with bootstrap risk profiles
- policy evaluation with built-in fallback when OPA is unavailable
- tool broker with filesystem, HTTP, and exec adapters
- local SQLite-backed audit and approval persistence for development
- approval request API endpoints
- passing automated test suite for the current spine

Not finished yet:
- production-grade approval UX
- sandboxed exec enforcement
- rich capability constraints (path/domain/command allowlists)
- live OPA policy bundle management
- polished packaging/install workflow

## Architecture Overview

Request flow:

`Agent -> Kernel -> Capability Check -> Risk -> Policy -> Decision -> Broker -> Audit`

Core components in this repo:

- `src/constrail/kernel_v2.py` - canonical request lifecycle
- `src/constrail/kernel.py` - FastAPI API wrapper
- `src/constrail/tool_broker/broker.py` - tool dispatch and execution modes
- `src/constrail/capability/manager.py` - capability manifest loading and checks
- `src/constrail/risk/risk_engine.py` - heuristic risk scoring
- `src/constrail/policy/policy_engine.py` - OPA integration with builtin fallback
- `src/constrail/approval.py` - approval persistence and state changes
- `src/constrail/database.py` - development DB models/session

## Repository Layout

```text
src/constrail/           application code
policies/                bootstrap capability and risk profiles
tests/                   supported automated tests
archive/obsolete-tests/  old scratch tests kept for reference
examples/                reserved for future examples
scripts/                 reserved for future tooling
```

## Development Defaults

For local development, the repo currently defaults to:

- database: `sqlite:///./constrail-dev.db`
- policy fallback: builtin simple policy if OPA is unavailable
- filesystem adapter base path: current repository working directory

This is intentionally developer-friendly and not the final production posture.

## Bootstrap Policy Files

Current bootstrap files:

- `policies/capabilities/dev-agent.json`
- `policies/tool_risk_profiles.json`

The included `dev-agent` manifest allows basic development-time flows and still routes risky actions like `exec`, `http_request`, and writes into approval-required handling.

## Running Locally

### 1. Use the project virtualenv if available

This repo already has a `.venv` in the workspace. If it exists, prefer it.

```bash
source .venv/bin/activate
```

### 2. Ensure dependencies are present

If the environment is missing packages, install them with the interpreter for your venv.

```bash
python -m pip install fastapi uvicorn httpx sqlalchemy psycopg2-binary pydantic pydantic-settings pytest pytest-asyncio
```

Note: editable install via `pip install -e .` may require a newer local packaging toolchain than the system Python currently provides.

### 3. Initialize the development database

```bash
PYTHONPATH=src python - <<'PY'
from constrail.database import init_db
init_db()
print('db initialized')
PY
```

### 4. Start the API

Use module form for uvicorn if the shell entrypoint is missing.

```bash
PYTHONPATH=src python -m uvicorn constrail.kernel:app --host 127.0.0.1 --port 8011
```

### 5. Smoke test the API

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

## API Endpoints

### Health

- `GET /health`

### Action execution

- `POST /v1/action`

Example request:

```json
{
  "agent": {"agent_id": "placeholder", "trust_level": 0.8},
  "call": {"tool": "read_file", "parameters": {"path": "README.md"}},
  "context": {"goal": "read the project readme"}
}
```

### Approval flow

- `GET /v1/approval`
- `GET /v1/approval/{approval_id}`
- `POST /v1/approval/{approval_id}/approve`
- `POST /v1/approval/{approval_id}/deny`
- `POST /v1/approval/{approval_id}/replay`

Example approval request creation:

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

## Running Tests

Use the workspace venv if present.

```bash
.venv/bin/python -m pytest -q tests
```

Current suite covers:
- kernel happy paths
- fail-closed behavior
- broker dispatch
- filesystem adapter behavior
- FastAPI smoke path
- approval request lifecycle

## What to Push

Yes, I think it is reasonable to start pushing code now, but with one caveat:

**Push this as an MVP spine milestone, not as "production-ready."**

That means the next commit/PR should clearly describe:
- canonical kernel cleanup
- broker/adapter contract unification
- dev SQLite bring-up
- bootstrap policy/capability files
- test suite cleanup and passing coverage
- initial approval flow endpoints

That is enough real substance to justify pushing.

## Recommended Next Milestones

1. tighten approval replay semantics so approved requests can execute without re-entering approval
2. add path/domain/command constraints to capability manifests
3. enforce sandbox execution for `exec`
4. improve audit records with approver linkage and replay provenance
5. support real OPA bundles/policies
6. clean up packaging/install flow for editable installs

## Safety Note

Current development defaults are intentionally permissive enough to enable local bring-up.
Do not mistake the dev SQLite path, local filesystem base path, or fallback policy mode for the intended final production deployment posture.
