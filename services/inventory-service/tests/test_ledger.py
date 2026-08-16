"""Unit tests for the inventory ledger logic (run against in-memory SQLite).

These test pure domain behavior (balances, weighted-average cost, oversell guards, reservations).
Production runs on PostgreSQL; SQLite is used here only as a fast, dependency-light harness.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models, service


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    s.add(models.Material(id="cement", name="Cement", unit="bags", grade="OPC 53", per_sqft=Decimal("0.4")))
    s.commit()
    yield s
    s.close()


def test_receive_sets_on_hand_and_avg_cost(db):
    service.receive(db, "cement", 100, 400)
    item = service.get_item(db, "cement")
    assert float(item.on_hand) == 100
    assert float(item.avg_cost) == 400


def test_weighted_average_cost(db):
    service.receive(db, "cement", 100, 400)   # 100 @ 400
    service.receive(db, "cement", 100, 500)   # +100 @ 500  -> avg 450
    item = service.get_item(db, "cement")
    assert float(item.on_hand) == 200
    assert float(item.avg_cost) == 450


def test_dispatch_reduces_stock_at_avg_cost(db):
    service.receive(db, "cement", 100, 400)
    entry = service.dispatch(db, "cement", 30, ref_id="ORD-1")
    item = service.get_item(db, "cement")
    assert float(item.on_hand) == 70
    assert entry.direction == "outbound"
    assert float(entry.qty) == -30
    assert float(entry.unit_cost) == 400  # valued at average cost


def test_dispatch_oversell_guarded(db):
    service.receive(db, "cement", 10, 400)
    with pytest.raises(service.InventoryError):
        service.dispatch(db, "cement", 25)


def test_reservation_flow(db):
    service.receive(db, "cement", 100, 400)
    service.reserve(db, "cement", 40)
    item = service.get_item(db, "cement")
    assert float(item.reserved) == 40
    assert float(item.available) == 60
    # cannot reserve beyond available
    with pytest.raises(service.InventoryError):
        service.reserve(db, "cement", 70)
    # dispatch from reservation consumes both reserved and on_hand
    service.dispatch(db, "cement", 40, from_reservation=True)
    item = service.get_item(db, "cement")
    assert float(item.on_hand) == 60
    assert float(item.reserved) == 0


def test_adjustment_and_negative_guard(db):
    service.receive(db, "cement", 50, 400)
    service.adjust(db, "cement", -5, note="breakage")
    assert float(service.get_item(db, "cement").on_hand) == 45
    with pytest.raises(service.InventoryError):
        service.adjust(db, "cement", -100)


def test_ledger_records_every_movement(db):
    service.receive(db, "cement", 100, 400)
    service.dispatch(db, "cement", 20)
    service.adjust(db, "cement", -5)
    entries = service.ledger(db, "cement")
    assert len(entries) == 3
    # newest first; balances reflect running total
    assert [float(e.balance_after) for e in entries] == [75, 80, 100]
