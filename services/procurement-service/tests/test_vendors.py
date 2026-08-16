"""Unit tests for vendor registry + product-level price lists (catalog mocked)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service, catalog_client

CATALOG = {
    "cement-ultratech": {"material_id": "cement", "brand": "UltraTech", "name": "UltraTech OPC 53"},
    "cement-acc": {"material_id": "cement", "brand": "ACC", "name": "ACC Gold PPC"},
    "cement-bharathi": {"material_id": "cement", "brand": "Bharathi", "name": "Bharathi OPC 53"},
    "steel-tata": {"material_id": "steel", "brand": "TATA", "name": "TATA Tiscon"},
}


@pytest.fixture()
def db(monkeypatch):
    monkeypatch.setattr(catalog_client, "get_product", lambda pid: CATALOG.get(pid))
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    yield s
    s.close()


def test_create_vendor_generates_unique_ids(db):
    a = service.create_vendor(db, "Deccan Traders", city="Medchal")
    b = service.create_vendor(db, "Deccan Distributors")
    assert a.id == "v_deccan"
    assert b.id == "v_deccan2"


def test_set_price_upserts_per_product(db):
    v = service.create_vendor(db, "Metro")
    service.set_price(db, v.id, "cement-acc", 402)
    service.set_price(db, v.id, "cement-acc", 398)  # update same product
    assert len(v.prices) == 1
    assert float(v.prices[0].price) == 398
    assert v.prices[0].brand == "ACC"
    assert v.prices[0].material_id == "cement"


def test_market_prices_cheapest_first_active_only(db):
    a = service.create_vendor(db, "Alpha")
    b = service.create_vendor(db, "Bravo")
    c = service.create_vendor(db, "Charlie")
    service.set_price(db, a.id, "cement-ultratech", 420)
    service.set_price(db, b.id, "cement-acc", 402)
    service.set_price(db, c.id, "cement-bharathi", 395)
    service.deactivate_vendor(db, c.id)  # cheapest but inactive → excluded
    market = service.market_prices(db, "cement")
    assert [m["vendor_id"] for m in market] == [b.id, a.id]
    assert market[0]["price"] == 402 and market[0]["brand"] == "ACC"


def test_market_shows_multiple_brands_per_material(db):
    a = service.create_vendor(db, "Alpha")
    service.set_price(db, a.id, "cement-ultratech", 420)
    service.set_price(db, a.id, "cement-bharathi", 375)
    brands = {m["brand"] for m in service.market_prices(db, "cement")}
    assert brands == {"UltraTech", "Bharathi"}


def test_unknown_product_rejected(db):
    v = service.create_vendor(db, "Godavari")
    with pytest.raises(service.ProcurementError):
        service.set_price(db, v.id, "cement-nonexistent", 400)
