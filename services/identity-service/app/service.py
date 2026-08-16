"""User + login domain logic."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, models


class IdentityError(Exception):
    """Invalid identity operation."""


def create_user(db: Session, email: str, password: str, name: str, role: str,
                org_ref: str = "") -> models.User:
    email = email.strip().lower()
    if role not in models.ROLES:
        raise IdentityError(f"role must be one of {models.ROLES}")
    if db.get(models.User, email) is not None:
        raise IdentityError(f"User already exists: {email}")
    user = models.User(id=email, name=name.strip() or email, role=role, org_ref=org_ref,
                       password_hash=auth.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> models.User:
    user = db.get(models.User, email.strip().lower())
    if user is None or not user.active or not auth.verify_password(password, user.password_hash):
        raise IdentityError("Invalid credentials")
    return user


def list_users(db: Session) -> list[models.User]:
    return list(db.execute(select(models.User).order_by(models.User.role)).scalars())
