from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_instructor
from app.core.database import get_db
from app.models.course import (
    ContentStatus,
    DifficultyLevel,
    Course,
    Lesson,
    Module,
    Quiz,
    QuizQuestion,
)
from app.models.progress import Enrollment, LessonProgress
from app.models.user import User
from app.schemas.base import APIResponse, MessageResponse

router = APIRouter()


class CourseCreate(BaseModel):
    learning_path_id: UUID | None = None
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    short_description: str = Field(..., min_length=5, max_length=500)
    difficulty: str = Field(DifficultyLevel.BEGINNER.value, max_length=20)
    estimated_hours: int = Field(0, ge=0, le=1000)
    prerequisites: list[str] = []
    learning_objectives: list[str] = []
    tags: list[str] = []
    is_premium: bool = False


class CourseUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, min_length=10)
    short_description: str | None = Field(None, min_length=5, max_length=500)
    difficulty: str | None = Field(None, max_length=20)
    estimated_hours: int | None = Field(None, ge=0, le=1000)
    prerequisites: list[str] | None = None
    learning_objectives: list[str] | None = None
    tags: list[str] | None = None
    is_premium: bool | None = None


class ModuleCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5)
    short_description: str = Field("", max_length=500)
    estimated_minutes: int = Field(0, ge=0)
    order: int = Field(0, ge=0)
    is_optional: bool = False


class LessonCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=5000)
    short_description: str = Field("", max_length=500)
    lesson_type: str = Field("lesson", max_length=50)
    content: dict = {}
    estimated_minutes: int = Field(10, ge=0)
    xp_reward: int = Field(10, ge=0)
    coins_reward: int = Field(5, ge=0)
    order: int = Field(0, ge=0)
    is_premium: bool = False


class LessonUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, max_length=5000)
    content: dict | None = None
    estimated_minutes: int | None = Field(None, ge=0)
    xp_reward: int | None = Field(None, ge=0)
    coins_reward: int | None = Field(None, ge=0)
    order: int | None = Field(None, ge=0)
    is_locked: bool | None = None


class QuizCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=2000)
    passing_score: int = Field(70, ge=0, le=100)
    max_attempts: int = Field(3, ge=1, le=20)
    time_limit_minutes: int | None = Field(None, ge=1, le=300)
    shuffle_questions: bool = True
    xp_reward: int = Field(50, ge=0)
    coins_reward: int = Field(20, ge=0)


class QuestionCreate(BaseModel):
    question_type: str = Field(..., max_length=50)
    question: str = Field(..., min_length=3)
    explanation: str | None = Field(None, max_length=3000)
    options: list[dict] = []
    correct_answer: dict
    points: int = Field(1, ge=1, le=100)
    order: int = Field(0, ge=0)


async def _get_course_or_404(db: AsyncSession, course_id: UUID) -> Course:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


async def _get_module_or_404(db: AsyncSession, module_id: UUID) -> Module:
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


async def _get_lesson_or_404(db: AsyncSession, lesson_id: UUID) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def _serialize_course(course: Course) -> dict:
    return {
        "id": str(course.id),
        "name": course.name,
        "description": course.description,
        "short_description": course.short_description,
        "difficulty": course.difficulty.value,
        "estimated_hours": course.estimated_hours,
        "status": course.status.value,
        "is_premium": course.is_premium,
        "order": course.order,
        "tags": course.tags,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }


