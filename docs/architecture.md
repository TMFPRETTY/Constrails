# Constrail MVP Architecture

## Overview

The Minimum Viable Product (MVP) of Constrail is a monolithic service (for simplicity) that implements the core safety kernel, policy engine, tool broker, risk engine, approval service, sandbox execution, audit logging, and basic anomaly detection. It is designed to be deployed as a single container with a PostgreSQL database and a Redis queue.

## High‑Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent (untrusted)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Framework  │  │ Framework  │  │ Framework  │            │
│  │ (LangChain)│  │ (AutoGPT)  │  │ (Custom)   │            │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
└────────┼────────────────┼────────────────┼──────────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│               Constrail Kernel (HTTP/gRPC API)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Request Interceptor                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────┐  │
│  │  Context   │  │   Risk     │  │  Policy    │  │Capab│  │
│  │ Enrichment │  │  Engine    │  │  Engine    │  │Mgr  │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┘  │
│        │                │                │                  │
│        ▼                ▼                ▼                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Decider                           │  │
│  │ (allow/deny/approval/sandbox/quarantine)             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Tool Broker                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────┐  │
│  │ Filesystem │  │   HTTP     │  │   Exec     │  │ ... │  │
│  │  Adapter   │  │  Adapter   │  │  Adapter   │  │     │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┘  │
└────────┼────────────────┼────────────────┼──────────────────┘
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │Local    │    │External │    │Sandboxed│
    │Files    │    │APIs     │    │Process  │
    └─────────┘    └─────────┘    └─────────┘
