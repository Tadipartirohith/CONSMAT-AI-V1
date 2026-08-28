"""Field REST API: spokes, consumers, sites, plans, and phase-driven dispatch."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import bom, inventory_client, models, schemas, service
from ..auth import current_user, require_role
from ..db import get_db

# Reads: any authenticated user. Field actions: the spoke team (spokesperson/architect/site engineer).
# Kept as one field role-set since the spoke-app blends the three personas; admin bypasses.
FIELD = require_role("spokesperson", "architect", "site_engineer")
# Backfill is a dispatch action either side can trigger after a replenishment.
BACKFILL = require_role("spokesperson", "architect", "site_engineer", "hub_supervisor", "hub_manager")
# Scheduling (phase dates) + oversight: the field team plus the hub, since the manager sits above the spoke.
SCHEDULE = require_role("spokesperson", "architect", "site_engineer", "hub_supervisor", "hub_manager")
# Enquiry queue: the spoke sees its own leads; hub supervisor/manager see hub-routed (unserved) leads.
ENQUIRY = require_role("spokesperson", "architect", "site_engineer", "hub_supervisor", "hub_manager")
# The design is the architect's authority: only the architect uploads it (the SE/spoke view + download).
ARCHITECT = require_role("architect")
router = APIRouter(tags=["sites"], dependencies=[Depends(current_user)])

# Public (unauthenticated) endpoints - a prospective customer's enquiry before they have an account.
public_router = APIRouter(tags=["public"])


@public_router.post("/enquiries", response_model=schemas.EnquiryResult, status_code=201)
def create_enquiry(body: schemas.EnquiryIn, db: Session = Depends(get_db)):
    """Public enquiry: routed by geofence to the covering spoke, else to the hub supervisor queue."""
    try:
        return service.create_enquiry(db, name=body.name, phone=body.phone, email=body.email,
                                      location=body.location, message=body.message)
    except service.SiteError as e:
        raise HTTPException(409, str(e))


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


@router.get("/spokes", response_model=list[schemas.SpokeDetailOut])
def list_spokes(db: Session = Depends(get_db)):
    spokes = db.execute(select(models.Spoke).order_by(models.Spoke.name)).scalars().all()
    return [schemas.SpokeDetailOut.from_spoke(s) for s in spokes]


@router.get("/spokes/{spoke_id}", response_model=schemas.SpokeDetailOut)
def get_spoke(spoke_id: str, db: Session = Depends(get_db)):
    spoke = db.get(models.Spoke, spoke_id)
    if spoke is None:
        raise HTTPException(404, f"Unknown spoke: {spoke_id}")
    return schemas.SpokeDetailOut.from_spoke(spoke)


@router.post("/spokes/{spoke_id}/areas", dependencies=[Depends(SCHEDULE)])
def change_area(spoke_id: str, body: schemas.AreaIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Add/remove a coverage region. A spokesperson's change needs supervisor/manager approval; a
    supervisor/manager change applies directly."""
    return _run(service.change_area, db=db, spoke_id=spoke_id, area=body.area, action=body.action,
                actor_role=user.get("role", ""), actor_name=user.get("name", ""))


@router.get("/area-requests", response_model=list[schemas.AreaRequestOut])
def list_area_requests(status: str | None = None, db: Session = Depends(get_db)):
    """Coverage-region change requests (supervisor/manager review queue)."""
    return service.list_area_requests(db, status)


@router.post("/area-requests/{req_id}/decide", response_model=schemas.AreaRequestOut)
def decide_area_request(req_id: int, body: schemas.DecideChangeIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Supervisor/manager approves or rejects a spoke's coverage change."""
    return _run(service.decide_area_request, db=db, req_id=req_id, approve=body.approve,
                actor_role=user.get("role", ""), actor_name=user.get("name", ""))


@router.get("/spokes/{spoke_id}/sites")
def territory_sites(spoke_id: str, db: Session = Depends(get_db)):
    return _run(service.territory_sites, db=db, spoke_id=spoke_id)


@router.get("/spokes/{spoke_id}/dashboard")
def spoke_dashboard(spoke_id: str, db: Session = Depends(get_db)):
    return _run(service.spoke_dashboard, db=db, spoke_id=spoke_id)


@router.post("/consumers", response_model=schemas.ConsumerOut, status_code=201, dependencies=[Depends(FIELD)])
def create_consumer(body: schemas.ConsumerIn, db: Session = Depends(get_db)):
    return _run(service.create_consumer, db=db, name=body.name, tier=body.tier,
                spoke_id=body.spoke_id, phone=body.phone, fund_type=body.fund_type)


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
                  location=body.location, phone=body.phone, email=body.email, fund_type=body.fund_type)
    c, s = result["consumer"], result["spoke"]
    return {
        "consumer": {"id": c.id, "name": c.name, "tier": c.tier, "phone": c.phone,
                     "spoke_id": c.spoke_id, "fund_type": c.fund_type},
        "assigned_spoke": {"id": s.id, "name": s.name},
        "login": result.get("login"),
    }


