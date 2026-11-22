"""Security, Identity, Scrypt Password Hashing, Signed Sessions, RBAC, and Rate Limiting."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque

SESSION_SECRET = os.environ.get("RJ_SESSION_SECRET", secrets.token_hex(32)).encode("utf-8")
SESSION_TTL_SECONDS = int(os.environ.get("RJ_SESSION_TTL", "28800"))  # 8 hours

ROLE_PERMISSIONS = {
    "principal": {
        "brand:write",
        "project:write",
        "project:delete",
        "settlement:write",
        "settlement:approve",
        "orchestrator:run",
        "admin:backup",
        "audit:read",
        "export:pdf",
    },
    "director": {
        "project:write",
        "settlement:write",
        "orchestrator:run",
        "audit:read",
        "export:pdf",
    },
    "viewer": {
        "audit:read",
    },
}


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(dk).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = encoded.split("$", 2)
        if scheme != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(dk_b64.encode())
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def issue_session_token(user_id: str, username: str, role: str) -> str:
    payload = {
        "uid": user_id,
        "sub": username,
        "role": role,
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
        "jti": secrets.token_hex(8),
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(SESSION_SECRET, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_session_token(token: str) -> dict | None:
    if not token or "." not in token:
        return None
    try:
        body, sig = token.rsplit(".", 1)
        expected = hmac.new(SESSION_SECRET, body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body.encode()).decode())
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, int]:
        now_ts = time.monotonic()
        bucket = self._hits[key]
        cutoff = now_ts - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now_ts - bucket[0])))
            return False, retry_after
        bucket.append(now_ts)
        return True, 0
