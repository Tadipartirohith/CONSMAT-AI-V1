"""Deterministic procurement planning.

Given a demand (materials + quantities), pick the cheapest active vendor for each material from the
market view and compute costs. This is the reliable backbone; the Hub LLM (llm.py) only *advises* on
top of these numbers — it never sets a price. Profitability is computed here when selling prices are
supplied.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from . import service


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def plan(db: Session, demand: list[dict]) -> dict:
    """demand: [{material_id, qty}] -> cheapest-source plan.

    Returns {lines:[...], unavailable:[...], total_cost}. Each line picks the cheapest active vendor
    and flags below_min_qty when the demand is under that vendor's minimum order quantity.
    """
    lines: list[dict] = []
    unavailable: list[str] = []
    total = Decimal("0")
    for d in demand:
        mid = d["material_id"]
        pid = d.get("product_id") or ""
        qty = _dec(d["qty"])
        # A specific product (brand) if requested; otherwise the cheapest brand for the material.
        market = service.product_offers(db, pid) if pid else service.market_prices(db, mid)
        if not market:
            unavailable.append(pid or mid)
            continue
        best = market[0]
        unit_cost = _dec(best["price"])
        line_cost = (qty * unit_cost).quantize(Decimal("0.01"))
        total += line_cost
        lines.append({
            "material_id": mid,
            "product_id": best.get("product_id", ""),
            "product_name": best.get("product_name", ""),
            "brand": best.get("brand", ""),
            "vendor_id": best["vendor_id"],
            "vendor_name": best["vendor_name"],
            "is_hub_self": best["is_hub_self"],
            "qty": float(qty),
            "unit_cost": float(unit_cost),
            "line_cost": float(line_cost),
            "below_min_qty": qty < _dec(best["min_qty"]),
            "alternatives": len(market) - 1,  # other brands/vendors available
        })
    return {"lines": lines, "unavailable": unavailable, "total_cost": float(total)}


def profitability(plan_result: dict, selling_prices: dict | None) -> dict | None:
    """Margin analysis when selling prices are provided (map material_id -> unit selling price)."""
    if not selling_prices:
        return None
    rows = []
    buy_total = Decimal("0")
    sell_total = Decimal("0")
    for ln in plan_result["lines"]:
        mid = ln["material_id"]
        if mid not in selling_prices:
            continue
        qty = _dec(ln["qty"])
        buy = _dec(ln["line_cost"])
        sell = (qty * _dec(selling_prices[mid])).quantize(Decimal("0.01"))
        margin = sell - buy
        buy_total += buy
        sell_total += sell
        rows.append({
            "material_id": mid,
            "buy_cost": float(buy),
            "sell_value": float(sell),
            "margin": float(margin),
            "margin_pct": float((margin / sell * 100).quantize(Decimal("0.1"))) if sell > 0 else None,
            "loss_making": margin <= 0,
        })
    total_margin = sell_total - buy_total
    return {
        "lines": rows,
        "buy_total": float(buy_total),
        "sell_total": float(sell_total),
        "margin_total": float(total_margin),
        "margin_pct": float((total_margin / sell_total * 100).quantize(Decimal("0.1"))) if sell_total > 0 else None,
        "profitable": total_margin > 0,
    }
