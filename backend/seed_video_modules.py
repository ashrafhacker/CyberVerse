"""
Seed real video lessons into the real schema for the three video courses
defined in frontend/lib/curriculum.ts:

  course-ceh-system-network  18 videos → grouped by asset folder into 4 modules
  course-burp-suite           8 videos → 1 module
  course-http-debugger        3 videos → 2 modules (main + bonus)

The curriculum TS is parsed (not duplicated) so the DB stays in lock-step with
the static offline fallback. Each lesson stores the exact on-disk resource
path, which is what the player streams and the completion verifier checks
against (≥90% watch-through). Idempotent: already-seeded paths are skipped.
Invalidates the structure:{course_id} cache afterwards.

Usage:
  cd backend && python seed_video_modules.py
"""
import asyncio
import re
import struct
from pathlib import Path

CURRICULUM_TS = Path(__file__).resolve().parents[1] / "frontend" / "lib" / "curriculum.ts"
VIDEO_COURSE_KEYS = ("course-ceh-system-network", "course-burp-suite", "course-http-debugger")

COURSE_RE = re.compile(r"^  '(?P<key>course-[^']+)': \{")
LESSON_RE = re.compile(
    r"\{ id: '(?P<id>[^']+)', title: '(?P<title>[^']+)', type: '(?P<type>\w+)', "
    r"asset: '(?P<asset>[^']+)', free: (?P<free>true|false)(?:, duration: '(?P<duration>[^']+)')? \}"
)


def parse_curriculum() -> dict[str, list[dict]]:
    """Extract video lessons per course key from curriculum.ts, preserving order."""
    courses: dict[str, list[dict]] = {}
    current: str | None = None
    for line in CURRICULUM_TS.read_text(encoding="utf-8").splitlines():
        m_course = COURSE_RE.match(line)
        if m_course:
            current = m_course.group("key")
            courses.setdefault(current, [])
            continue
        if line.startswith("  },"):
            current = None
            continue
        if current is None:
            continue
        m = LESSON_RE.search(line)
        if m and m.group("type") == "video":
            courses[current].append(
                {
                    "static_id": m.group("id"),
                    "title": m.group("title"),
                    "asset": m.group("asset"),
                    "free": m.group("free") == "true",
                    "duration": m.group("duration"),
                }
            )
    return courses


def mp4_duration_seconds(path: Path) -> float | None:
    """Read the real duration from a faststart MP4 (moov before mdat)."""
    try:
        with path.open("rb") as f:
            size = path.stat().st_size
            pos = 0
            while pos + 8 <= size:
                f.seek(pos)
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                atom_size, name = struct.unpack(">I4s", hdr)
                hdr_len = 8
                if atom_size == 1:
                    atom_size = struct.unpack(">Q", f.read(8))[0]
                    hdr_len = 16
                if atom_size == 0:
                    atom_size = size - pos
                if atom_size < hdr_len:
                    break
                if name == b"moov":
                    data = f.read(min(atom_size, 8 << 20))
                    i = data.find(b"mvhd")
                    if i < 0:
                        return None
                    ver = data[i + 4]
                    if ver == 1:
                        timescale = struct.unpack(">I", data[i + 24 : i + 28])[0]
                        duration = struct.unpack(">Q", data[i + 28 : i + 36])[0]
                    else:
                        timescale = struct.unpack(">I", data[i + 16 : i + 20])[0]
                        duration = struct.unpack(">I", data[i + 20 : i + 24])[0]
                    return duration / timescale if timescale else None
                pos += atom_size
    except OSError:
        return None
    return None


def estimated_minutes(asset_path: str, duration_field: str | None) -> int:
    """Prefer the actual file duration; fall back to 'M:SS' strings."""
    from app.api.v1.endpoints.media import ASSETS_ROOT

    seconds = mp4_duration_seconds(ASSETS_ROOT / asset_path)
    if seconds and seconds > 0:
        return max(1, round(seconds / 60))
    if duration_field and re.fullmatch(r"\d+:\d+", duration_field):
        return max(1, int(duration_field.split(":")[0]))
    return 10


