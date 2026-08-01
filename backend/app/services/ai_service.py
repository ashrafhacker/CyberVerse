import json
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisClient
from app.models.user import Profile, User
from app.services.progress_service import LevelSystem, ProgressService


class AIService:
    """AI Mentor service — quiz generation, hints, explanations, recommendations."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _chat(
        self,
        messages: list[dict],
        temperature: float = settings.OPENAI_TEMPERATURE,
        max_tokens: int = settings.OPENAI_MAX_TOKENS,
    ) -> str:
        if not self.api_key:
            return self._fallback_response(messages)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._headers,
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @staticmethod
    def _fallback_response(messages: list[dict]) -> str:
        """Deterministic fallback when no API key is configured."""
        last = messages[-1] if messages else {"content": ""}
        prompt = last.get("content", "").lower()

        if "hint" in prompt or "hint" in str(messages[0].get("content", "")):
            return (
                "CyberVerse Mentor: Break the problem into smaller steps. "
                "Review the related lesson, check the hint objectives, and think about "
                "what tool or command maps to the objective. You can do this!"
            )
        if "quiz" in prompt:
            return "CyberVerse Mentor: Write 5 questions about the lesson topic with 4 answer choices each."
        return (
            "CyberVerse Mentor: Keep practicing! Review the lesson materials, "
            "try the practice lab, and come back with specific questions. "
            "Configure an OPENAI_API_KEY to unlock full AI guidance."
        )

    async def generate_quiz(self, topic: str, num_questions: int = 5, difficulty: str = "beginner") -> dict:
        cache_key = f"ai:quiz:{topic}:{num_questions}:{difficulty}"
        cached = await RedisClient.cache_get_json(cache_key)
        if cached:
            return cached

        system = (
            "You are the CyberVerse AI Mentor. Generate an educational quiz about cybersecurity. "
            "Return STRICT JSON: {\"questions\": [{\"question\": str, \"options\": [4 strings], "
            "\"correct_index\": int, \"explanation\": str}]}. Topic: " + topic +
            f". Difficulty: {difficulty}. Number of questions: {num_questions}."
        )

        content = await self._chat([{"role": "system", "content": system}])

        try:
            if content.strip().startswith("```"):
                content = content.strip().strip("`")
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            await RedisClient.cache_set_json(cache_key, result, ttl=60 * 60)
            return result
        except json.JSONDecodeError:
            return {
                "questions": [
                    {
                        "question": f"Which of the following best describes {topic}?",
                        "options": ["Concept overview", "Unrelated option", "Unrelated option", "Unrelated option"],
                        "correct_index": 0,
                        "explanation": "Review the lesson materials for a full explanation.",
                    }
                ]
            }

    async def generate_hint(self, mission_name: str, objective: str, hint_level: int = 1) -> str:
        system = (
            "You are the CyberVerse AI Mentor. Provide a single progressive hint for a cybersecurity "
            f"training mission called '{mission_name}'. Objective: {objective}. Hint level: {hint_level} "
            "(1 = vague nudge, 2 = specific direction, 3 = near-answer). Keep it under 120 words."
        )
        return await self._chat([{"role": "system", "content": system}], temperature=0.5)

    async def generate_explanation(self, concept: str, difficulty: str = "beginner") -> str:
        system = (
            f"Explain the cybersecurity concept '{concept}' to a {difficulty} learner. "
            "Use a real-world analogy, 3 key points, and 1 practice suggestion. Under 200 words."
        )
        return await self._chat([{"role": "system", "content": system}])

    async def recommend_learning_path(
        self,
        db: AsyncSession,
        user_id: UUID,
        top_n: int = 3,
    ) -> list[dict]:
        """Personalized learning recommendation based on user progress."""
        profile_result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()

        progress = await ProgressService.get_or_create_player_progress(db, user_id)
        stats = progress.statistics or {}

        level = LevelSystem.level_from_xp(progress.total_xp)
        completed_categories = stats.get("completed_categories", {})

        # Catalog of learning paths with difficulty mapping
        catalog = [
            {"slug": "cybersecurity-fundamentals", "name": "Cybersecurity Fundamentals", "difficulty": 1},
            {"slug": "networking", "name": "Networking", "difficulty": 1},
            {"slug": "linux-basics", "name": "Linux Basics", "difficulty": 1},
            {"slug": "windows-admin", "name": "Windows Administration", "difficulty": 2},
            {"slug": "programming", "name": "Programming Fundamentals", "difficulty": 1},
            {"slug": "web-security", "name": "Web Security", "difficulty": 2},
            {"slug": "cloud-security", "name": "Cloud Security", "difficulty": 2},
            {"slug": "digital-forensics", "name": "Digital Forensics", "difficulty": 3},
            {"slug": "incident-response", "name": "Incident Response", "difficulty": 3},
            {"slug": "threat-hunting", "name": "Threat Hunting", "difficulty": 3},
            {"slug": "security-operations", "name": "Security Operations", "difficulty": 3},
            {"slug": "governance", "name": "Governance & Compliance", "difficulty": 2},
        ]

        user_difficulty = min(4, max(1, (level - 1) // 10 + 1))

        recommended = []
        for path in catalog:
            if path["slug"] in completed_categories:
                continue
            score = 0
            if path["difficulty"] == user_difficulty:
                score += 3
            elif abs(path["difficulty"] - user_difficulty) == 1:
                score += 1
            if level >= path["difficulty"] * 5:
                score += 2
            if profile and profile.badges:
                score += 1
            recommended.append({**path, "score": score, "reason": f"Suitable for level {level}"})

        recommended.sort(key=lambda x: -x["score"])
        return recommended[:top_n]

    async def analyze_progress(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> dict:
        progress = await ProgressService.get_or_create_player_progress(db, user_id)
        level_info = LevelSystem.progress_to_next_level(progress.total_xp)

        return {
            "level_info": level_info,
            "stats": {
                "lessons_completed": progress.lessons_completed,
                "missions_completed": progress.missions_completed,
                "quizzes_passed": progress.quizzes_passed,
                "labs_completed": progress.labs_completed,
                "learning_streak": progress.learning_streak,
                "time_spent_seconds": progress.time_spent_seconds,
            },
            "recommendations": await self.recommend_learning_path(db, user_id),
        }