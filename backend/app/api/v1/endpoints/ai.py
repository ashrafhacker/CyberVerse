from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.base import APIResponse
from app.services.ai_service import AIService

router = APIRouter()


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