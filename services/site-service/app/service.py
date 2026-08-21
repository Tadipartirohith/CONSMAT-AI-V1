"""Field-domain logic: spokes, consumers, sites, plan generation, and phase-driven JIT dispatch."""
from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import bom, geofence, identity_client, inventory_client, models
from .config import settings


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


AREA_APPROVERS = ("hub_supervisor", "hub_manager", "admin")


def _apply_add_area(db: Session, spoke_id: str, area: str) -> None:
    spoke = db.get(models.Spoke, spoke_id)
    if spoke and not any(a.area.lower() == area.lower() for a in spoke.areas):
        db.add(models.SpokeArea(spoke_id=spoke_id, area=area))


def _apply_remove_area(db: Session, spoke_id: str, area: str) -> None:
    for a in db.execute(select(models.SpokeArea).where(models.SpokeArea.spoke_id == spoke_id)).scalars():
        if a.area.lower() == area.lower():
            db.delete(a)


def add_area(db: Session, spoke_id: str, area: str) -> models.Spoke:
    """Directly add a coverage region (used by seed/tests). The API uses change_area for approvals."""
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    area = (area or "").strip()
    if not area:
        raise SiteError("Region is required")
    _apply_add_area(db, spoke_id, area)
    db.commit()
    db.refresh(spoke)
    return spoke


def change_area(db: Session, spoke_id: str, area: str, action: str, actor_role: str,
                actor_name: str) -> dict:
    """Add/remove a coverage region. A spokesperson's change becomes a pending request; a
    supervisor/manager (or admin) change applies directly."""
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    area = (area or "").strip()
    if not area:
        raise SiteError("Region is required")
    if action not in (models.AR_ADD, models.AR_REMOVE):
        raise SiteError("action must be 'add' or 'remove'")
    if actor_role in AREA_APPROVERS:
        (_apply_add_area if action == models.AR_ADD else _apply_remove_area)(db, spoke_id, area)
        db.commit()
        return {"applied": True}
    req = models.AreaRequest(spoke_id=spoke_id, area=area, action=action,
                             requested_by_role=actor_role, requested_by=actor_name)
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"applied": False, "pending_request_id": req.id}


def list_area_requests(db: Session, status: str | None = None) -> list[models.AreaRequest]:
    stmt = select(models.AreaRequest).order_by(models.AreaRequest.id.desc())
    if status:
        stmt = stmt.where(models.AreaRequest.status == status)
    return list(db.execute(stmt).scalars())


def decide_area_request(db: Session, req_id: int, approve: bool, actor_role: str,
                        actor_name: str) -> models.AreaRequest:
    if actor_role not in AREA_APPROVERS:
        raise SiteError("Only a hub supervisor or manager can decide coverage requests")
    req = db.get(models.AreaRequest, req_id)
    if req is None:
        raise SiteError(f"Unknown area request: {req_id}")
    if req.status != models.AR_PENDING:
        raise SiteError("This request has already been decided")
    if approve:
        (_apply_add_area if req.action == models.AR_ADD else _apply_remove_area)(db, req.spoke_id, req.area)
        req.status = models.AR_APPROVED
    else:
        req.status = models.AR_REJECTED
    req.decided_by_role = actor_role
    req.decided_by = actor_name
    req.decided_at = db.execute(select(func.now())).scalar()
    db.commit()
    db.refresh(req)
    return req


def create_consumer(db: Session, name: str, tier: str, spoke_id: str, phone: str = "",
                    email: str = "") -> models.Consumer:
    if tier not in models.CONSUMER_TIERS:
        raise SiteError(f"tier must be one of {models.CONSUMER_TIERS}")
    if db.get(models.Spoke, spoke_id) is None:
        raise SiteError(f"Unknown spoke: {spoke_id}")
    cid = _unique_id(db, models.Consumer, _slug(name, "c"))
    c = models.Consumer(id=cid, name=name.strip(), tier=tier, spoke_id=spoke_id, phone=phone,
                        email=email.strip().lower())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def intake(db: Session, name: str, tier: str, location: str, phone: str = "", email: str = "") -> dict:
    """Onboarding: classify the consumer (tier), auto-assign the serving spoke by geofence (location),
    and provision a `consumer` login (the customer's own email if given) so they can track their
    project. Fails if no active spoke covers the location."""
    spoke = geofence.resolve_spoke(db, location)
    if spoke is None:
        raise SiteError(f"No spoke covers '{location}'. Add coverage to a spoke or assign manually.")
    login_email = (email or "").strip().lower()
    consumer = create_consumer(db, name, tier, spoke.id, phone, email=login_email)
    if not login_email:
        login_email = f"{consumer.id}@consmat.com"
        consumer.email = login_email
        db.commit()
    login = None
    try:
        identity_client.create_consumer_user(login_email, consumer.name, consumer.id, settings.demo_password)
        login = {"email": login_email, "temp_password": settings.demo_password, "created": True}
    except identity_client.IdentityUnavailable as e:
        login = {"email": login_email, "created": False, "error": str(e)}
    return {"consumer": consumer, "spoke": spoke, "login": login}


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