@router.get("/stats", response_model=APIResponse[dict], summary="Instructor statistics")
async def instructor_stats(
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    my_courses = (
        await db.execute(select(func.count(Course.id)).where(Course.creator_id == user.id))
    ).scalar_one()

    total_enrollments = 0
    total_lessons = 0
    avg_completion = 0.0

    courses = (
        await db.execute(
            select(Course).where(Course.creator_id == user.id).order_by(Course.created_at.desc())
        )
    ).scalars().all()

    for course in courses:
        enrolled = (
            await db.execute(select(func.count(Enrollment.id)).where(Enrollment.course_id == course.id))
        ).scalar_one()
        total_enrollments += enrolled
        lessons_count = (
            await db.execute(
                select(func.count(Lesson.id))
                .join(Module, Module.id == Lesson.module_id)
                .where(Module.course_id == course.id)
            )
        ).scalar_one()
        total_lessons += lessons_count
        if enrolled > 0:
            sum_pct = (
                await db.execute(
                    select(func.coalesce(func.sum(Enrollment.progress_percentage), 0)).where(
                        Enrollment.course_id == course.id
                    )
                )
            ).scalar_one()
            avg_completion += sum_pct / enrolled

    if len(courses) > 0:
        avg_completion /= len(courses)

    return APIResponse[dict](
        data={
            "my_courses": my_courses,
            "total_enrollments": total_enrollments,
            "total_lessons": total_lessons,
            "average_completion": round(avg_completion, 1),
            "courses": [_serialize_course(c) for c in courses],
        }
    )


@router.post("/courses", response_model=APIResponse[dict], summary="Create a course")
async def create_course(
    payload: CourseCreate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    slug = payload.name.lower().replace(" ", "-").replace("_", "-")[:100]
    existing = await db.execute(select(Course).where(Course.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A course with this name already exists")

    course = Course(
        creator_id=user.id,
        learning_path_id=payload.learning_path_id,
        slug=slug,
        name=payload.name,
        description=payload.description,
        short_description=payload.short_description,
        difficulty=DifficultyLevel(payload.difficulty),
        estimated_hours=payload.estimated_hours,
        prerequisites=payload.prerequisites,
        learning_objectives=payload.learning_objectives,
        tags=payload.tags,
        is_premium=payload.is_premium,
        status=ContentStatus.DRAFT,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return APIResponse[dict](message="Course created as draft", data=_serialize_course(course))


@router.put("/courses/{course_id}", response_model=APIResponse[dict], summary="Update a course")
async def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course_or_404(db, course_id)
    if str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only edit your own courses")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(course, key, value)
    await db.commit()
    await db.refresh(course)
    return APIResponse[dict](message="Course updated", data=_serialize_course(course))


@router.post("/courses/{course_id}/publish", response_model=APIResponse[dict], summary="Publish a course")
async def publish_course(
    course_id: UUID,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course_or_404(db, course_id)
    if str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only publish your own courses")
    course.status = ContentStatus.PUBLISHED
    await db.commit()
    return APIResponse[dict](message="Course published", data=_serialize_course(course))


@router.post("/courses/{course_id}/modules", response_model=APIResponse[dict], summary="Add a module")
async def create_module(
    course_id: UUID,
    payload: ModuleCreate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_course_or_404(db, course_id)
    if str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only edit your own courses")

    module = Module(
        course_id=course.id,
        name=payload.name,
        description=payload.description,
        short_description=payload.short_description,
        estimated_minutes=payload.estimated_minutes,
        order=payload.order,
        is_optional=payload.is_optional,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return APIResponse[dict](
        message="Module created",
        data={
            "id": str(module.id),
            "course_id": str(module.course_id),
            "name": module.name,
            "order": module.order,
        },
    )


@router.post("/modules/{module_id}/lessons", response_model=APIResponse[dict], summary="Add a lesson")
async def create_lesson(
    module_id: UUID,
    payload: LessonCreate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    module = await _get_module_or_404(db, module_id)
    course = await db.get(Course, module.course_id)
    if course and str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only edit your own courses")

    lesson = Lesson(
        module_id=module.id,
        lesson_type=payload.lesson_type,
        name=payload.name,
        description=payload.description,
        short_description=payload.short_description,
        content=payload.content,
        estimated_minutes=payload.estimated_minutes,
        xp_reward=payload.xp_reward,
        coins_reward=payload.coins_reward,
        order=payload.order,
        is_premium=payload.is_premium,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return APIResponse[dict](
        message="Lesson created",
        data={
            "id": str(lesson.id),
            "module_id": str(lesson.module_id),
            "name": lesson.name,
            "order": lesson.order,
            "xp_reward": lesson.xp_reward,
        },
    )


@router.put("/lessons/{lesson_id}", response_model=APIResponse[dict], summary="Update a lesson")
async def update_lesson(
    lesson_id: UUID,
    payload: LessonUpdate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lesson = await _get_lesson_or_404(db, lesson_id)
    module = await db.get(Module, lesson.module_id)
    course = await db.get(Course, module.course_id)
    if course and str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only edit your own courses")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(lesson, key, value)
    await db.commit()
    return APIResponse[dict](message="Lesson updated")


@router.post("/lessons/{lesson_id}/quiz", response_model=APIResponse[dict], summary="Attach a quiz to a lesson")
async def create_quiz(
    lesson_id: UUID,
    payload: QuizCreate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lesson = await _get_lesson_or_404(db, lesson_id)
    module = await db.get(Module, lesson.module_id)
    course = await db.get(Course, module.course_id)
    if course and str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only edit your own courses")

    existing = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Lesson already has a quiz")

    quiz = Quiz(
        lesson_id=lesson.id,
        name=payload.name,
        description=payload.description,
        passing_score=payload.passing_score,
        max_attempts=payload.max_attempts,
        time_limit_minutes=payload.time_limit_minutes,
        shuffle_questions=payload.shuffle_questions,
        xp_reward=payload.xp_reward,
        coins_reward=payload.coins_reward,
    )
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    return APIResponse[dict](
        message="Quiz created",
        data={"id": str(quiz.id), "lesson_id": str(quiz.lesson_id), "name": quiz.name},
    )


@router.post("/quizzes/{quiz_id}/questions", response_model=APIResponse[dict], summary="Add a question to a quiz")
async def add_question(
    quiz_id: UUID,
    payload: QuestionCreate,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    lesson = await db.get(Lesson, quiz.lesson_id)
    module = await db.get(Module, lesson.module_id)
    course = await db.get(Course, module.course_id)
    if course and str(course.creator_id) != str(user.id) and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="You can only edit your own courses")

    question = QuizQuestion(
        quiz_id=quiz.id,
        question_type=payload.question_type,
        question=payload.question,
        explanation=payload.explanation,
        options=payload.options,
        correct_answer=payload.correct_answer,
        points=payload.points,
        order=payload.order,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return APIResponse[dict](
        message="Question added",
        data={"id": str(question.id), "quiz_id": str(question.quiz_id)},
    )


@router.get("/lessons/{lesson_id}/progress", response_model=APIResponse[dict], summary="Lesson analytics")
async def lesson_progress(
    lesson_id: UUID,
    user: CurrentUser = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lesson = await _get_lesson_or_404(db, lesson_id)
    total = (
        await db.execute(select(func.count(LessonProgress.id)).where(LessonProgress.lesson_id == lesson.id))
    ).scalar_one()
    completed = (
        await db.execute(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.lesson_id == lesson.id,
                LessonProgress.status == "completed",
            )
        )
    ).scalar_one()

    return APIResponse[dict](
        data={
            "lesson_id": str(lesson.id),
            "total_students": total,
            "completed": completed,
            "completion_rate": round((completed / total * 100) if total else 0, 1),
        }
    )
