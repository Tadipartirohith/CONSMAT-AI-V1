"""Payment REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, service
from ..auth import current_user, require_role
from ..config import payment_config
from ..db import get_db

# A payer (consumer) or hub/field staff may initiate a payment; reads for any authenticated user.
PAYER = require_role("consumer", "hub_manager", "hub_supervisor", "spokesperson")
# Escrow release is triggered by the site-service (role=service) on delivery confirmation, or by hub/field staff.
RELEASE = require_role("service", "hub_manager", "hub_supervisor", "spokesperson", "site_engineer", "architect")
# Billing: hub/spoke staff issue client progress invoices and mark them paid.
BILLER = require_role("hub_manager", "hub_supervisor", "spokesperson", "site_engineer", "architect")
router = APIRouter(tags=["payments"], dependencies=[Depends(current_user)])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.PaymentError as e:
        raise HTTPException(409, str(e))


@router.get("/payments/config", response_model=schemas.ConfigOut)
def config():
    """Active gateway (non-secret) for the UI."""
    cfg = payment_config()
    return {"provider": cfg.get("provider", "mock"), "currency": cfg.get("currency", "INR"),
            "enabled": cfg.get("enabled", True)}


@router.post("/payments", response_model=schemas.PaymentOut, status_code=201, dependencies=[Depends(PAYER)])
def create_payment(body: schemas.PaymentIn, db: Session = Depends(get_db)):
    return _run(service.create_payment, db=db, ref=body.ref, consumer_id=body.consumer_id,
                amount=body.amount, currency=body.currency, note=body.note, escrow=body.escrow)


@router.post("/payments/release", dependencies=[Depends(RELEASE)])
def release_escrow(body: schemas.ReleaseIn, db: Session = Depends(get_db)):
    """Release held escrow for a project ref up to `fraction` (deliveries confirmed at the site)."""
    return service.release_for_ref(db, body.ref, body.fraction)


@router.post("/payments/{payment_id}/confirm", response_model=schemas.PaymentOut, dependencies=[Depends(PAYER)])
def confirm_payment(payment_id: int, db: Session = Depends(get_db)):
    return _run(service.confirm_payment, db=db, payment_id=payment_id)


@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(consumer_id: str | None = None, ref: str | None = None, db: Session = Depends(get_db)):
    return service.list_payments(db, consumer_id=consumer_id, ref=ref)


@router.get("/payments/{payment_id}", response_model=schemas.PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    pay = service.get_payment(db, payment_id)
    if pay is None:
        raise HTTPException(404, f"Unknown payment: PAY-{payment_id}")
    return pay


# ---- Client progress invoices (billing) - PDF stage 13 ----

@router.get("/invoices", response_model=list[schemas.InvoiceOut])
def list_invoices(ref: str | None = None, consumer_id: str | None = None, db: Session = Depends(get_db)):
    return service.list_invoices(db, ref=ref, consumer_id=consumer_id)


@router.post("/invoices", response_model=schemas.InvoiceOut, status_code=201, dependencies=[Depends(BILLER)])
def create_invoice(body: schemas.InvoiceIn, db: Session = Depends(get_db)):
    return _run(service.create_invoice, db=db, ref=body.ref, consumer_id=body.consumer_id,
                amount=body.amount, phase_seq=body.phase_seq, title=body.title, note=body.note,
                currency=body.currency)


@router.post("/invoices/{invoice_id}/pay", response_model=schemas.InvoiceOut, dependencies=[Depends(BILLER)])
def pay_invoice(invoice_id: int, payment_id: int | None = None, db: Session = Depends(get_db)):
    return _run(service.mark_invoice_paid, db=db, invoice_id=invoice_id, payment_id=payment_id)