# Who may approve a civil-engineer's phase end-date change, and edit dates directly.
FIELD_APPROVERS = ("spokesperson", "hub_supervisor", "hub_manager", "admin")


def _bom_line_dicts(site: models.Site) -> list[dict]:
    return [{"product_id": b.product_id, "material_id": b.material_id, "product_name": b.product_name,
             "phase_seq": int(b.phase_seq or 0), "total_qty": float(b.total_qty)} for b in site.bom_lines]


def _phase_dispatch_lines(lines: list[dict], seq: int) -> list[dict]:
    """Products a phase needs = explicit per-phase lines (phase_seq == seq) + the weight-sliced portion
    of any whole-project lines (phase_seq == 0)."""
    out: list[dict] = []
    for ln in lines:
        if ln.get("phase_seq") and int(ln["phase_seq"]) == seq:
            q = float(ln.get("total_qty") or 0)
            if q > 0 and ln.get("product_id"):
                out.append({"product_id": ln["product_id"], "material_id": ln["material_id"],
                            "product_name": ln.get("product_name", ""), "qty": q})
    auto = [ln for ln in lines if not ln.get("phase_seq")]
    out += bom.product_phase_slice(auto, seq)
    return out


def _reserve_totals(lines: list[dict]) -> dict[str, float]:
    """Total quantity that will actually be dispatched per product (sum across the 9 phases)."""
    agg: dict[str, float] = {}
    for seq, _n, _r in bom.PHASES:
        for item in _phase_dispatch_lines(lines, seq):
            if item["product_id"]:
                agg[item["product_id"]] = agg.get(item["product_id"], 0.0) + item["qty"]
    return agg


def set_bom(db: Session, site_id: int, lines: list[dict]) -> models.Site:
    """CE/spoke enters the Bill of Materials (product/brand level, whole-project totals).

    The system slices it into the 9 phases at dispatch time; the hub reserves the committed demand so
    the 3x buffer can flag low/no-stock early. Editable until construction starts.
    """
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if site.status not in ("planning", "planned"):
        raise SiteError("The BOM can only be changed before construction starts")
    if not lines:
        raise SiteError("The BOM needs at least one line")
    for ln in lines:
        if not ln.get("material_id") or _dec(ln.get("total_qty", 0)) <= 0:
            raise SiteError("Each BOM line needs a material and a positive quantity")

    # Release the previous committed reservation (pre-start, so nothing dispatched yet).
    for pid, qty in _reserve_totals(_bom_line_dicts(site)).items():
        try:
            inventory_client.post_product_release(pid, qty)
        except inventory_client.InventoryUnavailable:
            pass
    site.bom_lines.clear()
    db.flush()
    for ln in lines:
        db.add(models.BOMLine(site_id=site.id, material_id=ln["material_id"],
                              product_id=ln.get("product_id", ""), product_name=ln.get("product_name", ""),
                              phase_seq=int(ln.get("phase_seq") or 0), total_qty=_dec(ln["total_qty"])))
    existing = {p.phase_seq for p in site.phases}
    for seq, _n, _r in bom.PHASES:
        if seq not in existing:
            db.add(models.PhaseProgress(site_id=site.id, phase_seq=seq, status=models.PH_PENDING))
    # Reserve the new committed demand (over-reservation allowed -> surfaces the 3x buffer breach).
    for pid, qty in _reserve_totals([{**l} for l in lines]).items():
        try:
            inventory_client.post_product_reserve(pid, qty)
        except inventory_client.InventoryUnavailable:
            pass
    site.status = "planned"
    db.commit()
    db.refresh(site)
    return site


