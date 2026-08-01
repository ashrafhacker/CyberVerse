import enum
from datetime import datetime, timezone
from typing import Optional, Dict
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    Numeric,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlanTier(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    LIFETIME = "lifetime"


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (
        Index("ix_subscription_plans_slug", "slug", unique=True),
        Index("ix_subscription_plans_is_active", "is_active"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    tier: Mapped[PlanTier] = mapped_column(
        SQLEnum(PlanTier, native_enum=False),
        default=PlanTier.MONTHLY,
        nullable=False,
    )

    price_amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), default="month", nullable=False)
    billing_interval_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    permissions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    subscriptions: Mapped[list] = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_id", "user_id"),
        Index("ix_subscriptions_plan_id", "plan_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_current_period_end", "current_period_end"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus, native_enum=False),
        default=SubscriptionStatus.PENDING,
        nullable=False,
    )

    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    trial_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")  # noqa: F821
    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan", back_populates="subscriptions")
    payments: Mapped[list] = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_user_id", "user_id"),
        Index("ix_payments_subscription_id", "subscription_id"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_created_at", "created_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    payment_intent_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="card", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="stripe", nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")  # noqa: F821
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="payments")


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        Index("ix_coupons_code", "code", unique=True),
        Index("ix_coupons_is_active", "is_active"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    discount_type: Mapped[str] = mapped_column(String(20), default="percentage", nullable=False)  # percentage, fixed
    discount_value: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)

    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )