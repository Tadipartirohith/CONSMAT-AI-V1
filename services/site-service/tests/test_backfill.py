"""Tests for backfill: retry short dispatch lines against current stock."""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models, service, inventory_client


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    # a site with one partial dispatch: aggregate dispatched, cement short
    site = models.Site(consumer_id="c1", label="Villa", area_sqft=Decimal("1000"), floors=1)
    s.add(site); s.flush()
    d = models.Dispatch(site_id=site.id, phase_seq=3, status=models.DSP_PARTIAL)
    s.add(d); s.flush()
    s.add(models.DispatchLine(dispatch_id=d.id, material_id="aggregate", qty=Decimal("50"),
                              status=models.DSP_DISPATCHED))
    s.add(models.DispatchLine(dispatch_id=d.id, material_id="cement", qty=Decimal("360"), status="short"))
    s.commit()
    yield s
    s.close()


def test_backfill_heals_dispatch_when_stock_available(db, monkeypatch):
    monkeypatch.setattr(inventory_client, "post_outbound", lambda *a, **k: {"ok": True})
    result = service.backfill_site(db, 1)
    assert len(result["backfilled"]) == 1
    assert result["backfilled"][0]["material_id"] == "cement"
    assert result["still_short"] == []
    d = db.get(models.Dispatch, 1)
    assert d.status == models.DSP_DISPATCHED           # partial -> dispatched
    assert all(l.status == models.DSP_DISPATCHED for l in d.lines)


def test_backfill_leaves_short_when_stock_insufficient(db, monkeypatch):
    def boom(*a, **k):
        raise inventory_client.InsufficientStock("cement")
    monkeypatch.setattr(inventory_client, "post_outbound", boom)
    result = service.backfill_site(db, 1)
    assert result["backfilled"] == []
    assert len(result["still_short"]) == 1
    d = db.get(models.Dispatch, 1)
    assert d.status == models.DSP_PARTIAL              # unchanged
    assert any(l.status == "short" for l in d.lines)


def test_backfill_idempotent_when_nothing_short(db, monkeypatch):
    calls = {"n": 0}
    def count(*a, **k):
        calls["n"] += 1
        return {}
    monkeypatch.setattr(inventory_client, "post_outbound", count)
    service.backfill_site(db, 1)   # heals cement
    calls["n"] = 0
    result = service.backfill_site(db, 1)  # nothing short now
    assert result["backfilled"] == [] and result["still_short"] == []
    assert calls["n"] == 0  # no outbound attempted
