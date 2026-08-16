"""Field REST API: spokes, consumers, sites, plans, and phase-driven dispatch."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import bom, inventory_client, models, schemas, service
from ..db import get_db

router = APIRouter(tags=["sites"])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.SiteError as e:
        raise HTTPException(409, str(e))
    except inventory_client.InventoryUnavailable as e:
        raise HTTPException(502, f"inventory-service error: {e}")


# ---- reference ----
@router.get("/phases", response_model=list[schemas.PhaseRef])
def list_phases(db: Session = Depends(get_db)):
    return db.execute(select(models.Phase).order_by(models.Phase.seq)).scalars().all()


# ---- spokes / consumers ----
@router.post("/spokes", response_model=schemas.SpokeOut, status_code=201)
def create_spoke(body: schemas.SpokeIn, db: Session = Depends(get_db)):
    return _run(service.create_spoke, db=db, name=body.name, geofence=body.geofence)


@router.get("/spokes", response_model=list[schemas.SpokeOut])
def list_spokes(db: Session = Depends(get_db)):
    return db.execute(select(models.Spoke).order_by(models.Spoke.name)).scalars().all()


@router.get("/spokes/{spoke_id}", response_model=schemas.SpokeDetailOut)
def get_spoke(spoke_id: str, db: Session = Depends(get_db)):
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise HTTPException(404, f"Unknown spoke: {spoke_id}")
    return schemas.SpokeDetailOut.from_spoke(spoke)


@router.post("/spokes/{spoke_id}/areas", response_model=schemas.SpokeDetailOut)
def add_area(spoke_id: str, body: schemas.AreaIn, db: Session = Depends(get_db)):
    """Add a geofence coverage keyword to a spoke."""
    spoke = _run(service.add_area, db=db, spoke_id=spoke_id, area=body.area)
    return schemas.SpokeDetailOut.from_spoke(spoke)


@router.get("/spokes/{spoke_id}/sites")
def territory_sites(spoke_id: str, db: Session = Depends(get_db)):
    return _run(service.territory_sites, db=db, spoke_id=spoke_id)


@router.get("/spokes/{spoke_id}/dashboard")
def spoke_dashboard(spoke_id: str, db: Session = Depends(get_db)):
    return _run(service.spoke_dashboard, db=db, spoke_id=spoke_id)


@router.post("/consumers", response_model=schemas.ConsumerOut, status_code=201)
def create_consumer(body: schemas.ConsumerIn, db: Session = Depends(get_db)):
    return _run(service.create_consumer, db=db, name=body.name, tier=body.tier,
                spoke_id=body.spoke_id, phone=body.phone)


@router.get("/consumers", response_model=list[schemas.ConsumerOut])
def list_consumers(db: Session = Depends(get_db)):
    return db.execute(select(models.Consumer).order_by(models.Consumer.name)).scalars().all()


@router.patch("/consumers/{consumer_id}", response_model=schemas.ConsumerOut)
def update_consumer(consumer_id: str, body: schemas.ConsumerUpdate, db: Session = Depends(get_db)):
    return _run(service.update_consumer, db=db, consumer_id=consumer_id,
                tier=body.tier, phone=body.phone)


@router.post("/intake", status_code=201)
def intake(body: schemas.IntakeIn, db: Session = Depends(get_db)):
    """Consumer intake: classify (tier) and auto-assign the serving spoke by geofence (location)."""
    result = _run(service.intake, db=db, name=body.name, tier=body.tier,
                  location=body.location, phone=body.phone)
    c, s = result["consumer"], result["spoke"]
    return {
        "consumer": {"id": c.id, "name": c.name, "tier": c.tier, "phone": c.phone, "spoke_id": c.spoke_id},
        "assigned_spoke": {"id": s.id, "name": s.name},
    }


# ---- sites ----
@router.post("/sites", response_model=schemas.SiteOut, status_code=201)
def create_site(body: schemas.SiteIn, db: Session = Depends(get_db)):
    return _run(service.create_site, db=db, consumer_id=body.consumer_id, label=body.label,
                location=body.location, area_sqft=body.area_sqft, floors=body.floors,
                construction_type=body.construction_type)


@router.get("/sites", response_model=list[schemas.SiteOut])
def list_sites(db: Session = Depends(get_db)):
    return service.list_sites(db)


@router.get("/sites/{site_id}", response_model=schemas.SiteOut)
def get_site(site_id: int, db: Session = Depends(get_db)):
    site = service.get_site(db, site_id)
    if site is None:
        raise HTTPException(404, f"Unknown site: SITE-{site_id}")
    return site


@router.post("/sites/{site_id}/plan", response_model=schemas.SiteOut)
def generate_plan(site_id: int, db: Session = Depends(get_db)):
    """Architect: compute the BOM and lay out the 9 phases."""
    return _run(service.generate_plan, db=db, site_id=site_id)


@router.post("/sites/{site_id}/start", response_model=schemas.DispatchOut)
def start_site(site_id: int, db: Session = Depends(get_db)):
    """Begin construction: phase 1 in-progress + dispatch its materials."""
    return _run(service.start_site, db=db, site_id=site_id)


@router.post("/sites/{site_id}/phases/{seq}/complete")
def complete_phase(site_id: int, seq: int, db: Session = Depends(get_db)):
    """Civil engineer: mark a phase complete → triggers JIT dispatch of the next phase."""
    return _run(service.complete_phase, db=db, site_id=site_id, seq=seq)
