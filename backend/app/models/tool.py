from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, FlexibleArray


class ToolCategory(Base):
    __tablename__ = "tool_categories"
    __table_args__ = (Index("ix_tool_categories_slug", "slug", unique=True),)

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    tools: Mapped[list["Tool"]] = relationship(back_populates="category")


class Tool(Base):
    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("name", name="uq_tools_name"),
        Index("ix_tools_category_id", "category_id"),
        Index("ix_tools_slug", "slug", unique=True),
        Index("ix_tools_license", "license_name"),
        Index("ix_tools_published", "is_published"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tool_categories.id", ondelete="RESTRICT"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    license_name: Mapped[str] = mapped_column(String(120), nullable=False)
    open_source: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    free_tier: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supported_os: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(40), default="beginner", nullable=False
    )
    official_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    docs_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tutorial_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lab_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tags: Mapped[list] = mapped_column(FlexibleArray(str), default=list, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    category: Mapped[ToolCategory] = relationship(back_populates="tools")