# ---- sites ----
@router.post("/sites", response_model=schemas.SiteOut, status_code=201, dependencies=[Depends(FIELD)])
def create_site(body: schemas.SiteIn, db: Session = Depends(get_db)):
    return _run(service.create_site, db=db, consumer_id=body.consumer_id, label=body.label,
                location=body.location, area_sqft=body.area_sqft, floors=body.floors,
                construction_type=body.construction_type, project_type=body.project_type)


@router.patch("/sites/{site_id}", response_model=schemas.SiteOut, dependencies=[Depends(FIELD)])
def update_site(site_id: int, body: schemas.SiteUpdate, db: Session = Depends(get_db)):
    """Set/change a project's financing type (captive|client) or lifecycle stage."""
    return _run(service.update_site, db=db, site_id=site_id, project_type=body.project_type,
                stage=body.stage)


@router.get("/sites", response_model=list[schemas.SiteOut])
def list_sites(db: Session = Depends(get_db)):
    return service.list_sites(db)


# ---- Enquiries (spoke sees its own; hub sees hub-routed leads) ----
@router.get("/enquiries", response_model=list[schemas.EnquiryOut], dependencies=[Depends(ENQUIRY)])
def list_enquiries(spoke_id: str | None = None, routed_to: str | None = None,
                   status: str | None = None, db: Session = Depends(get_db)):
    return service.list_enquiries(db, spoke_id=spoke_id, routed_to=routed_to, status=status)


@router.patch("/enquiries/{enquiry_id}", response_model=schemas.EnquiryOut, dependencies=[Depends(ENQUIRY)])
def update_enquiry(enquiry_id: int, body: schemas.EnquiryUpdate, user: dict = Depends(current_user),
                   db: Session = Depends(get_db)):
    return _run(service.update_enquiry, db=db, enquiry_id=enquiry_id, status=body.status,
                handled_by=user.get("name", ""))


# ---- Project documents (design / BOQ files) ----
@router.post("/sites/{site_id}/documents", response_model=schemas.ProjectDocumentOut,
             status_code=201, dependencies=[Depends(ARCHITECT)])
async def upload_document(site_id: int, file: UploadFile = File(...), kind: str = Form("design"),
                          note: str = Form(""), user: dict = Depends(current_user),
                          db: Session = Depends(get_db)):
    """Architect uploads a design (CAD/pdf), or a BOQ document, attached to the project."""
    data = await file.read()
    return _run(service.add_document, db=db, site_id=site_id, kind=kind, filename=file.filename or "file",
                content_type=file.content_type or "", data=data,
                uploaded_by_role=user.get("role", ""), uploaded_by=user.get("name", ""), note=note)


@router.get("/sites/{site_id}/documents", response_model=list[schemas.ProjectDocumentOut])
def list_documents(site_id: int, kind: str | None = None, db: Session = Depends(get_db)):
    return service.list_documents(db, site_id, kind)