def phase_needs(db: Session, site_id: int) -> list[dict]:
    """Return each phase's product requirements (the BOM sliced by the material weight matrix)."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    lines = _bom_line_dicts(site)
    phase_status = {p.phase_seq: p.status for p in site.phases}
    out = []
    for seq, name, _rpf in bom.PHASES:
        out.append({
            "phase_seq": seq, "name": name, "status": phase_status.get(seq, models.PH_PENDING),
            "lines": _phase_dispatch_lines(lines, seq),
        })
    return out


def _totals(site: models.Site) -> dict[str, float]:
    return {b.material_id: float(b.total_qty) for b in site.bom_lines}


def _phase(site: models.Site, seq: int) -> models.PhaseProgress | None:
    return next((p for p in site.phases if p.phase_seq == seq), None)


# ---- Dispatch (hub → site) for a phase ----

def _dispatch_phase(db: Session, site: models.Site, seq: int) -> models.Dispatch:
    """Compute the phase's product slice and pull it from hub inventory (brand-level outbound)."""
    slice_ = _phase_dispatch_lines(_bom_line_dicts(site), seq)
    dispatch = models.Dispatch(site_id=site.id, phase_seq=seq, status=models.DSP_DISPATCHED)
    db.add(dispatch)
    db.flush()
    dispatched, short = 0, 0
    for item in slice_:
        line = models.DispatchLine(dispatch_id=dispatch.id, material_id=item["material_id"],
                                   product_id=item.get("product_id", ""),
                                   product_name=item.get("product_name", ""), qty=_dec(item["qty"]))
        try:
            if item.get("product_id"):
                inventory_client.post_product_outbound(item["product_id"], item["qty"],
                                                       f"{site.code}-P{seq}", from_reservation=True)
            else:  # legacy material-level BOM (architect auto-plan)
                inventory_client.post_outbound(item["material_id"], item["qty"], f"{site.code}-P{seq}")
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
                     "material_id": line.material_id, "product_id": line.product_id,
                     "product_name": line.product_name, "qty": float(line.qty)}
            try:
                if line.product_id:
                    inventory_client.post_product_outbound(line.product_id, float(line.qty),
                                                           f"{site.code}-P{d.phase_seq}-backfill",
                                                           from_reservation=True)
                else:
                    inventory_client.post_outbound(line.material_id, float(line.qty),
                                                   f"{site.code}-P{d.phase_seq}-backfill")
                line.status = models.DSP_DISPATCHED
                backfilled.append(entry)
                changed = True
            except inventory_client.InsufficientStock:
                still_short.append(entry)
        if changed:
            _recompute_dispatch(d)
    if backfilled:
        _notify(db, site, "dispatched",
                f"Previously-short materials have now been delivered ({len(backfilled)} item(s)).",
                audience="all")
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


def _ensure_phase_dispatched(db: Session, site: models.Site, seq: int) -> models.Dispatch | None:
    """Dispatch a phase's materials once (idempotent). The scheduler may pre-dispatch before the CE
    completes the prior phase; this guard stops a second dispatch on completion. Emits a consumer-
    visible 'dispatched' event for every path (start / complete / scheduler)."""
    ph = _phase(site, seq)
    if ph is None or ph.dispatched:
        return None
    dispatch = _dispatch_phase(db, site, seq)
    ph.dispatched = True
    shorts = [l.product_name or l.material_id for l in dispatch.lines if l.status == "short"]
    msg = f"Materials for Phase {seq} ({_PHASE_NAME.get(seq, '')}) have been dispatched to the site."
    if shorts:
        msg += f" Awaiting stock: {', '.join(shorts)}."
    _notify(db, site, "dispatched", msg, phase_seq=seq, audience="all")
    return dispatch


