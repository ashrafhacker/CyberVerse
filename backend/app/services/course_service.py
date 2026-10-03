from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import course_cache
from app.models.course import Course, LearningPath, Module
from app.models.mission import Mission


class CourseService:
    @staticmethod
    async def get_course_structure(db: AsyncSession, course_id: UUID) -> dict | None:
        cache_key = f"structure:{course_id}"
        cached = await course_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await db.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.modules).selectinload(Module.lessons))
        )
        course = result.scalar_one_or_none()
        if not course:
            return None

        structure = []
        for module in sorted(course.modules, key=lambda m: m.order):
            lessons = sorted(module.lessons, key=lambda l: l.order)
            module_meta = module.meta_data or {}
            structure.append(
                {
                    "id": str(module.id),
                    "name": module.name,
                    "description": module.description,
                    "order": module.order,
                    "estimated_minutes": module.estimated_minutes,
                    "resource_type": module_meta.get("resource_type"),
                    "resource_label": module_meta.get("resource_label"),
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
                            "resources": lesson.resources or [],
                        }
                        for lesson in lessons
                    ],
                }
            )

        result_dict = {
            "id": str(course.id),
            "name": course.name,
            "description": course.description,
            "modules": structure,
        }
        
        await course_cache.set(cache_key, result_dict, ttl=600)
        return result_dict

    @staticmethod
    async def search(
        db: AsyncSession,
        query: str = "",
        difficulty: str | None = None,
        premium_only: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        cache_key = f"search:q={query}:d={difficulty}:p={premium_only}:page={page}:size={page_size}"
        cached = await course_cache.get(cache_key)
        if cached is not None:
            return cached["courses"], cached["total"]

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
        courses = list(result.scalars().all())
        
        await course_cache.set(cache_key, {"courses": courses, "total": total}, ttl=300)
        return courses, total

    @staticmethod
    async def list_learning_paths(db: AsyncSession) -> list:
        cache_key = "learning_paths:all"
        cached = await course_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await db.execute(
            select(LearningPath).where(LearningPath.status == "published").order_by(LearningPath.order)
        )
        paths = list(result.scalars().all())
        
        await course_cache.set(cache_key, paths, ttl=600)
        return paths

    @staticmethod
    async def list_missions(db: AsyncSession, mission_type: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        cache_key = f"missions:type={mission_type}:page={page}:size={page_size}"
        cached = await course_cache.get(cache_key)
        if cached is not None:
            return cached["missions"], cached["total"]

        stmt = select(Mission).where(Mission.status == "published")
        if mission_type:
            stmt = stmt.where(Mission.mission_type == mission_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Mission.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        missions = list(result.scalars().all())
        
        await course_cache.set(cache_key, {"missions": missions, "total": total}, ttl=300)
        return missions, total
