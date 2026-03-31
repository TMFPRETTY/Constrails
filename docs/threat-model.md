# Constrail Threat Model

## Introduction

This document describes the threat model for Constrail, an Agent Safety System. It identifies the assets, trust boundaries, potential attackers, and the specific threats the system is designed to mitigate.

## Assets

1. **Agent execution environment** – the sandbox where agents run.
2. **Tool broker** – the service that mediates all tool calls.
3. **Policy engine** – the component that evaluates actions against policies.
4. **Audit logs** – immutable records of all agent actions and decisions.
5. **Capability manifests** – documents that define what each agent is allowed to do.
6. **Approval queue** – pending actions that require human review.
7. **Self‑modification pipeline** – workflows for agent‑proposed code changes.
8. **Admin credentials** – keys/tokens used to administer Constrail.
9. **Secrets** – credentials, API keys, and other sensitive data that agents may need to use (but not exfiltrate).

## Trust Boundaries

- **Agent ↔ Constrail Kernel** – agents are untrusted; the kernel is trusted.
- **Kernel ↔ Tool Broker** – internal trusted communication.
- **Tool Broker ↔ External services** – external services are partially trusted; the broker enforces policies before calling them.
- **Policy Engine ↔ Policy storage** – policies are trusted, but may be misconfigured.
- **Audit Logger ↔ Storage** – audit logs must be tamper‑evident; storage is trusted.
- **Admin CLI ↔ Kernel API** – admin actions are authenticated and authorized.

## Potential Attackers

1. **Malicious agents** – agents that actively try to escape containment, escalate privileges, exfiltrate data, or disrupt the system.
2. **Compromised agents** – otherwise benign agents that have been subverted via prompt injection, compromised tools, or supply‑chain attacks.
3. **Insider threats** – human operators with legitimate access who misuse the system.
4. **External attackers** – attackers who attempt to compromise the Constrail infrastructure (network attacks, software vulnerabilities).
5. **Supply‑chain attackers** – attackers who inject malicious code into agent‑generated patches or dependencies.

## Threat Scenarios

### T1: Prompt Injection
- **Description**: An attacker injects hidden instructions into the agent’s input, attempting to override its intended behavior.
- **Mitigation**: Constrail does not rely on prompt‑based trust. All actions are evaluated by the kernel based on the agent’s identity, context, and policy—not on the agent’s self‑reported intent.

### T2: Tool Misuse
- **Description**: An agent uses a tool in a way that violates policy (e.g., reading a file it shouldn’t, making an unauthorized API call).
- **Mitigation**: All tool calls go through the Tool Broker, which enforces capability‑based permissions and policy rules before executing the call.

### T3: Unauthorized Filesystem Access
- **Description**: An agent attempts to read, write, or delete files outside its allowed scope.
- **Mitigation**: The Tool Broker virtualizes filesystem access, presenting only allowed directories. Sandbox execution ensures the agent cannot escape the container.

### T4: Unauthorized API Calls
- **Description**: An agent tries to call an external API endpoint that is not permitted.
- **Mitigation**: The Tool Broker maintains an allow‑list of API endpoints per agent, validates parameters, and can inject rate‑limiting, authentication tokens, and audit headers.

### T5: Data Exfiltration
- **Description**: An agent attempts to send sensitive data outside the controlled environment (e.g., via HTTP, email, or hidden channels).
- **Mitigation**: All outbound communication is brokered. The policy engine can block messages containing sensitive data patterns (e.g., credit‑card numbers, secrets). Network egress from the sandbox is restricted.

### T6: Memory Leakage Between Tasks
- **Description**: An agent retains information from a previous task that should be isolated.
- **Mitigation**: Memory Guard enforces isolation between tasks, either by wiping memory between invocations or by using separate sandbox instances.

### T7: Secrets Exposure
- **Description**: An agent accidentally or intentionally logs, transmits, or stores secrets.
- **Mitigation**: Secrets are never passed directly to the agent; they are injected at tool‑call time by the broker. Audit logs are redacted automatically. Secret scanning is applied to agent‑generated code.

