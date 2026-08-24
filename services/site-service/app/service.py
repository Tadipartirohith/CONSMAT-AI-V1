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
                area_sqft: float, floors: int = 1, construction_type: str = "standard",
                project_type: str = "") -> models.Site:
    if db.get(models.Consumer, consumer_id) is None:
        raise SiteError(f"Unknown consumer: {consumer_id}")
    if area_sqft <= 0:
        raise SiteError("area_sqft must be positive")
    if project_type and project_type not in models.PROJECT_TYPES:
        raise SiteError(f"project_type must be one of {models.PROJECT_TYPES}")
    site = models.Site(consumer_id=consumer_id, label=label, location=location,
                       area_sqft=_dec(area_sqft), floors=max(1, floors),
                       construction_type=construction_type, project_type=project_type or "")
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def update_site(db: Session, site_id: int, *, project_type: str | None = None,
                stage: str | None = None) -> models.Site:
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if project_type is not None:
        if project_type not in models.PROJECT_TYPES:
            raise SiteError(f"project_type must be one of {models.PROJECT_TYPES}")
        site.project_type = project_type
    if stage is not None:
        site.stage = stage
    db.commit()
    db.refresh(site)
    return site


def get_site(db: Session, site_id: int) -> models.Site | None:
    return db.get(models.Site, site_id)


# ---- Project documents (architect design / BOQ files) ----

MAX_DOC_BYTES = 8 * 1024 * 1024  # 8 MB cap (binary lives in the DB; object store is a later extension)


def add_document(db: Session, site_id: int, *, kind: str, filename: str, content_type: str,
                 data: bytes, uploaded_by_role: str, uploaded_by: str, note: str = "") -> models.ProjectDocument:
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if not data:
        raise SiteError("Empty file")
    if len(data) > MAX_DOC_BYTES:
        raise SiteError("File too large (max 8 MB)")
    kind = kind or "design"
    doc = models.ProjectDocument(site_id=site_id, kind=kind, filename=filename or "file",
                                 content_type=content_type or "application/octet-stream", size=len(data),
                                 data=data, uploaded_by_role=uploaded_by_role, uploaded_by=uploaded_by,
                                 note=note or "")
    db.add(doc)
    if kind == "design" and site.stage == models.STAGE_ONBOARDED:
        site.stage = models.STAGE_DESIGN
    ev = "design_uploaded" if kind == "design" else "document_uploaded"
    _notify(db, site, ev, f"{kind.replace('_', ' ')} '{filename}' uploaded"
            f"{f' by {uploaded_by}' if uploaded_by else ''}.", audience="all")
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session, site_id: int, kind: str | None = None) -> list[models.ProjectDocument]:
    stmt = select(models.ProjectDocument).where(models.ProjectDocument.site_id == site_id).order_by(
        models.ProjectDocument.id.desc())
    if kind:
        stmt = stmt.where(models.ProjectDocument.kind == kind)
    return list(db.execute(stmt).scalars())


def get_document(db: Session, doc_id: int) -> models.ProjectDocument | None:
    return db.get(models.ProjectDocument, doc_id)


# ---- BOQ: CE BOQ vs external BOQ, reconciliation, approval, stock check ----

BOQ_SPOKE_APPROVERS = ("spokesperson", "admin")
BOQ_HUB_APPROVERS = ("hub_supervisor", "hub_manager", "admin")


def _boq_norm(lines) -> list[dict]:
    out = []
    for l in lines:
        d = l if isinstance(l, dict) else l.model_dump()
        pid = d.get("product_id", "") or ""
        mid = d.get("material_id", "") or ""
        if not (pid or mid):
            continue
        out.append({"material_id": mid, "product_id": pid, "product_name": d.get("product_name", "") or "",
                    "phase_seq": int(d.get("phase_seq", 0) or 0), "total_qty": float(d.get("total_qty", 0) or 0)})
    return out


