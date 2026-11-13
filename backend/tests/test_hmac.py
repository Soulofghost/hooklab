import pytest
from backend.app.engine.hmac_verifier import HMACVerifier

def test_compute_signature():
    secret = "test_secret_123"
    body = b'{"event": "charge.success", "amount": 1000}'
    sig = HMACVerifier.compute_signature(secret, body)
    assert len(sig) == 64 # SHA-256 hex string

def test_verify_signature_valid():
    secret = "whsec_abc123"
    payload = '{"status": "paid"}'
    expected = HMACVerifier.compute_signature(secret, payload.encode())

    # Raw match
    assert HMACVerifier.verify_signature(secret, payload, expected) is True
    # With sha256= prefix
    assert HMACVerifier.verify_signature(secret, payload, f"sha256={expected}") is True

def test_verify_signature_invalid():
    secret = "whsec_abc123"
    payload = '{"status": "paid"}'
    # Tampered payload
    assert HMACVerifier.verify_signature(secret, '{"status": "unpaid"}', "bad_sig") is False

def test_backoff_schedule():
    sched = HMACVerifier.calculate_backoff_schedule(max_attempts=4, base_delay_s=2.0)
    assert len(sched) == 4
    assert sched[0]["delay_seconds"] == 2.0
    assert sched[1]["delay_seconds"] == 4.0
    assert sched[2]["delay_seconds"] == 8.0
    assert sched[3]["delay_seconds"] == 16.0
