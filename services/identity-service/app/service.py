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
    "hr": 70,
    "hub_supervisor": 60,
    "spokesperson": 40,
    "architect": 40,
    "site_engineer": 40,
    "finance": 40,
    "vendor": 20,
    "consumer": 10,
    "service": 0,
}
# Roles the Team portal manages (consumers/vendors/service are provisioned by their own flows).
MANAGEABLE_ROLES = ("admin", "hub_manager", "hr", "hub_supervisor", "spokesperson", "architect",
                    "site_engineer", "finance")

# Staff who may administer teams and their membership regardless of team-level role: the org admin,
# hub leadership, and HR. Anyone else needs to be a team-admin of the specific team.
TEAM_STAFF = ("admin", "hub_manager", "hr")


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
        if not active and user.role == "admin":
            raise IdentityError("The admin account is permanent and cannot be deactivated")
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


def delete_user(db: Session, email: str, actor_role: str, actor_email: str) -> None:
    """Permanently delete a user. The admin account is protected; the actor must out-rank the target."""
    email = email.strip().lower()
    user = db.get(models.User, email)
    if user is None:
        raise IdentityError(f"Unknown user: {email}")
    if user.role == "admin":
        raise IdentityError("The admin account is permanent and cannot be deleted")
    if user.id == (actor_email or "").strip().lower():
        raise IdentityError("You cannot delete your own account")
    _require_can_manage(actor_role, user.role)
    # drop the user's team memberships first (they reference the user id).
    for m in db.execute(select(models.TeamMember).where(models.TeamMember.user_id == email)).scalars():
        db.delete(m)
    db.delete(user)
    db.commit()


# ---- Teams (OpenStack-style projects) + membership grants ----

def list_teams(db: Session) -> list[dict]:
    teams = list(db.execute(select(models.Team).order_by(models.Team.name)).scalars())
    out = []
    for t in teams:
        out.append({"id": t.id, "name": t.name, "description": t.description, "spoke_id": t.spoke_id,
                    "active": t.active, "member_count": len(t.members), "created_at": t.created_at})
    return out


def get_team(db: Session, team_id: int) -> dict:
    t = db.get(models.Team, team_id)
    if t is None:
        raise IdentityError(f"Unknown team: {team_id}")
    names = {u.id: u.name for u in db.execute(select(models.User)).scalars()}
    members = [{"user_id": m.user_id, "name": names.get(m.user_id, m.user_id), "role": m.role,
                "granted_by": m.granted_by, "created_at": m.created_at}
               for m in sorted(t.members, key=lambda m: (m.role != "admin", m.user_id))]
    return {"id": t.id, "name": t.name, "description": t.description, "spoke_id": t.spoke_id,
            "active": t.active, "members": members, "created_at": t.created_at}


def create_team(db: Session, name: str, description: str = "", spoke_id: str = "") -> models.Team:
    name = (name or "").strip()
    if not name:
        raise IdentityError("A team needs a name")
    if db.execute(select(models.Team).where(models.Team.name == name)).scalar_one_or_none():
        raise IdentityError(f"A team named '{name}' already exists")
    t = models.Team(name=name, description=(description or "").strip(), spoke_id=(spoke_id or "").strip())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def update_team(db: Session, team_id: int, **fields) -> models.Team:
    t = db.get(models.Team, team_id)
    if t is None:
        raise IdentityError(f"Unknown team: {team_id}")
    for k in ("name", "description", "spoke_id", "active"):
        if k in fields and fields[k] is not None:
            setattr(t, k, fields[k].strip() if isinstance(fields[k], str) else fields[k])
    db.commit()
    db.refresh(t)
    return t


def is_team_admin(db: Session, team_id: int, user_email: str) -> bool:
    m = db.execute(select(models.TeamMember).where(
        models.TeamMember.team_id == team_id, models.TeamMember.user_id == user_email.strip().lower())
    ).scalar_one_or_none()
    return bool(m and m.role == "admin")


def can_admin_team(db: Session, actor_role: str, actor_email: str, team_id: int) -> bool:
    """Org admin, hub leadership and HR may manage any team; otherwise the actor must be a team-admin
    of this specific team."""
    if actor_role in TEAM_STAFF:
        return True
    return is_team_admin(db, team_id, actor_email)


def assign_member(db: Session, team_id: int, user_id: str, role: str, granted_by: str = "") -> models.TeamMember:
    """Grant (or change) a user's role in a team. Idempotent per (team, user)."""
    t = db.get(models.Team, team_id)
    if t is None:
        raise IdentityError(f"Unknown team: {team_id}")
    if role not in models.TEAM_ROLES:
        raise IdentityError(f"team role must be one of {models.TEAM_ROLES}")
    user_id = user_id.strip().lower()
    if db.get(models.User, user_id) is None:
        raise IdentityError(f"Unknown user: {user_id}")
    m = db.execute(select(models.TeamMember).where(
        models.TeamMember.team_id == team_id, models.TeamMember.user_id == user_id)).scalar_one_or_none()
    if m is None:
        m = models.TeamMember(team_id=team_id, user_id=user_id, role=role, granted_by=granted_by)
        db.add(m)
    else:
        m.role = role
        m.granted_by = granted_by
    db.commit()
    db.refresh(m)
    return m


def remove_member(db: Session, team_id: int, user_id: str) -> None:
    """Revoke a user's membership (and their grant) in a team."""
    m = db.execute(select(models.TeamMember).where(
        models.TeamMember.team_id == team_id,
        models.TeamMember.user_id == user_id.strip().lower())).scalar_one_or_none()
    if m is None:
        raise IdentityError("That user is not a member of this team")
    db.delete(m)
    db.commit()