def compare_boqs(ce_lines: list[dict], ext_lines: list[dict]) -> float:
    """Worst per-product resource difference (%) between two BOQs."""
    def totals(lines):
        m: dict[str, float] = {}
        for l in lines:
            k = l.get("product_id") or l.get("material_id")
            m[k] = m.get(k, 0.0) + float(l.get("total_qty", 0) or 0)
        return m
    a, b = totals(ce_lines), totals(ext_lines)
    worst = 0.0
    for k in set(a) | set(b):
        x, y = a.get(k, 0.0), b.get(k, 0.0)
        denom = max(x, y) or 1.0
        worst = max(worst, abs(x - y) / denom * 100.0)
    return round(worst, 2)


def submit_boq(db: Session, site_id: int, lines, actor_name: str = "") -> dict:
    """Persist the CE BOQ, fetch the external app's BOQ, and compare them (>5% => final BOQ needed)."""
    from . import procurement_client
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    norm = _boq_norm(lines)
    if not norm:
        raise SiteError("BOQ has no valid lines")
    for b in db.execute(select(models.ProjectBOQ).where(
            models.ProjectBOQ.site_id == site_id,
            models.ProjectBOQ.source.in_([models.BOQ_CE, models.BOQ_EXTERNAL]),
            models.ProjectBOQ.status == models.BOQ_DRAFT)).scalars():
        b.status = models.BOQ_SUPERSEDED
    ce = models.ProjectBOQ(site_id=site_id, source=models.BOQ_CE, status=models.BOQ_DRAFT,
                           created_by=actor_name,
                           lines=[models.ProjectBOQLine(**l) for l in norm])
    db.add(ce)
    ext_lines, provider = [], "unavailable"
    try:
        res = procurement_client.estimate_boq(norm)
        ext_lines, provider = _boq_norm(res.get("lines", [])), res.get("provider", "stub")
    except Exception as e:  # noqa: BLE001, estimator is best-effort
        print(f"[boq] estimator failed: {type(e).__name__}: {e}", flush=True)
    if ext_lines:
        db.add(models.ProjectBOQ(site_id=site_id, source=models.BOQ_EXTERNAL, status=models.BOQ_DRAFT,
                                 created_by=f"estimator:{provider}",
                                 lines=[models.ProjectBOQLine(**l) for l in ext_lines]))
    diff = compare_boqs(norm, ext_lines) if ext_lines else 0.0
    ce.diff_pct = _dec(diff)
    needs_final = diff > models.BOQ_DIFF_THRESHOLD
    _notify(db, site, "boq_submitted", f"CE BOQ submitted ({len(norm)} line(s)).", audience="all")
    if needs_final:
        _notify(db, site, "boq_diff_flagged",
                f"CE and external BOQ differ by {diff:.1f}% (over {models.BOQ_DIFF_THRESHOLD:.0f}%); "
                "a reconciled final BOQ is required.", audience="all")
    db.commit()
    db.refresh(ce)
    return {"ce_boq_id": ce.id, "ce_lines": norm, "external": ext_lines, "external_provider": provider,
            "diff_pct": diff, "threshold": models.BOQ_DIFF_THRESHOLD, "needs_final": needs_final}


def submit_final_boq(db: Session, site_id: int, lines, actor_name: str = "") -> models.ProjectBOQ:
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    if not site.project_type:
        raise SiteError("Select a project type (captive/client) before submitting the final BOQ")
    norm = _boq_norm(lines)
    if not norm:
        raise SiteError("Final BOQ has no valid lines")
    for b in db.execute(select(models.ProjectBOQ).where(
            models.ProjectBOQ.site_id == site_id, models.ProjectBOQ.source == models.BOQ_FINAL,
            models.ProjectBOQ.status == models.BOQ_SUBMITTED)).scalars():
        b.status = models.BOQ_SUPERSEDED
    fin = models.ProjectBOQ(site_id=site_id, source=models.BOQ_FINAL, status=models.BOQ_SUBMITTED,
                            created_by=actor_name, lines=[models.ProjectBOQLine(**l) for l in norm])
    db.add(fin)
    site.stage = models.STAGE_BOQ_REVIEW
    _notify(db, site, "boq_final_submitted",
            f"Final BOQ submitted for spoke + hub approval ({len(norm)} line(s)).", audience="all")
    db.commit()
    db.refresh(fin)
    return fin


