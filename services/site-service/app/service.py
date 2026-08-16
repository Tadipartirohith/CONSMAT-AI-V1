"""Field-domain logic: spokes, consumers, sites, plan generation, and phase-driven JIT dispatch."""
from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import bom, geofence, inventory_client, models


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


def add_area(db: Session, spoke_id: str, area: str) -> models.Spoke:
    """Add a coverage keyword (geofence) to a spoke."""
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    area = area.strip()
    if not area:
        raise SiteError("Area is required")
    if not any(a.area.lower() == area.lower() for a in spoke.areas):
        db.add(models.SpokeArea(spoke_id=spoke_id, area=area))
        db.commit()
        db.refresh(spoke)
    return spoke


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


def intake(db: Session, name: str, tier: str, location: str, phone: str = "") -> dict:
    """Spokesperson intake: classify the consumer (tier) and auto-assign the serving spoke by
    geofence (location). Fails if no active spoke covers the location."""
    spoke = geofence.resolve_spoke(db, location)
    if spoke is None:
        raise SiteError(f"No spoke covers '{location}'. Add coverage to a spoke or assign manually.")
    consumer = create_consumer(db, name, tier, spoke.id, phone)
    return {"consumer": consumer, "spoke": spoke}


def update_consumer(db: Session, consumer_id: str, *, tier: str | None = None,
                    phone: str | None = None) -> models.Consumer:
    c = db.get(models.Consumer, consumer_id)
    if c is None:
        raise SiteError(f"Unknown consumer: {consumer_id}")
    if tier is not None:
        if tier not in models.CONSUMER_TIERS:
            raise SiteError(f"tier must be one of {models.CONSUMER_TIERS}")
        c.tier = tier
    if phone is not None:
        c.phone = phone
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


# ---- Spokesperson territory view ----

def _current_phase(site: models.Site) -> int | None:
    ip = next((p.phase_seq for p in site.phases if p.status == models.PH_IN_PROGRESS), None)
    return ip


def territory_sites(db: Session, spoke_id: str) -> list[dict]:
    """Every site in a spoke's territory (via its consumers), with status + current phase."""
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    out = []
    for c in spoke.consumers:
        for s in c.sites:
            out.append({
                "site": s.code, "site_id": s.id, "label": s.label, "location": s.location,
                "consumer": c.name, "tier": c.tier, "status": s.status,
                "current_phase": _current_phase(s),
            })
    return out


def spoke_dashboard(db: Session, spoke_id: str) -> dict:
    """Territory summary for the spokesperson: consumers by tier, sites by status, and any
    dispatches needing attention (partial/pending = material shortfall)."""
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    by_tier: dict[str, int] = {}
    by_status: dict[str, int] = {}
    attention = []
    consumers = spoke.consumers
    for c in consumers:
        by_tier[c.tier] = by_tier.get(c.tier, 0) + 1
        for s in c.sites:
            by_status[s.status] = by_status.get(s.status, 0) + 1
            for d in s.dispatches:
                if d.status in (models.DSP_PARTIAL, models.DSP_PENDING):
                    shorts = [l.material_id for l in d.lines if l.status == "short"]
                    attention.append({"site": s.code, "dispatch": d.code, "phase_seq": d.phase_seq,
                                      "status": d.status, "short_materials": shorts})
    return {
        "spoke": {"id": spoke.id, "name": spoke.name,
                  "areas": [a.area for a in spoke.areas]},
        "consumers": {"total": len(consumers), "by_tier": by_tier},
        "sites": {"total": sum(by_status.values()), "by_status": by_status},
        "attention": attention,
    }


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


def _recompute_dispatch(d: models.Dispatch) -> None:
    statuses = [l.status for l in d.lines]
    if statuses and all(s == models.DSP_DISPATCHED for s in statuses):
        d.status = models.DSP_DISPATCHED
    elif any(s == models.DSP_DISPATCHED for s in statuses):
        d.status = models.DSP_PARTIAL
    else:
        d.status = models.DSP_PENDING


def backfill_site(db: Session, site_id: int) -> dict:
    """Retry every still-short dispatch line for a site against current hub stock.

    When the hub replenishes after a shortfall, this pushes the outstanding materials out and heals the
    affected dispatches (partial/pending → dispatched). Idempotent: already-dispatched lines are skipped.
    """
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    backfilled, still_short = [], []
    for d in site.dispatches:
        changed = False
        for line in d.lines:
            if line.status != "short":
                continue
            entry = {"dispatch": d.code, "phase_seq": d.phase_seq,
                     "material_id": line.material_id, "qty": float(line.qty)}
            try:
                inventory_client.post_outbound(line.material_id, float(line.qty),
                                               f"{site.code}-P{d.phase_seq}-backfill")
                line.status = models.DSP_DISPATCHED
                backfilled.append(entry)
                changed = True
            except inventory_client.InsufficientStock:
                still_short.append(entry)
        if changed:
            _recompute_dispatch(d)
    db.commit()
    return {"site": site.code, "backfilled": backfilled, "still_short": still_short}


def backfill_all(db: Session) -> dict:
    """Network-wide backfill across every site (hub action after a replenishment)."""
    results = []
    for s in list_sites(db):
        r = backfill_site(db, s.id)
        if r["backfilled"] or r["still_short"]:
            results.append(r)
    return {"sites": results}


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
