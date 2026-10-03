-- CyberVerse Labs schema extension draft.
-- Convert to an Alembic migration before production use.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS lab_facilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    facility_type VARCHAR(50) NOT NULL,
    min_level INTEGER NOT NULL DEFAULT 1,
    unlock_rules JSONB NOT NULL DEFAULT '{}',
    ue5_map_name VARCHAR(120),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_mission_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id UUID NOT NULL REFERENCES lab_facilities(id) ON DELETE CASCADE,
    slug VARCHAR(120) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    mission_type VARCHAR(80) NOT NULL,
    difficulty VARCHAR(40) NOT NULL DEFAULT 'beginner',
    estimated_minutes INTEGER NOT NULL DEFAULT 30,
    story_context TEXT NOT NULL,
    objectives JSONB NOT NULL DEFAULT '[]',
    tools JSONB NOT NULL DEFAULT '[]',
    evidence_blueprint JSONB NOT NULL DEFAULT '[]',
    generation_rules JSONB NOT NULL DEFAULT '{}',
    scoring_rubric JSONB NOT NULL DEFAULT '{}',
    debrief_rubric JSONB NOT NULL DEFAULT '{}',
    safety_rules JSONB NOT NULL DEFAULT '{}',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_scenario_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES lab_mission_templates(id) ON DELETE CASCADE,
    seed VARCHAR(120) NOT NULL,
    generator_version VARCHAR(80) NOT NULL,
    company_profile JSONB NOT NULL DEFAULT '{}',
    topology JSONB NOT NULL DEFAULT '{}',
    generated_assets JSONB NOT NULL DEFAULT '[]',
    generated_identities JSONB NOT NULL DEFAULT '[]',
    generated_logs JSONB NOT NULL DEFAULT '[]',
    generated_alerts JSONB NOT NULL DEFAULT '[]',
    generated_evidence JSONB NOT NULL DEFAULT '[]',
    generated_objectives JSONB NOT NULL DEFAULT '[]',
    safety_metadata JSONB NOT NULL DEFAULT '{}',
    validation_status VARCHAR(40) NOT NULL DEFAULT 'pending',
    validation_errors JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(template_id, seed)
);

CREATE TABLE IF NOT EXISTS lab_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scenario_id UUID NOT NULL REFERENCES lab_scenario_instances(id) ON DELETE CASCADE,
    mode VARCHAR(40) NOT NULL DEFAULT 'solo',
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    mentor_level VARCHAR(40) NOT NULL DEFAULT 'guided',
    current_facility_slug VARCHAR(80) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    abandoned_at TIMESTAMPTZ,
    score INTEGER,
    xp_awarded INTEGER NOT NULL DEFAULT 0,
    coins_awarded INTEGER NOT NULL DEFAULT 0,
    tool_state JSONB NOT NULL DEFAULT '{}',
    objective_state JSONB NOT NULL DEFAULT '{}',
    save_state JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lab_sessions_user_id ON lab_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_lab_sessions_status ON lab_sessions(status);

CREATE TABLE IF NOT EXISTS lab_session_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES lab_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(60) NOT NULL DEFAULT 'analyst',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    left_at TIMESTAMPTZ,
    permissions JSONB NOT NULL DEFAULT '{}',
    UNIQUE(session_id, user_id)
);

CREATE TABLE IF NOT EXISTS lab_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES lab_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    tool_id VARCHAR(100),
    target_id VARCHAR(120),
    payload JSONB NOT NULL DEFAULT '{}',
    client_time TIMESTAMPTZ,
    server_time TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lab_events_session_id ON lab_events(session_id);
CREATE INDEX IF NOT EXISTS ix_lab_events_event_type ON lab_events(event_type);

CREATE TABLE IF NOT EXISTS lab_evidence_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES lab_sessions(id) ON DELETE CASCADE,
    evidence_key VARCHAR(120) NOT NULL,
    title VARCHAR(200) NOT NULL,
    evidence_type VARCHAR(80) NOT NULL,
    source_tool VARCHAR(100),
    source_asset_id VARCHAR(120),
    content JSONB NOT NULL DEFAULT '{}',
    hash_value VARCHAR(128),
    custody JSONB NOT NULL DEFAULT '[]',
    collected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    collected_at TIMESTAMPTZ,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id, evidence_key)
);

CREATE TABLE IF NOT EXISTS lab_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES lab_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    body TEXT NOT NULL,
    linked_evidence_ids JSONB NOT NULL DEFAULT '[]',
    linked_target_id VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES lab_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    executive_summary TEXT NOT NULL,
    technical_findings TEXT NOT NULL,
    containment_actions TEXT,
    remediation_plan TEXT,
    evidence_ids JSONB NOT NULL DEFAULT '[]',
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mentor_feedback JSONB NOT NULL DEFAULT '{}',
    instructor_feedback JSONB NOT NULL DEFAULT '{}',
    grade VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS lab_home_attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attestation_text TEXT NOT NULL,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_home_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attestation_id UUID NOT NULL REFERENCES lab_home_attestations(id) ON DELETE RESTRICT,
    name VARCHAR(120) NOT NULL,
    lab_type VARCHAR(80) NOT NULL,
    scope JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(40) NOT NULL DEFAULT 'inactive',
    read_only BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID REFERENCES lab_sessions(id) ON DELETE SET NULL,
    home_profile_id UUID REFERENCES lab_home_profiles(id) ON DELETE SET NULL,
    action VARCHAR(120) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(120),
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lab_audit_logs_user_id ON lab_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_lab_audit_logs_action ON lab_audit_logs(action);
