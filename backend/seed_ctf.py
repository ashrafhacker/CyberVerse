"""Seed the CTF engine with synthetic, isolated challenges.

Flags are stored ONLY as SHA-256 hashes. All content is curated and synthetic;
no real exploits or public targets are involved. Each flag is a random token.

Run from the repo root:  python seed_ctf.py   (backend venv activated)
"""

import asyncio
import hashlib
import os
import sys
from uuid import uuid4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import async_session_maker  # noqa: E402
from app.models.ctf import Challenge  # noqa: E402


def _flag_hash(flag: str) -> str:
    return hashlib.sha256(flag.encode("utf-8")).hexdigest()


# category, title, slug, story, points, difficulty, hint, flag, prefix
CHALLENGES = [
    ("crypto", "Caesar Cipher Basics", "crypto-caesar-cipher",
     "A messenger left a message shifted by three letters. Decode it to recover the access phrase.",
     50, "beginner", "ROT3 was used on the ciphertext.", "CVX{shifted_secret}", "CVX{"),
    ("crypto", "Base64 Passport", "crypto-base64-passport",
     "The registry encoded a passphrase using a common binary-to-text encoding. Decode it.",
     50, "beginner", "Try a decoder for the encoding that turns binary into printable text.",
     "CVX{base64_checked}", "CVX{"),
    ("crypto", "XOR Key Hunt", "crypto-xor-key-hunt",
     "A one-byte key was XORed over the flag. The plaintext begins with CVX.",
     150, "intermediate", "The first bytes let you recover the repeating key byte.",
     "CVX{xor_recovered}", "CVX{"),
    ("web", "Cookie Inspector", "web-cookie-inspector",
     "A demo shop stores the admin flag in an unsigned cookie. No real store is involved.",
     100, "beginner", "Inspect the request and decode the base64 cookie value.",
     "CVX{cookie_checked}", "CVX{"),
    ("web", "SQL Injection Academy", "web-sql-injection-academy",
     "A synthetic login form leaks the answer when the query breaks out of its quotes.",
     150, "intermediate", "A classic tautology bypass: always-true condition.",
     "CVX{sqli_mastered}", "CVX{"),
    ("forensics", "Hidden Stream", "forensics-hidden-stream",
     "A synthetic document hides text using the zero-width technique.",
     100, "beginner", "Search the file for invisible characters.",
     "CVX{steg_found}", "CVX{"),
    ("forensics", "PCAP Trail", "forensics-pcap-trail",
     "Analyze the synthetic capture and recover the credential exchanged in plaintext.",
     150, "intermediate", "Follow the TCP stream in a packet analyzer.",
     "CVX{pcap_plaintext}", "CVX{"),
    ("reversing", "Binary Greeting", "reversing-binary-greeting",
     "The binary prints the flag only if you pass the right argument.",
     150, "intermediate", "Use strings on the binary to find the accepted argument.",
     "CVX{strings_win}", "CVX{"),
    ("reversing", "Crack the Hash", "reversing-crack-the-hash",
     "A config file contains a SHA-1 hash of a six-letter password.",
     100, "beginner", "The password is a lowercase six-letter word.",
     "CVX{md5_recovered}", "CVX{"),
    ("osint", "Public Profile", "osint-public-profile",
     "A fictional employee posted their pet's name in their profile — use it.",
     100, "beginner", "Reconnaissance begins with public information.",
     "CVX{osint_round}", "CVX{"),
    ("networking", "Port Math", "networking-port-math",
     "Identify the standard ports from the service hints and combine them.",
     50, "beginner", "HTTP=80, HTTPS=443, SSH=22.",
     "CVX{port_master}", "CVX{"),
    ("defensive", "IOC Extraction", "defensive-ioc-extraction",
     "Extract the domain indicator from the given synthetic log line.",
     100, "beginner", "The domain ends in .cyberverse.test.",
     "CVX{ioc_extracted}", "CVX{"),
    ("defensive", "Containment Plan", "defensive-containment-plan",
     "Pick the correct first containment action in the scenario.",
     100, "beginner", "Isolate before you remediate.",
     "CVX{contain_first}", "CVX{"),
]


async def seed():
    async with async_session_maker() as db:
        existing = await db.scalar(select(func.count()).select_from(Challenge))
        if existing and existing > 0:
            print(f"CTF already has {existing} challenges. Skipping.")
            return

        for category, title, slug, story, points, difficulty, hint, flag, prefix in CHALLENGES:
            db.add(Challenge(
                id=uuid4(),
                slug=slug,
                title=title,
                story=story,
                category=category,
                difficulty=difficulty,
                points=points,
                hint=hint,
                flag_sha256=_flag_hash(flag),
                flag_hint_prefix=prefix,
                tags=[category, difficulty],
                is_active=True,
            ))
        await db.commit()
        print(f"Seeded {len(CHALLENGES)} CTF challenges.")


if __name__ == "__main__":
    asyncio.run(seed())
