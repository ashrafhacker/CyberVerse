"""replace Razorpay metadata with YouPI defaults

Revision ID: c4f8a2e91b76
Revises: a1b2c3d4e5f6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4f8a2e91b76"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("subscriptions", "razorpay_subscription_id")
    op.drop_column("subscriptions", "razorpay_customer_id")

    op.alter_column(
        "payments",
        "provider",
        existing_type=sa.String(50),
        server_default="youpi",
        existing_nullable=False,
    )
    op.execute("UPDATE payments SET provider = 'youpi' WHERE provider = 'razorpay'")
    op.alter_column(
        "payments",
        "currency",
        existing_type=sa.String(3),
        server_default="INR",
        existing_nullable=False,
    )
    op.alter_column(
        "payments",
        "payment_method",
        existing_type=sa.String(50),
        server_default="upi",
        existing_nullable=False,
    )
    op.alter_column(
        "subscription_plans",
        "price_currency",
        existing_type=sa.String(3),
        server_default="INR",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("razorpay_subscription_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("razorpay_customer_id", sa.String(100), nullable=True),
    )
    op.create_unique_constraint(
        "uq_subscriptions_razorpay_subscription_id",
        "subscriptions",
        ["razorpay_subscription_id"],
    )

    op.alter_column(
        "payments",
        "provider",
        existing_type=sa.String(50),
        server_default="razorpay",
        existing_nullable=False,
    )
    op.alter_column(
        "payments",
        "currency",
        existing_type=sa.String(3),
        server_default="USD",
        existing_nullable=False,
    )
    op.alter_column(
        "payments",
        "payment_method",
        existing_type=sa.String(50),
        server_default="card",
        existing_nullable=False,
    )
    op.alter_column(
        "subscription_plans",
        "price_currency",
        existing_type=sa.String(3),
        server_default="USD",
        existing_nullable=False,
    )
