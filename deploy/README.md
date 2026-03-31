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

## Notes

- This stack is intended as a starting point for local and early-stage deployment experiments.
- It uses the repository source as a bind mount for convenience.
- For more serious deployment, replace this with built images, stronger auth, externalized storage, and stricter runtime isolation.
