# CyberVerse — SQL schema bootstrap
# This mirrors the Alembic migration for quick local bootstrap.
# Production must use Alembic migrations, not this file.

\connect cyberverse

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users & Identity
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    role VARCHAR(50) NOT NULL DEFAULT 'student',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_2fa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    totp_secret VARCHAR(32),
    backup_codes JSONB NOT NULL DEFAULT '[]',
    provider VARCHAR(50) NOT NULL DEFAULT 'email',
    provider_id VARCHAR(100),
    last_login TIMESTAMPTZ,
    last_login_ip VARCHAR(45),
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    email_verification_token VARCHAR(100),
    email_verification_expires TIMESTAMPTZ,
    password_reset_token VARCHAR(100),
    password_reset_expires TIMESTAMPTZ,
    preferences JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(50) NOT NULL UNIQUE,
    bio TEXT,
    banner_url VARCHAR(500),
    xp INTEGER NOT NULL DEFAULT 0,
    coins INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    rank VARCHAR(50),
    titles JSONB NOT NULL DEFAULT '[]',
    badges JSONB NOT NULL DEFAULT '[]',
    equipped_title VARCHAR(100),
    equipped_badge VARCHAR(100),
    statistics JSONB NOT NULL DEFAULT '{}',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL,
    refresh_token VARCHAR(500) NOT NULL,
    device_info JSONB NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    location VARCHAR(200),
    expires_at TIMESTAMPTZ NOT NULL,
    refresh_expires_at TIMESTAMPTZ NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS ix_sessions_refresh_token ON sessions(refresh_token);

CREATE TABLE IF NOT EXISTS login_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    location VARCHAR(200),
    method VARCHAR(50) NOT NULL DEFAULT 'email',
    failure_reason VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50) NOT NULL DEFAULT 'web',
    browser VARCHAR(100) NOT NULL,
    os VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    location VARCHAR(200),
    is_trusted BOOLEAN NOT NULL DEFAULT FALSE,
    last_active TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    before JSONB,
    after JSONB,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);

-- See alembic/versions/0001_initial.py for the complete schema.
-- Remaining tables (learning_paths, courses, modules, lessons, quizzes,
-- missions, player_progress, achievements, certificates, notifications,
-- social, premium, support, leaderboards, analytics) are defined fully
-- in the Alembic migration.
