"""Unit tests for the deterministic procurement engine + profitability (product-level, catalog mocked)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service, procurement_engine, catalog_client

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
    a = service.create_vendor(s, "Alpha")
    b = service.create_vendor(s, "Bravo")
    c = service.create_vendor(s, "Charlie")
    service.set_price(s, a.id, "cement-ultratech", 420)
    service.set_price(s, b.id, "cement-acc", 402)
    service.set_price(s, c.id, "cement-bharathi", 395, min_qty=500)  # cheapest but high min order
    service.set_price(s, a.id, "steel-tata", 63000)
    yield s
    s.close()


def test_plan_picks_cheapest_product(db):
    result = procurement_engine.plan(db, [{"material_id": "cement", "qty": 100}])
    line = result["lines"][0]
    assert line["unit_cost"] == 395
    assert line["brand"] == "Bharathi"
    assert line["product_id"] == "cement-bharathi"
    assert line["below_min_qty"] is True            # 100 < 500
    assert line["alternatives"] == 2                # UltraTech + ACC also available
    assert result["total_cost"] == 39500


def test_plan_flags_unavailable(db):
    result = procurement_engine.plan(db, [{"material_id": "bricks", "qty": 1000}])
    assert len(result["unavailable"]) == 1
    assert result["unavailable"][0]["material_id"] == "bricks"
    assert result["lines"] == []


def test_specific_product_without_vendor_is_unavailable(db):
    result = procurement_engine.plan(db, [
        {"material_id": "cement", "product_id": "cement-nobody-sells", "product_name": "Nobody Sells Cement", "qty": 100}])
    assert result["lines"] == []
    u = result["unavailable"][0]
    assert u["product_id"] == "cement-nobody-sells"
    assert u["name"] == "Nobody Sells Cement"
    assert "no vendor" in u["reason"]


def test_multi_material_total(db):
    result = procurement_engine.plan(db, [
        {"material_id": "cement", "qty": 100},
        {"material_id": "steel", "qty": 2},
    ])
    assert result["total_cost"] == 39500 + 126000


def test_profitability(db):
    result = procurement_engine.plan(db, [{"material_id": "cement", "qty": 100}])
    prof = procurement_engine.profitability(result, {"cement": 450})
    assert prof["buy_total"] == 39500
    assert prof["sell_total"] == 45000
    assert prof["margin_total"] == 5500
    assert prof["profitable"] is True
