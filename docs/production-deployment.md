# Constrails Production Deployment Guide

Constrails is still an early beta, but it is ready for production-oriented pilots when deployed with care. This guide documents the current best practices for running Constrails outside of development.

## 1. Overview

Constrails acts as an external runtime governance layer for AI agents. A production deployment should treat Constrails like any other critical control-plane component:

- run it on a hardened host or cluster
- use a production-grade database (Postgres recommended)
- secure secrets and approval webhooks
- monitor health, quota activity, approvals, and sandbox posture
- plan for upgrade/migration and audit retention

## 2. Prerequisites

- Linux host or Kubernetes cluster with hardened configuration
- Python 3.10+ runtime or container-based deployment
- Docker runtime (for Docker sandbox enforcement) or equivalent sandbox executor
- Postgres 13+ (recommended) for the Constrails database
- OPA server (optional but recommended) for live policy evaluation

## 3. Configuration Checklist

Key environment settings for production:

| Setting | Purpose | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Postgres connection string | Use managed Postgres or hardened self-hosted instance |
| `SECRET_KEY` | Bearer token signing key | Rotate regularly; never use dev default |
| `PREVIOUS_SECRET_KEY` | Prior signing key | Optional, only during rotation windows |
| `TOKEN_ISSUER` / `TOKEN_AUDIENCE` | Bearer token validation | Set to company-specific values |
| `OPA_URL` | Policy evaluation endpoint | Required for strict mode |
| `POLICY_AVAILABILITY_MODE` | `degraded` or `strict` | Use `strict` in production if OPA is reliable |
| `SANDBOX_TYPE` / `SANDBOX_MODE` | Sandbox behavior | Use Docker-based or hardened executor |
| `SANDBOX_REQUIRE_IMAGE_DIGEST` | Enforce image pinning | Must be `true` in production |
| `APPROVAL_WEBHOOK_URL` | Notification endpoint | Use HTTPS endpoint with auth |
| `APPROVAL_WEBHOOK_SECRET` | HMAC signing secret | Required when webhook URL configured |
| `RATE_LIMIT_TOOL_THRESHOLDS` / `RATE_LIMIT_TENANT_THRESHOLDS` | Scoped quota controls | Configure realistic thresholds per tool/tenant |
| `RATE_LIMIT_ENFORCEMENT_MODE` | `quarantine`, `approval_required`, or `sandbox` | Choose enforcement strategy |

## 4. Database (Postgres) Guidance

- Create a dedicated Postgres database and user for Constrails.
- Apply migrations before each deployment (Alembic recommended).
- Enable TLS or run inside a trusted network segment.
- Backup regularly; treat Constrails audit/quota tables as sensitive records.

Example DSN:
```
DATABASE_URL=postgresql+psycopg2://constrail_user:strong-password@db-host/constrail_prod
```

## 5. Secrets & Credentials

- Store secrets (token signing keys, webhook secrets, DB passwords) in a secrets manager or encrypted env files.
- Rotate signing keys using `constrail auth-rotate-secret` and update production deployments promptly.
- Do not use dev static keys (`dev-agent`, `dev-admin`) in production.

## 6. Sandbox Posture

- Prefer Docker-based sandbox (`SANDBOX_TYPE=docker`, `SANDBOX_MODE=production`).
- Enforce image digest pinning (`SANDBOX_REQUIRE_IMAGE_DIGEST=true`).
- Disable host networking for sandbox containers.
- Consider rootless Docker or alternative sandbox executors for stronger isolation.
- Run `constrail sandbox-validate --json` and ensure `production_ready=true` before exposing to agents.

## 7. Policy & Capability Files

- Manage capability manifests and policy bundles via version control or internal GitOps pipelines.
- Keep policy bundles synchronized between OPA and fallback logic.
- Use scoped capability manifests (tenant + namespace) to avoid cross-tenant leakage.
- Document the process for updating policy/capability files and redeploying.

## 8. Approval Workflow in Production

- Configure `APPROVAL_WEBHOOK_URL` with an authenticated HTTPS endpoint.
- Use the bounded worker command (`constrail approval-run-worker` or future service mode) as a long-lived process.
- Monitor webhook delivery status via `constrail approval-summary` and the admin API.
- Set `APPROVAL_WEBHOOK_MAX_ATTEMPTS` to match the reliability expectations of the receiving system.

## 9. Quota & Rate Limits

- Define scoped thresholds in `RATE_LIMIT_TOOL_THRESHOLDS` and `RATE_LIMIT_TENANT_THRESHOLDS` JSON settings.
- Choose enforcement mode per environment: `quarantine`, `approval_required`, or `sandbox`.
- Use `constrail quota-summary`, `constrail quota-events`, and `constrail quota-prune` to inspect and maintain quota data.
- Expose admin quota endpoints (`/v1/admin/quotas`, `/v1/admin/quota-events`) with proper auth.

## 10. Monitoring & Observability

Recommended metrics and logs:
- Approval queue depth, delivered/failed counts
- Quota hits per tool/tenant
- Policy availability (OPA health)
- Sandbox posture warnings/failures
- Audit verification results
- Worker loop metrics (processed/delivered/failed/idle cycles)

Integrate with Prometheus or log analytics where possible. Until a native metrics endpoint ships, capture logs from CLI commands and admin APIs.

## 11. Deployment Patterns

### Single-host
- Install Constrails in a Python venv or container on a hardened VM.
- Use systemd or supervisor to run: API server, approval worker, OPA, Docker daemon.

### Container/Kubernetes
- Build/pull the Constrails container image.
- Deploy API pod + OPA sidecar (or external OPA service).
- Use stateful set or managed Postgres for DB.
- Run approval worker as a separate deployment/job.
- Mount policy/capability files via ConfigMap/Secret.

## 12. Backup & Upgrade Procedures

- Backup the Postgres database regularly (daily increments, weekly full).
- Export audit checkpoints periodically (once implemented).
- Before upgrades:
  1. Backup DB
  2. Apply migrations
  3. Redeploy API and worker
  4. Run smoke tests (`constrail audit-verify`, `constrail quota-summary`, `constrail approval-summary`)

## 13. Security Checklist

- [ ] Postgres DSN configured; migrations applied
- [ ] Secrets stored in secrets manager
- [ ] Sandbox posture `production_ready=true`
- [ ] OPA reachable; policy availability mode set to `strict`
- [ ] Token signing keys rotated from dev defaults
- [ ] Approval webhooks configured with HTTPS + secret
- [ ] Quota thresholds defined per tool/tenant
- [ ] Worker loop/service running continuously
- [ ] Audit verification CLI run after major changes
- [ ] Monitoring alerts set up for approvals/quota/policy availability

## 14. Future Enhancements (Roadmap Alignment)

As Constrails approaches GA, expect additional improvements in:
- Postgres-first migrations (Alembic)
- Dedicated approval worker service
- Metrics endpoint
- Signed audit checkpoints
- Session-level exfiltration detection

Document updates will follow as these features land.

## 15. Support / Feedback

- Open issues or pull requests on the GitHub repo
- Join the Constrails / OpenClaw community discussions
- Share production learnings to help shape the roadmap

---

This guide will evolve as Constrails moves through beta and beyond. Treat it as living documentation and update it as you deploy.
