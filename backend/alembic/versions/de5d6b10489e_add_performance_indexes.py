"""add_performance_indexes

Revision ID: de5d6b10489e
Revises: 0006_skills
Create Date: 2026-09-28 13:13:39.680515

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de5d6b10489e'
down_revision: Union[str, None] = '0006_skills'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _safe_index(name, table, cols):
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return
    tcols = [c["name"] for c in insp.get_columns(table)]
    if all(c in tcols for c in cols):
        existing = [ix["name"] for ix in insp.get_indexes(table)]
        if name not in existing:
            try:
                op.create_index(name, table, cols)
            except Exception:
                pass



def upgrade() -> None:
    # Courses - composite indexes for common query patterns
    _safe_index("ix_courses_status_difficulty", "courses", ["status", "difficulty"])
    _safe_index("ix_courses_status_is_premium", "courses", ["status", "is_premium"])
    _safe_index("ix_courses_status_order", "courses", ["status", "order"])
    _safe_index("ix_courses_learning_path_status", "courses", ["learning_path_id", "status"])
    
    # Modules - composite indexes for course structure queries
    _safe_index("ix_modules_course_id_order", "modules", ["course_id", "order"])
    
    # Lessons - composite indexes for module structure queries
    _safe_index("ix_lessons_module_id_order", "lessons", ["module_id", "order"])
    _safe_index("ix_lessons_module_id_type", "lessons", ["module_id", "lesson_type"])
    
    # Enrollments - composite indexes for user course queries
    _safe_index("ix_enrollments_user_id_status", "enrollments", ["user_id", "status"])
    _safe_index("ix_enrollments_course_id_status", "enrollments", ["course_id", "status"])
    
    # Lesson Progress - composite indexes for user progress queries
    _safe_index("ix_lesson_progress_user_id_status", "lesson_progress", ["user_id", "status"])
    _safe_index("ix_lesson_progress_lesson_id_status", "lesson_progress", ["lesson_id", "status"])
    
    # Player Progress - composite indexes for leaderboard queries
    _safe_index("ix_player_progress_user_id_updated_at", "player_progress", ["user_id", "updated_at"])
    _safe_index("ix_player_progress_total_xp", "player_progress", ["total_xp"])
    _safe_index("ix_player_progress_current_level", "player_progress", ["current_level"])
    
    # Users - composite indexes for auth and admin queries
    _safe_index("ix_users_email_status", "users", ["email", "status"])
    _safe_index("ix_users_role_status", "users", ["role", "status"])
    _safe_index("ix_users_provider_provider_id", "users", ["provider", "provider_id"])
    
    # Quizzes - composite indexes for quiz queries
    _safe_index("ix_quizzes_lesson_id", "quizzes", ["lesson_id"])
    
    # Quiz Attempts - composite indexes for user quiz history
    _safe_index("ix_quiz_attempts_user_id_completed_at", "quiz_attempts", ["user_id", "completed_at"])
    _safe_index("ix_quiz_attempts_quiz_id_user_id", "quiz_attempts", ["quiz_id", "user_id"])
    
    # Missions - composite indexes for mission listing
    _safe_index("ix_missions_status_type", "missions", ["status", "mission_type"])
    _safe_index("ix_missions_status_created_at", "missions", ["status", "created_at"])
    
    # Learning Paths - composite indexes
    _safe_index("ix_learning_paths_status_order", "learning_paths", ["status", "order"])
    
    # Notifications - composite indexes for user notifications
    _safe_index("ix_notifications_user_id_read_created", "notifications", ["user_id", "is_read", "created_at"])
    _safe_index("ix_notifications_user_id_type", "notifications", ["user_id", "notification_type"])
    
    # Threat Intel - composite indexes
    _safe_index("ix_threat_intel_status_severity", "threat_intel", ["status", "severity"])
    _safe_index("ix_threat_intel_type_severity", "threat_intel", ["type", "severity"])
    
    # CTF Challenges - composite indexes
    _safe_index("ix_ctf_challenges_status_category", "ctf_challenges", ["status", "category"])
    _safe_index("ix_ctf_challenges_status_difficulty", "ctf_challenges", ["status", "difficulty"])
    
    # Labs - composite indexes
    _safe_index("ix_labs_status_type", "labs", ["status", "type"])
    _safe_index("ix_labs_status_difficulty", "labs", ["status", "difficulty"])
    
    # Lab Sessions - composite indexes
    _safe_index("ix_lab_sessions_user_id_status", "lab_sessions", ["user_id", "status"])
    _safe_index("ix_lab_sessions_lab_id_status", "lab_sessions", ["lab_id", "status"])
    
    # Certificates - composite indexes
    _safe_index("ix_certificates_user_id_course_id", "certificates", ["user_id", "course_id"])
    _safe_index("ix_certificates_verification_code", "certificates", ["verification_code"])
    
    # Analytics - composite indexes
    _safe_index("ix_analytics_user_id_event_type", "analytics", ["user_id", "event_type"])
    _safe_index("ix_analytics_event_type_created_at", "analytics", ["event_type", "created_at"])
    
    # Sessions - composite indexes
    _safe_index("ix_sessions_user_id_expires_at", "sessions", ["user_id", "expires_at"])
    _safe_index("ix_sessions_refresh_token", "sessions", ["refresh_token"])
    
    # Social - composite indexes
    _safe_index("ix_friends_user_id_status", "friends", ["user_id", "status"])
    _safe_index("ix_friends_friend_id_status", "friends", ["friend_id", "status"])


def downgrade() -> None:
    # Drop all indexes in reverse order
    op.drop_index("ix_friends_friend_id_status", table_name="friends")
    op.drop_index("ix_friends_user_id_status", table_name="friends")
    op.drop_index("ix_sessions_refresh_token", table_name="sessions")
    op.drop_index("ix_sessions_user_id_expires_at", table_name="sessions")
    op.drop_index("ix_analytics_event_type_created_at", table_name="analytics")
    op.drop_index("ix_analytics_user_id_event_type", table_name="analytics")
    op.drop_index("ix_certificates_verification_code", table_name="certificates")
    op.drop_index("ix_certificates_user_id_course_id", table_name="certificates")
    op.drop_index("ix_lab_sessions_lab_id_status", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_user_id_status", table_name="lab_sessions")
    op.drop_index("ix_labs_status_difficulty", table_name="labs")
    op.drop_index("ix_labs_status_type", table_name="labs")
    op.drop_index("ix_ctf_challenges_status_difficulty", table_name="ctf_challenges")
    op.drop_index("ix_ctf_challenges_status_category", table_name="ctf_challenges")
    op.drop_index("ix_threat_intel_type_severity", table_name="threat_intel")
    op.drop_index("ix_threat_intel_status_severity", table_name="threat_intel")
    op.drop_index("ix_notifications_user_id_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id_read_created", table_name="notifications")
    op.drop_index("ix_learning_paths_status_order", table_name="learning_paths")
    op.drop_index("ix_missions_status_created_at", table_name="missions")
    op.drop_index("ix_missions_status_type", table_name="missions")
    op.drop_index("ix_quiz_attempts_quiz_id_user_id", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_user_id_completed_at", table_name="quiz_attempts")
    op.drop_index("ix_quizzes_lesson_id", table_name="quizzes")
    op.drop_index("ix_users_provider_provider_id", table_name="users")
    op.drop_index("ix_users_role_status", table_name="users")
    op.drop_index("ix_users_email_status", table_name="users")
    op.drop_index("ix_player_progress_current_level", table_name="player_progress")
    op.drop_index("ix_player_progress_total_xp", table_name="player_progress")
    op.drop_index("ix_player_progress_user_id_updated_at", table_name="player_progress")
    op.drop_index("ix_lesson_progress_lesson_id_status", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_user_id_status", table_name="lesson_progress")
    op.drop_index("ix_enrollments_course_id_status", table_name="enrollments")
    op.drop_index("ix_enrollments_user_id_status", table_name="enrollments")
    op.drop_index("ix_lessons_module_id_type", table_name="lessons")
    op.drop_index("ix_lessons_module_id_order", table_name="lessons")
    op.drop_index("ix_modules_course_id_order", table_name="modules")
    op.drop_index("ix_courses_learning_path_status", table_name="courses")
    op.drop_index("ix_courses_status_order", table_name="courses")
    op.drop_index("ix_courses_status_is_premium", table_name="courses")
    op.drop_index("ix_courses_status_difficulty", table_name="courses")
