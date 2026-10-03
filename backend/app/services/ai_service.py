import json
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisClient
from app.models.user import Profile
from app.services.progress_service import LevelSystem, ProgressService


class AIService:
    """AI Mentor service — quiz generation, hints, explanations, recommendations, chat."""

    OPENAI_BASE_URL = "https://api.openai.com/v1"

    SYSTEM_PROMPT = (
        "You are the CyberVerse Mentor, a friendly, human-like cybersecurity expert and teacher. "
        "You speak naturally, warmly, and encouragingly, as if you're a real person guiding the student. "
        "You help students learn defensive security and ethical-hacking concepts, explain lessons, "
        "quiz them, and guide them through the platform's fictional sandboxes (Neo Analysis virtual internet, "
        "Cyber Network Raid, CyberVerse Labs). "
        "CRITICAL INSTRUCTION: You MUST ONLY give answers related to CyberVerse, its courses, cybersecurity, and ethical hacking. "
        "If a user asks about programming (unrelated to security), history, math, general advice, or ANY other topic outside of cybersecurity, "
        "you MUST respectfully decline to answer and remind them that you are strictly a CyberVerse cybersecurity mentor. "
        "Always keep answers educational, safe, and legal: never provide instructions for attacking real third-party systems — "
        "redirect any such request to the platform's authorized fictional environments. "
        "Be concise, conversational, use relatable analogies for beginners, and gently suggest next steps "
        "inside CyberVerse.\n\n"
        "CYBERVERSE PLATFORM RESOURCES (You know everything about these and recommend them):\n"
        "- 'CEH v12 — Official Module PDFs (20 Modules)': The complete 20-module CEH v12 official study guide.\n"
        "- 'CEH v12 — System & Network Security (Video)': Covers system penetration testing, malware threats, network sniffing, ARP poisoning, and evading IDS/firewalls.\n"
        "- 'CEH v12 — Advanced Cybersecurity (Video)': Web server attacks, web application hacking, SQL injection, wireless network hacking, and mobile/cloud security.\n"
        "- 'Burp Suite Live Practical': Hands-on sessions with Burp Suite Pro, OTP bypass, account takeover via IDOR, and response manipulation.\n"
        "- 'HTTP Debugger Pro Basics': Learn to intercept and manipulate HTTP traffic with HTTP Debugger Pro.\n"
        "Suggest these resources to students when they ask for training, tutorials, or mention they want to learn a topic."
    )

    def __init__(self, api_key: str | None = None):
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
        model: str | None = None,
    ) -> str:
        """
        Chat with the best available provider, failing over gracefully.

        Provider priority: OpenRouter -> OpenAI -> Gemini -> offline fallback.
        A failing provider is skipped so the mentor stays available.
        """
        last_error: Exception | None = None

        if settings.OPENROUTER_API_KEY:
            try:
                return await self._openrouter_chat(messages, temperature, max_tokens, model)
            except Exception as e:  # noqa: BLE001
                last_error = e

        if self.api_key or settings.OPENAI_API_KEY:
            try:
                return await self._openai_chat(messages, temperature, max_tokens, model)
            except Exception as e:  # noqa: BLE001
                last_error = e

        if getattr(settings, "GEMINI_API_KEY", None):
            try:
                return await self._gemini_chat(messages, temperature, max_tokens, model)
            except Exception as e:  # noqa: BLE001
                last_error = e

        import logging
        if last_error:
            logging.getLogger(__name__).warning("All AI providers failed; using fallback", error=str(last_error))
        return await self._fallback_response(messages)

    async def _gemini_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise ValueError("No Gemini API key configured (set GEMINI_API_KEY)")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        gemini_messages = []
        system_instruction = None

        for m in messages:
            if m["role"] == "system":
                system_instruction = {"parts": [{"text": m["content"]}]}
            elif m["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [{"text": m["content"]}]})
            elif m["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [{"text": m["content"]}]})

        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _openai_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.OPENAI_BASE_URL}/chat/completions",
                headers=self._headers,
                json={
                    "model": model or settings.OPENAI_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            try:
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                data = e.response.json()
                if e.response.status_code == 429 and data.get("error", {}).get("type") == "insufficient_quota":
                    return "SYSTEM ALERT: The provided OpenAI API key has run out of credits. Please add billing credits to your OpenAI account at platform.openai.com to resume AI Mentor functionality."
                raise

    async def _openrouter_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        model: str | None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
        if settings.OPENROUTER_APP_NAME:
            headers["X-Title"] = settings.OPENROUTER_APP_NAME

        payload: dict = {
            "model": model or settings.OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=settings.OPENROUTER_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def chat(self, history: list[dict], context: str = "") -> dict:
        """Multi-turn mentor conversation. History is validated + trimmed by the caller."""
        if not history:
            return {
                "reply": await self._fallback_response([{"role": "user", "content": ""}]),
                "model": "fallback",
            }

        system_content = self.SYSTEM_PROMPT
        if context:
            system_content += f"\n\nREAL-TIME USER CONTEXT: {context}"

        messages = [{"role": "system", "content": system_content}] + history[-settings.AI_CHAT_HISTORY_LIMIT :]
        model = settings.OPENROUTER_MODEL if settings.OPENROUTER_API_KEY else settings.OPENAI_MODEL
        reply = await self._chat(
            messages,
            temperature=settings.OPENROUTER_TEMPERATURE if settings.OPENROUTER_API_KEY else settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENROUTER_MAX_TOKENS,
            model=model,
        )
        return {"reply": reply, "model": model}

    @staticmethod
    async def _fallback_response(messages: list[dict]) -> str:
        """Use g4f to provide a real AI response when no API key is configured."""
        try:

            import g4f
            from g4f.client import AsyncClient

            client = AsyncClient()
            response = await client.chat.completions.create(
                model=g4f.models.gpt_4o,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception:
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
            'Return STRICT JSON: {"questions": [{"question": str, "options": [4 strings], '
            '"correct_index": int, "explanation": str}]}. Topic: ' + topic +
            f". Difficulty: {difficulty}. Number of questions: {num_questions}."
        )

        content = await self._chat([{"role": "system", "content": system}])

        try:
            result = json.loads(self._extract_json(content))
            await RedisClient.cache_set_json(cache_key, result, ttl=60 * 60)
            return result
        except (json.JSONDecodeError, ValueError):
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

    @staticmethod
    def _extract_json(content: str) -> str:
        """Extract a JSON object from raw model output that may include prose/fences."""
        import re

        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            return text.strip()
        # Fall back to the first {...} block if prose surrounds the JSON.
        start = text.find("{")
        if start != -1:
            end = text.rfind("}")
            if end != -1 and end > start:
                return text[start : end + 1]
        return text

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