def start_site(db: Session, site_id: int) -> models.Dispatch:
    """Kick off construction: phase 1 in-progress + dispatch its materials."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if not site.bom_lines:
        raise SiteError("Enter a Bill of Materials before starting the site")
    p1 = _phase(site, 1)
    if p1 is None or p1.status != models.PH_PENDING:
        raise SiteError("Site already started")
    p1.status = models.PH_IN_PROGRESS
    site.status = "active"
    _notify(db, site, "started", "Construction has started. Phase 1 materials are on the way.", audience="all")
    dispatch = _ensure_phase_dispatched(db, site, 1)
    db.commit()
    if dispatch is not None:
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
    ph.completed_at = db.execute(select(func.now())).scalar()
    _notify(db, site, "phase_done", f"Phase {seq} ({_PHASE_NAME.get(seq, '')}) is complete.",
            phase_seq=seq, audience="all")

    next_seq = seq + 1
    nxt = _phase(site, next_seq)
    dispatch = None
    if nxt is not None and nxt.status == models.PH_PENDING:
        nxt.status = models.PH_IN_PROGRESS
        dispatch = _ensure_phase_dispatched(db, site, next_seq)  # skips if the scheduler pre-dispatched
    elif nxt is None:
        site.status = "completed"
        _notify(db, site, "project_done", "🎉 Your construction project is complete!", audience="all")
    db.commit()
    result = {"site": site.code, "completed_phase": seq,
              "next_phase": next_seq if nxt is not None else None,
              "site_status": site.status}
    if dispatch is not None:
        db.refresh(dispatch)
        result["dispatch"] = {"code": dispatch.code, "phase_seq": dispatch.phase_seq,
                              "status": dispatch.status,
                              "lines": [{"material_id": l.material_id, "product_id": l.product_id,
                                         "product_name": l.product_name, "qty": float(l.qty),
                                         "status": l.status} for l in dispatch.lines]}
    return result


# ---- Phase schedule dates + change approval ----

def set_phase_dates(db: Session, site_id: int, seq: int, start, end, actor_role: str,
                    actor_name: str) -> dict:
    """CE/spoke sets a phase's planned start/end.

    Start applies directly. For the end date: the first entry applies directly; a later change by a
    civil engineer becomes a pending request needing spoke/manager approval, while a spoke/manager
    change applies directly.
    """
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    ph = _phase(site, seq)
    if ph is None:
        raise SiteError(f"Site has no phase {seq}")
    if start is not None:
        ph.planned_start = start
    pending_id = None
    if end is not None:
        if ph.planned_start and end < ph.planned_start:
            raise SiteError("End date cannot be before the start date")
        if ph.planned_end is None or actor_role in FIELD_APPROVERS:
            ph.planned_end = end
        else:  # civil engineer changing an existing end date -> needs approval
            chg = models.PhaseDateChange(
                site_id=site.id, phase_seq=seq, old_end=ph.planned_end, new_end=end,
                requested_by_role=actor_role, requested_by=actor_name)
            db.add(chg)
            db.flush()
            pending_id = chg.id
    db.commit()
    db.refresh(ph)
    return {"phase_seq": seq, "planned_start": ph.planned_start, "planned_end": ph.planned_end,
            "pending_change_id": pending_id, "applied": pending_id is None}


def list_phase_changes(db: Session, *, status: str | None = None,
                       site_id: int | None = None) -> list[models.PhaseDateChange]:
    stmt = select(models.PhaseDateChange).order_by(models.PhaseDateChange.id.desc())
    if status:
        stmt = stmt.where(models.PhaseDateChange.status == status)
    if site_id is not None:
        stmt = stmt.where(models.PhaseDateChange.site_id == site_id)
    return list(db.execute(stmt).scalars())


def decide_phase_change(db: Session, change_id: int, approve: bool, actor_role: str,
                        actor_name: str) -> models.PhaseDateChange:
    """Spoke or hub manager approves/rejects a civil engineer's phase end-date change."""
    if actor_role not in FIELD_APPROVERS:
        raise SiteError("Only a spoke or the hub manager can approve a date change")
    chg = db.get(models.PhaseDateChange, change_id)
    if chg is None:
        raise SiteError(f"Unknown change request: {change_id}")
    if chg.status != models.PDC_PENDING:
        raise SiteError("This change has already been decided")
    from sqlalchemy import func
    chg.decided_by_role = actor_role
    chg.decided_by = actor_name
    chg.decided_at = db.execute(select(func.now())).scalar()
    if approve:
        chg.status = models.PDC_APPROVED
        site = db.get(models.Site, chg.site_id)
        ph = _phase(site, chg.phase_seq) if site else None
        if ph is not None:
            ph.planned_end = chg.new_end
    else:
        chg.status = models.PDC_REJECTED
    db.commit()
    db.refresh(chg)
    return chg


# ---- Notifications + JIT scheduler ----

_PHASE_NAME = {seq: name for seq, name, _ in bom.PHASES}


def _notify(db: Session, site: models.Site, kind: str, message: str, *, phase_seq: int = 0,
            audience: str = "field") -> models.Notification:
    spoke_id = site.consumer.spoke_id if site.consumer else ""
    n = models.Notification(site_id=site.id, spoke_id=spoke_id, audience=audience,
                            phase_seq=phase_seq, kind=kind, message=message)
    db.add(n)
    return n


