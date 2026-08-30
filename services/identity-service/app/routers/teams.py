"""Teams (OpenStack-style projects) + membership grants.

A team is a named container users are assigned into with a team-role (admin / member / viewer).
Assignment and revocation are the grant. They may be issued by a team-admin of that team, by HR, or by
the org admin (who can do anything). Team creation is a staff action (admin / hub leadership / HR).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth, schemas, service
from ..db import get_db

router = APIRouter(tags=["teams"])

# Reads: any authenticated internal staff. Team create/update: org admin, hub leadership, HR.
STAFF = auth.require_role("admin", "hub_manager", "hr")
READ = auth.require_role("admin", "hub_manager", "hub_supervisor", "hr",
                         "spokesperson", "architect", "site_engineer", "finance")


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.IdentityError as e:
        raise HTTPException(409, str(e))


@router.get("/teams", response_model=list[schemas.TeamOut])
def list_teams(_: dict = Depends(READ), db: Session = Depends(get_db)):
    return service.list_teams(db)


@router.post("/teams", response_model=schemas.TeamDetailOut, status_code=201)
def create_team(body: schemas.TeamIn, _: dict = Depends(STAFF), db: Session = Depends(get_db)):
    t = _run(service.create_team, db=db, name=body.name, description=body.description, spoke_id=body.spoke_id)
    return service.get_team(db, t.id)


@router.get("/teams/{team_id}", response_model=schemas.TeamDetailOut)
def get_team(team_id: int, _: dict = Depends(READ), db: Session = Depends(get_db)):
    return _run(service.get_team, db=db, team_id=team_id)


@router.patch("/teams/{team_id}", response_model=schemas.TeamDetailOut)
def update_team(team_id: int, body: schemas.TeamUpdate, _: dict = Depends(STAFF), db: Session = Depends(get_db)):
    _run(service.update_team, db=db, team_id=team_id, **body.model_dump(exclude_unset=True))
    return service.get_team(db, team_id)


def _require_team_admin(db: Session, actor: dict, team_id: int) -> None:
    if not service.can_admin_team(db, actor.get("role", ""), actor.get("sub", ""), team_id):
        raise HTTPException(403, "You must be an admin of this team, HR, or the org admin")


@router.post("/teams/{team_id}/members", response_model=schemas.TeamDetailOut, status_code=201)
def add_member(team_id: int, body: schemas.MemberIn, actor: dict = Depends(auth.current_user),
               db: Session = Depends(get_db)):
    """Grant a user a role in the team."""
    _require_team_admin(db, actor, team_id)
    _run(service.assign_member, db=db, team_id=team_id, user_id=body.user_id, role=body.role,
         granted_by=actor.get("name", "") or actor.get("sub", ""))
    return service.get_team(db, team_id)


@router.patch("/teams/{team_id}/members/{user_id}", response_model=schemas.TeamDetailOut)
def set_member_role(team_id: int, user_id: str, body: schemas.MemberIn,
                    actor: dict = Depends(auth.current_user), db: Session = Depends(get_db)):
    """Change a member's team-role."""
    _require_team_admin(db, actor, team_id)
    _run(service.assign_member, db=db, team_id=team_id, user_id=user_id, role=body.role,
         granted_by=actor.get("name", "") or actor.get("sub", ""))
    return service.get_team(db, team_id)


@router.delete("/teams/{team_id}/members/{user_id}", response_model=schemas.TeamDetailOut)
def remove_member(team_id: int, user_id: str, actor: dict = Depends(auth.current_user),
                  db: Session = Depends(get_db)):
    """Revoke a user's membership (their grant) in the team."""
    _require_team_admin(db, actor, team_id)
    _run(service.remove_member, db=db, team_id=team_id, user_id=user_id)
    return service.get_team(db, team_id)
