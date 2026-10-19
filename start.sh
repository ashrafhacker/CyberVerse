#!/bin/bash
# CyberVerse fast launcher (SSD copy at /home/neo/CyberVerse).
# Usage: ./start.sh   (stops: ./stop.sh)
set -e
cd "$(dirname "$0")"

echo "== infra (postgres + redis) =="
sudo service redis-server start || true
# NOTE: `service postgresql restart` leaves the 18/main cluster down on this
# box — start the cluster directly, fall back to the service wrapper.
sudo pg_ctlcluster 18 main start 2>/dev/null || sudo service postgresql restart
pg_isready
redis-cli ping

echo "== backend (4 workers, no reload) =="
cd backend
WEB_CONCURRENCY=4 nohup ./.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --workers 4 \
  > /tmp/opencode/cyberverse-backend.log 2>&1 &
cd ..

echo "== frontend (production build) =="
cd frontend
# `output: 'standalone'` does NOT copy public/ or .next/static into the
# standalone bundle — do it here, or every /_next/static chunk 404s and the
# page never hydrates. (next start can't be used with standalone output.)
rm -rf .next/standalone/public .next/standalone/.next/static
cp -r public .next/standalone/public
cp -r .next/static .next/standalone/.next/static
set -a && . ./.env.local && set +a
NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000 nohup node ./.next/standalone/server.js \
  > /tmp/opencode/cyberverse-frontend.log 2>&1 &
cd ..

sleep 10
curl -s -o /dev/null -w 'backend docs: %{http_code}\n' http://127.0.0.1:8000/api/v1/docs
curl -s -o /dev/null -w 'frontend /:  %{http_code}\n' http://127.0.0.1:3000/
echo "up: frontend http://127.0.0.1:3000  backend http://127.0.0.1:8000/api/v1/docs"
