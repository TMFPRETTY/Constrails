# Constrails Support Matrix

This document defines the intended support posture as Constrails moves from beta toward GA.

## Current beta support baseline

### Runtime
- Python 3.10
- Python 3.11

### Database
- SQLite for local development and testing
- Postgres 13+ for operator-managed deployments
- Postgres 16 recommended for production-oriented deployments

### Deployment modes
- single-host Linux VM deployment
- containerized deployment
- Kubernetes-style deployment patterns managed by the operator

### Policy engine
- built-in fallback policy logic for development and degraded mode
- OPA-backed policy evaluation for stricter production posture

### Sandbox posture
- development sandbox for local bring-up
- Docker-based production posture with documented validation requirements

## Intended GA support commitments

For GA, the target support posture should be:

### Supported runtimes
- Python 3.10 and 3.11
- newer versions only after explicit validation and documentation

### Supported databases
- Postgres as the primary supported production database
- SQLite documented as development-only, not a primary production target

### Supported deployment expectations
- production support assumes:
  - Postgres-backed persistence
  - documented backup/restore posture
  - sandbox validation performed
  - operator-managed monitoring and alerting

## Compatibility expectations

### Config compatibility
- configuration keys documented in `.env.example` and production docs are the supported operator surface
- breaking config changes should be called out in release notes

### Migration compatibility
- forward migration is the supported path
- downgrade compatibility is not assumed unless a release explicitly documents it
- restore-from-backup remains the default recovery posture after failed migrations

### API / CLI compatibility
- operator-facing CLI and admin surfaces should evolve conservatively
- behavior changes that affect operational workflows should be documented in release notes

## Explicit non-promises today

Until GA, Constrails does not promise:
- multi-version rollback safety
- packaged dashboards
- distributed approval worker semantics
- enterprise secret-manager integrations out of the box
- universal sandbox/runtime validation across all environments

## GA sign-off expectation

Before GA, this support matrix should be reviewed and updated alongside:
- release notes
- production deployment docs
- known limitations
- GA checklist
