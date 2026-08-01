from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.course import Lesson, Module, Quiz, QuizAttempt, QuizQuestion
from app.schemas.base import APIResponse

router = APIRouter()


@router.get("/{lesson_id}", response_model=APIResponse[dict], summary="Get lesson content")
async def get_lesson(
    lesson_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    module_result = await db.execute(select(Module).where(Module.id == lesson.module_id))
    module = module_result.scalar_one_or_none()

    return APIResponse[dict](
        data={
            "id": str(lesson.id),
            "module_id": str(lesson.module_id),
            "module_name": module.name if module else None,
            "name": lesson.name,
            "description": lesson.description,
            "content": lesson.content,
            "resources": lesson.resources,
            "estimated_minutes": lesson.estimated_minutes,
            "xp_reward": lesson.xp_reward,
            "coins_reward": lesson.coins_reward,
            "lesson_type": lesson.lesson_type.value if hasattr(lesson.lesson_type, "value") else lesson.lesson_type,
            "is_premium": lesson.is_premium,
        }
    )


@router.get("/{lesson_id}/quiz", response_model=APIResponse[dict], summary="Get quiz for lesson")
async def get_lesson_quiz(
    lesson_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    question_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order)
    )
    questions = question_result.scalars().all()

    return APIResponse[dict](
        data={
            "id": str(quiz.id),
            "name": quiz.name,
            "description": quiz.description,
            "passing_score": quiz.passing_score,
            "max_attempts": quiz.max_attempts,
            "time_limit_minutes": quiz.time_limit_minutes,
            "xp_reward": quiz.xp_reward,
            "coins_reward": quiz.coins_reward,
            "questions": [
                {
                    "id": str(q.id),
                    "question": q.question,
                    "question_type": q.question_type,
                    "options": q.options,
                    "points": q.points,
                }
                for q in questions
            ],
        }
    )


@router.post("/{lesson_id}/quiz/submit", response_model=APIResponse[dict], summary="Submit quiz answers")
async def submit_quiz(
    lesson_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    answers: dict = None,
):
    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    question_result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id)
    )
    questions = question_result.scalars().all()

    question_map = {str(q.id): q for q in questions}
    score = 0
    max_score = sum(q.points for q in questions)
    details = []

    for qid, selected_index in (answers or {}).items():
        q = question_map.get(qid)
        if not q:
            continue
        correct = q.correct_answer.get("index") == selected_index
        if correct:
            score += q.points
        details.append(
            {
                "question_id": qid,
                "correct": correct,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
            }
        )

    passed = score / max_score * 100 >= quiz.passing_score if max_score else False

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        answers=answers or {},
        score=score,
        max_score=max_score,
        passed=passed,
    )
    db.add(attempt)
    await db.commit()

    if passed:
        from app.services.progress_service import ProgressService

        progress = await ProgressService.get_or_create_player_progress(db, user.id)
        progress.quizzes_passed += 1
        await ProgressService.award_xp(db, user.id, quiz.xp_reward, quiz.coins_reward)

    return APIResponse[dict](
        data={
            "score": score,
            "max_score": max_score,
            "percentage": round(score / max_score * 100, 1) if max_score else 0,
            "passed": passed,
            "details": details,
            "xp_rewarded": quiz.xp_reward if passed else 0,
            "coins_rewarded": quiz.coins_reward if passed else 0,
        }
    )


@router.get("/{lesson_id}/quiz/attempts", response_model=APIResponse[list], summary="List quiz attempts")
async def list_quiz_attempts(
    lesson_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    quiz_result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = quiz_result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.created_at.desc())
    )
    attempts = result.scalars().all()
    return APIResponse[list](
        data=[
            {
                "id": str(a.id),
                "score": a.score,
                "max_score": a.max_score,
                "passed": a.passed,
                "time_spent_seconds": a.time_spent_seconds,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in attempts
        ]
    )