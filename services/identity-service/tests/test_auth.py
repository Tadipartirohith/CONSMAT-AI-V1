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
