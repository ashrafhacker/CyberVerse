"""add cyberverse labs tables

Revision ID: 0003_cyberverse_labs
Revises: 0002_library
Create Date: 2026-08-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_cyberverse_labs"
down_revision: Union[str, None] = "0002_library"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("facility_type", sa.String(50), nullable=False),
        sa.Column("min_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unlock_rules", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ue5_map_name", sa.String(120), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_facilities_slug", "lab_facilities", ["slug"], unique=True)
    op.create_index("ix_lab_facilities_type", "lab_facilities", ["facility_type"])

    op.create_table(
        "lab_mission_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("mission_type", sa.String(80), nullable=False),
        sa.Column("difficulty", sa.String(40), nullable=False, server_default="beginner"),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("story_context", sa.Text(), nullable=False),
        sa.Column("objectives", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("tools", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("evidence_blueprint", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("generation_rules", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("scoring_rubric", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("debrief_rubric", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("safety_rules", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_mission_templates_slug", "lab_mission_templates", ["slug"], unique=True)
    op.create_index("ix_lab_mission_templates_facility_id", "lab_mission_templates", ["facility_id"])
    op.create_index("ix_lab_mission_templates_type", "lab_mission_templates", ["mission_type"])
    op.create_index("ix_lab_mission_templates_published", "lab_mission_templates", ["is_published"])

    op.create_table(
        "lab_scenario_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_mission_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seed", sa.String(120), nullable=False),
        sa.Column("generator_version", sa.String(80), nullable=False),
        sa.Column("company_profile", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("topology", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("generated_assets", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("generated_identities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("generated_logs", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("generated_alerts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("generated_evidence", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("generated_objectives", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("safety_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("validation_status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("template_id", "seed", name="uq_lab_scenario_template_seed"),
    )
    op.create_index("ix_lab_scenario_template_id", "lab_scenario_instances", ["template_id"])
    op.create_index("ix_lab_scenario_validation_status", "lab_scenario_instances", ["validation_status"])

    op.create_table(
        "lab_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_scenario_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False, server_default="solo"),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("mentor_level", sa.String(40), nullable=False, server_default="guided"),
        sa.Column("current_facility_slug", sa.String(80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coins_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("objective_state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("save_state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_sessions_user_id", "lab_sessions", ["user_id"])
    op.create_index("ix_lab_sessions_scenario_id", "lab_sessions", ["scenario_id"])
    op.create_index("ix_lab_sessions_status", "lab_sessions", ["status"])

    op.create_table(
        "lab_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("tool_id", sa.String(100), nullable=True),
        sa.Column("target_id", sa.String(120), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("client_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_events_session_id", "lab_events", ["session_id"])
    op.create_index("ix_lab_events_event_type", "lab_events", ["event_type"])

    op.create_table(
        "lab_evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_key", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("evidence_type", sa.String(80), nullable=False),
        sa.Column("source_tool", sa.String(100), nullable=True),
        sa.Column("source_asset_id", sa.String(120), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("hash_value", sa.String(128), nullable=True),
        sa.Column("custody", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("collected_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("session_id", "evidence_key", name="uq_lab_evidence_session_key"),
    )
    op.create_index("ix_lab_evidence_session_id", "lab_evidence_items", ["session_id"])

    op.create_table(
        "lab_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("linked_evidence_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("linked_target_id", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_notes_session_id", "lab_notes", ["session_id"])

    op.create_table(
        "lab_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("technical_findings", sa.Text(), nullable=False),
        sa.Column("containment_actions", sa.Text(), nullable=True),
        sa.Column("remediation_plan", sa.Text(), nullable=True),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("mentor_feedback", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("instructor_feedback", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("grade", sa.String(20), nullable=True),
    )

    op.create_table(
        "lab_home_attestations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attestation_text", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_home_attestations_user_id", "lab_home_attestations", ["user_id"])

    op.create_table(
        "lab_home_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attestation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_home_attestations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("lab_type", sa.String(80), nullable=False),
        sa.Column("scope", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(40), nullable=False, server_default="inactive"),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_home_profiles_user_id", "lab_home_profiles", ["user_id"])

    op.create_table(
        "lab_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("home_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_home_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(120), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lab_audit_logs_user_id", "lab_audit_logs", ["user_id"])
    op.create_index("ix_lab_audit_logs_action", "lab_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_lab_audit_logs_action", table_name="lab_audit_logs")
    op.drop_index("ix_lab_audit_logs_user_id", table_name="lab_audit_logs")
    op.drop_table("lab_audit_logs")
    op.drop_index("ix_lab_home_profiles_user_id", table_name="lab_home_profiles")
    op.drop_table("lab_home_profiles")
    op.drop_index("ix_lab_home_attestations_user_id", table_name="lab_home_attestations")
    op.drop_table("lab_home_attestations")
    op.drop_table("lab_reports")
    op.drop_index("ix_lab_notes_session_id", table_name="lab_notes")
    op.drop_table("lab_notes")
    op.drop_index("ix_lab_evidence_session_id", table_name="lab_evidence_items")
    op.drop_table("lab_evidence_items")
    op.drop_index("ix_lab_events_event_type", table_name="lab_events")
    op.drop_index("ix_lab_events_session_id", table_name="lab_events")
    op.drop_table("lab_events")
    op.drop_index("ix_lab_sessions_status", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_scenario_id", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_user_id", table_name="lab_sessions")
    op.drop_table("lab_sessions")
    op.drop_index("ix_lab_scenario_validation_status", table_name="lab_scenario_instances")
    op.drop_index("ix_lab_scenario_template_id", table_name="lab_scenario_instances")
    op.drop_table("lab_scenario_instances")
    op.drop_index("ix_lab_mission_templates_published", table_name="lab_mission_templates")
    op.drop_index("ix_lab_mission_templates_type", table_name="lab_mission_templates")
    op.drop_index("ix_lab_mission_templates_facility_id", table_name="lab_mission_templates")
    op.drop_index("ix_lab_mission_templates_slug", table_name="lab_mission_templates")
    op.drop_table("lab_mission_templates")
    op.drop_index("ix_lab_facilities_type", table_name="lab_facilities")
    op.drop_index("ix_lab_facilities_slug", table_name="lab_facilities")
    op.drop_table("lab_facilities")
