"""
Learning Celery Tasks Package.

Re-exports learning-related Celery tasks for the CyberVerse platform.
"""

from app.tasks import rotate_daily_challenges, rotate_weekly_challenges

__all__ = ["rotate_daily_challenges", "rotate_weekly_challenges"]
