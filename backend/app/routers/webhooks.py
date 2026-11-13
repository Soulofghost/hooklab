import uuid
import datetime
import json
import time
from fastapi import APIRouter, Request, HTTPException, status
from typing import List, Dict, Any

from backend.app.database import get_connection
from backend.app.schemas import (
    CreateEndpointRequest, EndpointResponse,
    WebhookEventResponse, ReplayRequest, ReplayResponse
)
from backend.app.engine.hmac_verifier import HMACVerifier

router = APIRouter(tags=["webhooks"])

@router.get("/api/health")
def healthcheck():
    return {
        "status": "ok",
        "service": "HookLab",
        "version": "1.0.0",
        "engine": "HMAC-SHA256 Cryptographic Webhook Inspector & Replay Engine"
    }

@router.get("/api/stats")
def get_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as c FROM webhook_endpoints;")
    total_endpoints = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM webhook_events;")
    total_events = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM webhook_events WHERE signature_verified = 1;")
    verified_events = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM delivery_attempts;")
    total_replays = cursor.fetchone()["c"]

    conn.close()

    return {
        "totalEndpoints": total_endpoints,
        "totalEventsCaptured": total_events,
        "verifiedEventsCount": verified_events,
        "totalDeliveryReplays": total_replays
    }

@router.get("/api/endpoints", response_model=List[EndpointResponse])
def list_endpoints(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM webhook_endpoints ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()

    base_url = str(request.base_url).rstrip('/')

    return [
        {
            **dict(r),
            "webhook_url": f"{base_url}/webhook/{r['token']}"
        } for r in rows
    ]

@router.post("/api/endpoints", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
def create_endpoint(payload: CreateEndpointRequest, request: Request):
    conn = get_connection()
    cursor = conn.cursor()

    endpoint_id = "ep-" + str(uuid.uuid4())[:8]
    token = str(uuid.uuid4()).replace("-", "")[:16]
    secret = payload.secret or ("whsec_" + str(uuid.uuid4()).replace("-", "")[:24])
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cursor.execute("""
    INSERT INTO webhook_endpoints (id, token, name, secret, forward_url, status, total_events, created_at)
    VALUES (?, ?, ?, ?, ?, 'ACTIVE', 0, ?);
    """, (endpoint_id, token, payload.name, secret, payload.forward_url or "", now_iso))

    conn.commit()
    conn.close()

    base_url = str(request.base_url).rstrip('/')

    return {
        "id": endpoint_id,
        "token": token,
        "name": payload.name,
        "secret": secret,
        "forward_url": payload.forward_url or "",
        "status": "ACTIVE",
        "total_events": 0,
        "webhook_url": f"{base_url}/webhook/{token}",
        "created_at": now_iso
    }

@router.get("/api/endpoints/{endpoint_id}/events", response_model=List[WebhookEventResponse])
def get_endpoint_events(endpoint_id: str, limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM webhook_events WHERE endpoint_id = ? ORDER BY received_at DESC LIMIT ?;", (endpoint_id, limit))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "endpoint_id": r["endpoint_id"],
            "method": r["method"],
            "path": r["path"],
            "headers": json.loads(r["headers_json"] or "{}"),
            "query_params": r["query_params"] or "",
            "body": r["body"] or "",
            "signature_verified": bool(r["signature_verified"]),
            "client_ip": r["client_ip"] or "127.0.0.1",
            "received_at": r["received_at"]
        })

    return results

@router.post("/api/events/{event_id}/replay", response_model=ReplayResponse)
def replay_event(event_id: str, payload: ReplayRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM webhook_events WHERE id = ?;", (event_id,))
    event_row = cursor.fetchone()
    if not event_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook event not found")

    target = payload.target_url
    if not target:
        cursor.execute("SELECT forward_url FROM webhook_endpoints WHERE id = ?;", (event_row["endpoint_id"],))
        ep = cursor.fetchone()
        target = ep["forward_url"] if ep and ep["forward_url"] else "http://localhost:8080/webhook-receiver"

    # Simulate forwarding round-trip
    attempt_id = "att-" + str(uuid.uuid4())[:8]
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    simulated_duration_ms = 42.5
    simulated_status = 200

    cursor.execute("""
    INSERT INTO delivery_attempts (id, event_id, target_url, http_status, response_time_ms, response_body, success, attempted_at)
    VALUES (?, ?, ?, ?, ?, '{\"received\": true}', 1, ?);
    """, (attempt_id, event_id, target, simulated_status, simulated_duration_ms, now_iso))

    conn.commit()
    conn.close()

    return {
        "attempt_id": attempt_id,
        "event_id": event_id,
        "target_url": target,
        "http_status": simulated_status,
        "response_time_ms": simulated_duration_ms,
        "success": True,
        "attempted_at": now_iso
    }

# Dynamic Inbound Webhook Listener
@router.api_route("/webhook/{token}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def receive_webhook(token: str, request: Request):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM webhook_endpoints WHERE token = ?;", (token,))
    ep = cursor.fetchone()
    if not ep:
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8', errors='ignore')
    headers_dict = dict(request.headers)
    query_str = str(request.query_params)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Check HMAC signatures
    sig_header = headers_dict.get("x-hub-signature-256") or headers_dict.get("stripe-signature") or headers_dict.get("x-signature-sha256") or ""
    verified = False
    if sig_header and ep["secret"]:
        verified = HMACVerifier.verify_signature(ep["secret"], body_str, sig_header)

    event_id = "evt-" + str(uuid.uuid4())[:8]
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cursor.execute("""
    INSERT INTO webhook_events (id, endpoint_id, method, path, headers_json, query_params, body, signature_verified, client_ip, received_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        event_id,
        ep["id"],
        request.method,
        request.url.path,
        json.dumps(headers_dict),
        query_str,
        body_str,
        1 if verified else 0,
        client_ip,
        now_iso
    ))

    cursor.execute("UPDATE webhook_endpoints SET total_events = total_events + 1 WHERE id = ?;", (ep["id"],))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "event_id": event_id,
        "signature_verified": verified,
        "received_at": now_iso
    }
