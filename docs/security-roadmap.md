# Constrails Security Roadmap

This document turns the current security audit into an implementation queue.

## Goal

Move Constrails from strong alpha governance tooling toward a more production-hardened runtime control plane without destroying developer usability.

## Phase 1 - Immediate hardening

### 1. Strict policy availability modes
- Add config for `policy_availability_mode` with values like `dev`, `degraded`, `strict`
- Fail closed for selected high-risk operations when OPA is unavailable in strict mode
- Add tests for unavailable OPA under each mode

### 2. Approval replay binding
- Add approval expiry
- Store policy version/hash and capability manifest version at approval time
- Re-check bounded trust conditions before replay

### 3. Standalone approval worker mode
- Promote current worker-loop behavior into a more explicit long-running mode
- Add retry/backoff strategy
- Expose basic metrics or status summaries
- Status: bounded worker mode now has richer idle/backoff summaries, but a dedicated standalone service/daemon model still remains

## Phase 2 - Identity maturity

### 4. Key registry support
- Add key IDs
- Distinguish active vs previous keys
- Bound legacy key acceptance window

### 5. Token and auth observability
- Record token ID/auth type in audit metadata where appropriate
- Improve CLI visibility for active/previous secrets and revocation state

### 6. Static key de-emphasis
- Make production posture docs recommend bearer/managed auth over static keys
- Add stronger warnings when production-like mode still uses dev static keys

## Phase 3 - Sandbox enforcement

### 7. Strict sandbox enforcement mode
- Fail execution when posture checks do not meet minimum requirements in strict mode
- Add docs and tests around strict vs advisory posture modes

### 8. Deployment target validation matrix
- Linux CI validation
- Docker host variants
- optional rootless or alternative runtime notes/tests

## Phase 4 - Deeper forensic confidence

### 9. Audit integrity improvements
- append-only or signed event chain
- stronger replay / outbox / token correlation metadata
- Status: hash-chain groundwork and verification CLI now exist; signed checkpoints and stronger append-only guarantees remain

### 10. Approval/webhook authenticity
- signed webhooks
- delivery IDs and deduplication semantics

## Phase 5 - Adversarial behavior resistance

### 11. Anti-exfiltration chaining detection
- session-level or workflow-level policy checks across multiple actions
- detect suspicious file-read + outbound-network or similar combinations

### 12. Rate limiting / quota controls
- per-agent and per-tenant rate limits
- approval generation throttles
- sandbox/exec resource controls beyond current posture checks
- Status: durable quota events, summaries, scoped thresholds, enforcement modes, event inspection, and prune controls now exist; deeper per-event-class controls and longer-horizon policy tuning remain

## Guiding Principle

Do not trade away the core value proposition — external execution-time governance — for complicated security machinery that makes the system unusable. Prefer simple, explicit, measurable hardening steps with tests.
