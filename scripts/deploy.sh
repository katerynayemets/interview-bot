#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*" >&2; }

if ! command -v docker >/dev/null 2>&1; then
  error "Docker is not installed."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  error "Docker daemon is not running."
  exit 1
fi
info "Docker is available."

if ! docker compose version >/dev/null 2>&1; then
  error "Docker Compose plugin not found (need 'docker compose', not 'docker-compose')."
  exit 1
fi
info "Docker Compose plugin found."

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    warn ".env not found. Copying from .env.example."
    warn "Edit .env with real values and re-run this script."
    cp .env.example .env
    exit 1
  else
    error "Neither .env nor .env.example found."
    exit 1
  fi
fi
info ".env present."

info "Building images..."
docker compose build

info "Starting stack..."
docker compose up -d

info "Waiting for services to become healthy (up to 90s)..."
deadline=$(( $(date +%s) + 90 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  unhealthy=$(docker compose ps --format json | grep -c '"Health":"unhealthy"' || true)
  starting=$(docker compose ps --format json | grep -c '"Health":"starting"' || true)
  if [ "$unhealthy" -eq 0 ] && [ "$starting" -eq 0 ]; then
    info "All services healthy."
    break
  fi
  sleep 3
done

info "Running smoke test..."
if curl -fsS http://localhost:8000/health >/dev/null; then
  info "API responds on /health."
else
  warn "Smoke test failed — check 'docker compose logs api'."
fi

echo
info "Stack is up. URLs:"
echo "  API:      http://localhost:8000"
echo "  Health:   http://localhost:8000/health"
echo "  pgAdmin:  http://localhost:5050  (login from .env)"
echo "  Postgres: localhost:5433 (mapped from container 5432)"
echo
info "Useful commands:"
echo "  docker compose ps"
echo "  docker compose logs -f api"
echo "  docker compose down            # stop, keep volumes"
echo "  docker compose down -v         # stop and delete volumes"
