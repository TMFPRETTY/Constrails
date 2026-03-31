#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/compose/docker-compose.yml"
COMPOSE_ENV="$ROOT_DIR/deploy/compose/.env"

cleanup() {
  docker compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
  rm -f "$COMPOSE_ENV"
}
trap cleanup EXIT

cp "$ROOT_DIR/deploy/compose/.env.example" "$COMPOSE_ENV"

docker compose -f "$COMPOSE_FILE" up -d --build
python3 "$ROOT_DIR/scripts/opa_smoke.py"
