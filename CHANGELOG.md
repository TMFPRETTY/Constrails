# Changelog

All notable changes to Constrails will be documented in this file.

The format is inspired by Keep a Changelog and this project is currently in an early alpha stage.

## [0.1.0-alpha] - 2026-03-31

### Added
- canonical kernel path with FastAPI wrapper
- unified tool broker and adapter contract
- filesystem, HTTP, and exec adapters
- capability manifests with path, domain, and command constraints
- capability manifest persistence, versioning, activation/deactivation, and mutation operations
- approval request lifecycle, replay flow, delivery tracking, and webhook retry workflow
- sandbox executor abstraction with dev and Docker-backed paths
- sandbox execution persistence and audit provenance linkage
- admin inspection endpoints for audit, sandbox, and capability history
- scoped admin read boundaries for tenant-aware governance
- `constrail` CLI entrypoint with:
  - `init-db`
  - `serve`
  - `doctor`
  - `approval-*` management commands
  - `audit-list`
  - `sandbox-list`
  - `capability-*` lifecycle commands
- JSON output support for operational CLI commands
- expanded starter OPA policy bundle and policy fallback coverage
- automated test coverage across API, CLI, approvals, sandboxing, admin inspection, policy fallback, and OPA-response contract tests

### Changed
- development database defaults now use local SQLite for bring-up
- exec path is sandbox-first by default
- Docker sandbox path hardened with stronger isolation defaults and clearer posture reporting
- README significantly expanded with installation, operator workflow, sandbox posture, and policy setup guidance
- release guidance updated to reflect current operator and posture checks

### Notes
- This is an alpha-quality foundation intended for development and iteration.
- Production identity, durable delivery guarantees, stronger packaging flow, and deeper deployment hardening still have room to grow.
