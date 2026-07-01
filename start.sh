#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  start.sh  –  Start CCTV App backend & frontend together
#  Usage:  ./start.sh
# ──────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────
RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[1;36m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
DIM="\033[2m"

# ── Paths ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
INFRA_DIR="$SCRIPT_DIR/infra"

# ── Fix PATH for non-interactive shells (Homebrew / nvm / fnm) ─
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib"
if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck source=/dev/null
  source "$HOME/.nvm/nvm.sh"
fi
if command -v fnm &>/dev/null; then
  eval "$(fnm env --use-on-cd)"
fi

# ── PIDs for cleanup ──────────────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""

# ── Graceful shutdown ─────────────────────────────────────────
cleanup() {
  echo ""
  echo -e "${YELLOW}${BOLD}⚡ Shutting down services...${RESET}"

  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${CYAN}  → Stopping backend  (PID $BACKEND_PID)${RESET}"
    kill "$BACKEND_PID" 2>/dev/null || true
  fi

  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "${MAGENTA}  → Stopping frontend (PID $FRONTEND_PID)${RESET}"
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  wait 2>/dev/null || true
  echo -e "${GREEN}${BOLD}✔ All services stopped. Goodbye!${RESET}"
}
trap cleanup INT TERM EXIT

# ── Helpers ───────────────────────────────────────────────────
log()  { echo -e "${BOLD}[start.sh]${RESET} $*"; }
ok()   { echo -e "${GREEN}${BOLD}✔${RESET} $*"; }
err()  { echo -e "${RED}${BOLD}✘ ERROR:${RESET} $*" >&2; }
warn() { echo -e "${YELLOW}⚠  $*${RESET}"; }

# ── Banner ────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║        CCTV App  –  Dev Launcher         ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Pre-flight: check virtualenv ──────────────────────────────
if [[ ! -f "$BACKEND_DIR/venv/bin/activate" ]]; then
  err "Backend virtualenv not found at $BACKEND_DIR/venv"
  err "Create it first:  cd backend && python3 -m venv venv && pip install -r requirements.txt"
  exit 1
fi
ok "Backend virtualenv found"

# ── Pre-flight: check node_modules ────────────────────────────
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  err "Frontend node_modules not found at $FRONTEND_DIR/node_modules"
  err "Install first:  cd frontend && npm install"
  exit 1
fi
ok "Frontend node_modules found"

# ── Pre-flight: backend .env ──────────────────────────────────
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
  warn "backend/.env not found – copying root .env.example"
  if [[ -f "$SCRIPT_DIR/.env.example" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$BACKEND_DIR/.env"
    warn "Copied .env.example → backend/.env  (edit it with real values!)"
  fi
fi

# ── Docker Desktop: start if not running ──────────────────────
start_docker() {
  if docker info &>/dev/null; then
    ok "Docker is running"
    return
  fi

  warn "Docker Desktop is not running. Attempting to start it..."
  open -a "Docker" 2>/dev/null || true

  local attempts=0
  local max=30  # wait up to 60s
  until docker info &>/dev/null; do
    attempts=$((attempts + 1))
    if (( attempts >= max )); then
      err "Docker Desktop did not start in time."
      err "Please open Docker Desktop manually and re-run ./start.sh"
      exit 1
    fi
    echo -e "${DIM}  waiting for Docker Desktop… (${attempts}/${max})${RESET}"
    sleep 2
  done
  ok "Docker Desktop started"
}

# ── Infra: start Postgres + Redis via docker-compose.dev.yml ──
start_infra() {
  local compose_file="$INFRA_DIR/docker-compose.dev.yml"

  if [[ ! -f "$compose_file" ]]; then
    err "Dev compose file not found: $compose_file"
    exit 1
  fi

  log "Starting Postgres + Redis (docker compose)…"

  # Use --env-file so docker compose reads vars safely (avoids bash
  # misinterpreting special chars like < in SMTP_FROM when sourcing).
  local env_file="$BACKEND_DIR/.env"
  local env_flag=""
  [[ -f "$env_file" ]] && env_flag="--env-file $env_file"

  # shellcheck disable=SC2086
  docker compose -f "$compose_file" $env_flag up -d --remove-orphans

  # Derive creds for health-check commands (safe grep, no sourcing)
  local pg_user redis_pass
  pg_user=$(grep -m1 '^POSTGRES_USER=' "$env_file" 2>/dev/null | cut -d= -f2 || echo "cctv")
  redis_pass=$(grep -m1 '^REDIS_PASSWORD=' "$env_file" 2>/dev/null | cut -d= -f2 || echo "redis_dev_pass")

  # Wait until postgres is healthy
  echo -e "${DIM}  Waiting for Postgres to be healthy…${RESET}"
  local attempts=0
  # shellcheck disable=SC2086
  until docker compose -f "$compose_file" $env_flag exec -T postgres \
        pg_isready -U "$pg_user" &>/dev/null; do
    attempts=$((attempts + 1))
    if (( attempts >= 30 )); then
      err "Postgres did not become healthy in time. Check Docker logs:"
      err "  docker compose -f infra/docker-compose.dev.yml logs postgres"
      exit 1
    fi
    sleep 1
  done
  ok "Postgres is ready"

  # Wait until redis is healthy
  echo -e "${DIM}  Waiting for Redis to be healthy…${RESET}"
  attempts=0
  # shellcheck disable=SC2086
  until docker compose -f "$compose_file" $env_flag exec -T redis \
        redis-cli -a "$redis_pass" ping 2>/dev/null | grep -q PONG; do
    attempts=$((attempts + 1))
    if (( attempts >= 20 )); then
      warn "Redis health check timed out – continuing anyway"
      break
    fi
    sleep 1
  done
  ok "Redis is ready"
}

# ── Migrations ────────────────────────────────────────────────
run_migrations() {
  log "Running Alembic migrations…"
  (
    cd "$BACKEND_DIR"
    # shellcheck source=/dev/null
    source venv/bin/activate
    alembic upgrade head 2>&1 | while IFS= read -r line; do
      echo -e "${DIM}  [alembic] $line${RESET}"
    done
  )
  ok "Migrations applied"
}

# ── Orchestrate startup ───────────────────────────────────────
start_docker
start_infra
run_migrations

echo ""
log "Starting app services…"
echo ""

# ── Free ports if still in use (stale processes from a prior run) ─
for PORT in 8000 5173; do
  PIDS=$(lsof -ti:"$PORT" 2>/dev/null || true)
  if [[ -n "$PIDS" ]]; then
    warn "Port $PORT in use – killing stale process(es): $PIDS"
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
done

# ── Backend ───────────────────────────────────────────────────
(
  cd "$BACKEND_DIR"
  # shellcheck source=/dev/null
  source venv/bin/activate
  export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:/usr/local/lib:$DYLD_FALLBACK_LIBRARY_PATH"
  uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info 2>&1 \
  | while IFS= read -r line; do
      echo -e "${CYAN}${BOLD}[backend]${RESET}  $line"
    done
) &
BACKEND_PID=$!
echo -e "${CYAN}${BOLD}[backend]${RESET}  started  →  ${BLUE}http://localhost:8000${RESET}  (PID $BACKEND_PID)"

# ── Frontend ──────────────────────────────────────────────────
(
  cd "$FRONTEND_DIR"
  npm run dev 2>&1 \
  | while IFS= read -r line; do
      echo -e "${MAGENTA}${BOLD}[frontend]${RESET} $line"
      # Auto-open Chrome once Vite is ready
      if [[ "$line" == *"ready in"* || "$line" == *"Local:"* ]]; then
        open -a "Google Chrome" "http://localhost:5173" 2>/dev/null || true
      fi
    done
) &
FRONTEND_PID=$!
echo -e "${MAGENTA}${BOLD}[frontend]${RESET} started  →  ${BLUE}http://localhost:5173${RESET}  (PID $FRONTEND_PID)"

echo ""
echo -e "${GREEN}${BOLD}All services are running.${RESET}  Press ${BOLD}Ctrl+C${RESET} to stop."
echo ""

# ── Wait (exit if either child dies) ─────────────────────────
wait -n 2>/dev/null || wait
