"""Unit tests for vendor registry + price-list logic (in-memory SQLite harness)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    yield s
    s.close()


def test_create_vendor_generates_unique_ids(db):
    a = service.create_vendor(db, "Deccan Traders", city="Medchal")
    b = service.create_vendor(db, "Deccan Distributors")  # same first word -> collision
    assert a.id == "v_deccan"
    assert b.id == "v_deccan2"
    assert a.active is True


def test_set_price_upserts(db):
    v = service.create_vendor(db, "Metro")
    service.set_price(db, v.id, "cement", 402)
    service.set_price(db, v.id, "cement", 398)  # update, not duplicate
    assert len(v.prices) == 1
    assert float(v.prices[0].price) == 398


def test_market_prices_cheapest_first_and_active_only(db):
    a = service.create_vendor(db, "Alpha")
    b = service.create_vendor(db, "Bravo")
    c = service.create_vendor(db, "Charlie")
    service.set_price(db, a.id, "cement", 420)
    service.set_price(db, b.id, "cement", 402)
    service.set_price(db, c.id, "cement", 395)
    service.deactivate_vendor(db, c.id)  # cheapest but inactive -> excluded
    market = service.market_prices(db, "cement")
    assert [m["vendor_id"] for m in market] == [b.id, a.id]
    assert market[0]["price"] == 402


def test_delete_price_and_unknown_vendor(db):
    v = service.create_vendor(db, "Godavari")
    service.set_price(db, v.id, "sand", 1080)
    service.delete_price(db, v.id, "sand")
    assert service.market_prices(db, "sand") == []
    with pytest.raises(service.ProcurementError):
        service.set_price(db, "v_missing", "sand", 100)
