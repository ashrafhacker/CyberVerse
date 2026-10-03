# CyberVerse on Termux (Android)

Run the CyberVerse backend + frontend natively on an Android phone/tablet via
[Termux](https://termux.dev) — no Docker or PC required.

> **Why PostgreSQL is required:** the backend uses async SQLAlchemy with
> Postgres-specific types (JSONB, UUID, enums), so it cannot run on SQLite.
> Termux ships a working PostgreSQL, so this is fine — it just needs one extra
> step to start the service.

---

## 1. Install Termux and the basic packages

Play Store / F-Droid → install **Termux**. Then, inside Termux:

```bash
pkg update && pkg upgrade -y
pkg install -y python python-pip nodejs-lts redis postgresql \
    build-essential openssl curl git
```

- `redis` → in-memory rate limiting + cache (started by the launcher).
- `postgresql` → the database.
- `build-essential` → needed to compile `bcrypt`/`asyncpg` wheels.
- `nodejs-lts` → runs the Next.js frontend.

> If a package name is not found, run `pkg search <name>` and install the
> closest match.

## 2. Checkout / copy the project

If the repo is on this device already (e.g. on a microSD card), just open it:

```bash
cd /storage/4E21-0000/CyberVerse
```

Otherwise clone it:

```bash
git clone <your-repo-url> && cd CyberVerse
```

## 3. Automate everything (recommended)

Run the one-shot setup script from **inside** the project root:

```bash
bash termux/setup_termux.sh
```

This will:

1. Initialize PostgreSQL data dir + start the server.
2. Create the `cyberverse` role and `cyberverse` database.
3. Create a Python virtualenv and install `backend/requirements.txt`.
4. Build `backend/.env` (asks for OpenAI/OpenRouter/Gemini keys — press Enter
   to skip; the AI mentor then falls back to offline mode).
5. Create `frontend/.env.local` with the correct local API URL.
6. Create the DB schema and seed the platform content.
7. Build the frontend.

## 4. Start everything

```bash
bash termux/start_termux.sh
```

This starts PostgreSQL (if stopped), runs the backend on `:8000`, and serves
the built frontend on `:3000`. Open `http://127.0.0.1:3000` in your browser.

> Termux on Android can host a real LAN server so a laptop can connect too.
> With `curl ifconfig.me` or your local IP, set `--host 0.0.0.0` (see below).

---

## Manual steps (if you skip the script)

### PostgreSQL

```bash
# one-time init
mkdir -p "$PREFIX/var/lib/postgresql"
initdb "$PREFIX/var/lib/postgresql"

# start
pg_ctl -D "$PREFIX/var/lib/postgresql" -l "$PREFIX/var/log/pg.log" start

# create role + db
createuser -s cyberverse
createdb -O cyberverse cyberverse
psql -d postgres -c "ALTER USER cyberverse WITH PASSWORD 'cyberverse';"
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# configure (edit your .env; see backend/.env.example)
cp .env.example .env
#  -> set DATABASE_URL=postgresql+asyncpg://cyberverse:cyberverse@127.0.0.1:5432/cyberverse
#  -> set REDIS_URL=redis://127.0.0.1:6379/0
#  -> set AI_PROVIDER, OPENAI_API_KEY / OPENROUTER_API_KEY / GEMINI_API_KEY (optional)

# create schema + seed
python -m app.init_db           # if present; else use alembic
python scripts/seed.py

# run the API (in its own Termux session)
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
# ensure .env.local has: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
npm run build
npm start        # serves on :3000
```

### Redis (for rate limiting / cache)

```bash
redis-server --daemonize yes
```

---

## Notes & troubleshooting

- **Default admin:** `admin@cyberverse.io` / `ChangeMe123!` (created by the
  seed script). **Change this on a shared/networked device.**
- **Battery / background:** Termux processes stop when the app is swiped away.
  Termux's "Acquire wakelock" (`termux-wake-lock`) keeps the CPU awake while
  the server runs.
- **Binding to LAN:** for another device to reach it, start with
  `--host 0.0.0.0` and set `NEXT_PUBLIC_API_URL=http://<your-lan-ip>:8000/api/v1`
  in `frontend/.env.local`, then rebuild the frontend. Keep the device on the
  same Wi-Fi. Your phone firewall / Android may prompt to allow the connection.
- **AI keys:** the AI mentor works fully offline as a local tutor when no API
  key is set. Adding an `OPENROUTER_API_KEY` (or OpenAI/Gemini) enables rich
  model responses via the automatic failover chain.
- **Low memory devices:** stop other apps; consider lowering `DATABASE_POOL_SIZE`
  to 2 in `backend/.env`.
