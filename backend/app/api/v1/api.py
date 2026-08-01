from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    profile,
    progress,
    missions,
    courses,
    lessons,
    ai,
    chat,
    leaderboard,
    notifications,
    admin,
    instructor,
    settings_router,
    premium,
    analytics,
    support,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
api_router.include_router(progress.router, prefix="/progress", tags=["Progress"])
api_router.include_router(missions.router, prefix="/missions", tags=["Missions"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(lessons.router, prefix="/lessons", tags=["Lessons"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(instructor.router, prefix="/instructor", tags=["Instructor"])
api_router.include_router(settings_router.router, prefix="/settings", tags=["Settings"])
api_router.include_router(premium.router, prefix="/premium", tags=["Premium"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(support.router, prefix="/support", tags=["Support"])