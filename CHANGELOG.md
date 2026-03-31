# Changelog

All notable changes to Constrails will be documented in this file.

The format is inspired by Keep a Changelog and this project is currently in an early alpha stage.

## [0.1.0-alpha] - 2026-03-31

### Added
- canonical kernel path with FastAPI wrapper
- unified tool broker and adapter contract
- filesystem, HTTP, and exec adapters
- capability manifests with path, domain, and command constraints
- approval request lifecycle and replay flow
- sandbox executor abstraction with dev and Docker-backed paths
- sandbox execution persistence and audit provenance linkage
- admin inspection endpoints for audit and sandbox history
- `constrail` CLI entrypoint with:
  - `init-db`
  - `serve`
  - `doctor`
  - `approval-*` management commands
  - `audit-list`
  - `sandbox-list`
- JSON output support for selected CLI commands
- sample OPA policy bundle and example input payload
- automated test coverage across API, CLI, approvals, sandboxing, admin inspection, and policy fallback

### Changed
- development database defaults now use local SQLite for bring-up
- exec path is sandbox-first by default
- Docker sandbox path hardened with safer defaults
- README significantly expanded with installation, operator workflow, and policy setup guidance

### Notes
- This is an alpha-quality foundation intended for development and iteration.
- Production hardening, deeper policy coverage, stronger auth, and deployment ergonomics are still in progress.
