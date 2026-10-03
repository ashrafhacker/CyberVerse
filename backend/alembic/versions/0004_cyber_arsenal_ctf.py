"""add cyber arsenal + ctf tables

Revision ID: 0004_cyber_arsenal_ctf
Revises: 0003_cyberverse_labs
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_cyber_arsenal_ctf"
down_revision: Union[str, None] = "0003_cyberverse_labs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- Cyber Arsenal ----------
    op.create_table(
        "tool_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tool_categories_slug", "tool_categories", ["slug"], unique=True)

    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tool_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("license_name", sa.String(120), nullable=False),
        sa.Column("open_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("free_tier", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("supported_os", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("difficulty", sa.String(40), nullable=False, server_default="beginner"),
        sa.Column("official_url", sa.String(500), nullable=True),
        sa.Column("docs_url", sa.String(500), nullable=True),
        sa.Column("tutorial_url", sa.String(500), nullable=True),
        sa.Column("lab_reference", sa.String(200), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tools_category_id", "tools", ["category_id"])
    op.create_index("ix_tools_slug", "tools", ["slug"], unique=True)
    op.create_index("ix_tools_license", "tools", ["license_name"])
    op.create_index("ix_tools_published", "tools", ["is_published"])

    # ---------- CTF ----------
    op.create_table(
        "ctf_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("story", sa.Text(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, server_default="general"),
        sa.Column("difficulty", sa.String(40), nullable=False, server_default="beginner"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("flag_sha256", sa.String(128), nullable=False),
        sa.Column("flag_hint_prefix", sa.String(120), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ctf_challenges_slug", "ctf_challenges", ["slug"], unique=True)
    op.create_index("ix_ctf_challenges_category", "ctf_challenges", ["category"])
    op.create_index("ix_ctf_challenges_difficulty", "ctf_challenges", ["difficulty"])
    op.create_index("ix_ctf_challenges_active", "ctf_challenges", ["is_active"])

    op.create_table(
        "ctf_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("challenge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ctf_challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_blood", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ctf_submissions_challenge_id", "ctf_submissions", ["challenge_id"])
    op.create_index("ix_ctf_submissions_user_id", "ctf_submissions", ["user_id"])


def downgrade() -> None:
    op.drop_table("ctf_submissions")
    op.drop_table("ctf_challenges")
    op.drop_table("tools")
    op.drop_table("tool_categories")
