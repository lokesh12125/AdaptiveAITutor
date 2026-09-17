"""Secure, self-contained local authentication using PBKDF2-HMAC password hashing and signed tokens."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import BACKEND_DIR

# Persist or generate a local server secret for signing tokens
SECRET_FILE = BACKEND_DIR / ".auth_secret"
if SECRET_FILE.exists():
    SERVER_SECRET = SECRET_FILE.read_bytes()
else:
    SERVER_SECRET = secrets.token_bytes(32)
    try:
        SECRET_FILE.write_bytes(SERVER_SECRET)
    except Exception:
        pass

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a unique salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt:key hash."""
    try:
        salt_hex, key_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        actual_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False


def create_access_token(user_id: str, name: str, email: str, role: str = "student", expires_in_seconds: int = 86400 * 7) -> str:
    """Create a signed HMAC-SHA256 token encoding payload and expiry."""
    payload = {
        "uid": user_id,
        "name": name,
        "email": email,
        "role": role,
        "exp": int(time.time()) + expires_in_seconds,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(SERVER_SECRET, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def decode_access_token(token: str) -> dict:
    """Validate signature and expiry, returning decoded payload."""
    try:
        payload_b64, signature = token.split(".", 1)
        expected_sig = hmac.new(SERVER_SECRET, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
        # Pad payload_b64
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")


def get_current_user(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(security_bearer)]) -> dict:
    """Dependency for endpoints requiring authentication."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return decode_access_token(credentials.credentials)


def get_optional_user(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Security(security_bearer)]) -> Optional[dict]:
    """Optional auth dependency allowing anonymous fallback."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except Exception:
        return None
