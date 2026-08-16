"""Field-domain logic: spokes, consumers, sites, plan generation, and phase-driven JIT dispatch."""
from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import bom, inventory_client, models


class SiteError(Exception):
    """Invalid field/site operation."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _slug(name: str, prefix: str) -> str:
    first = (name.strip().lower().split() or ["x"])[0]
    return f"{prefix}_" + (re.sub(r"[^a-z0-9]+", "", first) or "x")


def _unique_id(db: Session, model, base: str) -> str:
    vid, n = base, 1
    while db.get(model, vid) is not None:
        n += 1
        vid = f"{base}{n}"
    return vid


# ---- Spokes / consumers / sites ----

def create_spoke(db: Session, name: str, geofence: str = "") -> models.Spoke:
    if not name.strip():
        raise SiteError("Spoke name required")
    sid = _unique_id(db, models.Spoke, _slug(name, "s"))
    s = models.Spoke(id=sid, name=name.strip(), geofence=geofence)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def create_consumer(db: Session, name: str, tier: str, spoke_id: str, phone: str = "") -> models.Consumer:
    if tier not in models.CONSUMER_TIERS:
        raise SiteError(f"tier must be one of {models.CONSUMER_TIERS}")
    if db.get(models.Spoke, spoke_id) is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    cid = _unique_id(db, models.Consumer, _slug(name, "c"))
    c = models.Consumer(id=cid, name=name.strip(), tier=tier, spoke_id=spoke_id, phone=phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def create_site(db: Session, consumer_id: str, *, label: str = "", location: str = "",
                area_sqft: float, floors: int = 1, construction_type: str = "standard") -> models.Site:
    if db.get(models.Consumer, consumer_id) is None:
        raise SiteError(f"Unknown consumer: {consumer_id}")
    if area_sqft <= 0:
        raise SiteError("area_sqft must be positive")
    site = models.Site(consumer_id=consumer_id, label=label, location=location,
                       area_sqft=_dec(area_sqft), floors=max(1, floors),
                       construction_type=construction_type)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def get_site(db: Session, site_id: int) -> models.Site | None:
    return db.get(models.Site, site_id)


def list_sites(db: Session) -> list[models.Site]:
    return list(db.execute(select(models.Site).order_by(models.Site.id.desc())).scalars())


# ---- Plan (architect) ----

def generate_plan(db: Session, site_id: int) -> models.Site:
    """Architect action: compute the BOM (from inventory catalog coefficients) and lay out the 9 phases."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if site.bom_lines:
        raise SiteError("Site already has a plan")
    per_sqft = inventory_client.get_materials()  # {material_id: per_sqft}
    total_area, totals = bom.compute_bom(float(site.area_sqft), site.floors,
                                         site.construction_type, per_sqft)
    site.total_area = _dec(total_area)
    for mid, qty in totals.items():
        db.add(models.BOMLine(site_id=site.id, material_id=mid, total_qty=_dec(qty)))
    for seq, _name, _rpf in bom.PHASES:
        db.add(models.PhaseProgress(site_id=site.id, phase_seq=seq, status=models.PH_PENDING))
    site.status = "planned"
    db.commit()
    db.refresh(site)
    return site


def _totals(site: models.Site) -> dict[str, float]:
    return {b.material_id: float(b.total_qty) for b in site.bom_lines}


def _phase(site: models.Site, seq: int) -> models.PhaseProgress | None:
    return next((p for p in site.phases if p.phase_seq == seq), None)


# ---- Dispatch (hub → site) for a phase ----

def _dispatch_phase(db: Session, site: models.Site, seq: int) -> models.Dispatch:
    """Compute the phase's material slice and pull it from hub inventory (outbound)."""
    slice_ = bom.phase_slice(_totals(site), seq)
    dispatch = models.Dispatch(site_id=site.id, phase_seq=seq, status=models.DSP_DISPATCHED)
    db.add(dispatch)
    db.flush()
    dispatched, short = 0, 0
    for mid, qty in slice_.items():
        line = models.DispatchLine(dispatch_id=dispatch.id, material_id=mid, qty=_dec(qty))
        try:
            inventory_client.post_outbound(mid, qty, f"{site.code}-P{seq}")
            line.status = models.DSP_DISPATCHED
            dispatched += 1
        except inventory_client.InsufficientStock:
            line.status = "short"
            short += 1
        db.add(line)
    if short and dispatched:
        dispatch.status = models.DSP_PARTIAL
    elif short and not dispatched:
        dispatch.status = models.DSP_PENDING
    return dispatch


def start_site(db: Session, site_id: int) -> models.Dispatch:
    """Kick off construction: phase 1 in-progress + dispatch its materials."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if not site.bom_lines:
        raise SiteError("Generate a plan before starting the site")
    p1 = _phase(site, 1)
    if p1 is None or p1.status != models.PH_PENDING:
        raise SiteError("Site already started")
    p1.status = models.PH_IN_PROGRESS
    site.status = "active"
    dispatch = _dispatch_phase(db, site, 1)
    db.commit()
    db.refresh(dispatch)
    return dispatch


def complete_phase(db: Session, site_id: int, seq: int) -> dict:
    """Civil-engineer action: mark a phase done → trigger dispatch of the next phase (JIT)."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    ph = _phase(site, seq)
    if ph is None:
        raise SiteError(f"Site has no phase {seq}")
    if ph.status == models.PH_DONE:
        raise SiteError(f"Phase {seq} already complete")
    ph.status = models.PH_DONE
    from sqlalchemy import func
    ph.completed_at = db.execute(select(func.now())).scalar()

    next_seq = seq + 1
    nxt = _phase(site, next_seq)
    dispatch = None
    if nxt is not None and nxt.status == models.PH_PENDING:
        nxt.status = models.PH_IN_PROGRESS
        dispatch = _dispatch_phase(db, site, next_seq)
    elif nxt is None:
        site.status = "completed"
    db.commit()
    result = {"site": site.code, "completed_phase": seq,
              "next_phase": next_seq if nxt is not None else None,
              "site_status": site.status}
    if dispatch is not None:
        db.refresh(dispatch)
        result["dispatch"] = {"code": dispatch.code, "phase_seq": dispatch.phase_seq,
                              "status": dispatch.status,
                              "lines": [{"material_id": l.material_id, "qty": float(l.qty),
                                         "status": l.status} for l in dispatch.lines]}
    return result
