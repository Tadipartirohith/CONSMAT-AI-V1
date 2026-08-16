"""Unit tests for the deterministic procurement engine + profitability."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service, procurement_engine


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    # three vendors for cement, one for steel
    a = service.create_vendor(s, "Alpha")
    b = service.create_vendor(s, "Bravo")
    c = service.create_vendor(s, "Charlie")
    service.set_price(s, a.id, "cement", 420)
    service.set_price(s, b.id, "cement", 402)
    service.set_price(s, c.id, "cement", 395, min_qty=500)  # cheapest but high min order
    service.set_price(s, a.id, "steel", 63000)
    yield s
    s.close()


def test_plan_picks_cheapest_vendor(db):
    result = procurement_engine.plan(db, [{"material_id": "cement", "qty": 100}])
    line = result["lines"][0]
    assert line["unit_cost"] == 395            # cheapest overall
    assert line["line_cost"] == 39500
    assert line["below_min_qty"] is True       # 100 < min_qty 500
    assert line["alternatives"] == 2
    assert result["total_cost"] == 39500


def test_plan_flags_unavailable(db):
    result = procurement_engine.plan(db, [{"material_id": "bricks", "qty": 1000}])
    assert result["unavailable"] == ["bricks"]
    assert result["lines"] == []


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
    assert prof["lines"][0]["loss_making"] is False


def test_profitability_none_without_prices(db):
    result = procurement_engine.plan(db, [{"material_id": "cement", "qty": 100}])
    assert procurement_engine.profitability(result, None) is None
