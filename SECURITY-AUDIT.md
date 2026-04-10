# Constrails Security Audit

_Date:_ 2026-03-31  
_Status:_ beta security sweep  
_Scope:_ full-system adversarial review of identity, authorization, kernel lifecycle, tool brokering, sandboxing, policy evaluation, approval workflows, auditability, tenant isolation, API/CLI surfaces, and delivery operations.

## Executive Summary

Constrails is now meaningfully safer than uncontrolled direct tool access for agents. It externalizes key execution-time controls including capability checks, policy enforcement, sandbox routing, approvals, audit logging, and scoped admin/operator access.

The major remaining security risks are no longer about the whole concept being porous; they are now concentrated in production-hardening areas:

- fallback-policy mismatch or degraded-mode abuse
- approval replay and delivery edge cases
- token/key lifecycle maturity
- Docker sandbox overtrust
- audit tamperability in local/dev-backed storage
- chained exfiltration via otherwise individually-authorized actions

## Top Threats

1. Policy fallback mismatch abuse
2. Capability manifest confusion / identity mismatch
3. Approval workflow race / replay abuse
4. Audit tampering in local/dev storage
5. Approval outbox abuse / notification degradation
6. Docker sandbox overtrust or misconfiguration
7. Tool-broker exfiltration chaining
8. Static key compromise
9. Token lifecycle weakness
10. Multi-tenant isolation leakage
11. Resource exhaustion / approval flood DoS
12. Dependency / supply chain compromise
13. Policy drift between rego and fallback
14. Replay / correlation gaps
15. CLI/operator misuse risk

## High-Priority Findings

### 1. Policy fallback remains a critical trust boundary
If OPA is unavailable or misconfigured, fallback logic becomes enforcement source. Drift between rego and fallback semantics remains one of the most important residual risks.

**Recommended actions:**
- add strict policy-availability mode
- fail closed for selected high-risk operations when OPA is unavailable
- continuously test rego/fallback parity for covered decision classes

**Performance impact:** low

### 2. Approval replay needs tighter context binding
Replay should not depend only on approval ID. It should bind to more of the original trust context.

**Recommended actions:**
- bind replay to approval expiry
- include policy hash/version and capability manifest version in approval records
- re-check key trust invariants before replaying

**Performance impact:** low-medium

### 3. Approval outbox is better, but not yet a full standalone service
The current outbox, drain, auto-drain, signed delivery, and bounded worker mode with richer summaries/backoff materially improve reliability, but this is still not a dedicated durable worker service.

**Recommended actions:**
- standalone worker mode/service
- retry backoff/jitter
- delivery idempotency semantics
- webhook signing/authentication

**Performance impact:** medium

### 4. Token lifecycle has improved, but key management is still early
Bearer auth now includes issuer/audience validation, revocation, key registry visibility, and a basic secret rotation bridge. That is solid beta-stage progress, but not mature key management.

**Recommended actions:**
- key IDs (`kid`)
- active/previous key registry
- retirement windows
- clearer issuance policy
- stronger operator visibility into active key state

**Performance impact:** low

### 5. Sandbox posture is much more inspectable, but not universally validated
Sandbox posture checks are stronger and more explicit now, and strict posture enforcement exists, but Docker-based isolation should still be treated carefully.

**Recommended actions:**
- strict enforcement mode when posture checks fail
- broader environment validation matrix
- stronger image pinning and deployment examples
- evaluate seccomp/apparmor/rootless/runtime-specific hardening

**Performance impact:** low-medium

## Zero-Trust Improvements

- separate human-admin identities from machine-agent identities
- bind capabilities to tenant + namespace + agent + auth identity
- add session-scoped temporary capabilities where appropriate
- reduce reliance on static keys in real deployments
- treat replay as a fresh trust decision with bounded reuse
- isolate approval delivery processing from the request hot path

## Audit / Forensics Review

### Strengths
- approval and sandbox linkage exists
- replay provenance exists
- audit auth-correlation metadata exists
- audit hash-chain verification now exists
- quota event visibility now exists
- audit surfaces are substantially better than an ungoverned system

### Remaining weaknesses
- local SQLite is still easy to tamper with
- append-only / signed audit chain is not yet default
- stronger correlation between token ID, approval event, outbox item, and replay path would still help investigations further
- quota/event retention policy is still early and not yet policy-rich by event class

## Performance-Aware Security Design Notes

- keep webhook delivery off the hot path where possible
- cache manifest resolution and stable policy metadata
- avoid blocking on OPA when degraded mode is known
- rate-limit abusive actors rather than slowing all traffic
- precompute posture and policy bundle metadata where practical

## Top 10 Immediate Fixes

1. Strict policy availability modes
2. Approval replay expiry + trust binding
3. Standalone approval worker/service
4. Signed/authenticated webhook delivery
5. Key ID and key registry support
6. Auth/token metadata in audit records
7. Anti-exfil chaining detection across request sequences
8. Enforced strict sandbox mode
9. Per-tenant / per-agent rate limiting and quotas
10. Signed or append-only audit chain

## Recommended Next Implementation Order

### Phase 1
- strict policy availability mode
- approval replay expiry/context binding
- standalone approval worker mode

### Phase 2
- signed webhook delivery
- key ID / key registry support
- auth metadata in audit records

### Phase 3
- enforced strict sandbox mode
- tenant/agent rate limits
- broader environment validation matrix

### Phase 4
- append-only/signed audit chain
- session-level exfiltration/chaining detection
- deeper multi-scenario live OPA CI matrix

## Release-Bar Perspective

For GA, the main remaining security bar is not proving the concept. That part is already established. The remaining bar is operational trust:

- documented production assumptions
- no unresolved high-severity security issues
- operator-ready key, audit, and sandbox guidance
- clear known limitations
- repeatable upgrade and recovery procedures

## Bottom Line

Constrails now materially improves agent safety and security compared with uncontrolled agent tool access. The remaining work is primarily production hardening, reliability, and trust-boundary strengthening, not proof that the model of external runtime governance is unsound.
