#!/usr/bin/env bash
#
# CyberVerse launcher for Termux.
# Starts PostgreSQL, then the backend (:8000) and frontend (:3000).
# Run from the project ROOT:  bash termux/start_termux.sh
#
# Optional: bind to the LAN so another device can connect.
#   HOST=0.0.0.0 bash termux/start_termux.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PG_DATA="${PREFIX:-$HOME}/var/lib/postgresql"
PG_LOG="${PREFIX:-$HOME}/var/log/postgres.log"

# The on-sdcard .venv loses symlinks (vfat), so prefer a realfs venv.
VENV="$ROOT/backend/.venv"
[ -x "$VENV/bin/activate" ] || VENV="$HOME/cyberverse-venv"

# Same disease: node_modules/.bin needs symlinks + exec bits.
FRONTEND="$ROOT/frontend"
[ -x "$FRONTEND/node_modules/.bin/next" ] || FRONTEND="$HOME/CyberVerse-frontend"

# ---------------------------------------------------------------- postgres
if ! pg_ctl -D "$PG_DATA" status >/dev/null 2>&1; then
  echo "==> Starting PostgreSQL"
  pg_ctl -D "$PG_DATA" -l "$PG_LOG" -o "-p 5432" start >/dev/null
else
  echo "==> PostgreSQL already running"
fi

# ------------------------------------------------------------------- redis
if ! redis-cli ping >/dev/null 2>&1; then
  echo "==> Starting Redis"
  redis-server --daemonize yes >/dev/null
else
  echo "==> Redis already running"
fi

# ------------------------------------------------------------------ backend
echo "==> Starting backend on $HOST:8000"
cd "$ROOT/backend"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
exec uvicorn app.main:app --host "$HOST" --port 8000 "$@" &
BACKEND_PID=$!

# ---------------------------------------------------------------- frontend
echo "==> Starting frontend on $HOST:3000"
cd "$FRONTEND"
if [ ! -d node_modules/.next ]; then
  echo "  First run: building the frontend (this can take a while)"
  npm run build
fi
exec npm start -- --hostname "$HOST" --port 3000 "$@" &
FRONTEND_PID=$!

# ------------------------------------------------------------------- trap
cleanup() {
  echo "==> Stopping servers"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo
echo "CyberVerse is running:"
echo "  Frontend : http://$HOST:3000"
echo "  API      : http://$HOST:8000/api/v1"
echo "  Press Ctrl+C to stop."

wait
