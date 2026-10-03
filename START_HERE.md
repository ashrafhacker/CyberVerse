# CyberVerse — Portable Copy (F:\CyberVerse)

This is a portable source copy (no node_modules / .venv). Works on any Windows/Mac/Linux.

## Quick start (any system)

### Option 1 — Docker (recommended, zero setup)
```bash
cd F:\CyberVerse   # or /media/usb/CyberVerse on Linux/Mac
docker compose -f docker/docker-compose.yml up --build
# frontend: http://localhost:3000  backend: http://localhost:8000
```

### Option 2 — Manual
```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # fill DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev  # http://localhost:3000
```

## What was optimized for low CPU
- `frontend/next.config.mjs`: `output:standalone` + `optimizePackageImports` + `removeConsole` → smaller JS, less client CPU
- `backend/app/core/config.py`: DB pool 20→5, `backend/app/core/security.py`: bcrypt respects BCRYPT_ROUNDS + async wrappers (set `BCRYPT_ROUNDS=10` in .env for 4x faster on weak CPUs)
- `docker/Dockerfile.backend`: workers 4→`${WEB_CONCURRENCY:-2}` → half RAM/CPU idle

Copy on F: = 6.3 MB (226 files). For offline USB without internet, copy with deps: run `robocopy E:\CyberVerse\CyberVerse F:\CyberVerse-Full /E` (883 MB).
