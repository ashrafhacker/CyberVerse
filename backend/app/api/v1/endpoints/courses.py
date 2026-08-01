from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.course import Course, Lesson, Module, Quiz
from app.schemas.base import APIResponse, PaginatedResponse
from app.services.course_service import CourseService

router = APIRouter()


@router.get("/", response_model=APIResponse[PaginatedResponse], summary="Search/list courses")
async def list_courses(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    difficulty: str = Query(None),
):
    courses, total = await CourseService.search(
        db,
        query=search or "",
        difficulty=difficulty,
        page=page,
        page_size=page_size,
    )

    items = [
        {
            "id": str(c.id),
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "short_description": c.short_description,
            "difficulty": c.difficulty.value if hasattr(c.difficulty, "value") else c.difficulty,
            "estimated_hours": c.estimated_hours,
            "thumbnail_url": c.thumbnail_url,
            "is_premium": c.is_premium,
            "tags": c.tags,
        }
        for c in courses
    ]

    data = PaginatedResponse.create(items, total, page, page_size)
    return APIResponse[PaginatedResponse](data=data)


@router.get("/learning-paths", response_model=APIResponse[list], summary="List learning paths")
async def list_learning_paths(
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    paths = await CourseService.list_learning_paths(db)
    return APIResponse[list](
        data=[
            {
                "id": str(p.id),
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "difficulty": p.difficulty.value if hasattr(p.difficulty, "value") else p.difficulty,
                "estimated_hours": p.estimated_hours,
                "is_premium": p.is_premium,
                "order": p.order,
            }
            for p in paths
        ]
    )


@router.get("/{course_id}", response_model=APIResponse[dict], summary="Get course with structure")
async def get_course(
    course_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    structure = await CourseService.get_course_structure(db, course_id)
    if not structure:
        raise HTTPException(status_code=404, detail="Course not found")

    return APIResponse[dict](
        data={
            **structure,
            "slug": course.slug,
            "difficulty": course.difficulty.value if hasattr(course.difficulty, "value") else course.difficulty,
            "estimated_hours": course.estimated_hours,
            "is_premium": course.is_premium,
            "tags": course.tags,
            "learning_objectives": course.learning_objectives,
            "is_enrolled": True,
        }
    )


@router.post("/{course_id}/enroll", response_model=APIResponse[dict], summary="Enroll in a course")
async def enroll_course(
    course_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.exc import IntegrityError

    from app.models.progress import Enrollment

    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.course_id == course_id,
        )
    )
    if existing.scalar_one_or_none():
        return APIResponse[dict](data={"enrolled": True, "message": "Already enrolled"})

    try:
        enrollment = Enrollment(user_id=user.id, course_id=course_id, status="in_progress")
        db.add(enrollment)
        await db.commit()
    except IntegrityError:
        await db.rollback()

    return APIResponse[dict](data={"enrolled": True, "message": "Enrolled successfully"})


@router.get("/{course_id}/quiz", response_model=APIResponse[dict], summary="Get course quiz")
async def get_course_quiz(
    course_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Quiz)
        .join(Lesson, Lesson.id == Quiz.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this course")
    return APIResponse[dict](data={"id": str(quiz.id), "name": quiz.name})