"""Contact form endpoint tests: validation, honeypot, rate limit."""

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _reset_contact_rate_limit():
    """Clear the per-IP contact counter before every test.

    Redis persists across runs (1h TTL) and the ASGI client always comes from
    127.0.0.1, so leftover counts from earlier suites would throttle fresh
    tests. Runs before the client fixture issues any request.
    """
    from app.core.cache import CacheService

    await CacheService(prefix="contact").delete("rate:127.0.0.1")


async def test_contact_submit_accepted(client):
    r = await client.post(
        "/api/v1/contact",
        json={
            "name": "Test Visitor",
            "email": "visitor@example.com",
            "subject": "Institutional licensing",
            "message": "Do you offer school-wide licenses for 300 students?",
        },
    )
    assert r.status_code == 202, r.text
    assert "reply" in r.json()["message"].lower()


async def test_contact_rejects_short_message(client):
    r = await client.post(
        "/api/v1/contact",
        json={
            "name": "T",
            "email": "bad",
            "subject": "x",
            "message": "short",
        },
    )
    assert r.status_code == 422


async def test_contact_honeypot_blocks_bots(client):
    r = await client.post(
        "/api/v1/contact",
        json={
            "name": "Bot",
            "email": "bot@example.com",
            "subject": "Cheap traffic",
            "message": "Visit my site for guaranteed hits and followers.",
            "website": "http://spam.example",
        },
    )
    # Honeypot field has max_length=0 → any bot-filled value fails validation.
    assert r.status_code == 422


async def test_contact_rate_limit_per_ip(client):
    from app.core.cache import CacheService

    # Reset the per-IP counter: Redis persists across test runs (1h TTL), so
    # earlier runs of this suite would otherwise start mid-budget. The client
    # IP differs by httpx version ('testclient' vs None→'unknown'), so clear
    # every candidate key.
    cache = CacheService(prefix="contact")
    for candidate in ("rate:testclient", "rate:unknown"):
        await cache.delete(candidate)
    await cache.delete_pattern("rate:*")
    payload = {
        "name": "Floody McFlood",
        "email": "floody@example.com",
        "subject": "Repeat message",
        "message": "Sending this more times than allowed from one address.",
    }
    codes = [(await client.post("/api/v1/contact", json=payload)).status_code for _ in range(6)]
    # First five are within the hourly budget; the sixth is throttled.
    assert codes[:5] == [202] * 5
    assert codes[5] == 429