def list_boqs(db: Session, site_id: int) -> list[models.ProjectBOQ]:
    return list(db.execute(select(models.ProjectBOQ).where(models.ProjectBOQ.site_id == site_id)
                           .order_by(models.ProjectBOQ.id.desc())).scalars())


def list_boq_pending(db: Session) -> list[models.ProjectBOQ]:
    """Final BOQs awaiting approval (the hub review queue)."""
    return list(db.execute(select(models.ProjectBOQ).where(
        models.ProjectBOQ.source == models.BOQ_FINAL,
        models.ProjectBOQ.status == models.BOQ_SUBMITTED).order_by(models.ProjectBOQ.id.desc())).scalars())


def approve_boq(db: Session, boq_id: int, actor_role: str, actor_name: str) -> models.ProjectBOQ:
    """Two-gate approval: the spoke and a hub supervisor/manager (or admin). Both required."""
    boq = db.get(models.ProjectBOQ, boq_id)
    if boq is None or boq.source != models.BOQ_FINAL:
        raise SiteError("Not a final BOQ")
    if boq.status != models.BOQ_SUBMITTED:
        raise SiteError("This BOQ is not awaiting approval")
    name = actor_name or actor_role
    before_spoke, before_hub = bool(boq.spoke_approved_by), bool(boq.hub_approved_by)
    if actor_role == "admin":
        boq.spoke_approved_by = boq.spoke_approved_by or name
        boq.hub_approved_by = boq.hub_approved_by or name
    elif actor_role in BOQ_SPOKE_APPROVERS:
        boq.spoke_approved_by = name
    elif actor_role in BOQ_HUB_APPROVERS:
        boq.hub_approved_by = name
    else:
        raise SiteError("Only the spokesperson or a hub supervisor/manager can approve a BOQ")
    site = db.get(models.Site, boq.site_id)
    if not before_spoke and boq.spoke_approved_by:
        _notify(db, site, "boq_spoke_approved", f"Final BOQ {boq.code} approved by the spoke.", audience="all")
    if not before_hub and boq.hub_approved_by:
        _notify(db, site, "boq_hub_approved", f"Final BOQ {boq.code} approved by the hub.", audience="all")
    if boq.spoke_approved_by and boq.hub_approved_by:
        boq_lines = [{"material_id": l.material_id, "product_id": l.product_id,
                      "product_name": l.product_name, "phase_seq": l.phase_seq,
                      "total_qty": float(l.total_qty)} for l in boq.lines]
        # Write the operational BOM FIRST: if the site already started, set_bom raises and the whole
        # approval (gates + events) rolls back cleanly rather than leaving a half-approved BOQ.
        set_bom(db, boq.site_id, boq_lines)  # reserve against hub stock (3x buffer surfaces shortfalls)
        boq.status = models.BOQ_APPROVED
        site = db.get(models.Site, boq.site_id)
        site.stage = models.STAGE_BOQ_APPROVED
        _notify(db, site, "boq_approved",
                "Final BOQ fully approved and reserved against hub stock.", audience="all")
        db.commit()
        _safe_stock_check(db, boq.site_id)
    else:
        db.commit()
    db.refresh(boq)
    return boq


def request_boq_change(db: Session, site_id: int, note: str, actor_name: str) -> models.BOQChangeRequest:
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    latest = db.execute(select(models.ProjectBOQ).where(
        models.ProjectBOQ.site_id == site_id, models.ProjectBOQ.source == models.BOQ_FINAL)
        .order_by(models.ProjectBOQ.id.desc())).scalars().first()
    cr = models.BOQChangeRequest(site_id=site_id, boq_id=latest.id if latest else 0,
                                 note=note.strip(), requested_by=actor_name)
    db.add(cr)
    _notify(db, site, "boq_change_requested",
            f"Hub requested a BOQ change: {note.strip()[:180]}", audience="field")
    db.commit()
    db.refresh(cr)
    return cr


