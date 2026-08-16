"""Tests for geofence resolution + consumer intake auto-assignment."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import geofence, service, models


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    medchal = service.create_spoke(s, "Medchal Spoke")
    sangareddy = service.create_spoke(s, "Sangareddy Spoke")
    service.add_area(s, medchal.id, "Medchal")
    service.add_area(s, medchal.id, "Kompally")
    service.add_area(s, sangareddy.id, "Sangareddy")
    yield s
    s.close()


def test_resolve_by_area_keyword(db):
    spoke = geofence.resolve_spoke(db, "Plot 4, Medchal, Hyderabad")
    assert spoke.id == "s_medchal"


def test_resolve_no_coverage_returns_none(db):
    assert geofence.resolve_spoke(db, "Shamshabad") is None


def test_most_specific_area_wins(db):
    # add an overlapping broad keyword to sangareddy that also appears in a medchal address
    service.add_area(db, "s_sangareddy", "Hyd")
    spoke = geofence.resolve_spoke(db, "Kompally, Hyd")
    assert spoke.id == "s_medchal"        # "Kompally" (8) beats "Hyd" (3)


def test_intake_auto_assigns_spoke(db):
    result = service.intake(db, "Ravi Constructions", "contractor", "Site near Medchal X Roads")
    assert result["spoke"].id == "s_medchal"
    assert result["consumer"].tier == "contractor"
    assert result["consumer"].spoke_id == "s_medchal"


def test_intake_fails_without_coverage(db):
    with pytest.raises(service.SiteError):
        service.intake(db, "Someone", "individual", "Vizag")
