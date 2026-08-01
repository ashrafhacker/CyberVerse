from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, Lesson, LearningPath, Module
from app.models.mission import Mission


class CourseService:
    @staticmethod
    async def get_course_structure(db: AsyncSession, course_id: UUID) -> dict | None:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            return None

        module_result = await db.execute(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.order)
        )
        modules = module_result.scalars().all()

        structure = []
        for module in modules:
            lesson_result = await db.execute(
                select(Lesson)
                .where(Lesson.module_id == module.id)
                .order_by(Lesson.order)
            )
            lessons = lesson_result.scalars().all()
            structure.append(
                {
                    "id": str(module.id),
                    "name": module.name,
                    "description": module.description,
                    "order": module.order,
                    "estimated_minutes": module.estimated_minutes,
                    "lessons": [
                        {
                            "id": str(lesson.id),
                            "name": lesson.name,
                            "lesson_type": lesson.lesson_type.value
                            if hasattr(lesson.lesson_type, "value") else lesson.lesson_type,
                            "order": lesson.order,
                            "estimated_minutes": lesson.estimated_minutes,
                            "xp_reward": lesson.xp_reward,
                            "is_premium": lesson.is_premium,
                        }
                        for lesson in lessons
                    ],
                }
            )

        return {
            "id": str(course.id),
            "name": course.name,
            "description": course.description,
            "modules": structure,
        }

    @staticmethod
    async def search(
        db: AsyncSession,
        query: str = "",
        difficulty: str | None = None,
        premium_only: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        stmt = select(Course).where(Course.status == "published")

        if query:
            stmt = stmt.where(Course.name.ilike(f"%{query}%"))
        if difficulty:
            stmt = stmt.where(Course.difficulty == difficulty)
        if premium_only is not None:
            stmt = stmt.where(Course.is_premium == premium_only)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Course.order).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def list_learning_paths(db: AsyncSession) -> list:
        result = await db.execute(
            select(LearningPath).where(LearningPath.status == "published").order_by(LearningPath.order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_missions(db: AsyncSession, mission_type: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        stmt = select(Mission).where(Mission.status == "published")
        if mission_type:
            stmt = stmt.where(Mission.mission_type == mission_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Mission.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total