def list_boq_changes(db: Session, site_id: int | None = None, status: str | None = None) -> list[models.BOQChangeRequest]:
    stmt = select(models.BOQChangeRequest).order_by(models.BOQChangeRequest.id.desc())
    if site_id is not None:
        stmt = stmt.where(models.BOQChangeRequest.site_id == site_id)
    if status:
        stmt = stmt.where(models.BOQChangeRequest.status == status)
    return list(db.execute(stmt).scalars())


def ack_boq_change(db: Session, req_id: int, actor_role: str, actor_name: str) -> models.BOQChangeRequest:
    """A hub-requested BOQ change needs both the spoke and the CE to acknowledge; then the BOQ reopens."""
    cr = db.get(models.BOQChangeRequest, req_id)
    if cr is None:
        raise SiteError(f"Unknown change request: {req_id}")
    if cr.status != "pending":
        raise SiteError("This change request is already resolved")
    if actor_role == "admin":
        cr.spoke_acked = cr.ce_acked = True
    elif actor_role == "spokesperson":
        cr.spoke_acked = True
    elif actor_role == "civil_engineer":
        cr.ce_acked = True
    else:
        raise SiteError("Only the spokesperson and the civil engineer can acknowledge a change request")
    site = db.get(models.Site, cr.site_id)
    if cr.spoke_acked and cr.ce_acked:
        cr.status = "resolved"
        cr.resolved_at = db.execute(select(func.now())).scalar()
        for b in db.execute(select(models.ProjectBOQ).where(
                models.ProjectBOQ.site_id == cr.site_id, models.ProjectBOQ.source == models.BOQ_FINAL,
                models.ProjectBOQ.status == models.BOQ_APPROVED)).scalars():
            b.status = models.BOQ_SUPERSEDED
        site.stage = models.STAGE_BOQ_REVIEW
        _notify(db, site, "boq_change_ack",
                "BOQ change acknowledged by spoke + CE; the BOQ is reopened for revision.", audience="all")
    db.commit()
    db.refresh(cr)
    return cr


