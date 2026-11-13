import hmac
import hashlib
import math
from typing import Dict, Any, List

class HMACVerifier:
    @staticmethod
    def compute_signature(secret: str, payload_bytes: bytes) -> str:
        """
        Computes standard HMAC-SHA256 hex digest.
        """
        if not secret:
            return ""
        return hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(secret: str, raw_body: str, provided_signature: str) -> bool:
        """
        Validates HMAC signature in constant time.
        Supports raw hex or 'sha256=' prefix.
        """
        if not secret or not provided_signature:
            return False

        sig = provided_signature.strip()
        if sig.startswith("sha256="):
            sig = sig[7:]

        expected = HMACVerifier.compute_signature(secret, raw_body.encode('utf-8'))
        return hmac.compare_digest(sig.lower(), expected.lower())

    @staticmethod
    def calculate_backoff_schedule(max_attempts: int = 5, base_delay_s: float = 2.0, max_delay_s: float = 300.0) -> List[Dict[str, Any]]:
        """
        Calculates deterministic exponential backoff delivery schedule.
        """
        schedule = []
        cumulative = 0.0

        for attempt in range(1, max_attempts + 1):
            delay = min(max_delay_s, base_delay_s * (2 ** (attempt - 1)))
            cumulative += delay
            schedule.append({
                "attempt": attempt,
                "delay_seconds": round(delay, 2),
                "cumulative_seconds": round(cumulative, 2)
            })

        return schedule
