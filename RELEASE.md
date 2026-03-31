# Release Guide

This document describes the suggested process for publishing Constrails releases.

## Current target

- `0.1.0-alpha`

## Pre-release checklist

- ensure `main` is clean
- run the full test suite
- confirm README, CHANGELOG, CONTRIBUTING, and SECURITY docs are current
- confirm `.env.example` and deployment examples are current
- confirm sample OPA bundle and compose example are present
- confirm sandbox posture defaults are documented and intentional
- confirm capability lifecycle commands and approval operator workflows are current
- review `.github/release-notes/0.1.0-alpha.md`

## Suggested commands

### 1. Verify repo state

```bash
git status
.venv/bin/python -m pytest -q tests
.venv/bin/python -m constrail.cli doctor --json
.venv/bin/python -m constrail.cli auth-status --json
```

### 2. Sanity check operator surfaces

```bash
.venv/bin/python -m constrail.cli approval-list --limit 5 --json
.venv/bin/python -m constrail.cli capability-list --json
```

### 3. Create the annotated tag

```bash
git tag -a v0.1.0-alpha -m "Constrails 0.1.0-alpha"
```

### 4. Push the tag

```bash
git push origin v0.1.0-alpha
```

### 5. Create the GitHub release

Use the contents of:

- `.github/release-notes/0.1.0-alpha.md`

Recommended release title:

- `Constrails 0.1.0-alpha`

Mark it as a **pre-release** on GitHub.

## After release

- verify tag is visible on GitHub
- verify release notes render correctly
- verify README links and badges still look right
- verify sandbox posture and env defaults still match documentation
- optionally announce the alpha in project/community channels
