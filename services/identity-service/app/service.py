"""User + login domain logic."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, models


class IdentityError(Exception):
    """Invalid identity operation."""


class PermissionError_(IdentityError):
    """The actor's role may not manage the target role."""


# Role hierarchy (higher rank = more authority). Team management is gated by this: an actor may only
# create/modify users whose role ranks strictly below the actor's own. `admin` is the overall role and
# may manage every role (including other admins, so there can be many). See can_manage().
ROLE_RANK = {
    "admin": 100,
    "hub_manager": 80,
    "hub_supervisor": 60,
    "spokesperson": 40,
    "architect": 40,
    "civil_engineer": 40,
    "finance": 40,
    "vendor": 20,
    "consumer": 10,
    "service": 0,
}
# Roles the Team portal manages (consumers/vendors/service are provisioned by their own flows).
MANAGEABLE_ROLES = ("admin", "hub_manager", "hub_supervisor", "spokesperson", "architect",
                    "civil_engineer", "finance")


def role_rank(role: str) -> int:
    return ROLE_RANK.get(role, 0)


def can_manage(actor_role: str, target_role: str) -> bool:
    """True if an actor with actor_role may assign/modify a user to target_role."""
    if actor_role == "admin":
        return True  # the overall role manages everyone, admins included
    return role_rank(actor_role) > role_rank(target_role)


def _require_can_manage(actor_role: str, *target_roles: str) -> None:
    for r in target_roles:
        if not can_manage(actor_role, r):
            raise PermissionError_(f"role '{actor_role}' cannot manage role '{r}'")


def create_user(db: Session, email: str, password: str, name: str, role: str,
                org_ref: str = "", actor_role: str | None = None) -> models.User:
    email = email.strip().lower()
    if role not in models.ROLES:
        raise IdentityError(f"role must be one of {models.ROLES}")
    if actor_role is not None:
        _require_can_manage(actor_role, role)
    if db.get(models.User, email) is not None:
        raise IdentityError(f"User already exists: {email}")
    user = models.User(id=email, name=name.strip() or email, role=role, org_ref=org_ref,
                       password_hash=auth.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, email: str, actor_role: str, actor_email: str, *,
                role: str | None = None, active: bool | None = None,
                org_ref: str | None = None, name: str | None = None) -> models.User:
    """Change a user's role / team / active flag, honouring the role hierarchy."""
    user = db.get(models.User, email.strip().lower())
    if user is None:
        raise IdentityError(f"Unknown user: {email}")
    # The actor must out-rank the user's CURRENT role to touch them at all...
    _require_can_manage(actor_role, user.role)
    if role is not None and role != user.role:
        if role not in models.ROLES:
            raise IdentityError(f"role must be one of {models.ROLES}")
        _require_can_manage(actor_role, role)  # ...and out-rank the NEW role too
        user.role = role
    if active is not None:
        if not active and user.id == actor_email:
            raise IdentityError("You cannot deactivate your own account")
        user.active = active
    if org_ref is not None:
        user.org_ref = org_ref
    if name is not None and name.strip():
        user.name = name.strip()
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
