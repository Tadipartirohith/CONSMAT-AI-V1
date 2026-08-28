"""Public enquiry: geofence routing to the covering spoke, else to the hub queue."""
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
    spoke = service.create_spoke(s, "Medchal Spoke")
    service.add_area(s, spoke.id, "Medchal")
    yield s
    s.close()


def test_enquiry_routes_to_covering_spoke(db):
    r = service.create_enquiry(db, name="Asha", location="Plot 4, Medchal, Hyderabad", phone="999")
    assert r["routed_to"] == "spoke"
    assert r["spoke"] == "Medchal Spoke"
    enq = db.get(models.Enquiry, r["id"])
    assert enq.spoke_id and enq.status == models.ENQ_NEW


def test_enquiry_routes_to_hub_when_unserved(db):
    r = service.create_enquiry(db, name="Ravi", location="Gachibowli")
    assert r["routed_to"] == "hub"
    assert r["spoke"] is None
    enq = db.get(models.Enquiry, r["id"])
    assert enq.spoke_id == ""


def test_enquiry_requires_name_and_location(db):
    with pytest.raises(service.SiteError):
        service.create_enquiry(db, name="", location="Medchal")
    with pytest.raises(service.SiteError):
        service.create_enquiry(db, name="X", location="")


def test_update_enquiry_status(db):
    r = service.create_enquiry(db, name="Asha", location="Medchal")
    e = service.update_enquiry(db, r["id"], status=models.ENQ_CONTACTED, handled_by="Spoke")
    assert e.status == "contacted" and e.handled_by == "Spoke"
    with pytest.raises(service.SiteError):
        service.update_enquiry(db, r["id"], status="bogus")
