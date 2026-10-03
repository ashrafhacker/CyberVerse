#!/usr/bin/env bash
#
# CyberVerse one-shot Termux setup script.
# Run from the project ROOT:  bash termux/setup_termux.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
# venv lives on the internal filesystem: external storage (/storage/...) often
# does not permit the lib -> lib64 symlink that venv needs to create.
VENV_DIR="${VENV_DIR:-$HOME/cyberverse-venv}"
PG_DATA="${PREFIX:-$HOME}/var/lib/postgresql"
PG_LOG="${PREFIX:-$HOME}/var/log/postgres.log"
PG_USER="cyberverse"
PG_PASS="cyberverse"
PG_DB="cyberverse"

echo "==> CyberVerse Termux setup"
echo "    Project root: $ROOT"

# ---------------------------------------------------------------- postgresql
ensure_postgres() {
  if ! command -v initdb >/dev/null 2>&1; then
    echo "  !! initdb not found. Install it:  pkg install postgresql"
    exit 1
  fi

  if [ ! -d "$PG_DATA" ] || [ ! -f "$PG_DATA/PG_VERSION" ]; then
    echo "==> Initializing PostgreSQL data dir at $PG_DATA"
    mkdir -p "$(dirname "$PG_DATA")"
    initdb -D "$PG_DATA" -U "$PG_USER" --auth=trust >/dev/null 2>&1 || {
      echo "  !! initdb failed"; exit 1; }
  else
    echo "==> PostgreSQL data dir already initialized"
  fi

  if ! pg_ctl -D "$PG_DATA" status >/dev/null 2>&1; then
    echo "==> Starting PostgreSQL"
    pg_ctl -D "$PG_DATA" -l "$PG_LOG" -o "-p 5432" start >/dev/null
  else
    echo "==> PostgreSQL already running"
  fi

  # give the server a moment to accept connections
  for _ in $(seq 1 15); do
    if pg_isready -q -h 127.0.0.1 -p 5432 2>/dev/null; then break; fi
    sleep 1
  done

  # role + database
  if ! psql -h 127.0.0.1 -U "$PG_USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" | grep -q 1; then
    echo "==> Creating role $PG_USER"
    psql -h 127.0.0.1 -U "$PG_USER" -d postgres -c "CREATE ROLE $PG_USER WITH LOGIN SUPERUSER PASSWORD '$PG_PASS';" >/dev/null
  else
    psql -h 127.0.0.1 -U "$PG_USER" -d postgres -c "ALTER ROLE $PG_USER WITH PASSWORD '$PG_PASS';" >/dev/null
  fi

  if ! psql -h 127.0.0.1 -U "$PG_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" | grep -q 1; then
    echo "==> Creating database $PG_DB"
    createdb -h 127.0.0.1 -U "$PG_USER" "$PG_DB"
  fi
  echo "==> PostgreSQL ready (db=$PG_DB user=$PG_USER)"
}

# ------------------------------------------------------------------- backend
# Termux's newest Python (3.14+) has no prebuilt binary wheels for many
# packages (pydantic-core, asyncpg, bcrypt, greenlet, ruff) on the Android
# target, forcing slow/failing Rust builds. Prefer a stable interpreter that
# ships Termux wheels (3.11/3.12).
pick_python() {
  for py in python3.12 python3.11 python3; do
    if command -v "$py" >/dev/null 2>&1; then echo "$py"; return; fi
  done
  echo python
}

