"""Field REST API: spokes, consumers, sites, plans, and phase-driven dispatch."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import bom, inventory_client, models, schemas, service
from ..auth import current_user, require_role
from ..db import get_db

# Reads: any authenticated user. Field actions: the spoke team (spokesperson/architect/civil engineer).
# Kept as one field role-set since the spoke-app blends the three personas; admin bypasses.
FIELD = require_role("spokesperson", "architect", "civil_engineer")
# Backfill is a dispatch action either side can trigger after a replenishment.
BACKFILL = require_role("spokesperson", "architect", "civil_engineer", "hub_supervisor", "hub_manager")
# Scheduling (phase dates) + oversight: the field team plus the hub, since the manager sits above the spoke.
SCHEDULE = require_role("spokesperson", "architect", "civil_engineer", "hub_supervisor", "hub_manager")
router = APIRouter(tags=["sites"], dependencies=[Depends(current_user)])


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
@router.post("/spokes", response_model=schemas.SpokeOut, status_code=201, dependencies=[Depends(FIELD)])
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


@router.post("/spokes/{spoke_id}/areas", response_model=schemas.SpokeDetailOut, dependencies=[Depends(FIELD)])
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


@router.post("/consumers", response_model=schemas.ConsumerOut, status_code=201, dependencies=[Depends(FIELD)])
def create_consumer(body: schemas.ConsumerIn, db: Session = Depends(get_db)):
    return _run(service.create_consumer, db=db, name=body.name, tier=body.tier,
                spoke_id=body.spoke_id, phone=body.phone)


@router.get("/consumers", response_model=list[schemas.ConsumerOut])
def list_consumers(db: Session = Depends(get_db)):
    return db.execute(select(models.Consumer).order_by(models.Consumer.name)).scalars().all()


@router.patch("/consumers/{consumer_id}", response_model=schemas.ConsumerOut, dependencies=[Depends(FIELD)])
def update_consumer(consumer_id: str, body: schemas.ConsumerUpdate, db: Session = Depends(get_db)):
    return _run(service.update_consumer, db=db, consumer_id=consumer_id,
                tier=body.tier, phone=body.phone)


@router.post("/intake", status_code=201, dependencies=[Depends(FIELD)])
def intake(body: schemas.IntakeIn, db: Session = Depends(get_db)):
    """Consumer intake: classify (tier) and auto-assign the serving spoke by geofence (location)."""
    result = _run(service.intake, db=db, name=body.name, tier=body.tier,
                  location=body.location, phone=body.phone)
    c, s = result["consumer"], result["spoke"]
    return {
        "consumer": {"id": c.id, "name": c.name, "tier": c.tier, "phone": c.phone, "spoke_id": c.spoke_id},
        "assigned_spoke": {"id": s.id, "name": s.name},
        "login": result.get("login"),
    }


# ---- sites ----
@router.post("/sites", response_model=schemas.SiteOut, status_code=201, dependencies=[Depends(FIELD)])
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


@router.post("/sites/{site_id}/plan", response_model=schemas.SiteOut, dependencies=[Depends(FIELD)])
def generate_plan(site_id: int, db: Session = Depends(get_db)):
    """Architect: compute the BOM and lay out the 9 phases (legacy auto-plan)."""
    return _run(service.generate_plan, db=db, site_id=site_id)


@router.post("/sites/{site_id}/bom", response_model=schemas.SiteOut, dependencies=[Depends(FIELD)])
def set_bom(site_id: int, body: schemas.SetBomIn, db: Session = Depends(get_db)):
    """CE/spoke enters (or edits) the site's product-level Bill of Materials. Editable before start."""
    return _run(service.set_bom, db=db, site_id=site_id, lines=[l.model_dump() for l in body.lines])


@router.post("/sites/{site_id}/phases/{seq}/dates", dependencies=[Depends(SCHEDULE)])
def set_phase_dates(site_id: int, seq: int, body: schemas.PhaseDatesIn,
                    user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Set/modify a phase's planned start & end. A civil engineer's end-date change needs approval."""
    return _run(service.set_phase_dates, db=db, site_id=site_id, seq=seq, start=body.start,
                end=body.end, actor_role=user.get("role", ""), actor_name=user.get("name", ""))


@router.get("/phase-changes", response_model=list[schemas.PhaseDateChangeOut])
def list_phase_changes(status: str | None = None, site_id: int | None = None,
                       db: Session = Depends(get_db)):
    """Phase end-date change requests (spoke/manager review queue). Filter by status/site."""
    return service.list_phase_changes(db, status=status, site_id=site_id)


@router.post("/phase-changes/{change_id}/decide", response_model=schemas.PhaseDateChangeOut)
def decide_phase_change(change_id: int, body: schemas.DecideChangeIn,
                        user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Spoke or hub manager approves/rejects a civil engineer's phase end-date change."""
    return _run(service.decide_phase_change, db=db, change_id=change_id, approve=body.approve,
                actor_role=user.get("role", ""), actor_name=user.get("name", ""))


@router.post("/sites/{site_id}/start", response_model=schemas.DispatchOut, dependencies=[Depends(FIELD)])
def start_site(site_id: int, db: Session = Depends(get_db)):
    """Begin construction: phase 1 in-progress + dispatch its materials."""
    return _run(service.start_site, db=db, site_id=site_id)


@router.post("/sites/{site_id}/phases/{seq}/complete", dependencies=[Depends(FIELD)])
def complete_phase(site_id: int, seq: int, db: Session = Depends(get_db)):
    """Civil engineer: mark a phase complete → triggers JIT dispatch of the next phase."""
    return _run(service.complete_phase, db=db, site_id=site_id, seq=seq)


@router.post("/sites/{site_id}/backfill", dependencies=[Depends(BACKFILL)])
def backfill_site(site_id: int, db: Session = Depends(get_db)):
    """Retry this site's still-short dispatch lines against current hub stock."""
    return _run(service.backfill_site, db=db, site_id=site_id)


@router.post("/backfill", dependencies=[Depends(BACKFILL)])
def backfill_all(db: Session = Depends(get_db)):
    """Network-wide backfill across all sites (hub action after a replenishment)."""
    return service.backfill_all(db)


# ---- Notifications + JIT scheduler ----
@router.get("/notifications", response_model=list[schemas.NotificationOut])
def list_notifications(spoke_id: str | None = None, site_id: int | None = None,
                       unread_only: bool = False, db: Session = Depends(get_db)):
    """Field-team notifications (JIT dispatch warnings). Filter by spoke, site, or unread."""
    return service.list_notifications(db, spoke_id=spoke_id, site_id=site_id, unread_only=unread_only)


@router.post("/notifications/{notif_id}/read", response_model=schemas.NotificationOut)
def read_notification(notif_id: int, db: Session = Depends(get_db)):
    return _run(service.mark_notification_read, db=db, notif_id=notif_id)


@router.post("/scheduler/tick", dependencies=[Depends(BACKFILL)])
def scheduler_tick(db: Session = Depends(get_db)):
    """Manually run one JIT scheduler pass (the same logic runs automatically in the background)."""
    return service.run_scheduler_tick(db)
