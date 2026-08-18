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


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(_: dict = Depends(auth.require_role("admin", "hub_manager")), db: Session = Depends(get_db)):
    return service.list_users(db)


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserIn,
                _: dict = Depends(auth.require_role("admin", "hub_manager", "service")),
                db: Session = Depends(get_db)):
    try:
        return service.create_user(db, body.email, body.password, body.name, body.role, body.org_ref)
    except service.IdentityError as e:
        raise HTTPException(409, str(e))
