# Constrail Project Definition

## Overview

Constrail is an open source Agent Safety System—a runtime governance and containment platform for AI agents. It acts as an external control plane that intercepts, evaluates, and enforces policy on every meaningful action an agent attempts, ensuring agents operate within strict boundaries.

**Publisher brand**: by TMFPRETTY

**Core purpose**: prevent agents from exceeding their authority, violating scope, misusing tools, exfiltrating data, self‑modifying unsafely, or acting outside policy boundaries.

## Why External Enforcement Matters

Prompt‑based trust is brittle and easily subverted. Constrail shifts safety out of the prompt and into the infrastructure, applying zero‑trust principles to autonomous software.

## Positioning

- **OPA for agents** – a declarative policy engine that governs agent actions  
- **Zero‑trust runtime** – every action is authenticated, authorized, and audited  
- **Service mesh for agent actions** – a sidecar‑like broker that mediates all tool calls  
- **Control plane for governed autonomy** – enables safe, scalable agent deployments  

## Product Principles

1. **External enforcement over prompt‑based trust** – safety is not a prompt engineering problem.  
2. **Default deny for high‑risk actions** – unless explicitly allowed, actions are blocked.  
3. **Explicit capabilities, no hidden permissions** – agents receive a capability manifest; they cannot exceed it.  
4. **Least privilege everywhere** – each agent gets the minimal set of rights needed for its task.  
5. **Fail closed when possible** – if the safety kernel cannot decide, it denies.  
6. **Human in the loop for protected operations** – certain actions (e.g., self‑modification, external API calls) require explicit approval.  
7. **Reversible changes** – all agent‑driven modifications can be rolled back.  
8. **Strong observability and replayability** – every decision is logged; any execution can be replayed.  
9. **Immutable or tamper‑evident audit records** – logs are cryptographically signed or append‑only.  
10. **Clear separation between proposing and finalizing changes** – agents can propose, but cannot finalize protected changes.  
11. **No silent privilege escalation** – any attempt to expand capabilities is detected and blocked.  
12. **No direct tool access outside the broker** – all tool calls flow through the Constrail Tool Broker.

## Target Users

- **AI platform engineers** who need to deploy agents in production with safety guarantees.  
- **Security teams** responsible for governance of autonomous systems.  
- **Open‑source maintainers** building agent frameworks that require runtime safety.  
- **Enterprises** using AI agents for sensitive workflows (finance, healthcare, legal).  

## Scope

Constrail is not:

- A prompt‑engineering library  
- A fine‑tuning or alignment tool  
- An AI model itself  
- A replacement for model‑level safety measures  

Constrail is:

- A runtime enforcement layer that sits between agents and the world  
- A policy engine that evaluates actions against a declarative policy  
- A broker that mediates all tool calls, memory access, and external communication  
- An audit system that records every decision and action  

## Success Metrics

- **Policy coverage** – percentage of agent actions that pass through the kernel  
- **Decision latency** – median time from action request to decision  
- **False positive/negative rates** – how often safe actions are blocked or unsafe actions allowed  
- **Audit completeness** – whether every action is logged with sufficient context  
- **Integration ease** – time to integrate a new agent framework with Constrail  

## Roadmap

### Phase 1 (MVP)
- Kernel with basic policy engine  
- Tool broker for a small set of tools (filesystem, HTTP, exec)  
- Risk engine with simple scoring  
- Approval flow (human in the loop)  
- Sandbox execution (Docker‑based)  
- Audit logging (structured, immutable)  
- Self‑update via pull request (no direct code modification)  
- Example integration with a popular agent framework (e.g., LangChain, AutoGPT)  
- Basic anomaly detection (threshold‑based)  
- CLI for administration  

### Phase 2 (Production)
- Advanced policy language (Rego‑like)  
- Multi‑tenant support  
- High‑availability deployment  
- Performance optimizations (caching, parallel evaluation)  
- Plugin system for custom risk scorers, sandboxes, log sinks  
- Real‑time anomaly detection (ML‑based)  
- Integration with secret managers (Vault, AWS Secrets Manager)  
- Support for more agent frameworks  

### Phase 3 (Enterprise)
- Federated policy management  
- Compliance reporting (SOC2, HIPAA, GDPR)  
- Hardware‑backed audit logging (TEEs)  
- Fine‑grained capability delegation  
- Cross‑agent communication controls  
- Supply‑chain security for agent‑generated code  

## License

Open source (see LICENSE).