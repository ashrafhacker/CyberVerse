async def register_and_auth(client, email="labs@test.io", username="labs_user"):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "full_name": "Labs Tester",
            "username": username,
        },
    )
    assert response.status_code == 201
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_labs_facilities_seed_and_list(client):
    headers = await register_and_auth(client)
    response = await client.get("/api/v1/labs/facilities", headers=headers)

    assert response.status_code == 200
    facilities = response.json()["data"]
    assert len(facilities) >= 7
    assert {item["slug"] for item in facilities} >= {"soc", "digital-forensics", "cloud-security"}


async def test_start_lab_session_and_fetch_world(client):
    headers = await register_and_auth(client, "labs2@test.io", "labs_user_2")
    start = await client.post(
        "/api/v1/labs/sessions",
        headers=headers,
        json={"mission_slug": "soc-suspicious-login-triage", "seed": "test-seed-001"},
    )
    assert start.status_code == 201
    session_id = start.json()["data"]["id"]

    world = await client.get(f"/api/v1/labs/sessions/{session_id}/world", headers=headers)
    assert world.status_code == 200
    data = world.json()["data"]
    assert data["scenario_seed"] == "test-seed-001"
    assert data["safety_metadata"]["fictional_only"] is True
    assert data["assets"][0]["ip_address"].startswith("10.")
    assert data["tool_manifest"]


async def test_lab_objective_requires_evidence_and_actions(client):
    headers = await register_and_auth(client, "labs3@test.io", "labs_user_3")
    start = await client.post(
        "/api/v1/labs/sessions",
        headers=headers,
        json={"mission_slug": "soc-suspicious-login-triage", "seed": "test-seed-002"},
    )
    session_id = start.json()["data"]["id"]

    failed = await client.post(
        f"/api/v1/labs/sessions/{session_id}/objectives/obj-contain-account/submit",
        headers=headers,
        json={"evidence_ids": ["auth-log-impossible-travel"], "actions": [{"action": "disable_identity"}]},
    )
    assert failed.status_code == 200
    assert failed.json()["data"]["passed"] is False
    assert failed.json()["data"]["missing_actions"] == ["revoke_sessions"]

    passed = await client.post(
        f"/api/v1/labs/sessions/{session_id}/objectives/obj-contain-account/submit",
        headers=headers,
        json={
            "evidence_ids": ["auth-log-impossible-travel"],
            "actions": [{"action": "disable_identity"}, {"action": "revoke_sessions"}],
        },
    )
    assert passed.status_code == 200
    assert passed.json()["data"]["passed"] is True


async def test_home_lab_requires_private_scope(client):
    headers = await register_and_auth(client, "labs4@test.io", "labs_user_4")
    attestation = await client.post(
        "/api/v1/labs/home-labs/attestations",
        headers=headers,
        json={
            "acknowledged": True,
            "attestation_text": "I own this local training environment and authorize CyberVerse to connect to it.",
        },
    )
    assert attestation.status_code == 201
    attestation_id = attestation.json()["data"]["id"]

    rejected = await client.post(
        "/api/v1/labs/home-labs",
        headers=headers,
        json={
            "attestation_id": attestation_id,
            "name": "Unsafe public lab",
            "lab_type": "docker",
            "scope": {"cidrs": ["8.8.8.0/24"]},
        },
    )
    assert rejected.status_code == 400

    accepted = await client.post(
        "/api/v1/labs/home-labs",
        headers=headers,
        json={
            "attestation_id": attestation_id,
            "name": "Local Docker Lab",
            "lab_type": "docker",
            "scope": {"cidrs": ["172.16.20.0/24"]},
        },
    )
    assert accepted.status_code == 201
    assert accepted.json()["data"]["read_only"] is True
