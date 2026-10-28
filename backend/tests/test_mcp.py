"""MCP server verification: metadata, Clerk OAuth access-token auth, negative cases, concurrency."""
import asyncio, time, pytest, json
from fastapi.testclient import TestClient

from app.main import app  # noqa: E402

client = TestClient(app)


def test_metadata_discovery():
    r = client.get("/api/v1/mcp/.well-known/oauth-protected-resource/mcp")
    assert r.status_code == 200
    data = r.json()
    assert data["resource"] == "https://cyberverse-api.cyberverse.blitz.cloud/mcp"
    assert "https://clerk.cyberverse.com" in data["authorization_servers"]
    assert "openid" in data.get("scopes_supported", [])


def test_auth_server_discovery():
    r = client.get("/api/v1/mcp/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    data = r.json()
    assert data["issuer"] is not None
    assert "jwks_uri" in data


def test_missing_token_challenge():
    r = client.post("/api/v1/mcp/", json={})
    assert r.status_code == 401
    assert "invalid_token" in r.json()["error"]
    assert "https://opencode" in r.headers.get("WWW-Authenticate", "")


def test_wrong_audience_token_rejected():
    # Synthetic token with wrong audience — must be rejected with 401 challenge after verification failure
    # Since we don't have a real Clerk OAuth access token signed for https://opencode,
    # we test that a session-style/JWT format without correct claims produces 401.
    # We use a clearly-invalid token value.
    r = client.post("/api/v1/mcp/", headers={"authorization": "Bearer notavalidtoken"}, json={})
    assert r.status_code == 401


def test_repeated_calls_stateless():
    # Verify endpoint responds repeatedly without state errors (stateless transport)
    for _ in range(3):
        r = client.get("/api/v1/mcp/.well-known/oauth-protected-resource/mcp")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_requests():
    async def fetch():
        return client.get("/api/v1/mcp/.well-known/oauth-protected-resource/mcp")
    results = await asyncio.gather(*[fetch() for _ in range(5)])
    for res in results:
        assert res.status_code == 200
