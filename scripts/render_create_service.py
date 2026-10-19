#!/usr/bin/env python3
"""Create the CyberVerse backend web service on Render via the public API.

Follows Render's OpenAPI `servicePOST` schema:
  - ownerId / repo / branch / rootDir / envVars at top level
  - serviceDetails: { runtime, region, healthCheckPath,
                      envSpecificDetails: { buildCommand, startCommand,
                                            preDeployCommand } }
"""
import json
import os
import sys
import urllib.error
import urllib.request

API_KEY = open(os.path.expanduser("~/.config/render/api_key")).read().strip()
OWNER_ID = "tea-d7hs2rv7f7vs738pv2eg"

payload = {
    "type": "web_service",
    "name": "cyberverse-api",
    "ownerId": OWNER_ID,
    "repo": "https://github.com/ashrafhacker/CyberVerse",
    "branch": "main",
    "rootDir": "backend",
    "serviceDetails": {
        "runtime": "python",
        "region": "oregon",
        "healthCheckPath": "/health",
        "preDeployCommand": "alembic upgrade head",
        "envSpecificDetails": {
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2",
        },
    },
}

req = urllib.request.Request(
    "https://api.render.com/v1/services",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=40) as resp:
        body = json.loads(resp.read())
    svc = body.get("service", body)
    print("CREATED:", svc.get("id"), "|", svc.get("name"), "| status:", svc.get("status"))
    print("url:", svc.get("serviceDetails", {}).get("url"))
    print("plan:", svc.get("plan"))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, ":", e.read().decode()[:600])
    sys.exit(1)
except Exception as e:
    print("ERR:", e)
    sys.exit(1)
