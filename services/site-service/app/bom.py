"""Bill-of-materials + 9-phase demand distribution (decision D4).

`compute_bom` turns a site's area/floors/construction-type into per-material totals using the
`per_sqft` coefficients fetched from inventory-service. `phase_slice` distributes each material's total
across the 9 phases via a tunable weight matrix (Q2), completing a phase triggers dispatch of the next
phase's slice.
"""
from __future__ import annotations

import math

# (seq, name, repeats_per_floor)
PHASES = [
    (1, "Excavation & footing", False),
    (2, "Foundation & plinth beam", False),
    (3, "RCC superstructure", True),
    (4, "Masonry / brickwork", False),
    (5, "Roofing / terrace slab", False),
    (6, "Internal plastering", False),
    (7, "External plastering", False),
    (8, "Flooring & tiling", False),
    (9, "MEP & finishing", False),
]

TYPE_MULT = {"economy": 0.9, "standard": 1.0, "premium": 1.18}

# weight[material][phase_seq]; each material's weights sum to ~1.0. Tunable (Q2).
PHASE_WEIGHTS: dict[str, dict[int, float]] = {
    "cement":    {1: 0.05, 2: 0.15, 3: 0.30, 4: 0.15, 5: 0.10, 6: 0.10, 7: 0.08, 8: 0.07},
    "steel":     {1: 0.05, 2: 0.20, 3: 0.45, 5: 0.30},
    "sand":      {2: 0.10, 3: 0.15, 4: 0.20, 5: 0.10, 6: 0.20, 7: 0.15, 8: 0.10},
    "aggregate": {1: 0.10, 2: 0.20, 3: 0.40, 5: 0.25, 8: 0.05},
    "bricks":    {4: 1.0},
}


def _round(material_id: str, q: float) -> float:
    # cement is sold in whole bags; other materials to 2 dp
    return float(math.ceil(q)) if material_id == "cement" else round(q, 2)


def compute_bom(area_sqft: float, floors: int, construction_type: str,
                per_sqft: dict[str, float]) -> tuple[float, dict[str, float]]:
    """Return (total_area, {material_id: total_qty})."""
    mult = TYPE_MULT.get(construction_type, 1.0)
    total_area = area_sqft * max(1, floors)
    totals: dict[str, float] = {}
    for mid, coeff in per_sqft.items():
        if coeff and coeff > 0:
            totals[mid] = _round(mid, total_area * coeff * mult)
    return total_area, totals


def phase_slice(totals: dict[str, float], phase_seq: int) -> dict[str, float]:
    """Materials (and quantities) required for a given phase."""
    out: dict[str, float] = {}
    for mid, total in totals.items():
        w = PHASE_WEIGHTS.get(mid, {}).get(phase_seq, 0.0)
        if w > 0:
            q = _round(mid, total * w)
            if q > 0:
                out[mid] = q
    return out


def phase_weight(material_id: str, phase_seq: int) -> float:
    return PHASE_WEIGHTS.get(material_id, {}).get(phase_seq, 0.0)


def product_phase_slice(lines: list[dict], phase_seq: int) -> list[dict]:
    """Distribute a product-level BOM (whole-project totals) into a phase's requirement.

    Each line is {product_id, material_id, product_name, total_qty}; the material's phase weight drives
    how much of that product is needed in this phase. Returns lines with a positive `qty`.
    """
    out: list[dict] = []
    for ln in lines:
        w = phase_weight(ln["material_id"], phase_seq)
        if w <= 0:
            continue
        q = _round(ln["material_id"], float(ln["total_qty"]) * w)
        if q > 0:
            out.append({"product_id": ln.get("product_id", ""), "material_id": ln["material_id"],
                        "product_name": ln.get("product_name", ""), "qty": q})
    return out
