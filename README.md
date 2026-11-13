# HookLab - Webhook Inspector, HMAC Verification & Delivery Replay Engine

HookLab is a developer tooling and API observability platform designed for testing, debugging, and replaying inbound HTTP webhooks. Built with Python 3.11, FastAPI, and SQLite WAL, HookLab provisions dynamic webhook listener URLs, validates cryptographic HMAC-SHA256 signatures in constant time, and allows developers to inspect payloads and simulate retry deliveries.

## Core Capabilities
- **Dynamic Webhook Listener Endpoints:** Provision dedicated webhook URLs (`/webhook/{token}`) to capture all incoming HTTP methods, headers, query parameters, client IP, and raw request bodies.
- **Constant-Time HMAC-SHA256 Verification:** Verifies signatures (e.g. `X-Hub-Signature-256`, `Stripe-Signature`) using `hmac.compare_digest` to defend against timing attacks.
- **Webhook Delivery Replay Engine:** Replays recorded payloads to local development (`localhost:3000`) or staging servers with one-click re-delivery.
- **Exponential Backoff Simulation:** Computes deterministic exponential backoff delivery schedules with jitter modeling.
- **Persistent Event Store:** Records complete raw payloads and audit logs in SQLite Write-Ahead Logging (WAL) mode.

## Technology Stack
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, Pytest
- **Database:** SQLite (WAL mode)
- **Frontend:** Vanilla JavaScript, Modern CSS Flex/Grid, Dark DevTools UI
- **DevOps:** Docker, Docker Compose, GitHub Actions CI

## Quickstart

```bash
# Clone the repository
git clone https://github.com/Soulofghost/hooklab.git
cd hooklab

# Install dependencies
pip install -r backend/requirements.txt

# Run test suite
pytest -v

# Run the API server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints
- `GET /api/health` - Service health and HMAC verification engine status.
- `GET /api/stats` - Platform telemetry (endpoints, captured events, verified HMACs, delivery attempts).
- `GET /api/endpoints` - List all provisioned webhook listener endpoints.
- `POST /api/endpoints` - Provision a new endpoint with custom or auto-generated HMAC secret.
- `GET /api/endpoints/{id}/events` - Retrieve captured webhook events for a specific endpoint.
- `POST /api/events/{id}/replay` - Forward or replay captured webhook payload to a destination URL.
- `ALL /webhook/{token}` - Inbound listener capturing incoming webhook events.

## Author
Alvin MS ([@Soulofghost](https://github.com/Soulofghost))
