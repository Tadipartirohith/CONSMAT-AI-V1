"""Pricing domain: margin-rule CRUD, precedence resolution, and selling-price computation."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import inventory_client, models
from .config import settings


class PricingError(Exception):
    """Invalid pricing operation."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _norm(v: str | None) -> str | None:
    v = (v or "").strip()
    return v or None


# ---- margin rule CRUD ----

def _find_rule(db: Session, material_id: str | None, tier: str | None) -> models.MarginRule | None:
    stmt = select(models.MarginRule)
    stmt = stmt.where(models.MarginRule.material_id.is_(None) if material_id is None
                      else models.MarginRule.material_id == material_id)
    stmt = stmt.where(models.MarginRule.tier.is_(None) if tier is None
                      else models.MarginRule.tier == tier)
    return db.execute(stmt).scalar_one_or_none()


def set_rule(db: Session, material_id: str | None, tier: str | None, margin_pct) -> models.MarginRule:
    """Upsert a margin rule for a (material?, tier?) combination."""
    material_id, tier = _norm(material_id), _norm(tier)
    if tier is not None and tier not in models.CONSUMER_TIERS:
        raise PricingError(f"tier must be one of {models.CONSUMER_TIERS}")
    margin = _dec(margin_pct)
    if margin < 0:
        raise PricingError("margin_pct cannot be negative")
    rule = _find_rule(db, material_id, tier)
    if rule is None:
        rule = models.MarginRule(material_id=material_id, tier=tier, margin_pct=margin)
        db.add(rule)
    else:
        rule.margin_pct = margin
    db.commit()
    db.refresh(rule)
    return rule


def list_rules(db: Session) -> list[models.MarginRule]:
    return list(db.execute(select(models.MarginRule).order_by(models.MarginRule.id)).scalars())


def delete_rule(db: Session, rule_id: int) -> None:
    rule = db.get(models.MarginRule, rule_id)
    if rule is None:
        raise PricingError(f"Unknown rule: {rule_id}")
    db.delete(rule)
    db.commit()


# ---- resolution + pricing ----

def resolve_margin(db: Session, material_id: str, tier: str | None) -> tuple[float, str]:
    """Return (margin_pct, rule_source) using precedence:
    (material, tier) > (material, *) > (*, tier) > (*, *) > service default."""
    tier = _norm(tier)
    for mat, ti, label in [
        (material_id, tier, "material+tier"),
        (material_id, None, "material"),
        (None, tier, "tier"),
        (None, None, "global"),
    ]:
        rule = _find_rule(db, mat, ti)
        if rule is not None:
            return float(rule.margin_pct), label
    return settings.default_margin_pct, "service-default"


def price_material(db: Session, material_id: str, tier: str | None) -> dict:
    """Selling price for one unit of a material at a tier = landed_cost * (1 + margin%)."""
    landed = inventory_client.landed_cost(material_id)
    margin, source = resolve_margin(db, material_id, tier)
    unit_price = round(landed * (1 + margin / 100), 2)
    return {
        "material_id": material_id, "tier": tier, "landed_cost": round(landed, 4),
        "margin_pct": margin, "rule": source, "unit_price": unit_price,
    }


def quote(db: Session, tier: str | None, items: list[dict]) -> dict:
    """Priced quote for a set of {material_id, qty}."""
    lines, total = [], 0.0
    for it in items:
        p = price_material(db, it["material_id"], tier)
        qty = float(it["qty"])
        line_total = round(p["unit_price"] * qty, 2)
        total += line_total
        lines.append({**p, "qty": qty, "line_total": line_total})
    return {"tier": _norm(tier), "lines": lines, "total": round(total, 2)}


def selling_prices(db: Session, tier: str | None) -> dict[str, float]:
    """Map material_id -> unit selling price for every catalog material (feeds procurement /analyze)."""
    out = {}
    for mid in inventory_client.material_ids():
        out[mid] = price_material(db, mid, tier)["unit_price"]
    return out
