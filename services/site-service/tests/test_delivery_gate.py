"""Delivery gate (captive finance / client payment) + the <1-week phase-date escalation."""
from datetime import date, timedelta
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
    yield s
    s.close()


def _captive_site(s, with_dates=True):
    site = models.Site(consumer_id="c1", label="Villa", area_sqft=Decimal("1000"), floors=1,
                       project_type="captive", status="planned")
    s.add(site); s.flush()
    start = date(2026, 1, 1)
    for seq in range(1, 10):
        s.add(models.PhaseProgress(site_id=site.id, phase_seq=seq, status=models.PH_PENDING,
                                   planned_start=start if with_dates else None,
                                   planned_end=start + timedelta(days=10) if with_dates else None))
    s.commit(); s.refresh(site)
    return site


def test_captive_blocked_without_finance(db):
    site = _captive_site(db)
    ready, reason = service.delivery_ready(db, site)
    assert not ready and "finance" in reason.lower()


def test_captive_ready_with_finance_and_dates(db):
    site = _captive_site(db)
    db.add(models.ProjectFinance(site_id=site.id, status=models.FIN_APPROVED)); db.commit()
    ready, reason = service.delivery_ready(db, site)
    assert ready and reason == ""


def test_captive_blocked_without_dates(db):
    site = _captive_site(db, with_dates=False)
    db.add(models.ProjectFinance(site_id=site.id, status=models.FIN_APPROVED)); db.commit()
    ready, reason = service.delivery_ready(db, site)
    assert not ready and "date" in reason.lower()


def test_phase_end_change_escalates_and_requires_remarks(db):
    site = _captive_site(db)
    p3 = next(p for p in site.phases if p.phase_seq == 3)
    p4 = next(p for p in site.phases if p.phase_seq == 4)
    p4.planned_start = date(2026, 2, 1)
    db.commit()
    # SE moves phase 3's end to Jan 28 -> only 4 days before phase 4 -> escalated, remark required
    with pytest.raises(service.SiteError):
        service.set_phase_dates(db, site.id, 3, None, date(2026, 1, 28), "site_engineer", "SE")
    res = service.set_phase_dates(db, site.id, 3, None, date(2026, 1, 28), "site_engineer", "SE",
                                  remarks="rain delay, compressing schedule")
    chg = db.get(models.PhaseDateChange, res["pending_change_id"])
    assert chg.escalated is True and chg.remarks


def test_escalated_change_needs_hub_not_spoke(db):
    site = _captive_site(db)
    p4 = next(p for p in site.phases if p.phase_seq == 4)
    p4.planned_start = date(2026, 2, 1); db.commit()
    res = service.set_phase_dates(db, site.id, 3, None, date(2026, 1, 28), "site_engineer", "SE",
                                  remarks="compress")
    cid = res["pending_change_id"]
    with pytest.raises(service.SiteError):
        service.decide_phase_change(db, cid, True, "spokesperson", "Spoke")  # spoke alone can't
    chg = service.decide_phase_change(db, cid, True, "hub_supervisor", "Sup")
    assert chg.status == models.PDC_APPROVED
