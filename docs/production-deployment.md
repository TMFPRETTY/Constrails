# Constrails Production Deployment Guide

Constrails is now in beta, and it is ready for production-oriented pilots when deployed with care. This guide documents the current best practices for running Constrails outside of development.

## 1. Overview

Constrails acts as an external runtime governance layer for AI agents. A production deployment should treat Constrails like any other critical control-plane component:

- run it on a hardened host or cluster
- use a production-grade database (Postgres recommended)
- secure secrets and approval webhooks
- monitor health, quota activity, approvals, and sandbox posture
- plan for upgrade/migration and audit retention

## 2. Prerequisites

### Supported baseline

- Linux host or Kubernetes cluster with hardened configuration
- Python 3.10 or 3.11
- Docker runtime (for Docker sandbox enforcement) or equivalent sandbox executor
- Postgres 16 recommended for production, Postgres 13+ supported for operator-managed deployments
- OPA server (optional but recommended) for live policy evaluation

### Deployment modes

Currently supported and documented:
- single-host VM deployment
- container deployment
- Kubernetes-style deployment patterns (operator-managed, not yet a packaged Helm distribution)

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
- Apply migrations before each deployment with `constrail db-upgrade`.
- Use a staging environment to validate upgrades before touching production.
- Enable TLS or run inside a trusted network segment.
- Backup regularly; treat Constrails audit/quota tables as sensitive records.

### Supported upgrade posture

For the current beta:
- forward upgrades are the supported path
- always back up the database before applying migrations
- test new releases against a staging copy of production data when possible
- if a deployment fails after migration, restore from backup rather than assuming automatic downgrade safety

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

## 12. Backup, Restore, and Upgrade Procedures

### Backup guidance

- Backup the Postgres database regularly (daily increments, weekly full).
- Treat approval, audit, quota, token, and capability records as operationally important state.
- Export audit checkpoints periodically with `constrail audit-checkpoint --json` and archive them outside the primary database.

### Restore guidance

- Restore to a fresh Postgres instance or isolated recovery database first.
- Run `constrail db-current --database-url <restored-dsn>` to confirm migration state.
- Run `constrail audit-verify --json` against the restored environment before promoting it.
- Validate approval summary, quota summary, and admin metrics before returning traffic.

### Upgrade procedure

1. Backup DB.
2. Roll out the new application image/package to staging.
3. Apply migrations with `constrail db-upgrade --revision head --database-url <dsn>`.
4. Run post-upgrade smoke checks:
   - `constrail db-current --database-url <dsn>`
   - `constrail audit-verify --json`
   - `constrail quota-summary --json`
   - `constrail approval-summary --json`
5. Redeploy API and worker.
6. Watch `/metrics` and admin metrics for regressions.

### Rollback posture

- Application rollback without DB rollback is only safe when the prior version is compatible with the migrated schema.
- Database rollback should be handled by restoring from backup unless a release explicitly documents a safe downgrade path.
- Treat restore-based rollback as the default supported recovery path in beta.

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
- broader multi-version upgrade-path validation
- stronger operator runbooks and alert packs
- deeper approval-worker durability guidance
- signed or externally anchored audit checkpoints
- session-level exfiltration detection

Document updates will follow as these features land.

## 15. Support / Feedback

- Open issues or pull requests on the GitHub repo
- Join the Constrails / OpenClaw community discussions
- Share production learnings to help shape the roadmap

---

This guide will evolve as Constrails moves through beta and beyond. Treat it as living documentation and update it as you deploy.
