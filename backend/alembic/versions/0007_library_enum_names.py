"""align library enum checks with ORM NAME convention

Revision ID: 0007_library_enum_names
Revises: a1b2c3d4e5f6

The application maps Python enums with SQLEnum(..., native_enum=False),
which persists member NAMES (e.g. 'ARTICLE', 'INTERMEDIATE'). The original
0002_library CHECK constraints enforced lowercase values, rejecting ORM
writes and conflicting with legacy lowercase rows. Normalize existing rows
to uppercase and rewrite the checks.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_library_enum_names"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_library_resources_type", "library_resources", type_="check")
    op.drop_constraint("ck_library_resources_difficulty", "library_resources", type_="check")
    op.execute("UPDATE library_resources SET resource_type = UPPER(resource_type)")
    op.execute("UPDATE library_resources SET difficulty = UPPER(difficulty)")
    op.create_check_constraint(
        "ck_library_resources_type",
        "library_resources",
        "resource_type IN ('ARTICLE', 'VIDEO', 'COURSE', 'BOOK', 'LAB', 'TOOL', 'PODCAST')",
    )
    op.create_check_constraint(
        "ck_library_resources_difficulty",
        "library_resources",
        "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_library_resources_type", "library_resources", type_="check")
    op.drop_constraint("ck_library_resources_difficulty", "library_resources", type_="check")
    op.execute("UPDATE library_resources SET resource_type = LOWER(resource_type)")
    op.execute("UPDATE library_resources SET difficulty = LOWER(difficulty)")
    op.create_check_constraint(
        "ck_library_resources_type",
        "library_resources",
        "resource_type IN ('article', 'video', 'course', 'book', 'lab', 'tool', 'podcast')",
    )
    op.create_check_constraint(
        "ck_library_resources_difficulty",
        "library_resources",
        "difficulty IN ('beginner', 'intermediate', 'advanced', 'expert')",
    )