def boq_stock_check(db: Session, site_id: int, *, notify: bool = False) -> list[dict]:
    """Compare the approved BOQ's product demand against current hub stock; flag low/out-of-stock."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    req: dict[str, dict] = {}
    for l in site.bom_lines:
        if not l.product_id:
            continue
        r = req.setdefault(l.product_id, {"product_name": l.product_name or l.material_id, "required": 0.0})
        r["required"] += float(l.total_qty)
    rows = []
    for pid, r in req.items():
        st = inventory_client.get_product_stock(pid)
        on_hand = float(st["on_hand"]) if st else 0.0
        available = float(st["available"]) if st else 0.0
        status = "out" if available <= 0 else ("low" if available < r["required"] else "ok")
        rows.append({"product_id": pid, "product_name": r["product_name"], "required": round(r["required"], 3),
                     "on_hand": on_hand, "available": available, "status": status})
        if notify and status == "out":
            _notify(db, site, "out_of_stock",
                    f"{r['product_name']} is out of stock at the hub for this project.", audience="all")
        elif notify and status == "low":
            _notify(db, site, "low_stock",
                    f"{r['product_name']} is low at the hub ({available:g} available, {r['required']:g} needed).",
                    audience="all")
    if notify:
        db.commit()
    return sorted(rows, key=lambda x: {"out": 0, "low": 1, "ok": 2}[x["status"]])


def _safe_stock_check(db: Session, site_id: int) -> None:
    try:
        boq_stock_check(db, site_id, notify=True)
    except Exception as e:  # noqa: BLE001
        print(f"[boq] stock-check failed for SITE-{site_id}: {type(e).__name__}: {e}", flush=True)


# ---- Budget + finance ----

def compute_budget(db: Session, site_id: int) -> dict:
    """Price the project's operational BOM (approved BOQ) at the consumer's tier -> a budget total."""
    from . import pricing_client
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    tier = site.consumer.tier if site.consumer else None
    items: dict[str, float] = {}
    for l in site.bom_lines:
        if l.product_id:
            items[l.product_id] = items.get(l.product_id, 0.0) + float(l.total_qty)
    if not items:
        raise SiteError("Approve a BOQ before computing the budget")
    quote = pricing_client.quote_products(tier, [{"product_id": p, "qty": q} for p, q in items.items()])
    return {"tier": tier, "total": quote.get("total", 0), "lines": quote.get("lines", [])}


def issue_budget(db: Session, site_id: int, actor_name: str = "") -> models.Site:
    """Hub prices the approved BOQ and issues the project budget."""
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    budget = compute_budget(db, site_id)
    site.budget = _dec(budget["total"])
    if site.stage in (models.STAGE_BOQ_APPROVED, models.STAGE_BOQ_REVIEW):
        site.stage = models.STAGE_BUDGETED
    _notify(db, site, "budget_issued",
            f"Hub issued a project budget of Rs {budget['total']:.0f}"
            f"{f' by {actor_name}' if actor_name else ''}.", audience="all")
    db.commit()
    db.refresh(site)
    return site


def list_finance_partners(db: Session, active_only: bool = False) -> list[models.FinancePartner]:
    stmt = select(models.FinancePartner).order_by(models.FinancePartner.name)
    if active_only:
        stmt = stmt.where(models.FinancePartner.active.is_(True))
    return list(db.execute(stmt).scalars())


def create_finance_partner(db: Session, name: str, kind: str = "bank", note: str = "") -> models.FinancePartner:
    if not name.strip():
        raise SiteError("Partner name is required")
    p = models.FinancePartner(name=name.strip(), kind=kind or "bank", note=note or "")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def deactivate_finance_partner(db: Session, partner_id: int) -> None:
    p = db.get(models.FinancePartner, partner_id)
    if p is not None:
        p.active = False
        db.commit()


def get_or_create_project_finance(db: Session, site_id: int) -> models.ProjectFinance:
    site = db.get(models.Site, site_id)
    if site is None:
        raise SiteError(f"Unknown site: SITE-{site_id}")
    pf = db.execute(select(models.ProjectFinance).where(models.ProjectFinance.site_id == site_id)).scalars().first()
    if pf is None:
        pf = models.ProjectFinance(site_id=site_id, status=models.FIN_PENDING)
        db.add(pf)
        db.commit()
        db.refresh(pf)
    return pf


def list_project_finance(db: Session, status: str | None = None) -> list[models.ProjectFinance]:
    stmt = select(models.ProjectFinance).order_by(models.ProjectFinance.id.desc())
    if status:
        stmt = stmt.where(models.ProjectFinance.status == status)
    return list(db.execute(stmt).scalars())


def update_project_finance(db: Session, site_id: int, *, status: str | None = None,
                           partner_id: int | None = None, amount: float | None = None,
                           remarks: str | None = None, actor_name: str = "") -> models.ProjectFinance:
    """Finance team updates the funding status/partner/amount for a project."""
    pf = get_or_create_project_finance(db, site_id)
    site = db.get(models.Site, site_id)
    if status is not None:
        if status not in models.FINANCE_STATUSES:
            raise SiteError(f"status must be one of {models.FINANCE_STATUSES}")
        pf.status = status
    if partner_id is not None:
        pf.partner_id = partner_id or None
    if amount is not None:
        pf.amount = _dec(amount)
    if remarks is not None:
        pf.remarks = remarks
    pf.handled_by = actor_name or pf.handled_by
    if pf.status == models.FIN_APPROVED:
        pf.decided_at = db.execute(select(func.now())).scalar()
        if site.stage in (models.STAGE_BUDGETED, models.STAGE_FINANCING, models.STAGE_BOQ_APPROVED):
            site.stage = models.STAGE_FINANCE_APPROVED
        _notify(db, site, "finance_approved",
                f"Finance approved for this project{f' via partner' if pf.partner_id else ''}.", audience="all")
    elif pf.status == models.FIN_REJECTED:
        pf.decided_at = db.execute(select(func.now())).scalar()
        _notify(db, site, "finance_rejected", "Finance was declined for this project.", audience="all")
    elif pf.status == models.FIN_IN_PROGRESS and site.stage == models.STAGE_BUDGETED:
        site.stage = models.STAGE_FINANCING
    db.commit()
    db.refresh(pf)
    return pf


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


# ---- Dispatch (hub to site) for a phase ----

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
    affected dispatches (partial/pending to dispatched). Idempotent: already-dispatched lines are skipped.
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
    """Civil-engineer action: mark a phase done to trigger dispatch of the next phase (JIT)."""
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


def confirm_receipt(db: Session, dispatch_id: int, actor_role: str, actor_name: str) -> models.Dispatch:
    """The CE/spoke (or hub staff) confirms the stock reached the site; feeds back into dispatch status.

    Customers never confirm; they only track progress. The confirmation is surfaced to everyone
    (audience 'all') so the customer sees the delivery as confirmed on their timeline."""
    d = db.get(models.Dispatch, dispatch_id)
    if d is None:
        raise SiteError(f"Unknown dispatch: {dispatch_id}")
    if actor_role not in ("spokesperson", "architect", "civil_engineer",
                          "hub_supervisor", "hub_manager", "admin"):
        raise SiteError("Only the spoke/CE or hub staff can confirm a delivery")
    if d.status not in (models.DSP_DISPATCHED, models.DSP_RECEIVED):
        raise SiteError("Only a fully-delivered shipment can be confirmed (shortfalls are still pending)")
    site = db.get(models.Site, d.site_id)
    if d.received_at is None:
        d.received_at = db.execute(select(func.now())).scalar()
        d.status = models.DSP_RECEIVED
        _notify(db, site, "received",
                f"Phase {d.phase_seq} ({_PHASE_NAME.get(d.phase_seq, '')}) materials delivery confirmed"
                f"{f' by {actor_name}' if actor_name else ''}.", phase_seq=d.phase_seq, audience="all")
    db.commit()
    db.refresh(d)
    _release_escrow_for_site(db, site)
    return d


def _release_escrow_for_site(db: Session, site: models.Site) -> None:
    """Escrow: release the delivered fraction of the project's held payment. Best-effort - a payment
    outage must never block a delivery confirmation. Fraction = confirmed deliveries / planned phases."""
    if site is None:
        return
    total_phases = len(site.phases) or 0
    if total_phases == 0:
        return
    confirmed = sum(1 for x in site.dispatches if x.status == models.DSP_RECEIVED)
    fraction = min(1.0, confirmed / total_phases)
    try:
        from . import payment_client
        payment_client.release_escrow(site.code, fraction)
    except Exception as e:  # noqa: BLE001, escrow release is best-effort
        print(f"[escrow] release failed for {site.code}: {type(e).__name__}: {e}", flush=True)


def run_scheduler_tick(db: Session, *, today=None, notice_days: int = 3, dispatch_days: int = 2,
                       confirm_reminder_days: int | None = None) -> dict:
    """JIT scheduler: for each active site, warn the field team ~3 days before the current phase's end
    date and pre-dispatch the next phase's materials ~1 day later, so construction is never halted.
    Also nudges the field team when a delivered shipment stays unconfirmed for too long."""
    from datetime import date as _date, datetime as _dt, timezone as _tz
    today = today or _date.today()
    if confirm_reminder_days is None:
        confirm_reminder_days = settings.confirm_reminder_days
    actions: list[dict] = []

    # Nudge: shipments delivered but not confirmed by the customer for > N days.
    now = _dt.now(_tz.utc)
    for d in db.execute(select(models.Dispatch).where(
            models.Dispatch.status == models.DSP_DISPATCHED)).scalars():
        if d.created_at is None:
            continue
        age = (now - d.created_at).days
        if age < confirm_reminder_days:
            continue
        already = db.execute(select(models.Notification).where(
            models.Notification.site_id == d.site_id,
            models.Notification.phase_seq == d.phase_seq,
            models.Notification.kind == "confirm_reminder")).first()
        if already:
            continue
        site = db.get(models.Site, d.site_id)
        _notify(db, site, "confirm_reminder",
                f"Phase {d.phase_seq} ({_PHASE_NAME.get(d.phase_seq, '')}) materials were dispatched "
                f"{age} day(s) ago but the delivery is not yet confirmed. Please confirm once the stock "
                f"reaches the site.", phase_seq=d.phase_seq, audience="field")
        actions.append({"site": site.code, "kind": "confirm_reminder", "phase": d.phase_seq})

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
