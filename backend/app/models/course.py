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
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ContentType(str, enum.Enum):
    COURSE = "course"
    MODULE = "module"
    LESSON = "lesson"
    MISSION = "mission"
    QUIZ = "quiz"
    LAB = "lab"


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LearningPath(Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        Index("ix_learning_paths_slug", "slug", unique=True),
        Index("ix_learning_paths_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)

    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel, native_enum=False),
        default=DifficultyLevel.BEGINNER,
        nullable=False,
    )
    estimated_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    prerequisites: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    learning_objectives: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    status: Mapped[ContentStatus] = mapped_column(
        SQLEnum(ContentStatus, native_enum=False),
        default=ContentStatus.DRAFT,
        nullable=False,
    )
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="learning_path", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        Index("ix_courses_slug", "slug", unique=True),
        Index("ix_courses_learning_path_id", "learning_path_id"),
        Index("ix_courses_status", "status"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    learning_path_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)

    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel, native_enum=False),
        default=DifficultyLevel.BEGINNER,
        nullable=False,
    )
    estimated_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    prerequisites: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    learning_objectives: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    status: Mapped[ContentStatus] = mapped_column(
        SQLEnum(ContentStatus, native_enum=False),
        default=ContentStatus.DRAFT,
        nullable=False,
    )
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    certificate_template_id: Mapped[Optional[PGUUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("certificate_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    learning_path: Mapped[Optional["LearningPath"]] = relationship("LearningPath", back_populates="courses")
    modules: Mapped[List["Module"]] = relationship(
        "Module", back_populates="course", cascade="all, delete-orphan", order_by="Module.order"
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )
    certificate_template: Mapped[Optional["CertificateTemplate"]] = relationship(
        "CertificateTemplate", back_populates="courses"
    )


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        Index("ix_modules_course_id", "course_id"),
        Index("ix_modules_order", "course_id", "order"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)

    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    course: Mapped["Course"] = relationship("Course", back_populates="modules")
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        Index("ix_lessons_module_id", "module_id"),
        Index("ix_lessons_order", "module_id", "order"),
        Index("ix_lessons_type", "lesson_type"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    module_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False,
    )

    lesson_type: Mapped[ContentType] = mapped_column(
        SQLEnum(ContentType, native_enum=False),
        default=ContentType.LESSON,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)

    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    resources: Mapped[List[dict]] = mapped_column(JSONB, default=list, nullable=False)

    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlock_requirements: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    module: Mapped["Module"] = relationship("Module", back_populates="lessons")
    progress: Mapped[List["LessonProgress"]] = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )
    quiz: Mapped[Optional["Quiz"]] = relationship(
        "Quiz", back_populates="lesson", uselist=False, cascade="all, delete-orphan"
    )


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        Index("ix_quizzes_lesson_id", "lesson_id", unique=True),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    lesson_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    passing_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_explanations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="quiz")
    questions: Mapped[List["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.order"
    )
    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        Index("ix_quiz_questions_quiz_id", "quiz_id"),
        Index("ix_quiz_questions_order", "quiz_id", "order"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    quiz_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(String(50), nullable=False)  # single, multiple, true_false, fill_blank
    question: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    options: Mapped[List[dict]] = mapped_column(JSONB, default=list, nullable=False)
    correct_answer: Mapped[dict] = mapped_column(JSONB, nullable=False)

    points: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

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

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_quiz_id_user_id", "quiz_id", "user_id"),
        Index("ix_quiz_attempts_completed_at", "completed_at"),
    )

    id: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    quiz_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[PGUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    answers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")