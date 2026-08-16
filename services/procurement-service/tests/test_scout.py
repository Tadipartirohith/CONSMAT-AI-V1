"""Tests for external price-scout + supplier price-list import (stub provider, no network)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service, llm


@pytest.fixture()
def db(monkeypatch):
    # force the stub scout provider (LLM not configured)
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    yield s
    s.close()


def test_scout_stores_indicative_offers(db):
    res = service.run_scout(db, "cement")
    assert res["provider"] == "stub"
    assert res["count"] >= 1
    offers = service.list_external_offers(db, "cement")
    assert offers and all(o.confidence == "indicative" for o in offers)


def test_scout_refreshes_indicative_but_keeps_firm(db):
    service.import_offers(db, [{"material_id": "cement", "seller": "PriceList Co", "price": 350}])
    service.run_scout(db, "cement")   # refreshes indicative
    service.run_scout(db, "cement")   # again — should not duplicate/lose the firm one
    offers = service.list_external_offers(db, "cement")
    firm = [o for o in offers if o.confidence == "firm"]
    assert len(firm) == 1 and firm[0].source == "csv"


def test_import_offers(db):
    n = service.import_offers(db, [
        {"material_id": "steel", "seller": "Kamdhenu", "price": 61000, "product_name": "Fe550D"},
        {"material_id": "steel", "price": None},  # skipped (no price)
    ])
    assert n == 1
    assert service.list_external_offers(db, "steel")[0].seller == "Kamdhenu"
