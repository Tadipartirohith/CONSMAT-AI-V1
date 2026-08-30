"""Auth + user REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, schemas, service
from ..db import get_db

router = APIRouter(tags=["identity"])


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    try:
        user = service.authenticate(db, body.email, body.password)
    except service.IdentityError:
        raise HTTPException(401, "Invalid credentials")
    token = auth.make_token(user.id, user.role, name=user.name, org_ref=user.org_ref)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/auth/me", response_model=schemas.UserOut)
def me(user: dict = Depends(auth.current_user), db: Session = Depends(get_db)):
    from ..models import User
    u = db.get(User, user["sub"])
    if u is None:
        raise HTTPException(401, "Unknown user")
    return u


# Team management: any hub role that can manage at least ops (supervisor and up), plus HR, may reach these.
TEAM = auth.require_role("admin", "hub_manager", "hub_supervisor", "hr")


@router.get("/roles")
def manageable_roles(actor: dict = Depends(TEAM)):
    """Roles the current actor may assign, plus the whole rank map (drives the Team portal)."""
    return {
        "assignable": [r for r in service.MANAGEABLE_ROLES if service.can_manage(actor.get("role", ""), r)],
        "ranks": service.ROLE_RANK,
        "manageable": list(service.MANAGEABLE_ROLES),
    }


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(_: dict = Depends(TEAM), db: Session = Depends(get_db)):
    return service.list_users(db)


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserIn, actor: dict = Depends(auth.current_user),
                db: Session = Depends(get_db)):
    # `service` (internal) provisions consumer/vendor logins; hub roles are gated by the hierarchy.
    actor_role = actor.get("role", "")
    if actor_role == "service":
        actor_role_for_check = None
    elif actor_role in ("admin", "hub_manager", "hub_supervisor", "hr"):
        actor_role_for_check = actor_role
    else:
        raise HTTPException(403, "Not allowed to create users")
    try:
        return service.create_user(db, body.email, body.password, body.name, body.role,
                                   body.org_ref, actor_role=actor_role_for_check)
    except service.PermissionError_ as e:
        raise HTTPException(403, str(e))
    except service.IdentityError as e:
        raise HTTPException(409, str(e))


@router.patch("/users/{email}", response_model=schemas.UserOut)
def update_user(email: str, body: schemas.UserUpdate, actor: dict = Depends(TEAM),
                db: Session = Depends(get_db)):
    """Assign/remove a role, move a user to a team (org_ref), or (de)activate them."""
    try:
        return service.update_user(db, email, actor.get("role", ""), actor.get("sub", ""),
                                   role=body.role, active=body.active, org_ref=body.org_ref,
                                   name=body.name)
    except service.PermissionError_ as e:
        raise HTTPException(403, str(e))
    except service.IdentityError as e:
        raise HTTPException(409, str(e))