def list_notifications(db: Session, *, spoke_id: str | None = None, site_id: int | None = None,
                       consumer_id: str | None = None, audiences: tuple | None = None,
                       unread_only: bool = False) -> list[models.Notification]:
    stmt = select(models.Notification).order_by(models.Notification.id.desc())
    if spoke_id:
        stmt = stmt.where(models.Notification.spoke_id == spoke_id)
    if site_id is not None:
        stmt = stmt.where(models.Notification.site_id == site_id)
    if consumer_id:  # scope to this customer's own sites (privacy)
        site_ids = [s for s in db.execute(
            select(models.Site.id).where(models.Site.consumer_id == consumer_id)).scalars()]
        stmt = stmt.where(models.Notification.site_id.in_(site_ids or [-1]))
    if audiences:
        stmt = stmt.where(models.Notification.audience.in_(audiences))
    if unread_only:
        stmt = stmt.where(models.Notification.read.is_(False))
    return list(db.execute(stmt.limit(100)).scalars())


def mark_notification_read(db: Session, notif_id: int) -> models.Notification:
    n = db.get(models.Notification, notif_id)
    if n is None:
        raise SiteError(f"Unknown notification: {notif_id}")
    n.read = True
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, consumer_id: str) -> dict:
    """Mark all of a customer's own project notifications read."""
    site_ids = [s for s in db.execute(
        select(models.Site.id).where(models.Site.consumer_id == consumer_id)).scalars()]
    rows = db.execute(select(models.Notification).where(
        models.Notification.site_id.in_(site_ids or [-1]),
        models.Notification.read.is_(False),
        models.Notification.audience.in_(("all", "consumer")))).scalars()
    n = 0
    for row in rows:
        row.read = True
        n += 1
    db.commit()
    return {"marked": n}


def confirm_receipt(db: Session, dispatch_id: int, actor_role: str, actor_org: str) -> models.Dispatch:
    """Customer (or hub staff) confirms a delivery arrived; feeds back into the dispatch status."""
    d = db.get(models.Dispatch, dispatch_id)
    if d is None:
        raise SiteError(f"Unknown dispatch: {dispatch_id}")
    site = db.get(models.Site, d.site_id)
    is_owner = actor_role == "consumer" and site is not None and site.consumer_id == actor_org
    is_staff = actor_role in ("spokesperson", "architect", "civil_engineer",
                              "hub_supervisor", "hub_manager", "admin")
    if not (is_owner or is_staff):
        raise SiteError("Only the customer or hub staff can confirm receipt")
    if d.status not in (models.DSP_DISPATCHED, models.DSP_RECEIVED):
        raise SiteError("Only a fully-delivered shipment can be confirmed (shortfalls are still pending)")
    if d.received_at is None:
        d.received_at = db.execute(select(func.now())).scalar()
        d.status = models.DSP_RECEIVED
        _notify(db, site, "received",
                f"Customer confirmed receipt of Phase {d.phase_seq} "
                f"({_PHASE_NAME.get(d.phase_seq, '')}) materials.", phase_seq=d.phase_seq, audience="all")
    db.commit()
    db.refresh(d)
    return d


def run_scheduler_tick(db: Session, *, today=None, notice_days: int = 3, dispatch_days: int = 2) -> dict:
    """JIT scheduler: for each active site, warn the field team ~3 days before the current phase's end
    date and pre-dispatch the next phase's materials ~1 day later, so construction is never halted."""
    from datetime import date as _date
    today = today or _date.today()
    actions: list[dict] = []
    for site in db.execute(select(models.Site).where(models.Site.status == "active")).scalars():
        cur = next((p for p in site.phases if p.status == models.PH_IN_PROGRESS), None)
        if cur is None or cur.planned_end is None:
            continue
        nxt = _phase(site, cur.phase_seq + 1)
        if nxt is None or nxt.dispatched:
            continue
        days_left = (cur.planned_end - today).days
        if days_left <= notice_days:
            warned = db.execute(select(models.Notification).where(
                models.Notification.site_id == site.id,
                models.Notification.phase_seq == nxt.phase_seq,
                models.Notification.kind == "dispatch_pending")).first()
            if not warned:
                _notify(db, site, "dispatch_pending",
                        f"Phase {cur.phase_seq} ends {cur.planned_end}. Dispatching phase "
                        f"{nxt.phase_seq} materials within a day so work is not halted.",
                        phase_seq=nxt.phase_seq)
                actions.append({"site": site.code, "kind": "dispatch_pending", "phase": nxt.phase_seq})
        if days_left <= dispatch_days:
            dispatch = _ensure_phase_dispatched(db, site, nxt.phase_seq)  # emits the 'dispatched' event
            if dispatch is not None:
                actions.append({"site": site.code, "kind": "dispatched", "phase": nxt.phase_seq,
                                "dispatch": dispatch.code})
    db.commit()
    return {"ran_at": str(today), "actions": actions}
