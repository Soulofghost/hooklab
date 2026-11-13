import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.engine.hmac_verifier import HMACVerifier

client = TestClient(app)

def test_healthcheck():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "HookLab"

def test_stats_endpoint():
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "totalEndpoints" in data

def test_create_endpoint_and_receive_webhook():
    ep_payload = {
        "name": "GitHub CI Webhook Receiver",
        "secret": "my_super_secret"
    }
    ep_res = client.post("/api/endpoints", json=ep_payload)
    assert ep_res.status_code == 201
    ep_data = ep_res.json()
    token = ep_data["token"]
    ep_id = ep_data["id"]

    # Send inbound webhook with valid HMAC signature
    body_str = '{"action": "completed", "workflow": "CI"}'
    sig = HMACVerifier.compute_signature("my_super_secret", body_str.encode())

    wh_res = client.post(
        f"/webhook/{token}",
        data=body_str,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={sig}"
        }
    )
    assert wh_res.status_code == 200
    wh_data = wh_res.json()
    assert wh_data["signature_verified"] is True
    event_id = wh_data["event_id"]

    # Fetch endpoint events
    evts_res = client.get(f"/api/endpoints/{ep_id}/events")
    assert evts_res.status_code == 200
    events = evts_res.json()
    assert len(events) >= 1
    assert events[0]["id"] == event_id

    # Test Replay
    replay_res = client.post(f"/api/events/{event_id}/replay", json={"target_url": "http://127.0.0.1:9090/test"})
    assert replay_res.status_code == 200
    assert replay_res.json()["success"] is True