@router.get("/documents/{doc_id}")
def download_document(doc_id: int, db: Session = Depends(get_db)):
    doc = service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(404, f"Unknown document: {doc_id}")
    return Response(content=doc.data, media_type=doc.content_type or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'})


# ---- BOQ: SE build + external compare + reconcile + approve + stock check ----
BOQ_APPROVE = require_role("spokesperson", "hub_supervisor", "hub_manager")
HUB = require_role("hub_supervisor", "hub_manager")


@router.post("/sites/{site_id}/boq/submit", dependencies=[Depends(FIELD)])
def submit_boq(site_id: int, body: schemas.SetBomIn, user: dict = Depends(current_user),
               db: Session = Depends(get_db)):
    """SE submits a BOQ; the external app returns a second BOQ and we compare (>5% => final BOQ needed)."""
    return _run(service.submit_boq, db=db, site_id=site_id, lines=body.lines, actor_name=user.get("name", ""))


@router.post("/sites/{site_id}/boq/final", response_model=schemas.ProjectBOQOut, dependencies=[Depends(FIELD)])
def submit_final_boq(site_id: int, body: schemas.SetBomIn, user: dict = Depends(current_user),
                     db: Session = Depends(get_db)):
    """Submit the reconciled final BOQ for spoke + hub approval."""
    return _run(service.submit_final_boq, db=db, site_id=site_id, lines=body.lines, actor_name=user.get("name", ""))


@router.get("/sites/{site_id}/boqs", response_model=list[schemas.ProjectBOQOut])
def list_boqs(site_id: int, db: Session = Depends(get_db)):
    return service.list_boqs(db, site_id)


@router.get("/boq-pending", response_model=list[schemas.ProjectBOQOut])
def list_boq_pending(db: Session = Depends(get_db)):
    """Final BOQs awaiting approval (hub review queue)."""
    return service.list_boq_pending(db)


@router.post("/boqs/{boq_id}/approve", response_model=schemas.ProjectBOQOut, dependencies=[Depends(BOQ_APPROVE)])
def approve_boq(boq_id: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Record this actor's approval gate (spoke or hub). Both are required to finalize."""
    return _run(service.approve_boq, db=db, boq_id=boq_id, actor_role=user.get("role", ""),
                actor_name=user.get("name", ""))


@router.post("/sites/{site_id}/boq-change", response_model=schemas.BOQChangeOut, dependencies=[Depends(HUB)])
def request_boq_change(site_id: int, body: schemas.BOQChangeIn, user: dict = Depends(current_user),
                       db: Session = Depends(get_db)):
    """Hub asks for a BOQ change; needs the spoke and the SE to acknowledge."""
    return _run(service.request_boq_change, db=db, site_id=site_id, note=body.note,
                actor_name=user.get("name", ""))


@router.get("/boq-changes", response_model=list[schemas.BOQChangeOut])
def list_boq_changes(site_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    return service.list_boq_changes(db, site_id=site_id, status=status)


@router.post("/boq-changes/{req_id}/ack", response_model=schemas.BOQChangeOut, dependencies=[Depends(FIELD)])
def ack_boq_change(req_id: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    return _run(service.ack_boq_change, db=db, req_id=req_id, actor_role=user.get("role", ""),
                actor_name=user.get("name", ""))


@router.get("/sites/{site_id}/boq-stock-check")
def boq_stock_check(site_id: int, db: Session = Depends(get_db)):
    """Approved-BOQ demand vs current hub stock (per product); flags low/out-of-stock."""
    return _run(service.boq_stock_check, db=db, site_id=site_id)


# ---- Budget + finance ----
FIN = require_role("finance", "hub_supervisor", "hub_manager", "spokesperson")


@router.get("/sites/{site_id}/budget")
def preview_budget(site_id: int, db: Session = Depends(get_db)):
    """Price the approved BOQ at the consumer's tier (budget preview)."""
    return _run(service.compute_budget, db=db, site_id=site_id)


@router.post("/sites/{site_id}/budget/issue", response_model=schemas.SiteOut, dependencies=[Depends(HUB)])
def issue_budget(site_id: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Hub issues the project budget from the priced approved BOQ."""
    return _run(service.issue_budget, db=db, site_id=site_id, actor_name=user.get("name", ""))


@router.get("/finance-partners", response_model=list[schemas.FinancePartnerOut])
def list_finance_partners(active_only: bool = False, db: Session = Depends(get_db)):
    return service.list_finance_partners(db, active_only=active_only)


@router.post("/finance-partners", response_model=schemas.FinancePartnerOut, status_code=201, dependencies=[Depends(FIN)])
def create_finance_partner(body: schemas.FinancePartnerIn, db: Session = Depends(get_db)):
    return _run(service.create_finance_partner, db=db, name=body.name, kind=body.kind, note=body.note)


@router.delete("/finance-partners/{partner_id}", status_code=204, dependencies=[Depends(FIN)])
def deactivate_finance_partner(partner_id: int, db: Session = Depends(get_db)):
    service.deactivate_finance_partner(db, partner_id)


@router.get("/finance", response_model=list[schemas.ProjectFinanceOut])
def list_project_finance(status: str | None = None, db: Session = Depends(get_db)):
    return service.list_project_finance(db, status=status)


@router.get("/sites/{site_id}/finance", response_model=schemas.ProjectFinanceOut)
def get_project_finance(site_id: int, db: Session = Depends(get_db)):
    return _run(service.get_or_create_project_finance, db=db, site_id=site_id)


@router.patch("/sites/{site_id}/finance", response_model=schemas.ProjectFinanceOut, dependencies=[Depends(FIN)])
def update_project_finance(site_id: int, body: schemas.ProjectFinanceUpdate,
                           user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Finance team updates a project's funding status/partner/amount/remarks."""
    return _run(service.update_project_finance, db=db, site_id=site_id, status=body.status,
                eligibility=body.eligibility, partner_id=body.partner_id, amount=body.amount,
                remarks=body.remarks, actor_name=user.get("name", ""))


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


@router.post("/sites/{site_id}/bom", response_model=schemas.SiteOut, dependencies=[Depends(SCHEDULE)])
def set_bom(site_id: int, body: schemas.SetBomIn, db: Session = Depends(get_db)):
    """SE/spoke (or the hub, as final authority) enters/edits the product BOM. Editable before start."""
    return _run(service.set_bom, db=db, site_id=site_id, lines=[l.model_dump() for l in body.lines])


@router.get("/sites/{site_id}/phase-needs")
def phase_needs(site_id: int, db: Session = Depends(get_db)):
    """Per-phase product requirements (the BOM sliced across the 9 phases)."""
    return _run(service.phase_needs, db=db, site_id=site_id)


@router.post("/sites/{site_id}/phases/{seq}/dates", dependencies=[Depends(SCHEDULE)])
def set_phase_dates(site_id: int, seq: int, body: schemas.PhaseDatesIn,
                    user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Set/modify a phase's planned start & end. A site engineer's end-date change needs approval."""
    return _run(service.set_phase_dates, db=db, site_id=site_id, seq=seq, start=body.start,
                end=body.end, actor_role=user.get("role", ""), actor_name=user.get("name", ""),
                remarks=body.remarks)


@router.get("/phase-changes", response_model=list[schemas.PhaseDateChangeOut])
def list_phase_changes(status: str | None = None, site_id: int | None = None,
                       db: Session = Depends(get_db)):
    """Phase end-date change requests (spoke/manager review queue). Filter by status/site."""
    return service.list_phase_changes(db, status=status, site_id=site_id)


@router.post("/phase-changes/{change_id}/decide", response_model=schemas.PhaseDateChangeOut)
def decide_phase_change(change_id: int, body: schemas.DecideChangeIn,
                        user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Spoke or hub manager approves/rejects a site engineer's phase end-date change."""
    return _run(service.decide_phase_change, db=db, change_id=change_id, approve=body.approve,
                actor_role=user.get("role", ""), actor_name=user.get("name", ""))


@router.post("/sites/{site_id}/start", response_model=schemas.DispatchOut, dependencies=[Depends(FIELD)])
def start_site(site_id: int, db: Session = Depends(get_db)):
    """Begin construction: phase 1 in-progress + dispatch its materials."""
    return _run(service.start_site, db=db, site_id=site_id)


@router.post("/sites/{site_id}/phases/{seq}/complete", dependencies=[Depends(FIELD)])
def complete_phase(site_id: int, seq: int, db: Session = Depends(get_db)):
    """Site engineer: mark a phase complete to triggers JIT dispatch of the next phase."""
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
                       consumer_id: str | None = None, audience: str | None = None,
                       unread_only: bool = False, db: Session = Depends(get_db)):
    """Notifications/events. Field/hub see everything; pass consumer_id for a customer's own project
    events (audience 'all'/'consumer'); pass audience (e.g. 'finance') for a role feed (that + 'all')."""
    if consumer_id:
        audiences = ("all", "consumer")
    elif audience:
        audiences = (audience, "all")
    else:
        audiences = None
    return service.list_notifications(db, spoke_id=spoke_id, site_id=site_id, consumer_id=consumer_id,
                                      audiences=audiences, unread_only=unread_only)


@router.post("/notifications/{notif_id}/read", response_model=schemas.NotificationOut)
def read_notification(notif_id: int, db: Session = Depends(get_db)):
    return _run(service.mark_notification_read, db=db, notif_id=notif_id)


@router.post("/notifications/read-all")
def read_all_notifications(consumer_id: str | None = None, spoke_id: str | None = None,
                           db: Session = Depends(get_db)):
    """Mark all of a customer's (consumer_id) or a spoke's (spoke_id) notifications read."""
    if spoke_id:
        return service.mark_all_read_spoke(db, spoke_id)
    return service.mark_all_read(db, consumer_id or "")


@router.post("/dispatches/{dispatch_id}/confirm", response_model=schemas.DispatchOut, dependencies=[Depends(BACKFILL)])
def confirm_receipt(dispatch_id: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """SE/spoke (or hub staff) confirms a delivery reached the site -> dispatch status 'received'."""
    return _run(service.confirm_receipt, db=db, dispatch_id=dispatch_id,
                actor_role=user.get("role", ""), actor_name=user.get("name", ""))


@router.post("/scheduler/tick", dependencies=[Depends(BACKFILL)])
def scheduler_tick(db: Session = Depends(get_db)):
    """Manually run one JIT scheduler pass (the same logic runs automatically in the background)."""
    return service.run_scheduler_tick(db)
