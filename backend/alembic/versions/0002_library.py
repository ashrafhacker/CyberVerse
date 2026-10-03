"""add library resources table

Revision ID: 0002_library
Revises: 0001_initial
Create Date: 2026-08-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_library"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "library_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False, server_default="article"),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="beginner"),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "resource_type IN ('article', 'video', 'course', 'book', 'lab', 'tool', 'podcast')",
            name="ck_library_resources_type",
        ),
        sa.CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced', 'expert')",
            name="ck_library_resources_difficulty",
        ),
    )
    op.create_index("ix_library_resources_category", "library_resources", ["category"])
    op.create_index("ix_library_resources_type", "library_resources", ["resource_type"])
    op.create_index("ix_library_resources_published", "library_resources", ["is_published"])


def downgrade() -> None:
    op.drop_index("ix_library_resources_published", table_name="library_resources")
    op.drop_index("ix_library_resources_type", table_name="library_resources")
    op.drop_index("ix_library_resources_category", table_name="library_resources")
    op.drop_table("library_resources")