```

## Components

### 1. Kernel
The central entry point for all agent actions. It exposes an HTTP/gRPC API that agent frameworks call instead of directly invoking tools.

**Responsibilities**:
- Authenticate the agent (via API key or token)
- Parse the action request (tool name, parameters)
- Enrich the request with agent identity, session context, previous actions
- Pass the enriched request through the risk engine, policy engine, and capability manager
- Make a final decision (allow, deny, require approval, sandbox, quarantine)
- If allowed, forward to the Tool Broker; if denied, return an error; if approval needed, place in approval queue
- Log the decision and request to the audit log

### 2. Policy Engine
Evaluates the enriched request against a set of declarative policies. Policies are written in a Rego‑like language (OPA‑compatible) and can reference agent attributes, request parameters, historical context, and external data.

**MVP policies**:
- Allow/deny based on tool name
- Allow/deny based on parameter values (e.g., file paths must be within `/workspace`)
- Rate limiting (max N calls per minute)
- Sequence constraints (e.g., “cannot read after write”)
- Human‑approval required for certain tools or parameter patterns

### 3. Risk Engine
Assigns a numeric risk score to each request based on heuristics.

**MVP risk factors**:
- Tool criticality (pre‑defined weights)
- Parameter sensitivity (e.g., paths containing “secret”, “key”, “password”)
- Agent trust level (new agents have higher risk)
- Recent anomaly detection alerts
- Time of day (optional)

If risk score exceeds a threshold, the request may be routed to approval queue or sandboxed.

### 4. Capability Manager
Stores and validates each agent’s capability manifest—a JSON document that lists the tools the agent is allowed to call, with optional constraints.

**Example manifest**:
```json
{
  "agent_id": "langchain‑agent‑1",
  "allowed_tools": [
    {"tool": "read_file", "constraints": {"path_prefix": "/workspace/data/"}},
    {"tool": "http_get", "constraints": {"domain": "api.example.com"}},
    {"tool": "execute", "constraints": {"command_allowlist": ["ls", "cat"]}}
  ]
}
```

### 5. Tool Broker
Executes the actual tool call after the kernel allows it. Each tool has an adapter that translates the generic tool call into the specific operation.

**MVP adapters**:
- **Filesystem**: read_file, write_file, list_directory (virtualized to a sandbox directory)
- **HTTP**: http_get, http_post (with headers, body, timeout)
- **Execute**: run a shell command in a sandboxed container

Adapters run with least privilege (e.g., filesystem adapter runs as a non‑root user, HTTP adapter uses a dedicated network namespace).

### 6. Approval Service
Manages a queue of actions that require human approval. Provides a CLI and web interface for reviewers to approve or deny requests.

**MVP approval flow**:
1. Request is placed in the `pending_approvals` table.
2. Admin is notified (via webhook, email, or CLI poll).
3. Admin reviews the request context (agent, tool, parameters, risk score).
4. Admin approves or denies; if approved, the action is re‑submitted to the kernel for execution.

### 7. Sandbox Executor
Provides isolated execution environments for risky actions or for validating self‑modification patches.

**MVP sandbox**: Docker container with resource limits, read‑only root filesystem except for a temporary `/workspace` volume. The container is destroyed after each use.

### 8. Audit Logger
Writes structured, immutable records of every kernel decision and every tool execution.

**Audit record fields**:
- `timestamp`, `agent_id`, `session_id`, `request_id`
- `tool`, `parameters`, `risk_score`, `policy_decision`
- `final_decision`, `approver_id` (if applicable), `sandbox_id` (if used)
- `outcome` (success/failure), `result` (truncated if large), `duration_ms`

Logs are written to PostgreSQL and optionally streamed to a secure object store (e.g., S3 with versioning).

### 9. Anomaly Detector
Monitors audit logs in real time and raises alerts when unusual patterns appear.

**MVP anomalies**:
- Burst of tool calls from a single agent
- Calls to tools the agent has never used before
- Failed authorization attempts
- High‑risk tools used in quick succession

### 10. Self‑Modification Controller
Orchestrates the workflow for agent‑proposed code changes.

**MVP workflow**:
1. Agent submits a patch (diff) and a rationale.
2. Kernel validates that the patch does not modify protected files (e.g., kernel code, policy definitions).
3. Static analysis runs (e.g., security linters).
4. Patch is applied in a sandbox and integration tests are run.
5. If tests pass, a pull request is created in the upstream Git repository.
6. Human reviews and merges the PR.
7. After merge, the new code is deployed (outside Constrail’s scope).

### 11. Admin API & CLI
Allows administrators to manage agents, policies, capabilities, and approval queues.

**MVP CLI commands**:
- `constrail agent list`
- `constrail policy validate <file>`
- `constrail approval list`
- `constrail approval approve <id>`
- `constrail logs tail`

## Data Flow

1. **Agent calls Constrail Kernel** with `{tool: "read_file", params: {path: "/workspace/data.txt"}}`.
2. **Kernel** authenticates agent, enriches request with agent’s identity and session context.
3. **Risk Engine** computes risk score (e.g., 0.2).
4. **Policy Engine** evaluates policies; returns `allow`.
5. **Capability Manager** verifies agent is allowed to call `read_file` on paths under `/workspace/data/`.
6. **Decider** combines inputs: risk low, policy allows, capability matches → decision = `allow`.
7. **Audit Logger** writes `decision=allow` record.
8. **Tool Broker** receives allowed request, invokes Filesystem Adapter.
9. **Filesystem Adapter** reads the file (within sandbox directory) and returns content.
10. **Audit Logger** writes `execution` record with result.
11. **Kernel** returns result to agent.
12. **Anomaly Detector** scans new audit records; no anomaly detected.

## Deployment

### Single‑Container Deployment (MVP)
- **Container**: `constrail:latest` (Python + FastAPI)
- **Database**: PostgreSQL (persistent volume)
- **Queue**: Redis (optional, for async approval notifications)
- **Sandbox**: Docker‑in‑Docker (DinD) or mounting Docker socket (security trade‑offs)

### Configuration
Environment variables:
- `CONSTRAIL_DATABASE_URL`
- `CONSTRAIL_REDIS_URL`
- `CONSTRAIL_SANDBOX_TYPE` (docker, gvisor, none)
- `CONSTRAIL_SECRET_KEY` (for signing audit logs)

## Integration with Agent Frameworks

Provide an SDK or middleware that wraps the framework’s tool‑calling mechanism.

**Example LangChain integration**:
```python
from langchain.tools import BaseTool
from constrail_sdk import ConstrailClient

class ConstrailTool(BaseTool):
    def _run(self, tool_name: str, **kwargs):
        client = ConstrailClient(api_key=...)
        return client.execute(tool_name, **kwargs)
```

Replace each native tool with a Constrail‑wrapped version.

## Next Steps

1. Implement kernel API (FastAPI app)
2. Define database schema (SQLAlchemy models)
3. Build tool adapters (filesystem, HTTP, exec)
4. Implement policy engine (OPA integration or custom)
5. Create approval queue (PostgreSQL table + CLI)
6. Add sandbox execution (Docker SDK)
7. Write audit logging (structured, signed)
8. Develop example integration (LangChain)
9. Create CLI tool (Click or Typer)
10. Write comprehensive tests (unit, integration, security)