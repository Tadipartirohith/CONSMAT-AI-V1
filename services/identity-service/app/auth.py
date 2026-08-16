"""Password hashing + JWT issuance (identity-service is the token issuer)."""
from __future__ import annotations

import time

import bcrypt
import jwt

from .config import settings


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(sub: str, role: str, *, name: str = "", org_ref: str = "") -> str:
    now = int(time.time())
    payload = {
        "sub": sub, "role": role, "name": name, "org_ref": org_ref,
        "iat": now, "exp": now + settings.access_token_ttl_min * 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


# --- validation (for identity-service's own protected endpoints) ---
from fastapi import Depends, HTTPException  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # noqa: E402

_bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    if creds is None:
        raise HTTPException(401, "Not authenticated")
    try:
        return jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except Exception:  # noqa: BLE001
        raise HTTPException(401, "Invalid or expired token")


def require_role(*roles):
    def guard(user: dict = Depends(current_user)) -> dict:
        if user.get("role") != "admin" and user.get("role") not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return user
    return guard
