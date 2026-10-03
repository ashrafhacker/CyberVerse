"""
Skill-tree and RPG rank progression for the learner.

Implements spec §24 (RPG ranks: Recruit → CyberVerse Elite) and §25 (skill tree
branches with per-branch progression). Ranks map to the numeric level, and each
skill branch tracks its own level + XP so the tree is meaningful rather than a
single global number.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import SkillBranch, UserSkill


class RankSystem:
    """Maps player level to the CyberVerse career rank ladder."""

    # (min_level, rank)
    RANKS = [
        (1, "Recruit"),
        (3, "Trainee"),
        (6, "Junior Analyst"),
        (10, "Security Analyst"),
        (15, "Security Engineer"),
        (21, "Threat Hunter"),
        (28, "Incident Responder"),
        (36, "Security Architect"),
        (50, "CyberVerse Elite"),
    ]

    @classmethod
    def rank_for_level(cls, level: int) -> str:
        rank = cls.RANKS[0][1]
        for min_level, name in cls.RANKS:
            if level >= min_level:
                rank = name
        return rank

    @classmethod
    def next_rank(cls, level: int) -> str | None:
        for min_level, name in cls.RANKS:
            if level < min_level:
                return name
        return None

    @classmethod
    def next_rank_level(cls, level: int) -> int | None:
        for min_level, _name in cls.RANKS:
            if level < min_level:
                return min_level
        return None


class SkillService:
    BRANCHES = [
        ("networking", "Networking", "Networks, protocols, and traffic analysis.", "network", ["foundations"]),
        ("linux", "Linux", "Linux administration, permissions, logs, and hardening.", "terminal", ["foundations"]),
        ("web-security", "Web Security", "Web application vulnerabilities and defense.", "globe", ["networking"]),
        ("soc", "Security Operations", "Triage, detection, and incident response.", "radio", ["networking"]),
        ("forensics", "Digital Forensics", "Disk, memory, and artifact analysis.", "search", ["linux"]),
        ("threat-intel", "Threat Intelligence", "CVE, IOC, and adversary tradecraft.", "radar", ["web-security"]),
        ("cloud-security", "Cloud Security", "IAM, storage, and cloud posture.", "cloud", ["linux"]),
        ("secure-coding", "Secure Coding", "Writing secure code and fixing vulns.", "code", ["web-security"]),
        ("incident-response", "Incident Response", "Containment, recovery, and reporting.", "shield", ["soc", "forensics"]),
        ("security-architecture", "Security Architecture", "Designing resilient security systems.", "layers", ["incident-response"]),
    ]

    @staticmethod
    async def ensure_branches(db: AsyncSession) -> list[SkillBranch]:
        result = await db.execute(select(func.count()).select_from(SkillBranch))
        if (result.scalar_one()) > 0:
            all_result = await db.execute(select(SkillBranch).order_by(SkillBranch.display_order))
            return list(all_result.scalars().all())

        branches: list[SkillBranch] = []
        for order, (slug, name, desc, icon, prereqs) in enumerate(SkillService.BRANCHES):
            branch = SkillBranch(
                slug=slug, name=name, description=desc, icon=icon,
                max_level=5, prerequisites=prereqs, display_order=order,
            )
            db.add(branch)
            branches.append(branch)
        await db.commit()
        for b in branches:
            await db.refresh(b)
        return branches

    @staticmethod
    async def get_user_skills(db: AsyncSession, user_id: UUID) -> list[dict]:
        branches = await SkillService.ensure_branches(db)
        result = await db.execute(select(UserSkill).where(UserSkill.user_id == user_id))
        skills = {s.branch_id: s for s in result.scalars().all()}

        out = []
        for b in branches:
            s = skills.get(b.id)
            out.append(
                {
                    "branch_id": b.id,
                    "slug": b.slug,
                    "name": b.name,
                    "level": s.level if s else 0,
                    "max_level": b.max_level,
                    "xp_in_branch": s.xp_in_branch if s else 0,
                    "activities": s.activities if s else 0,
                }
            )
        return out

    @staticmethod
    async def add_branch_xp(
        db: AsyncSession, user_id: UUID, branch_slug: str, xp: int, activity: str = ""
    ) -> dict:
        result = await db.execute(select(SkillBranch).where(SkillBranch.slug == branch_slug))
        branch = result.scalar_one_or_none()
        if not branch:
            return {"ok": False, "reason": "unknown branch"}

        res = await db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.branch_id == branch.id)
        )
        skill = res.scalar_one_or_none()
        if not skill:
            skill = UserSkill(user_id=user_id, branch_id=branch.id)
            db.add(skill)

        skill.xp_in_branch += xp
        skill.activities += 1
        # 400 XP levels a branch (matches BASE_XP-ish pacing against LevelSystem).
        new_level = min(branch.max_level, skill.xp_in_branch // 400)
        leveled_up = new_level > skill.level
        skill.level = new_level
        if activity:
            skill.meta_data = {**(skill.meta_data or {}), "last_activity": activity}
        await db.commit()
        await db.refresh(skill)
        return {"ok": True, "branch_slug": branch.slug, "level": skill.level, "leveled_up": leveled_up}

    @staticmethod
    async def progress(db: AsyncSession, user_id: UUID) -> dict:
        from app.services.progress_service import ProgressService

        player = await ProgressService.get_or_create_player_progress(db, user_id)
        branches = await SkillService.get_user_skills(db, user_id)
        return {
            "total_xp": player.total_xp,
            "level": player.current_level,
            "rank": RankSystem.rank_for_level(player.current_level),
            "next_rank": RankSystem.next_rank(player.current_level),
            "next_rank_level": RankSystem.next_rank_level(player.current_level),
            "branches": branches,
        }
