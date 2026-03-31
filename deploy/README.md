# Deployment examples

This directory contains practical deployment examples for Constrails.

## Included

- `compose/docker-compose.yml` - local multi-service stack for Constrails + OPA
- `compose/.env.example` - example environment values for the Compose stack

## Compose quick start

```bash
cd deploy/compose
cp .env.example .env
docker compose up --build
```

Services:
- Constrails API on `http://localhost:8000`
- OPA on `http://localhost:8181`

## Recommended follow-up checks

After the stack is up, validate the operator surface:

```bash
PYTHONPATH=src .venv/bin/python -m constrail.cli doctor --json
PYTHONPATH=src .venv/bin/python -m constrail.cli sandbox-validate --json
PYTHONPATH=src .venv/bin/python -m constrail.cli auth-status --json
PYTHONPATH=src .venv/bin/python -m constrail.cli capability-list --json
PYTHONPATH=src .venv/bin/python -m constrail.cli approval-list --limit 5 --json
```

For a serialized local compose smoke run, use:

```bash
bash scripts/run_compose_opa_smoke.sh
```

## Sandbox posture notes

The included Compose stack is still an early-stage example.

For more serious deployment, move toward:
- Docker-backed sandbox mode instead of dev mode
- pinned sandbox images by digest
- readonly workspace mounts where possible
- isolated sandbox networking by default
- explicit memory and timeout limits
- tmpfs-backed writable scratch space
- externalized state storage instead of local development paths
- stronger secret/auth handling than static development keys

Use `constrail sandbox-validate --json` as a posture gate before treating a configuration as closer to production-ready.

## Notes

- This stack is intended as a starting point for local and early-stage deployment experiments.
- It uses repository-local conventions for convenience.
- For more serious deployment, replace this with built images, stronger auth, externalized storage, and stricter runtime isolation.
