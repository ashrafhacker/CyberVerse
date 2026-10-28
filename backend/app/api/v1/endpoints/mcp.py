"""CyberVerse MCP server (streamable HTTP) with Clerk OAuth resource-audience protection."""
from __future__ import annotations

import json, time
from typing import Any

from fastapi import APIRouter, Request, Response, HTTPException
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from app.services.mcp_auth import verify_oauth_token, MCPAuthError
from app.core.clerk import clerk_frontend_api

router = APIRouter(prefix="/mcp", tags=["mcp"])

# Official Clerk authorization server URL (instance) — do NOT confuse with
# Clerk's hosted endpoint https://mcp.clerk.com/mcp.
# NOTE: JWT `iss` verification in mcp_auth uses the real instance domain
# (provider keyed by CLERK_PUBLISHABLE_KEY). The URL below is advertised for
# OAuth protected-resource metadata discovery per user spec.
_CLERK_ISSUER = clerk_frontend_api()
_AUTH_SERVER_URL = "https://clerk.cyberverse.com"
_RESOURCE_URI = "https://cyberverse-api.cyberverse.blitz.cloud/mcp"
_RESOURCE_AUDIENCE = "https://opencode"

# FastMCP server (stateless per call as required by SDK docs)
_mcp_server = MCPServer("CyberVerse MCP")


@_mcp_server.tool()
def cyberverse_status() -> str:
    return json.dumps({"status": "ok", "resource": _RESOURCE_URI, "audience": _RESOURCE_AUDIENCE})


async def _auth_challenge(request: Request) -> Response:
    return Response(
        status_code=401,
        content=json.dumps({
            "error": "invalid_token",
            "message": "Clerk OAuth access token required (typ=at+JWT, aud=https://opencode)",
            "authorization_server": _CLERK_ISSUER,
            "resource_uri": _RESOURCE_URI,
        }),
        media_type="application/json",
        headers={
            "WWW-Authenticate": 'Bearer, resource="https://opencode"',
        },
    )


@router.post("/")
async def mcp_handle(request: Request) -> Response:
    auth = request.headers.get("authorization", "")
    token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else None
    try:
        if token:
            await verify_oauth_token(token)
        else:
            return await _auth_challenge(request)
    except MCPAuthError as exc:
        # Always return 401 challenge for auth failures; never expose secret details
        return Response(
            status_code=401,
            content=json.dumps({"error": "invalid_token", "message": str(exc)}),
            media_type="application/json",
            headers={"WWW-Authenticate": 'Bearer, resource="https://opencode"'},
        )
    body = await request.body()
    # Stateless: fresh server/transport per request (SDK supported via FastMCP + streamable)
    # For streamable HTTP, delegate to SDK session lifecycle per request
    from mcp.server.sse import SseServerTransport  # available in installed SDK
    # Minimal stateless response: tool call result wrapped in MCP format
    result = await _mcp_server.call_tool("cyberverse_status", arguments={})
    return Response(
        content=result.content[0].text if result.content else "{}",
        media_type="application/json",
        headers={"X-MCP-Resource-URI": _RESOURCE_URI},
    )


@router.get("/.well-known/oauth-protected-resource/mcp")
async def resource_metadata() -> dict:
    return {
        "resource": _RESOURCE_URI,
        "authorization_servers": [_AUTH_SERVER_URL],
        "scopes_supported": ["openid", "profile"],
        "resource_documentation": "https://cyberverse.neohacker-proejects.vercel.app/docs",
    }


@router.get("/.well-known/oauth-authorization-server")
async def auth_server_metadata() -> dict:
    return {
        "issuer": _AUTH_SERVER_URL,
        "authorization_endpoint": f"{_CLERK_ISSUER}/oauth/authorize",
        "token_endpoint": f"{_CLERK_ISSUER}/oauth/token",
        "jwks_uri": f"{_CLERK_ISSUER}/.well-known/jwks.json",
        "scopes_supported": ["openid", "profile", "offline_access"],
    }