def pretty_module_name(folder: str) -> str:
    """'02_1-2-system-penetration-testing' → '1 2 System Penetration Testing'."""
    name = re.sub(r"^\d+_", "", folder)
    name = name.replace("-", " ").strip().title()
    return name or "Lessons"


async def main() -> None:
    from sqlalchemy import select

    from app.core.cache import course_cache
    from app.core.database import async_session_maker
    from app.models.course import ContentType, Course, Lesson, Module

    curriculum = parse_curriculum()
    missing_assets: list[str] = []

    async with async_session_maker() as db:
        for key in VIDEO_COURSE_KEYS:
            lessons = curriculum.get(key, [])
            if not lessons:
                print(f"{key}: no video lessons found in curriculum.ts — skipping.")
                continue

            res = await db.execute(select(Course).where(Course.slug == key))
            course = res.scalar_one_or_none()
            if not course:
                print(f"{key}: course not found in DB — skipping.")
                continue

            # Existing resource paths for this course (idempotency key).
            rows = await db.execute(
                select(Lesson.resources)
                .join(Module, Lesson.module_id == Module.id)
                .where(Module.course_id == course.id)
            )
            existing_paths: set[str] = set()
            for (resources,) in rows.all():
                if isinstance(resources, list):
                    for r in resources:
                        if isinstance(r, dict) and r.get("path"):
                            existing_paths.add(r["path"])

            # Validate assets on disk first — a lesson pointing at a missing
            # file would 404 and freeze the player, so never seed those.
            pending = [l for l in lessons if l["asset"] not in existing_paths]
            for l in list(pending):
                from app.api.v1.endpoints.media import ASSETS_ROOT

                if not (ASSETS_ROOT / l["asset"]).is_file():
                    missing_assets.append(l["asset"])
                    pending.remove(l)

            if not pending:
                print(f"{key}: all {len(lessons)} lessons already seeded (or no pending).")
                await course_cache.delete(f"structure:{course.id}")
                continue

            # Group pending lessons by asset folder, preserving first-appearance
            # order for module numbering (folder names carry NN_ prefixes).
            groups: dict[str, list[dict]] = {}
            for l in pending:
                folder = str(Path(l["asset"]).parent)
                groups.setdefault(folder, []).append(l)

            # Reuse modules from a partial previous run by name.
            mod_rows = await db.execute(select(Module).where(Module.course_id == course.id))
            modules_by_name = {m.name: m for m in mod_rows.scalars().all()}
            module_order = len(modules_by_name) + 1

            seeded = 0
            for folder, group in groups.items():
                mod_name = pretty_module_name(Path(folder).name)
                module = modules_by_name.get(mod_name)
                if module is None:
                    module = Module(
                        course_id=course.id,
                        name=mod_name,
                        description=f"Video module: {mod_name}.",
                        short_description=f"Video module: {mod_name}."[:497],
                        estimated_minutes=sum(
                            estimated_minutes(l["asset"], l["duration"]) for l in group
                        ),
                        order=module_order,
                        meta_data={"resource_type": "video", "lesson_count": len(group)},
                    )
                    db.add(module)
                    await db.flush()
                    modules_by_name[mod_name] = module
                    module_order += 1

                for ix, lesson in enumerate(group, start=1):
                    minutes = estimated_minutes(lesson["asset"], lesson["duration"])
                    db.add(
                        Lesson(
                            module_id=module.id,
                            lesson_type=ContentType.LESSON,
                            name=lesson["title"],
                            description=f"Video lesson: {lesson['title']}.",
                            short_description=f"Video lesson: {lesson['title']}."[:497],
                            content={},
                            resources=[
                                {"type": "video", "title": lesson["title"], "path": lesson["asset"]}
                            ],
                            estimated_minutes=minutes,
                            xp_reward=50,
                            coins_reward=10,
                            order=ix,
                            is_premium=not lesson["free"],
                        )
                    )
                    seeded += 1

            await db.commit()
            print(f"{key}: seeded {seeded} video lesson(s) across {len(groups)} module(s).")
            await course_cache.delete(f"structure:{course.id}")
            print(f"  structure cache invalidated for {course.id}")

        if missing_assets:
            print("\nSKIPPED (file missing on disk):")
            for a in missing_assets:
                print(f"  ✗ {a}")


if __name__ == "__main__":
    asyncio.run(main())
