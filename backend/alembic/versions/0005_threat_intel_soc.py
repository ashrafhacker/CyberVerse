"""add threat intelligence + soc module tables

Revision ID: 0005_threat_intel_soc
Revises: 0004_cyber_arsenal_ctf
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_threat_intel_soc"
down_revision: Union[str, None] = "0004_cyber_arsenal_ctf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- Threat Intelligence ----------
    op.create_table(
        "attack_techniques",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("technique_id", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("tactic", sa.String(120), nullable=False),
        sa.Column("platform", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("detection", sa.Text(), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("data_sources", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
    )
    op.create_index("ix_attack_techniques_tactic", "attack_techniques", ["tactic"])
    op.create_index("uq_attack_techniques_id", "attack_techniques", ["technique_id"], unique=True)

    op.create_table(
        "cves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cve_id", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("cvss_vector", sa.String(300), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("cwe_id", sa.String(40), nullable=True),
        sa.Column("cwe_name", sa.String(200), nullable=True),
        sa.Column("attack_vector", sa.String(40), nullable=True),
        sa.Column("complexity", sa.String(40), nullable=True),
        sa.Column("affected_products", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("references", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("mitigations", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("source", sa.String(120), nullable=False, server_default="NVD/CISA"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="high"),
    )
    op.create_index("uq_cves_cve_id", "cves", ["cve_id"], unique=True)
    op.create_index("ix_cves_severity", "cves", ["severity"])
    op.create_index("ix_cves_published_date", "cves", ["published_date"])

    op.create_table(
        "cve_attack_techniques",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cve_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cves.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technique_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attack_techniques.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_cve_attack_techniques_cve", "cve_attack_techniques", ["cve_id"])

    op.create_table(
        "threat_indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("indicator_type", sa.String(40), nullable=False),
        sa.Column("indicator_value", sa.String(600), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("threat_actor", sa.String(200), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(120), nullable=False, server_default="MISP feeding"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_threat_indicators_type", "threat_indicators", ["indicator_type"])
    op.create_index("uq_threat_indicators", "threat_indicators", ["indicator_value", "indicator_type"], unique=True)

    # ---------- SOC ----------
    op.create_table(
        "soc_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("mitre_mapping", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("affected_assets", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("evidence_ids", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("analyst_notes", postgresql.ARRAY(postgresql.JSONB()), nullable=False, server_default="{}"),
        sa.Column("timeline", postgresql.ARRAY(postgresql.JSONB()), nullable=False, server_default="{}"),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("containment_actions", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("remediation_plan", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_soc_incidents_status", "soc_incidents", ["status"])
    op.create_index("ix_soc_incidents_severity", "soc_incidents", ["severity"])
    op.create_index("ix_soc_incidents_opened_at", "soc_incidents", ["opened_at"])
    op.create_index("ix_soc_incidents_case_number", "soc_incidents", ["case_number"], unique=True)

    op.create_table(
        "soc_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="low"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("asset", sa.String(200), nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("mitre_technique_id", sa.String(40), nullable=True),
        sa.Column("event_details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("timeline", postgresql.ARRAY(postgresql.JSONB()), nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soc_incidents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_soc_alerts_severity", "soc_alerts", ["severity"])
    op.create_index("ix_soc_alerts_status", "soc_alerts", ["status"])
    op.create_index("ix_soc_alerts_timestamp", "soc_alerts", ["timestamp"])

    op.create_table(
        "incident_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("soc_incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_incident_notes_incident_id", "incident_notes", ["incident_id"])


def downgrade() -> None:
    op.drop_table("incident_notes")
    op.drop_table("soc_alerts")
    op.drop_table("soc_incidents")
    op.drop_table("threat_indicators")
    op.drop_table("cve_attack_techniques")
    op.drop_table("cves")
    op.drop_table("attack_techniques")
