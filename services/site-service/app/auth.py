"""Shared auth: validate JWTs issued by identity-service (shared secret) + mint service tokens.

Every service carries an identical copy of this module. Tokens are validated locally with the shared
JWT_SECRET — no call back to identity-service. `service_token()` mints a short-lived token with
role=service for internal service-to-service calls.
"""
from __future__ import annotations

import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

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
        role = user.get("role")
        if role != "admin" and role not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return user
    return guard


def service_token() -> str:
    """Short-lived token identifying an internal service call (role=service)."""
    now = int(time.time())
    return jwt.encode({"sub": "svc", "role": "service", "iat": now, "exp": now + 3600},
                      settings.jwt_secret, algorithm=settings.jwt_alg)
