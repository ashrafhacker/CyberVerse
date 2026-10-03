from collections import defaultdict, deque
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, OptionalUser
from app.core.config import settings
from app.core.database import get_db
from app.schemas.base import APIResponse
from app.services.ai_service import AIService

router = APIRouter()

# Lightweight in-memory sliding-window rate limiter for AI chat (per user).
_chat_buckets: dict[str, deque] = defaultdict(deque)


def _rate_limited(user_id: str) -> bool:
    window_start = monotonic() - 60
    bucket = _chat_buckets[user_id]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= settings.AI_CHAT_RATE_LIMIT_PER_MINUTE:
        return True
    bucket.append(monotonic())
    return False


class QuizGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    num_questions: int = Field(5, ge=1, le=20)
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced|expert)$")


class HintRequest(BaseModel):
    mission_name: str = Field(..., min_length=1, max_length=200)
    objective: str = Field(..., min_length=1, max_length=500)
    hint_level: int = Field(1, ge=1, le=3)


class ExplanationRequest(BaseModel):
    concept: str = Field(..., min_length=1, max_length=200)
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced|expert)$")


class ProgressAnalysisRequest(BaseModel):
    pass


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class MentorChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(..., min_length=1, max_length=30)
    current_page: str | None = None


@router.post("/chat", response_model=APIResponse[dict], summary="Chat with the AI mentor")
async def mentor_chat(
    request: MentorChatRequest,
    user: OptionalUser,
    db: AsyncSession = Depends(get_db),
):
    # For guests, we can use a hardcoded string or IP address.
    # In a real app we'd use the client IP, but for now we'll just group all guests.
    user_identifier = str(user.id) if user else "guest"
    if _rate_limited(user_identifier):
        raise HTTPException(
            status_code=429,
            detail="You are chatting too fast — pause a moment and continue.",
        )

    ai = AIService()

    # Fetch real-time progress to provide context to the mentor
    progress_info = ""
    if user:
        try:
            from app.services.progress_service import LevelSystem, ProgressService
            progress = await ProgressService.get_or_create_player_progress(db, user.id)
            level_info = LevelSystem.progress_to_next_level(progress.total_xp)
            page_context = f" They are currently looking at the page: {request.current_page}." if request.current_page else ""
            progress_info = (
                f"The user you are chatting with is Agent {user.full_name}.{page_context} "
                f"They are currently Level {level_info['level']} with {progress.total_xp} total XP. "
                f"They have completed {progress.lessons_completed} lessons, {progress.missions_completed} missions, "
                f"and {progress.labs_completed} labs. Use this real-time context to personalize your responses!"
            )
        except Exception:
            pass
    else:
        page_context = f" They are currently looking at the page: {request.current_page}." if request.current_page else ""
        progress_info = f"The user you are chatting with is a guest (unregistered).{page_context} Encourage them to create an account to track their progress!"

    history = [turn.model_dump() for turn in request.messages[-settings.AI_CHAT_HISTORY_LIMIT :]]
    try:
        result = await ai.chat(history, context=progress_info)
    except Exception as e:
        import logging
        # If DB is degraded (progress fetch failed), still try chat without context rather than 503
        is_db_error = any(kw in str(e) for kw in ["WinError 1225", "ConnectionRefused", "asyncpg", "pool"])
        if is_db_error:
            logging.warning(f"AI chat DB degraded, retrying without context: {e}")
            try:
                result = await ai.chat(history, context="")
                return APIResponse[dict](data=result)
            except Exception as e2:
                logging.exception(f"AI Chat retry failed: {e2}")
        # Let AIService._chat() handle provider fallbacks (including offline fallback).
        # Only raise 503 for truly unexpected errors not handled by the service.
        logging.exception(f"AI Chat error: {e}")
        raise HTTPException(
            status_code=503,
            detail="The AI mentor is temporarily unavailable — try again in a moment.",
        )
    return APIResponse[dict](data=result)


@router.post("/quiz", response_model=APIResponse[dict], summary="Generate a quiz with AI")
async def generate_quiz(
    request: QuizGenerateRequest,
    user: CurrentUser,
):
    ai = AIService()
    quiz = await ai.generate_quiz(request.topic, request.num_questions, request.difficulty)
    return APIResponse[dict](data=quiz)


@router.post("/hint", response_model=APIResponse[dict], summary="Generate a mission hint")
async def generate_hint(
    request: HintRequest,
    user: CurrentUser,
):
    ai = AIService()
    hint = await ai.generate_hint(request.mission_name, request.objective, request.hint_level)
    return APIResponse[dict](data={"hint": hint})


@router.post("/explain", response_model=APIResponse[dict], summary="Explain a cybersecurity concept")
async def explain_concept(
    request: ExplanationRequest,
    user: CurrentUser,
):
    ai = AIService()
    explanation = await ai.generate_explanation(request.concept, request.difficulty)
    return APIResponse[dict](data={"explanation": explanation})


@router.post("/analyze", response_model=APIResponse[dict], summary="Analyze user progress")
async def analyze_progress(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    ai = AIService()
    analysis = await ai.analyze_progress(db, user.id)
    return APIResponse[dict](data=analysis)


@router.get("/recommendations", response_model=APIResponse[list], summary="Get AI learning recommendations")
async def get_recommendations(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(3, ge=1, le=10),
):
    ai = AIService()
    recommendations = await ai.recommend_learning_path(db, user.id, top_n=limit)
    return APIResponse[list](data=recommendations)