setup_backend() {
  cd "$BACKEND_DIR"
  PY="$(pick_python)"
  echo "==> Using Python: $PY ($("$PY" --version 2>&1))"
  # Rebuild the venv if its interpreter is an unsupported (3.14+) version.
  NEEDS_REBUILD=0
  if [ -f "$VENV_DIR/bin/python" ] && \
     "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info > (3,13) else 1)' 2>/dev/null; then
    NEEDS_REBUILD=1
  fi
  if [ ! -f "$VENV_DIR/bin/activate" ] || [ "$NEEDS_REBUILD" -eq 1 ]; then
    echo "==> Creating Python venv at $VENV_DIR"
    if [ -d "$VENV_DIR" ]; then rm -rf "$VENV_DIR"; fi
    "$PY" -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  echo "==> Installing Python dependencies (this can take a while)"
  pip install --upgrade pip >/dev/null
  # Skip dev/lint tools that need a Rust toolchain to build from source on
  # Termux (ruff). They are not required to run the app.
  grep -vxE 'ruff[<>=~!]*.*' requirements.txt \
    | pip install -r /dev/stdin

  # build .env if missing
  if [ ! -f .env ]; then
    echo "==> Creating backend/.env from example"
    cp .env.example .env
  fi

  NEEDS_DATABASE_URL=1
  if grep -q '^DATABASE_URL=' .env 2>/dev/null; then NEEDS_DATABASE_URL=0; fi
  if [ "$NEEDS_DATABASE_URL" -eq 1 ]; then
    echo "==> Setting DATABASE_URL in backend/.env"
    echo "DATABASE_URL=postgresql+asyncpg://$PG_USER:$PG_PASS@127.0.0.1:5432/$PG_DB" >> .env
  fi

  NEEDS_REDIS=1
  if grep -q '^REDIS_URL=' .env 2>/dev/null; then NEEDS_REDIS=0; fi
  if [ "$NEEDS_REDIS" -eq 1 ]; then
    echo "==> Setting REDIS_URL in backend/.env"
    echo "REDIS_URL=redis://127.0.0.1:6379/0" >> .env
  fi

  # optional AI keys (press Enter to skip any)
  have_ai=0
  has_key_value() { grep -E "^$1=.+" .env >/dev/null 2>&1; }
  has_key_value "OPENROUTER_API_KEY" && have_ai=1
  has_key_value "OPENAI_API_KEY" && have_ai=1
  has_key_value "GEMINI_API_KEY" && have_ai=1
  if [ "$have_ai" -eq 0 ]; then
    echo "==> Optional AI keys (leave blank to skip; AI mentor then runs offline)"
    read -r -p "    OpenRouter API key: " OR
    read -r -p "    OpenAI API key:     " OA
    read -r -p "    Gemini API key:     " GM
    if [ -n "$OR" ]; then has_key_value "OPENROUTER_API_KEY" || echo "OPENROUTER_API_KEY=$OR" >> .env; fi
    if [ -n "$OA" ]; then has_key_value "OPENAI_API_KEY" || echo "OPENAI_API_KEY=$OA" >> .env; fi
    if [ -n "$GM" ]; then has_key_value "GEMINI_API_KEY" || echo "GEMINI_API_KEY=$GM" >> .env; fi
    if [ -n "$OR" ] || [ -n "$OA" ] || [ -n "$GM" ]; then
      echo "AI_PROVIDER=auto" >> .env
    else
      echo "AI_PROVIDER=offline" >> .env
    fi
  fi

  echo "==> Creating database schema and seeding content"
  cd "$ROOT"
  python scripts/seed.py

  cd "$BACKEND_DIR"
  deactivate 2>/dev/null || true
}

# ------------------------------------------------------------------ frontend
setup_frontend() {
  cd "$FRONTEND_DIR"
  if [ ! -d node_modules ]; then
    echo "==> Installing frontend dependencies"
    npm install
  fi
  if [ ! -f .env.local ]; then
    echo "==> Creating frontend/.env.local"
    cp .env.local.example .env.local 2>/dev/null || \
      printf 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1\n' > .env.local
  fi
}

# --------------------------------------------------------------------- main
ensure_postgres
setup_backend
setup_frontend

echo
echo "Setup complete!"
echo "  Next:  bash termux/start_termux.sh"
echo "  Then open http://127.0.0.1:3000"
