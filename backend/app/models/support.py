import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, enum.Enum):
    ACCOUNT = "account"
    BILLING = "billing"
    TECHNICAL = "technical"
    CONTENT = "content"
    GAMEPLAY = "gameplay"
    PREMIUM = "premium"
    OTHER = "other"


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_user_id", "user_id"),
        Index("ix_support_tickets_assignee_id", "assignee_id"),
        Index("ix_support_tickets_status", "status"),
        Index("ix_support_tickets_priority", "priority"),
        Index("ix_support_tickets_created_at", "created_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignee_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    category: Mapped[TicketCategory] = mapped_column(
        SQLEnum(TicketCategory, native_enum=False),
        default=TicketCategory.OTHER,
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(TicketPriority, native_enum=False),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, native_enum=False),
        default=TicketStatus.OPEN,
        nullable=False,
    )

    attachments: Mapped[List[Dict]] = mapped_column(JSONB, default=list, nullable=False)
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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

    user: Mapped["User"] = relationship("User", back_populates="support_tickets")  # noqa: F821
    messages: Mapped[List["TicketMessage"]] = relationship(
        "TicketMessage", back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    __table_args__ = (
        Index("ix_ticket_messages_ticket_id", "ticket_id"),
        Index("ix_ticket_messages_author_id", "author_id"),
        Index("ix_ticket_messages_created_at", "created_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_staff_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attachments: Mapped[List[Dict]] = mapped_column(JSONB, default=list, nullable=False)
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")


class FAQItem(Base):
    __tablename__ = "faq_items"
    __table_args__ = (
        Index("ix_faq_items_category", "category"),
        Index("ix_faq_items_is_published", "is_published"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    question: Mapped[str] = mapped_column(String(300), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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