### T8: Privilege Escalation
- **Description**: An agent attempts to gain higher privileges, e.g., by modifying its own capability manifest or calling admin APIs.
- **Mitigation**: Capability manifests are immutable at runtime. Admin APIs require separate authentication and are not exposed to agents. Self‑modification proposals are evaluated by the kernel and require human approval.

### T9: Recursive or Runaway Agent Spawning
- **Description**: An agent spawns child agents without limit, exhausting resources.
- **Mitigation**: The kernel tracks agent genealogy and enforces spawning quotas. Each child agent inherits the parent’s capabilities (or stricter). Resource limits are enforced per agent tree.

### T10: Policy Evasion
- **Description**: An agent finds a way to bypass policy evaluation, e.g., by using a tool in an unexpected way or combining allowed actions to achieve a disallowed outcome.
- **Mitigation**: Policy engine supports rich contextual rules (e.g., “agent may read file A only if it hasn’t written to file B in the last 5 minutes”). Anomaly detection looks for unusual patterns of behavior.

### T11: Malicious or Unintended Self‑Modification
- **Description**: An agent tries to modify its own code, dependencies, or configuration in a harmful way.
- **Mitigation**: Self‑Modification Controller requires a multi‑step workflow: patch creation, rationale, tests, policy validation, static analysis, sandbox validation, optional second‑agent review, human approval, and rollback support. Direct code writes are blocked.

### T12: Supply‑Chain Attacks via Agent‑Generated Code
- **Description**: An agent proposes a code change that introduces a backdoor or vulnerability.
- **Mitigation**: Static analysis, dependency scanning, and sandbox validation are performed before approval. Changes are reviewed by a separate “auditor” agent (optional) and a human.

### T13: Compromised Tool Adapters
- **Description**: A tool adapter (the component that translates agent requests into actual tool executions) is malicious or buggy, allowing unauthorized actions.
- **Mitigation**: Tool adapters run with least privilege, are sandboxed, and are subject to the same policy evaluation as agents. Adapter code is signed and verified.

### T14: Denial of Service
- **Description**: An agent (or attacker) floods the kernel with requests, causing service degradation.
- **Mitigation**: Rate limiting, request quotas, and queue management are enforced per agent. Low‑priority requests can be throttled or dropped.

### T15: Audit Log Tampering
- **Description**: An attacker attempts to alter or delete audit logs to cover their tracks.
- **Mitigation**: Audit logs are written to an append‑only, cryptographically‑signed store (e.g., a secure ledger). Logs are streamed to a separate, hardened service.

### T16: Kernel Subversion
- **Description**: An attacker exploits a vulnerability in the Constrail kernel itself to take control of the safety system.
- **Mitigation**: The kernel is kept minimal, written in a memory‑safe language where possible, regularly audited, and run with minimal privileges. It is isolated from the agents (e.g., runs in a separate container).

## Security Assumptions

1. The kernel, policy engine, and tool broker are correctly implemented and free of critical vulnerabilities.
2. The underlying containerization (Docker, gVisor, etc.) provides strong isolation.
3. Admin credentials are kept secure and are not leaked to agents.
4. The audit log storage is physically separate from the execution environment and is tamper‑evident.
5. Human approvers are trustworthy and will not approve malicious actions without review.

## Non‑Goals

- Protecting against physical attacks on the hardware.
- Preventing all zero‑day exploits in the underlying OS or container runtime.
- Stopping malicious insiders with full admin access (though audit logs will record their actions).
- Guaranteeing safety of agent actions that are allowed by policy (policy may be wrong).

## Open Questions

- How to handle non‑deterministic agent actions (e.g., network timing) during replay?
- Should the kernel support real‑time policy updates without restarting agents?
- How to delegate approval authority to other automated systems (e.g., a CI/CD pipeline)?