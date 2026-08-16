"""Unit tests for margin-rule precedence and selling-price computation."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service, inventory_client


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    service.set_rule(s, None, None, 12)               # global
    service.set_rule(s, None, "individual", 18)       # tier
    service.set_rule(s, "cement", None, 15)           # material
    service.set_rule(s, "cement", "individual", 20)   # material+tier
    yield s
    s.close()


def test_precedence_material_and_tier_wins(db):
    margin, src = service.resolve_margin(db, "cement", "individual")
    assert (margin, src) == (20, "material+tier")


def test_precedence_material_only(db):
    margin, src = service.resolve_margin(db, "cement", "contractor")  # no cement+contractor
    assert (margin, src) == (15, "material")


def test_precedence_tier_only(db):
    margin, src = service.resolve_margin(db, "steel", "individual")   # no steel rules
    assert (margin, src) == (18, "tier")


def test_precedence_global(db):
    margin, src = service.resolve_margin(db, "steel", "commercial")
    assert (margin, src) == (12, "global")


def test_service_default_when_no_rules():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, future=True)()
    margin, src = service.resolve_margin(s, "cement", "individual")
    assert src == "service-default"
    s.close()


def test_upsert_updates_not_duplicates(db):
    service.set_rule(db, "cement", "individual", 25)  # was 20
    rules = [r for r in service.list_rules(db) if r.material_id == "cement" and r.tier == "individual"]
    assert len(rules) == 1
    assert float(rules[0].margin_pct) == 25


def test_price_material_applies_margin(db, monkeypatch):
    monkeypatch.setattr(inventory_client, "landed_cost", lambda mid: 400.0)
    p = service.price_material(db, "cement", "individual")   # 20% margin
    assert p["landed_cost"] == 400.0
    assert p["margin_pct"] == 20
    assert p["unit_price"] == 480.0                          # 400 * 1.20


def test_invalid_tier_rejected(db):
    with pytest.raises(service.PricingError):
        service.set_rule(db, None, "vip", 10)
