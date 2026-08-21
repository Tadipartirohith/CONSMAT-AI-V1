"""Unit tests for identity: hashing, login, token issuance, role validation."""
import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import auth, service
from app.config import settings


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    yield s
    s.close()


def test_hash_and_verify():
    h = auth.hash_password("consmat123")
    assert auth.verify_password("consmat123", h)
    assert not auth.verify_password("wrong", h)


def test_create_and_authenticate(db):
    service.create_user(db, "Manager@Consmat.com", "consmat123", "Mgr", "hub_manager")
    user = service.authenticate(db, "manager@consmat.com", "consmat123")  # case-insensitive
    assert user.role == "hub_manager"
    with pytest.raises(service.IdentityError):
        service.authenticate(db, "manager@consmat.com", "nope")


def test_invalid_role_rejected(db):
    with pytest.raises(service.IdentityError):
        service.create_user(db, "x@y.com", "consmat123", "X", "superuser")


def test_token_roundtrip_and_claims():
    tok = auth.make_token("civil@consmat.com", "civil_engineer", name="CE", org_ref="s_medchal")
    payload = jwt.decode(tok, settings.jwt_secret, algorithms=[settings.jwt_alg])
    assert payload["sub"] == "civil@consmat.com"
    assert payload["role"] == "civil_engineer"
    assert payload["org_ref"] == "s_medchal"


def test_role_hierarchy_can_manage():
    # admin manages everyone (including other admins); supervisor manages only ops, not peers/up
    assert service.can_manage("admin", "admin")
    assert service.can_manage("admin", "civil_engineer")
    assert service.can_manage("hub_supervisor", "architect")
    assert not service.can_manage("hub_supervisor", "hub_supervisor")
    assert not service.can_manage("hub_supervisor", "hub_manager")
    assert not service.can_manage("architect", "spokesperson")  # ops cannot manage peers


def test_create_user_respects_actor_role(db):
    # a supervisor may create ops but not another supervisor/admin
    service.create_user(db, "ce1@consmat.com", "consmat123", "CE1", "civil_engineer",
                        actor_role="hub_supervisor")
    with pytest.raises(service.PermissionError_):
        service.create_user(db, "sup2@consmat.com", "consmat123", "S2", "hub_supervisor",
                            actor_role="hub_supervisor")


def test_update_user_role_and_active(db):
    service.create_user(db, "arch@consmat.com", "consmat123", "Arch", "architect")
    # admin promotes architect to supervisor
    u = service.update_user(db, "arch@consmat.com", "admin", "admin@consmat.com", role="hub_supervisor")
    assert u.role == "hub_supervisor"
    # a supervisor cannot then manage that same-rank supervisor
    with pytest.raises(service.PermissionError_):
        service.update_user(db, "arch@consmat.com", "hub_supervisor", "sup@consmat.com", active=False)
    # you cannot deactivate your own account
    service.create_user(db, "me@consmat.com", "consmat123", "Me", "hub_manager")
    with pytest.raises(service.IdentityError):
        service.update_user(db, "me@consmat.com", "hub_manager", "me@consmat.com", active=False)
