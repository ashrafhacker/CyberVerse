FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql redis-server curl gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

ENV DATABASE_URL=postgresql+asyncpg://cyberverse:cyberverse@127.0.0.1:5432/cyberverse \
    REDIS_URL=redis://127.0.0.1:6379/0 \
    ENVIRONMENT=production \
    DEBUG=false

RUN service postgresql start && \
    su postgres -c "psql -c \"CREATE USER cyberverse WITH PASSWORD 'cyberverse';\" && psql -c 'CREATE DATABASE cyberverse OWNER cyberverse;'" && \
    service postgresql stop

EXPOSE 8000

CMD service postgresql start && \
    service redis-server start && \
    cd /app/backend && alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
